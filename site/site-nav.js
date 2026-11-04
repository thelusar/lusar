(() => {
  const dropdowns = [...document.querySelectorAll(".nav-dropdown")];
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
    }
  });
})();
