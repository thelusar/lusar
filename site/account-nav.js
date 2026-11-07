(() => {
  const sidebar = document.querySelector('.account-nav');
  const session = window.lusarAccount;
  const avatar = sidebar.querySelector('#account-avatar');
  const nameLabel = sidebar.querySelector('#account-nav-name');
  const emailLabel = sidebar.querySelector('#account-nav-email');

  function render({authenticated, profile}) {
    sidebar.hidden = !authenticated;
    if (!authenticated) return;
    const name = profile.name.trim();
    const words = (name || profile.email.split('@')[0]).split(/\s+/u);
    const first = Array.from(words[0]);
    const initials = words.length > 1 ? first[0] + Array.from(words.at(-1))[0] : first.slice(0, 2).join('');
    avatar.textContent = initials.toUpperCase();
    nameLabel.textContent = name || profile.email;
    emailLabel.textContent = profile.email;
    emailLabel.hidden = !name;
  }

  for (const link of sidebar.querySelectorAll('[data-shopping-tab]')) {
    if (link.pathname === location.pathname) link.setAttribute('aria-current', 'page');
  }
  sidebar.querySelector('[data-account-logout]').addEventListener('click', async event => {
    const button = event.currentTarget;
    const status = sidebar.querySelector('.account-nav-status');
    status.textContent = '';
    button.disabled = true;
    try {
      await session.logout();
    } catch (problem) {
      status.textContent = problem.message;
      status.focus();
      button.disabled = false;
    }
  });
  document.addEventListener('lusar-account-change', event => render(event.detail));
  render(session.value);
})();
