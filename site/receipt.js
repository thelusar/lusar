(() => {
  let receipt;
  try {
    receipt = JSON.parse(sessionStorage.getItem("lusar-order-receipt"));
  } catch {
    return;
  }
  if (typeof receipt?.number !== "string" || !/^LS-[A-F0-9]{12}$/.test(receipt.number)) return;
  document.querySelector("#receipt-number").textContent = `Заявка №${receipt.number} получена.`;
  document.querySelector("#receipt-details").hidden = false;
  if (typeof receipt.trackingToken !== "string" || !/^[A-Za-z0-9_-]{43}$/.test(receipt.trackingToken)) return;
  const tracking = document.querySelector("#receipt-tracking");
  tracking.href = "/order-status#" + new URLSearchParams({ number: receipt.number, key: receipt.trackingToken });
  tracking.hidden = false;
})();
