(() => {
  const header = document.querySelector(".site-header");
  const nav = header.querySelector(".main-nav");
  const menuToggle = header.querySelector("#menu-toggle");
  const narrow = matchMedia("(max-width: 78rem)");
  const dropdowns = [...nav.querySelectorAll(".nav-dropdown")];
  const hover = matchMedia("(hover: hover) and (pointer: fine)");
  const closeTimers = new Map();
  function setDropdown(dropdown, open) {
    clearTimeout(closeTimers.get(dropdown));
    dropdown.dataset.open = String(open);
    dropdown.querySelector(".nav-dropdown-toggle").setAttribute("aria-expanded", String(open));
    dropdown.querySelector(".nav-panel").hidden = !open;
  }
  function openDropdown(dropdown) {
    for (const other of dropdowns) setDropdown(other, other === dropdown);
  }
  for (const link of nav.querySelectorAll("a")) {
    if (link.pathname === location.pathname) link.setAttribute("aria-current", "page");
  }

  function setMenu(open) {
    header.dataset.navOpen = String(open);
    menuToggle.setAttribute("aria-expanded", String(open));
    if (open) {
      nav.querySelector("a").focus();
    } else {
      for (const dropdown of dropdowns) setDropdown(dropdown, false);
    }
  }

  header.dataset.navOpen = "false";
  menuToggle.hidden = false;
  menuToggle.addEventListener("click", () => setMenu(header.dataset.navOpen !== "true"));
  function restoreVisibleFocus() {
    if (nav.contains(document.activeElement) && getComputedStyle(nav).display === "none") {
      menuToggle.focus();
    }
  }
  narrow.addEventListener("change", () => {
    setMenu(false);
    restoreVisibleFocus();
  });
  window.addEventListener("resize", restoreVisibleFocus);
  header.addEventListener("focusout", event => {
    if (event.relatedTarget && !header.contains(event.relatedTarget)) setMenu(false);
  });
  for (const dropdown of dropdowns) {
    const toggle = dropdown.querySelector(".nav-dropdown-toggle");
    toggle.addEventListener("click", () => {
      if (dropdown.dataset.open === "true") setDropdown(dropdown, false);
      else openDropdown(dropdown);
    });
    dropdown.addEventListener("pointerenter", () => {
      if (hover.matches && !narrow.matches) openDropdown(dropdown);
    });
    dropdown.addEventListener("pointerleave", () => {
      if (hover.matches && !narrow.matches) {
        closeTimers.set(dropdown, setTimeout(() => setDropdown(dropdown, false), 140));
      }
    });
    dropdown.addEventListener("focusin", event => {
      clearTimeout(closeTimers.get(dropdown));
      if (!narrow.matches && event.target.matches(".nav-overview")) openDropdown(dropdown);
    });
    toggle.addEventListener("keydown", event => {
      if (event.key !== "ArrowDown") return;
      event.preventDefault();
      openDropdown(dropdown);
      dropdown.querySelector(".nav-panel a").focus();
    });
    dropdown.addEventListener("focusout", event => {
      if (event.relatedTarget && !dropdown.contains(event.relatedTarget)) setDropdown(dropdown, false);
    });
  }
  document.addEventListener("click", event => {
    const cartLink = event.target.closest('a[href="/cart"]');
    if (cartLink && /^\/(?:catalog(?:\/.*)?|search|favorites|compare)\/?$/.test(location.pathname)) {
      try { sessionStorage.setItem("lusar-shopping-return", location.pathname + location.search + location.hash); } catch {}
    }
    if (header.dataset.navOpen === "true" && !header.contains(event.target)) setMenu(false);
    for (const dropdown of dropdowns) {
      if (!dropdown.contains(event.target)) setDropdown(dropdown, false);
    }
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const dropdown = dropdowns.find(menu => menu.dataset.open === "true");
    if (dropdown) {
      setDropdown(dropdown, false);
      dropdown.querySelector(".nav-dropdown-toggle").focus();
    } else if (header.dataset.navOpen === "true") {
      setMenu(false);
      menuToggle.focus();
    }
  });
})();
