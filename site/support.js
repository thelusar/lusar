(() => {
  const selected = new URLSearchParams(location.search).get("product");
  if (!selected || !Object.hasOwn(supportProducts, selected)) return;
  const product = supportProducts[selected];
  const link = document.querySelector("#support-product-link");
  link.href = product.path;
  link.textContent = product.name;
  link.setAttribute("data-locale-source", "");
  document.querySelector("#support-product").hidden = false;
})();
