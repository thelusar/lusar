(() => {
  const header = document.querySelector(".site-header");
  const nav = header.querySelector(".main-nav");
  const menuToggle = header.querySelector("#menu-toggle");
  const narrow = matchMedia("(max-width: 58rem)");
  const dropdowns = [...nav.querySelectorAll(".nav-dropdown")];

  function setMenu(open) {
    header.dataset.navOpen = String(open);
    menuToggle.setAttribute("aria-expanded", String(open));
    if (open) {
      nav.querySelector("summary").focus();
    } else {
      for (const dropdown of dropdowns) dropdown.open = false;
    }
  }

  header.dataset.navOpen = "false";
  menuToggle.hidden = false;
  menuToggle.addEventListener("click", () => setMenu(header.dataset.navOpen !== "true"));
  narrow.addEventListener("change", () => setMenu(false));
  for (const dropdown of dropdowns) {
    const summary = dropdown.querySelector("summary");
    summary.addEventListener("click", () => {
      for (const other of dropdowns) {
        if (other !== dropdown) other.open = false;
      }
    });
    dropdown.addEventListener("focusout", event => {
      if (event.relatedTarget && !dropdown.contains(event.relatedTarget)) dropdown.open = false;
    });
  }
  document.addEventListener("click", event => {
    if (header.dataset.navOpen === "true" && !header.contains(event.target)) setMenu(false);
    for (const dropdown of dropdowns) {
      if (!dropdown.contains(event.target)) dropdown.open = false;
    }
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const dropdown = dropdowns.find(menu => menu.open);
    if (dropdown) {
      dropdown.open = false;
      dropdown.querySelector("summary").focus();
    } else if (header.dataset.navOpen === "true") {
      setMenu(false);
      menuToggle.focus();
    }
  });
})();
