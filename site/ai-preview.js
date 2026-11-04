(() => {
  const selected = new URLSearchParams(location.search).get("product");
  const mode = document.querySelector("#ai-mode");
  if (selected && Object.hasOwn(aiProducts, selected)) {
    const product = aiProducts[selected];
    const link = document.querySelector("#ai-product-link");
    link.href = product.path;
    link.textContent = product.name;
    document.querySelector("#ai-product").hidden = false;
    mode.textContent = "Примерка выбранного светильника в вашей комнате.";
  } else if (selected) {
    mode.textContent = "Эта модель сейчас недоступна. Вернитесь в каталог или начните подбор по комнате.";
  }

  const input = document.querySelector("#ai-photo");
  const preview = document.querySelector("#ai-photo-preview");
  const status = document.querySelector("#ai-photo-status");
  let objectUrl;
  input.addEventListener("change", () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = undefined;
    preview.hidden = true;
    preview.removeAttribute("src");
    status.textContent = "";
    const file = input.files[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
      status.textContent = "Выберите JPEG, PNG или WebP размером до 10 МБ.";
      input.value = "";
      return;
    }
    const next = URL.createObjectURL(file);
    objectUrl = next;
    const image = new Image();
    image.src = next;
    image.decode().then(() => {
      if (objectUrl !== next) return;
      preview.src = next;
      preview.hidden = false;
      status.textContent = "Фотография открыта. Она не отправлена на сервер.";
    }).catch(() => {
      if (objectUrl !== next) return;
      URL.revokeObjectURL(next);
      objectUrl = undefined;
      input.value = "";
      status.textContent = "Не удалось открыть изображение. Выберите другую фотографию.";
    });
  });
})();
