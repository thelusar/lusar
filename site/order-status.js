(() => {
  const credentials = Object.fromEntries(new URLSearchParams(location.hash.slice(1)));
  const status = document.querySelector("#guest-order-status");
  if (!credentials.number || !credentials.key) return;
  status.textContent = "Проверяем статус заявки…";
  fetch("/api/order-status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ number: credentials.number, key: credentials.key })
  }).then(async response => {
    const result = await response.json();
    status.textContent = response.ok ? `Заявка №${result.number}: ${result.status}.` : result.error;
  }).catch(() => {
    status.textContent = "Не удалось проверить статус. Попробуйте обновить страницу.";
  });
})();
