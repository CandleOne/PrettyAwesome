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

    try {
      const response = await fetch(`${API_BASE}/geocode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: location }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) return null;

      const coords = {
        lat: Number(data.lat),
        lng: Number(data.lng),
        formatted: data.formatted || location,
      };
      if (!Number.isFinite(coords.lat) || !Number.isFinite(coords.lng)) return null;

      cache[key] = coords;
      writeCache(cache);
      return coords;
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
    if (!methodOffered) reasons.push('Fulfillment method not offered');
    if (context.sameDayRequested && !sameDayCapable) {
      reasons.push('Cannot meet same-day at this quantity');
    }

    const eligible = withinServiceArea && meetsMinimum && methodOffered && sameDayOk;

    return {
      shop,
      shopCoords: context.shopCoords,
      distanceMiles: distance,
      withinServiceArea,
      meetsMinimum,
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
    haversineMiles,
    getActivePrintShops,
    estimatePricing,
    evaluateShop,
    rankShops,
    assignShop,
    formatMiles,
    formatMoney,
  };
})();
