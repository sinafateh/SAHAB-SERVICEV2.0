(() => {
  "use strict";
  const token = () => localStorage.getItem("access_token") || "";
  const escapeHtml = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
  const date = (v) => v ? new Date(v).toLocaleDateString("fa-IR") : "-";
  const stageLabels = {
    RECEPTION_INTAKE: "پذیرش", TECHNICAL_DIAGNOSIS: "فنی",
    MANAGEMENT_PRICING: "قیمت", TECHNICAL_REPAIR: "تعمیر",
    TECHNICAL_FINAL_TEST: "تست", RECEPTION_DELIVERY: "آماده تحویل"
  };
  let board = null;
  let syncingScroll = false;

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { Authorization: `Bearer ${token()}`, "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "عملیات انجام نشد");
    return body;
  }

  function render() {
    const query = (document.getElementById("kanbanSearch")?.value || "").trim().toLowerCase();
    const root = document.getElementById("kanbanBoard");
    root.innerHTML = (board?.columns || []).map(column => {
      const cards = column.cards.filter(card => {
        const haystack = `${card.tracking_code} ${card.customer_name || ""} ${card.device || ""}`.toLowerCase();
        return !query || haystack.includes(query);
      });
      return `<section class="kanban-column" data-stage="${column.stage}" data-department="${column.department}">
        <div class="kanban-column-header"><strong>${escapeHtml(column.label)}</strong><span class="badge bg-primary">${cards.length}</span></div>
        <div class="kanban-dropzone">${cards.length ? cards.map(cardHtml).join("") :
          '<div class="text-center text-muted small py-5">پرونده‌ای در این ستون نیست</div>'}</div>
      </section>`;
    }).join("");
    syncKanbanScrollbars();
    bindDragDrop();
  }

  function syncKanbanScrollbars() {
    const boardElement = document.getElementById("kanbanBoard");
    const topScroll = document.getElementById("kanbanTopScroll");
    const topContent = document.getElementById("kanbanTopScrollContent");
    if (!boardElement || !topScroll || !topContent) return;
    topContent.style.width = `${Math.max(boardElement.scrollWidth, boardElement.clientWidth)}px`;
  }

  function bindKanbanScrollbars() {
    const boardElement = document.getElementById("kanbanBoard");
    const topScroll = document.getElementById("kanbanTopScroll");
    if (!boardElement || !topScroll) return;
    topScroll.addEventListener("scroll", () => {
      if (syncingScroll) return;
      syncingScroll = true;
      boardElement.scrollLeft = topScroll.scrollLeft;
      syncingScroll = false;
    });
    boardElement.addEventListener("scroll", () => {
      if (syncingScroll) return;
      syncingScroll = true;
      topScroll.scrollLeft = boardElement.scrollLeft;
      syncingScroll = false;
    });
    window.addEventListener("resize", syncKanbanScrollbars);
  }

  function cardHtml(card) {
    return `<article class="kanban-card" draggable="true" data-order-id="${card.id}">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <a href="/order/${card.id}" class="fw-bold text-decoration-none">${escapeHtml(card.tracking_code)}</a>
        <span class="badge bg-light text-dark">${escapeHtml(stageLabels[card.current_stage] || card.current_stage || "-")}</span>
      </div>
      <div>${escapeHtml(card.customer_name || "مشتری ثبت نشده")}</div>
      <small>${escapeHtml(card.device || "دستگاه ثبت نشده")}</small>
      <div class="small text-muted mt-2"><i class="fas fa-user"></i> ${escapeHtml(card.current_user_name || "بدون مسئول")} · ${date(card.created_at)}</div>
    </article>`;
  }

  function bindDragDrop() {
    document.querySelectorAll(".kanban-card").forEach(card => {
      card.addEventListener("dragstart", e => { card.classList.add("dragging"); e.dataTransfer.setData("text/plain", card.dataset.orderId); });
      card.addEventListener("dragend", () => card.classList.remove("dragging"));
    });
    document.querySelectorAll(".kanban-column").forEach(column => {
      column.addEventListener("dragover", e => { e.preventDefault(); column.classList.add("is-over"); });
      column.addEventListener("dragleave", () => column.classList.remove("is-over"));
      column.addEventListener("drop", async e => {
        e.preventDefault(); column.classList.remove("is-over");
        const id = Number(e.dataTransfer.getData("text/plain"));
        const targetStage = column.dataset.stage;
        const card = document.querySelector(`[data-order-id="${id}"]`);
        if (!id || !card || card.closest(".kanban-column")?.dataset.stage === targetStage) return;
        await moveCard(id, targetStage, column.dataset.department);
      });
    });
  }

  async function moveCard(orderId, stage, department) {
    try {
      const users = await api(`/api/panel/users/by-department/${encodeURIComponent(department)}`);
      const options = users.map(u => `<option value="${u.id}">${escapeHtml(u.full_name)} (${escapeHtml(u.username)})</option>`).join("");
      const result = await Swal.fire({
        title: `انتقال به ${escapeHtml(stageLabels[stage])}`,
        html: `<select id="kanbanRecipient" class="form-select"><option value="">انتخاب گیرنده</option>${options}</select>
               <textarea id="kanbanNote" class="form-control mt-2" placeholder="یادداشت انتقال (اختیاری)"></textarea>`,
        showCancelButton: true, confirmButtonText: "ثبت انتقال", cancelButtonText: "انصراف",
        preConfirm: () => {
          const recipient = document.getElementById("kanbanRecipient").value;
          if (!recipient) { Swal.showValidationMessage("گیرنده را انتخاب کنید"); return false; }
          return { to_user_id: Number(recipient), note: document.getElementById("kanbanNote").value.trim() || null };
        }
      });
      if (!result.isConfirmed) return;
      await api(`/api/workflow/kanban/orders/${orderId}/move`, {
        method: "POST",
        body: JSON.stringify({ ...result.value, stage, to_department: department })
      });
      await loadBoard();
      Swal.fire({ icon: "success", text: "درخواست انتقال ثبت شد.", timer: 1800, showConfirmButton: false });
    } catch (error) {
      Swal.fire({ icon: "error", text: error.message });
      render();
    }
  }

  async function loadBoard() {
    try { board = await api("/api/workflow/kanban/board"); render(); }
    catch (error) { document.getElementById("kanbanBoard").innerHTML = `<div class="alert alert-danger w-100">${escapeHtml(error.message)}</div>`; }
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!token()) { window.location.href = "/login"; return; }
    document.getElementById("refreshKanban").addEventListener("click", loadBoard);
    document.getElementById("kanbanSearch").addEventListener("input", render);
    bindKanbanScrollbars();
    loadBoard();
  });
})();
