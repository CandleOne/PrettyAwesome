(function () {
  const CURRENT_USER_KEY = 'teeminus_current_user_id';
  const isLoggedIn = Boolean(sessionStorage.getItem(CURRENT_USER_KEY));

  document.querySelectorAll('[data-account-link]').forEach((link) => {
    link.hidden = !isLoggedIn;
  });
})();
