(function () {
  function refreshAccountNavVisibility() {
    const isLoggedIn = window.TMAuth
      ? Boolean(window.TMAuth.getCurrentUserId())
      : Boolean(sessionStorage.getItem('teeminus_current_user_id'));

    document.querySelectorAll('[data-account-link]').forEach((link) => {
      link.hidden = false;
      link.textContent = isLoggedIn ? 'Account' : 'Sign In';
    });
  }

  window.refreshAccountNavVisibility = refreshAccountNavVisibility;
  refreshAccountNavVisibility();
})();
