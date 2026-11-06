(() => {
  let receipt;
  try {
    receipt = JSON.parse(sessionStorage.getItem("lusar-order-receipt"));
  } catch {
    return;
  }
  if (typeof receipt?.number !== "string" || !/^LS-(?:[0-9]{6}|[A-F0-9]{12})$/.test(receipt.number)) return;
  document.querySelector("#receipt-title").textContent = "Заявка принята";
  document.querySelector(".receipt-symbol").hidden = false;
  document.querySelector("#receipt-label").hidden = false;
  document.querySelector("#receipt-number").textContent = receipt.number;
  document.querySelector("#receipt-details").hidden = false;
  if (receipt.leadPending === true) {
    document.addEventListener("DOMContentLoaded", () => {
      try {
        sessionStorage.setItem("lusar-order-receipt", JSON.stringify({ ...receipt, leadPending: false }));
      } catch {}
      window.lusarAnalytics?.submitted();
    }, { once: true });
  }
  if (typeof receipt.trackingToken !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(receipt.trackingToken)) return;
  const tracking = document.querySelector("#receipt-tracking");
  tracking.href = "/order-status#" + new URLSearchParams({ number: receipt.number, key: receipt.trackingToken });
  tracking.hidden = false;
})();
