(function () {
  const KEYS = {
    ACCOUNTS: 'teeminus_accounts_v1',
    CURRENT_USER_ID: 'teeminus_current_user_id',
    LAST_REGISTRATION_ID: 'teeminus_last_registration_id',
    ADMIN_SESSION: 'teeminus_admin_session_v1',
    ACCOUNT_DATA_PREFIX: 'teeminus_account_data_v1_',
  };

  const ADMIN = {
    EMAIL: 'admin@teeminus.local',
    PASSWORD: 'admin123',
  };

  function normalize(value) {
    return String(value || '').trim();
  }

  function normalizeEmail(value) {
    return normalize(value).toLowerCase();
  }

  function readAccounts() {
    try {
      const raw = localStorage.getItem(KEYS.ACCOUNTS);
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function writeAccounts(accounts) {
    localStorage.setItem(KEYS.ACCOUNTS, JSON.stringify(accounts));
  }

  function roleLabel(role) {
    return role === 'print-shop' ? 'Print Shop Partner' : 'Customer';
  }

  async function hashPassword(password) {
    const text = String(password || '');

    if (window.crypto && window.crypto.subtle && window.TextEncoder) {
      const data = new TextEncoder().encode(text);
      const digest = await window.crypto.subtle.digest('SHA-256', data);
      const bytes = Array.from(new Uint8Array(digest));
      return bytes.map((b) => b.toString(16).padStart(2, '0')).join('');
    }

    return btoa(unescape(encodeURIComponent(text)));
  }

  async function createAccount(payload) {
    const accounts = readAccounts();
    const email = normalizeEmail(payload.email);
    const accountName = normalize(payload.accountName).toLowerCase();

    if (accounts.some((a) => normalizeEmail(a.email) === email)) {
      return { ok: false, error: 'email-exists' };
    }

    if (accounts.some((a) => normalize(a.accountName).toLowerCase() === accountName)) {
      return { ok: false, error: 'account-name-exists' };
    }

    const passwordHash = await hashPassword(payload.password || '');
    const account = {
      id: `acct_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      createdAt: new Date().toISOString(),
      status: 'active',
      name: normalize(payload.name),
      email,
      role: payload.role,
      accountName: normalize(payload.accountName),
      passwordHash,
      passwordLength: undefined,
      printShop: payload.printShop || null,
    };

    accounts.push(account);
    writeAccounts(accounts);
    setCurrentUserId(account.id);
    sessionStorage.setItem(KEYS.LAST_REGISTRATION_ID, account.id);
    return { ok: true, account };
  }

  function setCurrentUserId(id) {
    if (id) {
      sessionStorage.setItem(KEYS.CURRENT_USER_ID, id);
      return;
    }

    sessionStorage.removeItem(KEYS.CURRENT_USER_ID);
    sessionStorage.removeItem(KEYS.LAST_REGISTRATION_ID);
  }

  function getCurrentUserId() {
    return sessionStorage.getItem(KEYS.CURRENT_USER_ID);
  }

  function getCurrentAccount() {
    const id = getCurrentUserId();
    if (!id) return null;

    return readAccounts().find((a) => a.id === id) || null;
  }

  function getAccountById(id) {
    if (!id) return null;
    return readAccounts().find((a) => a.id === id) || null;
  }

  function emptyAccountData() {
    return {
      addresses: [],
      paymentMethods: [],
      orders: [],
    };
  }

  function makeAccountDataKey(accountId) {
    return `${KEYS.ACCOUNT_DATA_PREFIX}${accountId}`;
  }

  function readAccountData(accountId) {
    if (!accountId) return emptyAccountData();

    try {
      const raw = localStorage.getItem(makeAccountDataKey(accountId));
      const parsed = raw ? JSON.parse(raw) : {};
      return {
        addresses: Array.isArray(parsed.addresses) ? parsed.addresses : [],
        paymentMethods: Array.isArray(parsed.paymentMethods) ? parsed.paymentMethods : [],
        orders: Array.isArray(parsed.orders) ? parsed.orders : [],
      };
    } catch (error) {
      return emptyAccountData();
    }
  }

  function writeAccountData(accountId, data) {
    if (!accountId) return emptyAccountData();

    const normalized = {
      addresses: Array.isArray(data && data.addresses) ? data.addresses : [],
      paymentMethods: Array.isArray(data && data.paymentMethods) ? data.paymentMethods : [],
      orders: Array.isArray(data && data.orders) ? data.orders : [],
    };

    localStorage.setItem(makeAccountDataKey(accountId), JSON.stringify(normalized));
    return normalized;
  }

  function getCurrentAccountData() {
    return readAccountData(getCurrentUserId());
  }

  function updateCurrentAccountData(mutator) {
    const accountId = getCurrentUserId();
    if (!accountId) {
      return { ok: false, error: 'not-signed-in' };
    }

    const current = readAccountData(accountId);
    const next = typeof mutator === 'function' ? mutator(current) : current;
    return { ok: true, data: writeAccountData(accountId, next) };
  }

  function buildAddress(input) {
    const label = normalize(input && input.label);
    const recipient = normalize(input && input.recipient);
    const line1 = normalize(input && input.line1);
    const line2 = normalize(input && input.line2);
    const city = normalize(input && input.city);
    const state = normalize(input && input.state);
    const postalCode = normalize(input && input.postalCode);
    const deliveryNotes = normalize(input && input.deliveryNotes);

    return {
      id: normalize(input && input.id) || `addr_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      label,
      recipient,
      line1,
      line2,
      city,
      state,
      postalCode,
      deliveryNotes,
      isDefault: Boolean(input && input.isDefault),
      createdAt: normalize(input && input.createdAt) || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  function addAddress(accountId, input) {
    const data = readAccountData(accountId);
    const address = buildAddress(input);
    const addresses = data.addresses.map((item) => ({ ...item, isDefault: address.isDefault ? false : Boolean(item.isDefault) }));
    if (!addresses.length) {
      address.isDefault = true;
    }
    addresses.push(address);
    return writeAccountData(accountId, { ...data, addresses });
  }

  function updateAddress(accountId, addressId, updates) {
    const data = readAccountData(accountId);
    const index = data.addresses.findIndex((item) => item.id === addressId);
    if (index === -1) return null;

    const nextAddress = buildAddress({ ...data.addresses[index], ...updates, id: addressId, createdAt: data.addresses[index].createdAt });
    const addresses = data.addresses.map((item, idx) => {
      if (idx !== index) {
        return { ...item, isDefault: nextAddress.isDefault ? false : Boolean(item.isDefault) };
      }
      return nextAddress;
    });
    return writeAccountData(accountId, { ...data, addresses });
  }

  function deleteAddress(accountId, addressId) {
    const data = readAccountData(accountId);
    const removed = data.addresses.find((item) => item.id === addressId);
    const addresses = data.addresses.filter((item) => item.id !== addressId);
    if (removed && removed.isDefault && addresses.length) {
      addresses[0] = { ...addresses[0], isDefault: true, updatedAt: new Date().toISOString() };
    }
    return writeAccountData(accountId, { ...data, addresses });
  }

  function buildPaymentMethod(input) {
    const brand = normalize(input && input.brand) || 'Card';
    const cardholder = normalize(input && input.cardholder);
    const last4 = normalize(input && input.last4).slice(-4);
    const expMonth = normalize(input && input.expMonth);
    const expYear = normalize(input && input.expYear);

    return {
      id: normalize(input && input.id) || `pay_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      brand,
      cardholder,
      last4,
      expMonth,
      expYear,
      billingZip: normalize(input && input.billingZip),
      nickname: normalize(input && input.nickname),
      isDefault: Boolean(input && input.isDefault),
      createdAt: normalize(input && input.createdAt) || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  function addPaymentMethod(accountId, input) {
    const data = readAccountData(accountId);
    const paymentMethod = buildPaymentMethod(input);
    const paymentMethods = data.paymentMethods.map((item) => ({ ...item, isDefault: paymentMethod.isDefault ? false : Boolean(item.isDefault) }));
    if (!paymentMethods.length) {
      paymentMethod.isDefault = true;
    }
    paymentMethods.push(paymentMethod);
    return writeAccountData(accountId, { ...data, paymentMethods });
  }

  function updatePaymentMethod(accountId, paymentMethodId, updates) {
    const data = readAccountData(accountId);
    const index = data.paymentMethods.findIndex((item) => item.id === paymentMethodId);
    if (index === -1) return null;

    const nextPaymentMethod = buildPaymentMethod({
      ...data.paymentMethods[index],
      ...updates,
      id: paymentMethodId,
      createdAt: data.paymentMethods[index].createdAt,
    });
    const paymentMethods = data.paymentMethods.map((item, idx) => {
      if (idx !== index) {
        return { ...item, isDefault: nextPaymentMethod.isDefault ? false : Boolean(item.isDefault) };
      }
      return nextPaymentMethod;
    });
    return writeAccountData(accountId, { ...data, paymentMethods });
  }

  function deletePaymentMethod(accountId, paymentMethodId) {
    const data = readAccountData(accountId);
    const removed = data.paymentMethods.find((item) => item.id === paymentMethodId);
    const paymentMethods = data.paymentMethods.filter((item) => item.id !== paymentMethodId);
    if (removed && removed.isDefault && paymentMethods.length) {
      paymentMethods[0] = { ...paymentMethods[0], isDefault: true, updatedAt: new Date().toISOString() };
    }
    return writeAccountData(accountId, { ...data, paymentMethods });
  }

  function addOrderForAccount(accountId, input) {
    const data = readAccountData(accountId);
    const nextOrder = {
      id: normalize(input && input.id) || `order_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
      createdAt: normalize(input && input.createdAt) || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: normalize(input && input.status) || 'Quote Requested',
      title: normalize(input && input.title) || 'Custom Quote Request',
      summary: normalize(input && input.summary),
      deliveryMethod: normalize(input && input.deliveryMethod),
      quantity: Number((input && input.quantity) || 0),
      total: Number((input && input.total) || 0),
      reference: normalize(input && input.reference),
      accountRole: normalize(input && input.accountRole),
      details: input && input.details ? input.details : null,
    };

    return writeAccountData(accountId, { ...data, orders: [nextOrder, ...data.orders] });
  }

  function buildPrintShopDetails(input) {
    if (!input) return null;

    return {
      location: normalize(input.location),
      minimumOrderQuantity: Number(input.minimumOrderQuantity || 0),
      sameDaySamplesAvailable: Boolean(input.sameDaySamplesAvailable),
      sameDayFulfillmentAvailable: Boolean(input.sameDayFulfillmentAvailable),
      sameDayFulfillmentMaxQuantity: Number(input.sameDayFulfillmentMaxQuantity || 0),
      fulfillmentMethods: Array.isArray(input.fulfillmentMethods)
        ? input.fulfillmentMethods.map((value) => normalize(value)).filter(Boolean)
        : [],
    };
  }

  function validateAccountRole(role) {
    return role === 'customer' || role === 'print-shop';
  }

  async function updateAccount(accountId, updates) {
    const accounts = readAccounts();
    const index = accounts.findIndex((account) => account.id === accountId);
    if (index === -1) {
      return { ok: false, error: 'not-found' };
    }

    const existing = accounts[index];
    const nextRole = updates.role || existing.role;
    if (!validateAccountRole(nextRole)) {
      return { ok: false, error: 'invalid-role' };
    }

    const nextEmail = normalizeEmail(updates.email != null ? updates.email : existing.email);
    const nextAccountName = normalize(updates.accountName != null ? updates.accountName : existing.accountName);

    if (!nextEmail) {
      return { ok: false, error: 'missing-email' };
    }

    if (!nextAccountName) {
      return { ok: false, error: 'missing-account-name' };
    }

    const duplicateEmail = accounts.some((account, idx) => idx !== index && normalizeEmail(account.email) === nextEmail);
    if (duplicateEmail) {
      return { ok: false, error: 'email-exists' };
    }

    const duplicateAccountName = accounts.some((account, idx) => {
      return idx !== index && normalize(account.accountName).toLowerCase() === nextAccountName.toLowerCase();
    });
    if (duplicateAccountName) {
      return { ok: false, error: 'account-name-exists' };
    }

    const nextPrintShop = nextRole === 'print-shop'
      ? buildPrintShopDetails(updates.printShop != null ? updates.printShop : existing.printShop)
      : null;

    accounts[index] = {
      ...existing,
      name: normalize(updates.name != null ? updates.name : existing.name),
      email: nextEmail,
      role: nextRole,
      accountName: nextAccountName,
      printShop: nextPrintShop,
    };

    writeAccounts(accounts);
    return { ok: true, account: accounts[index] };
  }

  async function changePassword(accountId, currentPassword, nextPassword) {
    const accounts = readAccounts();
    const index = accounts.findIndex((account) => account.id === accountId);
    if (index === -1) {
      return { ok: false, error: 'not-found' };
    }

    const account = accounts[index];
    const currentHash = await hashPassword(String(currentPassword || ''));
    if (account.passwordHash) {
      if (account.passwordHash !== currentHash) {
        return { ok: false, error: 'invalid-password' };
      }
    } else {
      const expectedLength = Number(account.passwordLength || 0);
      if (!expectedLength || String(currentPassword || '').length !== expectedLength) {
        return { ok: false, error: 'invalid-password' };
      }
    }

    if (String(nextPassword || '').length < 8) {
      return { ok: false, error: 'password-too-short' };
    }

    accounts[index] = {
      ...account,
      passwordHash: await hashPassword(String(nextPassword || '')),
      passwordLength: undefined,
    };

    writeAccounts(accounts);
    return { ok: true, account: accounts[index] };
  }

  async function deleteAccount(accountId, password) {
    const accounts = readAccounts();
    const index = accounts.findIndex((account) => account.id === accountId);
    if (index === -1) {
      return { ok: false, error: 'not-found' };
    }

    const account = accounts[index];
    const providedPassword = String(password || '');
    const providedHash = await hashPassword(providedPassword);

    if (account.passwordHash) {
      if (account.passwordHash !== providedHash) {
        return { ok: false, error: 'invalid-password' };
      }
    } else {
      const expectedLength = Number(account.passwordLength || 0);
      if (!expectedLength || providedPassword.length !== expectedLength) {
        return { ok: false, error: 'invalid-password' };
      }
    }

    const [removed] = accounts.splice(index, 1);
    writeAccounts(accounts);
    localStorage.removeItem(makeAccountDataKey(accountId));

    if (getCurrentUserId() === accountId) {
      signOutCurrentUser();
    }

    return { ok: true, account: removed };
  }

  function signOutCurrentUser() {
    setCurrentUserId('');
  }

  async function signInUser(credentials) {
    const email = normalizeEmail(credentials.email);
    const password = String(credentials.password || '');
    const accountName = normalize(credentials.accountName).toLowerCase();

    const accounts = readAccounts();
    const found = accounts.find((a) => {
      const emailMatch = normalizeEmail(a.email) === email;
      if (!emailMatch) return false;

      if (!accountName) return true;
      return normalize(a.accountName).toLowerCase() === accountName;
    });

    if (!found) {
      return { ok: false, error: 'not-found' };
    }

    if ((found.status || 'active') === 'suspended') {
      return { ok: false, error: 'suspended' };
    }

    const expectedHash = found.passwordHash;
    const providedHash = await hashPassword(password);

    if (expectedHash) {
      if (providedHash !== expectedHash) {
        return { ok: false, error: 'invalid-password' };
      }
    } else {
      const expectedLength = Number(found.passwordLength || 0);
      if (!expectedLength || password.length !== expectedLength) {
        return { ok: false, error: 'invalid-password' };
      }

      found.passwordHash = providedHash;
      found.passwordLength = undefined;
      writeAccounts(accounts);
    }

    setCurrentUserId(found.id);
    return { ok: true, account: found };
  }

  function isAdminAuthed() {
    return sessionStorage.getItem(KEYS.ADMIN_SESSION) === '1';
  }

  function signOutAdmin() {
    sessionStorage.removeItem(KEYS.ADMIN_SESSION);
  }

  function signInAdmin(email, password) {
    if (normalizeEmail(email) !== ADMIN.EMAIL || String(password || '') !== ADMIN.PASSWORD) {
      return { ok: false };
    }

    sessionStorage.setItem(KEYS.ADMIN_SESSION, '1');
    return { ok: true };
  }

  window.TMAuth = {
    KEYS,
    normalize,
    normalizeEmail,
    readAccounts,
    writeAccounts,
    roleLabel,
    createAccount,
    updateAccount,
    changePassword,
    deleteAccount,
    signInUser,
    setCurrentUserId,
    getCurrentUserId,
    getAccountById,
    getCurrentAccount,
    readAccountData,
    writeAccountData,
    getCurrentAccountData,
    updateCurrentAccountData,
    addAddress,
    updateAddress,
    deleteAddress,
    addPaymentMethod,
    updatePaymentMethod,
    deletePaymentMethod,
    addOrderForAccount,
    signOutCurrentUser,
    isAdminAuthed,
    signInAdmin,
    signOutAdmin,
  };
})();
