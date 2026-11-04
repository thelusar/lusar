(() => {
  const selected = new URLSearchParams(location.search).get("product");
  const mode = document.querySelector("#ai-mode");
  const product = selected && Object.hasOwn(aiProducts, selected) ? aiProducts[selected] : null;
  const submit = document.querySelector("#ai-submit");
  if (product) {
    const link = document.querySelector("#ai-product-link");
    link.href = product.path;
    link.textContent = product.name;
    document.querySelector("#ai-product").hidden = false;
    mode.textContent = "Примерка выбранного светильника в вашей комнате.";
    submit.textContent = "Примерить светильник";
  } else if (selected) {
    mode.textContent = "Эта модель сейчас недоступна. Вернитесь в каталог или начните подбор по комнате.";
  }

  const input = document.querySelector("#ai-photo");
  const preview = document.querySelector("#ai-photo-preview");
  const status = document.querySelector("#ai-photo-status");
  const resultStatus = document.querySelector("#ai-result-status");
  const results = document.querySelector("#ai-results");
  const render = document.querySelector("#ai-render");
  const visualization = document.querySelector("#ai-visualization");
  let available = false;
  let objectUrl;
  function resetResult() {
    results.replaceChildren();
    results.hidden = true;
    visualization.hidden = true;
    render.removeAttribute("src");
    resultStatus.textContent = "";
  }
  fetch("/api/ai", { cache: "no-store" }).then(response => response.ok ? response.json() : {}).then(data => {
    available = data.available === true;
    submit.disabled = !available;
    if (!available) resultStatus.textContent = "Lusar AI пока не подключён на этом стенде.";
  }).catch(() => { resultStatus.textContent = "Не удалось проверить доступность Lusar AI."; });
  input.addEventListener("change", () => {
    resetResult();
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = undefined;
    preview.hidden = true;
    preview.removeAttribute("src");
    status.textContent = "";
    const file = input.files[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 4 * 1024 * 1024) {
      status.textContent = "Выберите JPEG, PNG или WebP размером до 4 МБ.";
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
      if (!input.disabled) status.textContent = "Фото готово к отправке.";
    }).catch(() => {
      if (objectUrl !== next) return;
      URL.revokeObjectURL(next);
      objectUrl = undefined;
      input.value = "";
      status.textContent = "Не удалось открыть изображение. Выберите другую фотографию.";
    });
  });

  document.querySelector("#ai-form").addEventListener("submit", async event => {
    event.preventDefault();
    const file = input.files[0];
    if (!available || !file || !document.querySelector("#ai-consent").checked) return;
    submit.disabled = true;
    input.disabled = true;
    resetResult();
    status.textContent = "Отправляем фото на обработку…";
    resultStatus.textContent = "Готовим визуализацию. Это может занять несколько минут.";
    try {
      const photo = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = reject;
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.readAsDataURL(file);
      });
      const response = await fetch("/api/ai", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ photo, consent: true, wishes: document.querySelector("#ai-wishes").value,
          productId: product ? selected : null })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Lusar AI временно недоступен.");
      status.textContent = "Фото обработано.";
      if (data.image) {
        render.src = data.image;
        visualization.hidden = false;
      }
      resultStatus.textContent = [data.advice, data.imageError].filter(Boolean).join(" ")
        || (data.image ? "Визуализация готова." : "Подходящую визуализацию не удалось подготовить.");
      for (const item of data.products || []) {
        const row = document.createElement("li");
        const link = document.createElement("a");
        link.href = item.path;
        link.textContent = item.name;
        if (item.inMockup) row.append(document.createTextNode("В примерке: "));
        row.append(link, document.createTextNode(" — " + item.reason));
        results.append(row);
      }
      results.hidden = !results.childElementCount;
    } catch (error) {
      status.textContent = "Обработка не завершилась.";
      resultStatus.textContent = error instanceof Error && error.message
        ? error.message : "Не удалось обработать фото. Попробуйте ещё раз.";
    } finally {
      input.disabled = false;
      submit.disabled = false;
    }
  });
})();
