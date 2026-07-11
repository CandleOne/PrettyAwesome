/**
 * Tee-Minus routing engine — "the DoorDash dispatcher for on-demand printing".
 *
 * Resolves customer + print-shop locations to coordinates (via the server
 * /geocode endpoint, cached in localStorage), ranks the active print-shop
 * network by proximity + capability, and computes the commission / platform
 * margin / shop payout split for an order.
 *
 * Depends on window.TMAuth (auth.js) for reading accounts.
 * Exposes window.TMRouting.
 */
(function () {
  const GEOCODE_CACHE_KEY = 'teeminus_geocode_cache_v1';
  const API_BASE = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';

  // Revenue model. Tune these to change unit economics across the whole app.
  const PRICING = {
    baseUnitPrice: 18.0, // retail price per garment (USD)
    rushMultiplier: 1.2, // +20% for rush orders
    platformMarginRate: 0.15, // Tee-Minus keeps 15% of the order subtotal
    commissionPerPiece: 0.75, // flat platform commission per garment piece
  };

  function normalizeKey(value) {
    return String(value || '').trim().toLowerCase();
  }

  // Optional offline lookup of 'city, st' -> { lat, lng, formatted }, injected
  // by pages that already load a US-cities dataset (see shop.html). Checked
  // before any network geocoding, so it is instant and rate-limit-free.
  let cityCoordIndex = null;
  function setCityCoordIndex(index) {
    cityCoordIndex = index && typeof index === 'object' ? index : null;
  }
  function lookupCityCoords(location) {
    if (!cityCoordIndex) return null;
    const key = normalizeKey(location);
    if (cityCoordIndex[key]) return cityCoordIndex[key];
    const canonical = key.replace(/\s*,\s*/g, ', ');
    return cityCoordIndex[canonical] || null;
  }

  function readCache() {
    try {
      return JSON.parse(localStorage.getItem(GEOCODE_CACHE_KEY)) || {};
    } catch (error) {
      return {};
    }
  }

  function writeCache(cache) {
    try {
      localStorage.setItem(GEOCODE_CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
      /* storage full or unavailable — ignore, coords just won't cache */
    }
  }

  /**
   * Resolve a "City, ST" or full address string to { lat, lng, formatted }.
   * Results are cached by normalized string to avoid repeat geocode calls.
   */
  async function geocode(location) {
    const key = normalizeKey(location);
    if (!key) return null;

    const cache = readCache();
    if (cache[key]) return cache[key];

    // 1) Offline city index (instant, no network).
    const localHit = lookupCityCoords(location);
    if (localHit) {
      cache[key] = localHit;
      writeCache(cache);
      return localHit;
    }

    // 2) Backend geocoder (supports keyed providers); 3) direct Photon (OSM).
    let coords = await geocodeViaBackend(location);
    if (!coords) coords = await geocodeViaPhoton(location);

    if (coords) {
      cache[key] = coords;
      writeCache(cache);
    }
    return coords;
  }

  async function geocodeViaBackend(location) {
    try {
      const response = await fetch(`${API_BASE}/geocode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: location }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      if (!data.ok) return null;
      const lat = Number(data.lat);
      const lng = Number(data.lng);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      return { lat, lng, formatted: data.formatted || location };
    } catch (error) {
      return null;
    }
  }

  async function geocodeViaPhoton(location) {
    try {
      const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(location)}&limit=1&lang=en`;
      const response = await fetch(url);
      if (!response.ok) return null;
      const data = await response.json();
      const feature = data && data.features && data.features[0];
      if (!feature) return null;
      const [lng, lat] = (feature.geometry && feature.geometry.coordinates) || [];
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
      const p = feature.properties || {};
      const formatted = [p.name, p.city, p.state, p.country].filter(Boolean).join(', ') || location;
      return { lat, lng, formatted };
    } catch (error) {
      return null;
    }
  }

  /** Great-circle distance in miles between two { lat, lng } points. */
  function haversineMiles(a, b) {
    if (!a || !b) return Infinity;
    const R = 3958.8; // Earth radius in miles
    const toRad = (deg) => (deg * Math.PI) / 180;
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const h =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }

  /** All print-shop accounts that are live in the marketplace (verified + activated). */
  function getActivePrintShops() {
    const accounts =
      window.TMAuth && window.TMAuth.readAccounts ? window.TMAuth.readAccounts() : [];
    return accounts.filter(
      (account) =>
        account.role === 'print-shop' &&
        (account.status || 'active') !== 'suspended' &&
        account.printShop &&
        account.printShop.activatedAt,
    );
  }

  /**
   * Break an order down into the Tee-Minus revenue split.
   * shop payout = subtotal - (platform margin + per-piece commission).
   */
  function estimatePricing(options) {
    const opts = options || {};
    const qty = Math.max(0, Number(opts.quantity) || 0);
    let unitPrice = PRICING.baseUnitPrice;
    if (opts.rush) unitPrice *= PRICING.rushMultiplier;

    const subtotal = unitPrice * qty;
    const platformMargin = subtotal * PRICING.platformMarginRate;
    const commission = PRICING.commissionPerPiece * qty;
    const platformRevenue = platformMargin + commission;
    const shopPayout = Math.max(0, subtotal - platformRevenue);

    return {
      quantity: qty,
      unitPrice,
      subtotal,
      platformMargin,
      commission,
      platformRevenue,
      shopPayout,
    };
  }

  /** Score a single shop against an order context. */
  function evaluateShop(shop, context) {
    const details = shop.printShop || {};
    const distance = haversineMiles(context.customerCoords, context.shopCoords);
    const radius = Number(details.serviceRadiusMiles || 0);

    const quantity = Number(context.quantity) || 0;
    // If a shop hasn't set a radius, don't exclude it on distance alone.
    const withinServiceArea = radius > 0 ? distance <= radius : Number.isFinite(distance);
    const meetsMinimum = quantity >= (Number(details.minimumOrderQuantity) || 0);
    // Per-shop capacity ceiling. 0 / unset = no maximum.
    const maxCapacity = Number(details.maximumOrderQuantity) || 0;
    const meetsMaximum = maxCapacity <= 0 || quantity <= maxCapacity;
    const methodOffered =
      !context.fulfillmentMethod ||
      (details.fulfillmentMethods || []).includes(context.fulfillmentMethod);
    const sameDayCapable =
      Boolean(details.sameDayFulfillmentAvailable) &&
      quantity <= (Number(details.sameDayFulfillmentMaxQuantity) || 0);
    const sameDayOk = !context.sameDayRequested || sameDayCapable;

    const reasons = [];
    if (!withinServiceArea) reasons.push('Outside service area');
    if (!meetsMinimum) reasons.push('Below minimum order quantity');
    if (!meetsMaximum) reasons.push('Exceeds maximum order quantity');
    if (!methodOffered) reasons.push('Fulfillment method not offered');
    if (context.sameDayRequested && !sameDayCapable) {
      reasons.push('Cannot meet same-day at this quantity');
    }

    const eligible = withinServiceArea && meetsMinimum && meetsMaximum && methodOffered && sameDayOk;

    return {
      shop,
      shopCoords: context.shopCoords,
      distanceMiles: distance,
      withinServiceArea,
      meetsMinimum,
      meetsMaximum,
      maxCapacity,
      methodOffered,
      sameDayCapable,
      eligible,
      reasons,
    };
  }

  /**
   * Rank the whole active network for an order.
   * context: { customerLocation | customerCoords, quantity, rush,
   *            sameDayRequested, fulfillmentMethod }
   * Returns { customerCoords, results } sorted eligible-first, then nearest-first.
   */
  async function rankShops(context) {
    const ctx = context || {};
    let customerCoords = ctx.customerCoords || null;
    if (!customerCoords && ctx.customerLocation) {
      customerCoords = await geocode(ctx.customerLocation);
    }

    const shops = getActivePrintShops();
    const results = [];
    for (const shop of shops) {
      const shopCoords = await geocode((shop.printShop || {}).location);
      results.push(evaluateShop(shop, { ...ctx, customerCoords, shopCoords }));
    }

    results.sort((a, b) => {
      if (a.eligible !== b.eligible) return a.eligible ? -1 : 1;
      return a.distanceMiles - b.distanceMiles;
    });

    return { customerCoords, results };
  }

  /**
   * Assign an order to the single best eligible shop and price it.
   * Returns { assigned, ranked, pricing }.
   */
  async function assignShop(context) {
    const ranked = await rankShops(context);
    const assigned = ranked.results.find((result) => result.eligible) || null;
    const pricing = estimatePricing({
      quantity: (context || {}).quantity,
      rush: (context || {}).rush,
    });
    return { assigned, ranked, pricing };
  }

  /**
   * Split an order that exceeds any single shop's capacity across multiple
   * nearby shops. Each shop is allocated up to its maximumOrderQuantity
   * (0 = unlimited) and only if the allocation meets its minimumOrderQuantity.
   * Candidates must be within their service area and offer the fulfillment
   * method; the per-shop maximum is satisfied by construction.
   *
   * Returns { customerCoords, segments, allocated, remaining, fullyCovered }.
   * Each segment: { shop, shopId, shopName, location, quantity, distanceMiles,
   *                 sameDayCapable, pricing }.
   */
  async function planSplit(context) {
    const ctx = context || {};
    const totalQuantity = Math.max(0, Number(ctx.quantity) || 0);
    const ranked = await rankShops(ctx);

    // Only shops we could physically route to; ignore the full-order maximum
    // here because we hand each shop a slice no larger than its ceiling.
    const candidates = ranked.results
      .filter((r) => r.withinServiceArea && r.methodOffered && Number.isFinite(r.distanceMiles))
      .sort((a, b) => a.distanceMiles - b.distanceMiles);

    const segments = [];
    let remaining = totalQuantity;

    for (const candidate of candidates) {
      if (remaining <= 0) break;
      const details = candidate.shop.printShop || {};
      const minQty = Number(details.minimumOrderQuantity) || 0;
      const ceiling = candidate.maxCapacity > 0 ? candidate.maxCapacity : remaining;
      const allocation = Math.min(remaining, ceiling);
      // Skip shops whose minimum we can't satisfy with what's left.
      if (allocation < minQty) continue;

      const sameDayMax = Number(details.sameDayFulfillmentMaxQuantity) || 0;
      const sameDayCapable =
        Boolean(details.sameDayFulfillmentAvailable) && allocation <= sameDayMax;

      segments.push({
        shop: candidate.shop,
        shopId: candidate.shop.id,
        shopName: candidate.shop.accountName || candidate.shop.name || 'Print Shop',
        location: details.location || '',
        quantity: allocation,
        distanceMiles: Number.isFinite(candidate.distanceMiles)
          ? Math.round(candidate.distanceMiles * 10) / 10
          : null,
        sameDayCapable,
        pricing: estimatePricing({ quantity: allocation, rush: ctx.rush }),
      });
      remaining -= allocation;
    }

    const allocated = totalQuantity - remaining;
    return {
      customerCoords: ranked.customerCoords,
      segments,
      allocated,
      remaining,
      fullyCovered: remaining <= 0 && segments.length > 0,
    };
  }

  function formatMiles(distance) {
    if (!Number.isFinite(distance)) return 'Distance unavailable';
    if (distance < 0.1) return 'Under 0.1 mi';
    return `${distance.toFixed(distance < 10 ? 1 : 0)} mi away`;
  }

  function formatMoney(amount) {
    const value = Number(amount) || 0;
    return `$${value.toFixed(2)}`;
  }

  window.TMRouting = {
    PRICING,
    geocode,
    setCityCoordIndex,
    haversineMiles,
    getActivePrintShops,
    estimatePricing,
    evaluateShop,
    rankShops,
    assignShop,
    planSplit,
    formatMiles,
    formatMoney,
  };
})();
