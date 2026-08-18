(() => {
  "use strict";

  const token = () => localStorage.getItem("access_token") || "";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
  const formatDate = (value) => value
    ? new Date(value).toLocaleString("fa-IR", { dateStyle: "medium", timeStyle: "short" })
    : "-";

  let orders = [];

  async function api(url) {
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token()}` }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "دریافت پرونده‌های مختومه انجام نشد.");
    return body;
  }

  function statusLabel(order) {
    return order.current_stage === "CLOSED_NO_REPAIR" ? "مختومه بدون تعمیر" : "تحویل شده";
  }

  function render() {
    const query = (document.getElementById("closedSearch")?.value || "").trim().toLowerCase();
    const filtered = orders.filter((order) => (
      `${order.tracking_code || ""} ${order.customer_name || ""} ${order.device || ""} ${order.serial_number || ""}`
    ).toLowerCase().includes(query));
    const root = document.getElementById("closedOrders");
    document.getElementById("closedSummary").textContent =
      `${filtered.length} پرونده از ${orders.length} پرونده مختومه`;

    if (!filtered.length) {
      root.innerHTML = `<div class="col-12"><div class="closed-empty text-center text-muted py-5">
        <i class="fas fa-box-open fa-2x mb-3"></i>
        <div>${query ? "پرونده‌ای با این جستجو پیدا نشد." : "هنوز پرونده مختومه‌ای ثبت نشده است."}</div>
      </div></div>`;
      return;
    }

    root.innerHTML = filtered.map((order) => `
      <div class="col-12 col-md-6 col-xl-4">
        <article class="closed-card h-100">
          <div class="card-header d-flex justify-content-between align-items-center">
            <strong><i class="fas fa-hashtag text-primary"></i>${escapeHtml(order.tracking_code || order.id)}</strong>
            <span class="badge ${order.current_stage === "CLOSED_NO_REPAIR" ? "bg-warning text-dark" : "bg-success"}">
              ${statusLabel(order)}
            </span>
          </div>
          <div class="card-body">
            <div class="mb-2"><i class="fas fa-user text-secondary me-1"></i>
              <strong>${escapeHtml(order.customer_name || "بدون نام مشتری")}</strong>
            </div>
            <div class="closed-meta mb-1"><i class="fas fa-microchip me-1"></i>${escapeHtml(order.device || "دستگاه ثبت نشده")}</div>
            <div class="closed-meta mb-1"><i class="fas fa-barcode me-1"></i>${escapeHtml(order.serial_number || "بدون شماره سریال")}</div>
            <div class="closed-meta mb-3"><i class="fas fa-calendar-check me-1"></i>${formatDate(order.delivered_at || order.created_at)}</div>
            <a href="/order/${order.id}" class="btn btn-outline-primary btn-sm w-100">
              <i class="fas fa-eye me-1"></i> مشاهده جزئیات پرونده
            </a>
          </div>
        </article>
      </div>
    `).join("");
  }

  async function load() {
    const root = document.getElementById("closedOrders");
    root.innerHTML = `<div class="col-12 text-center text-muted py-5"><i class="fas fa-spinner fa-spin fa-2x"></i></div>`;
    try {
      const data = await api("/api/workflow/closed-orders");
      orders = data.orders || [];
      render();
    } catch (error) {
      root.innerHTML = `<div class="col-12"><div class="alert alert-danger">${escapeHtml(error.message)}</div></div>`;
    }
  }

  document.getElementById("closedSearch")?.addEventListener("input", render);
  document.getElementById("refreshClosed")?.addEventListener("click", load);
  load();
})();
