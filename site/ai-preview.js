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
  const empty = document.querySelector("#ai-empty");
  const progress = document.querySelector("#ai-progress");
  const before = document.querySelector("#ai-before");
  const comparison = document.querySelector("#ai-compare");
  const dropzone = document.querySelector("#ai-dropzone");
  const fileLabel = document.querySelector("#ai-file-label");
  const wishes = document.querySelector("#ai-wishes");
  const advice = document.querySelector("#ai-advice");
  const adviceText = document.querySelector("#ai-advice-text");
  const unavailableMessage = "Lusar AI временно недоступен. Попробуйте позже.";
  let available = false;
  let objectUrl;
  function resetResult() {
    results.replaceChildren();
    results.hidden = true;
    visualization.hidden = true;
    render.removeAttribute("src");
    before.removeAttribute("src");
    advice.hidden = true;
    advice.open = false;
    adviceText.textContent = "";
    resultStatus.textContent = available ? "" : unavailableMessage;
  }
  fetch("/api/ai", { cache: "no-store" }).then(response => response.ok ? response.json() : {}).then(data => {
    available = data.available === true;
    submit.disabled = !available;
    if (!available) resultStatus.textContent = unavailableMessage;
  }).catch(() => { resultStatus.textContent = "Не удалось проверить доступность Lusar AI."; });
  input.addEventListener("change", () => {
    resetResult();
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = undefined;
    preview.hidden = true;
    preview.removeAttribute("src");
    empty.hidden = false;
    fileLabel.removeAttribute("data-locale-source");
    fileLabel.textContent = "Загрузите фото комнаты";
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
      empty.hidden = true;
      fileLabel.setAttribute("data-locale-source", "");
      fileLabel.textContent = file.name;
      if (!input.disabled) status.textContent = "Фото готово к отправке.";
    }).catch(() => {
      if (objectUrl !== next) return;
      URL.revokeObjectURL(next);
      objectUrl = undefined;
      input.value = "";
      status.textContent = "Не удалось открыть изображение. Выберите другую фотографию.";
    });
  });

  for (const eventName of ["dragenter", "dragover"]) {
    dropzone.addEventListener(eventName, event => {
      event.preventDefault();
      if (!input.disabled) dropzone.classList.add("is-dragging");
    });
  }
  dropzone.addEventListener("dragleave", event => {
    if (!dropzone.contains(event.relatedTarget)) dropzone.classList.remove("is-dragging");
  });
  dropzone.addEventListener("drop", event => {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
    if (input.disabled || !event.dataTransfer.files.length) return;
    const transfer = new DataTransfer();
    transfer.items.add(event.dataTransfer.files[0]);
    input.files = transfer.files;
    input.dispatchEvent(new Event("change"));
  });
  for (const button of document.querySelectorAll("[data-ai-wish]")) {
    button.addEventListener("click", () => {
      const parts = wishes.value.split(/\s*,\s*/).filter(Boolean);
      const phrase = button.dataset.insertedWish || button.textContent.trim();
      const index = parts.indexOf(phrase);
      if (index === -1) parts.push(phrase);
      else parts.splice(index, 1);
      const next = parts.join(", ");
      if (next.length > wishes.maxLength) return;
      if (index === -1) button.dataset.insertedWish = phrase;
      else delete button.dataset.insertedWish;
      wishes.value = next;
      wishes.dispatchEvent(new Event("input"));
    });
  }
  wishes.addEventListener("input", () => {
    const parts = wishes.value.split(/\s*,\s*/);
    for (const button of document.querySelectorAll("[data-ai-wish]")) {
      button.setAttribute("aria-pressed", String(parts.includes(button.dataset.insertedWish || button.textContent.trim())));
    }
  });
  comparison.addEventListener("input", () => {
    visualization.style.setProperty("--compare", comparison.value + "%");
  });

  document.querySelector("#ai-form").addEventListener("submit", async event => {
    event.preventDefault();
    const file = input.files[0];
    if (!available || input.disabled || !file || !document.querySelector("#ai-consent").checked) return;
    const submittedWishes = wishes.value;
    submit.disabled = true;
    input.disabled = true;
    progress.hidden = false;
    document.querySelector(".ai-stage").setAttribute("aria-busy", "true");
    resetResult();
    preview.src = objectUrl;
    preview.hidden = false;
    empty.hidden = true;
    status.textContent = "Отправляем фото на обработку…";
    resultStatus.textContent = "Готовим визуализацию. Это может занять несколько минут.";
    if (matchMedia("(max-width: 58rem)").matches) {
      document.querySelector(".ai-stage").scrollIntoView({
        behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
        block: "start"
      });
    }
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
        body: JSON.stringify({ photo, consent: true, wishes: submittedWishes,
          productId: product ? selected : null })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Lusar AI временно недоступен.");
      status.textContent = "Фото обработано.";
      if (data.image) {
        before.src = objectUrl;
        render.src = data.image;
        comparison.value = "50";
        visualization.style.setProperty("--compare", "50%");
        preview.hidden = true;
        empty.hidden = true;
        visualization.hidden = false;
      }
      resultStatus.textContent = data.imageError ||
        (data.image ? "Визуализация готова." : "Подходящую визуализацию не удалось подготовить.");
      adviceText.textContent = data.advice || "";
      advice.hidden = !data.advice;
      for (const item of data.products || []) {
        const row = document.createElement("li");
        const link = document.createElement("a");
        link.href = item.path;
        const catalogItem = Object.hasOwn(aiProducts, item.id) ? aiProducts[item.id] : null;
        if (catalogItem?.image) {
          const photo = document.createElement("img");
          photo.src = catalogItem.image;
          photo.alt = "";
          photo.width = photo.height = 64;
          photo.loading = "lazy";
          link.append(photo);
        }
        const title = document.createElement("span");
        title.textContent = item.name;
        link.append(title);
        if (item.inMockup) {
          const badge = document.createElement("span");
          badge.className = "result-badge";
          badge.textContent = "В примерке";
          row.append(badge);
        }
        const reason = document.createElement("p");
        reason.textContent = item.reason;
        row.append(link, reason);
        results.append(row);
      }
      results.hidden = !results.childElementCount;
    } catch (error) {
      status.textContent = "Обработка не завершилась.";
      resultStatus.textContent = error instanceof Error && error.message
        ? error.message : "Не удалось обработать фото. Попробуйте ещё раз.";
    } finally {
      input.disabled = false;
      submit.disabled = !available;
      progress.hidden = true;
      document.querySelector(".ai-stage").setAttribute("aria-busy", "false");
    }
  });
})();
