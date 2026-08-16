(() => {
  "use strict";
  const orderId = Number(window.orderId) || Number(location.pathname.split("/").filter(Boolean).pop());
  const token = () => localStorage.getItem("access_token") || "";
  const escapeHtml = v => String(v ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[c]));
  const faDate = v => v ? new Date(v).toLocaleString("fa-IR") : "-";
  const clockDate = v => v ? new Date(v).toLocaleString("fa-IR", {
    year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit"
  }) : "-";
  const stageLabels = {
    RECEPTION: "پذیرش", REPAIR: "تعمیر", TEST: "تست", DELIVERY: "تحویل", GENERAL: "عمومی",
    RECEPTION_INTAKE: "پذیرش", TECHNICAL_DIAGNOSIS: "عیب‌یابی فنی", MANAGEMENT_PRICING: "قیمت‌گذاری",
    CUSTOMER_APPROVAL: "تأیید مشتری", TECHNICAL_REPAIR: "تعمیر فنی",
    TECHNICAL_FINAL_TEST: "تست نهایی", RECEPTION_DELIVERY: "آماده تحویل"
  };
  const timedStages = new Set(["TECHNICAL_DIAGNOSIS", "TECHNICAL_REPAIR", "TECHNICAL_FINAL_TEST"]);
  let sessionUser = null;

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { Authorization: `Bearer ${token()}`, "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "عملیات انجام نشد");
    return body;
  }

  async function loadSessionUser() {
    if (sessionUser?.id) return sessionUser;
    try {
      const body = await api("/auth/verify");
      sessionUser = body.user || {};
      const savedUser = JSON.parse(localStorage.getItem("user") || "{}");
      localStorage.setItem("user", JSON.stringify({ ...savedUser, ...sessionUser }));
    } catch (_) {
      sessionUser = null;
    }
    return sessionUser;
  }
  const formatClockDuration = seconds => {
    if (seconds == null) return "در حال اجرا";
    const total = Math.max(0, Number(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    if (!hours && !minutes && total > 0) return "کمتر از یک دقیقه";
    return hours ? `${hours} ساعت و ${minutes} دقیقه` : `${minutes} دقیقه`;
  };
  const notify = (text, icon = "success") => window.Swal ? Swal.fire({ icon, text, timer: icon === "success" ? 1800 : undefined, showConfirmButton: icon !== "success" }) : alert(text);
  const currentUser = () => { try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; } };
  const formatDuration = seconds => {
    if (seconds == null) return "در حال اجرا";
    const total = Math.max(0, Number(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    if (!hours && !minutes && total > 0) return "کمتر از یک دقیقه";
    return hours ? `${hours} ساعت و ${minutes} دقیقه` : `${minutes} دقیقه`;
    /*
    if (seconds == null) return "در حال اجرا";
    const s = Math.max(0, Number(seconds)), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
    */
  };

  function renderImages(items) {
    const images = items.filter(x => x.file_type === "photo" || (x.mime_type || "").startsWith("image/"));
    if (!images.length) return '<div class="text-muted">تصویر مرحله‌ای ثبت نشده است.</div>';
    return `<div id="caseImageCarousel" class="carousel slide" data-bs-ride="false">
      <div class="carousel-inner rounded">${images.map((item, i) => `<div class="carousel-item ${i === 0 ? "active" : ""}">
        <img src="${escapeHtml(item.file_path)}" class="d-block w-100" style="max-height:360px;object-fit:contain;background:#f8f9fa" alt="${escapeHtml(item.file_name)}">
        <div class="carousel-caption d-block bg-dark bg-opacity-50 rounded"><span>${escapeHtml(stageLabels[item.stage] || item.stage || "عمومی")}</span> · ${escapeHtml(item.file_name)}</div>
      </div>`).join("")}</div>
      <button class="carousel-control-prev" type="button" data-bs-target="#caseImageCarousel" data-bs-slide="prev"><span class="carousel-control-prev-icon"></span></button>
      <button class="carousel-control-next" type="button" data-bs-target="#caseImageCarousel" data-bs-slide="next"><span class="carousel-control-next-icon"></span></button>
    </div>`;
  }

  function renderAttachments(items) {
    if (!items?.length) return '<div class="text-muted">فایلی برای این پرونده ثبت نشده است.</div>';
    return `<div class="row g-2">${items.map(item => `<div class="col-md-4"><div class="border rounded p-2 h-100">
      <div class="fw-semibold text-truncate">${escapeHtml(item.file_name)}</div>
      <small class="text-muted">${escapeHtml(stageLabels[item.stage] || item.stage || "عمومی")} · ${faDate(item.uploaded_at)}</small>
      <a class="btn btn-sm btn-outline-primary mt-2" target="_blank" href="${escapeHtml(item.file_path)}">مشاهده</a>
    </div></div>`).join("")}</div>`;
  }

  function renderTimeline(items) {
    if (!items?.length) return '<div class="text-muted">رویدادی ثبت نشده است.</div>';
    return `<div class="case-timeline">${items.map(item => `<div class="case-timeline-item">
      <div class="case-timeline-dot"></div><div class="case-timeline-content">
      <div class="d-flex justify-content-between gap-2"><strong>${escapeHtml(item.title)}</strong><small class="text-muted">${faDate(item.created_at)}</small></div>
      <div class="small text-muted">${escapeHtml(stageLabels[item.stage] || item.stage || "")}${item.actor_name ? ` · ${escapeHtml(item.actor_name)}` : ""}</div>
      ${item.description ? `<div class="mt-1">${escapeHtml(item.description)}</div>` : ""}</div></div>`).join("")}</div>`;
  }

  function renderTimings(items, order) {
    if (!timedStages.has(order.current_stage)) return "";
    const running = items.find(x => x.stage === order.current_stage && x.status === "RUNNING");
    const user = currentUser();
    const canControl = user.role === "ADMIN" || !order.current_user_id || Number(order.current_user_id) === Number(user.id);
    return `<div class="card shadow-sm mt-4 border-primary"><div class="card-header bg-primary text-white"><i class="fas fa-stopwatch"></i> زمان‌سنج مرحله فنی</div><div class="card-body">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>مرحله فعال: <strong>${escapeHtml(stageLabels[order.current_stage])}</strong></div>
        ${canControl ? `<button id="timingButton" class="btn ${running ? "btn-danger" : "btn-success"}" data-stage="${order.current_stage}">
          <i class="fas fa-${running ? "stop" : "play"}"></i> ${running ? "پایان مرحله" : "شروع مرحله"}</button>` : ""}
      </div>
      <div class="table-responsive mt-3"><table class="table table-sm mb-0"><thead><tr><th>مرحله</th><th>تکنسین</th><th>شروع</th><th>پایان</th><th>مدت</th></tr></thead><tbody>
        ${items.length ? items.map(x => `<tr><td>${escapeHtml(stageLabels[x.stage] || x.stage)}</td><td>${escapeHtml(x.user_name || "-")}</td><td>${clockDate(x.started_at)}</td><td>${clockDate(x.completed_at)}</td><td>${formatDuration(x.duration_seconds)}</td></tr>`).join("") : '<tr><td colspan="5" class="text-muted">هنوز زمان‌سنجی ثبت نشده است.</td></tr>'}
      </tbody></table></div></div></div>`;
  }

  async function handleTiming(stage, running) {
    const note = running ? (await Swal.fire({ title: "یادداشت پایان مرحله", input: "textarea", showCancelButton: true, confirmButtonText: "ثبت پایان", cancelButtonText: "انصراف" })).value : null;
    if (running && note === undefined) return;
    await api(`/api/workflow/orders/${orderId}/timing/${running ? "complete" : "start"}`, { method: "POST", body: JSON.stringify({ stage, note: note || null }) });
    notify(running ? "پایان مرحله ثبت شد." : "شروع مرحله ثبت شد.");
    await loadOrder();
  }

  async function uploadStageFile() {
    const input = document.getElementById("stageFile"), file = input?.files?.[0];
    if (!file) return notify("یک فایل انتخاب کنید.", "warning");
    const form = new FormData();
    form.append("file", file);
    form.append("stage", document.getElementById("fileStage").value);
    form.append("description", document.getElementById("fileDescription").value.trim());
    const response = await fetch(`/reception/repair-orders/${orderId}/upload`, { method: "POST", headers: { Authorization: `Bearer ${token()}` }, body: form });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "آپلود انجام نشد");
    notify("فایل مرحله‌ای ثبت شد.");
    await loadOrder();
  }

  async function renderWorkflow(order) {
    const stages = await api("/api/workflow/stages");
    const holder = document.getElementById("workflow-area");
    holder.innerHTML = `<div class="card shadow-sm mt-4"><div class="card-header"><strong><i class="fas fa-route"></i> گردش پرونده</strong></div><div class="card-body">
      <div class="small text-muted mb-3">مرحله فعلی: <strong>${escapeHtml(stageLabels[order.current_stage] || order.current_stage || "-")}</strong></div>
      <div id="workflow-action"></div>
      <form id="transferForm" class="row g-2 align-items-end mt-3"><div class="col-md-4"><label class="form-label">مرحله بعد</label><select id="workflowStage" class="form-select" required><option value="">انتخاب مرحله</option>${stages.map(x => `<option value="${x.code}" data-department="${x.department}">${escapeHtml(x.label)}</option>`).join("")}</select></div>
      <div class="col-md-3"><label class="form-label">گیرنده</label><select id="workflowRecipient" class="form-select" required><option value="">ابتدا مرحله را انتخاب کنید</option></select></div>
      <div class="col-md-2"><button class="btn btn-primary w-100">ارسال انتقال</button></div><div class="col-12"><textarea id="workflowNote" class="form-control" rows="2" placeholder="یادداشت انتقال (اختیاری)"></textarea></div></form>
    </div></div>`;
    const definition = {
      TECHNICAL_DIAGNOSIS: ["DIAGNOSIS","ثبت نتیجه عیب‌یابی"],
      MANAGEMENT_PRICING: ["PRICING","ثبت قیمت"],
      CUSTOMER_APPROVAL: ["CUSTOMER_DECISION","ثبت نظر مشتری"],
      TECHNICAL_REPAIR: ["REPAIR_COMPLETE","ثبت پایان تعمیر"],
      TECHNICAL_FINAL_TEST: ["FINAL_TEST","ثبت تست نهایی"],
      RECEPTION_DELIVERY: ["DELIVER","ثبت تحویل"]
    }[order.current_stage];
    if (definition) {
      document.getElementById("workflow-action").innerHTML = `<form id="actionForm" class="border rounded p-3 bg-light"><h6>${definition[1]}</h6>
        ${definition[0] === "PRICING" ? '<input id="quotedPrice" type="number" min="0" step="0.01" class="form-control mb-2" placeholder="مبلغ پیشنهادی">' : ""}
        <textarea id="actionNotes" class="form-control mb-2" rows="2" placeholder="توضیحات"></textarea>
        ${definition[0] === "CUSTOMER_DECISION" ? '<button type="button" class="btn btn-success me-2" data-approved="true">موافق است</button><button type="button" class="btn btn-outline-danger" data-approved="false">مخالف است</button>' : '<button class="btn btn-outline-primary">ثبت اقدام</button>'}</form>`;
      const submit = async approved => {
        await api(`/api/workflow/orders/${orderId}/action`, { method: "POST", body: JSON.stringify({ action: definition[0], notes: document.getElementById("actionNotes").value.trim() || null, quoted_price: document.getElementById("quotedPrice")?.value ? Number(document.getElementById("quotedPrice").value) : null, approved }) });
        notify("اقدام پرونده ثبت شد."); await loadOrder();
      };
      document.getElementById("actionForm").addEventListener("submit", e => { e.preventDefault(); submit(null).catch(e => notify(e.message, "error")); });
      document.querySelectorAll("[data-approved]").forEach(b => b.addEventListener("click", () => submit(b.dataset.approved === "true").catch(e => notify(e.message, "error"))));
    }
    document.getElementById("workflowStage").addEventListener("change", async e => {
      const dept = e.target.selectedOptions[0]?.dataset.department, recipient = document.getElementById("workflowRecipient");
      recipient.innerHTML = "<option>در حال بارگذاری...</option>";
      if (!dept) return;
      try { const users = await api(`/api/panel/users/by-department/${dept}`); recipient.innerHTML = '<option value="">انتخاب گیرنده</option>' + users.map(u => `<option value="${u.id}">${escapeHtml(u.full_name)}</option>`).join(""); }
      catch (err) { recipient.innerHTML = "<option>کاربری پیدا نشد</option>"; notify(err.message, "error"); }
    });
    document.getElementById("transferForm").addEventListener("submit", async e => {
      e.preventDefault(); const select = document.getElementById("workflowStage");
      try { await api(`/api/workflow/orders/${orderId}/transfer`, { method: "POST", body: JSON.stringify({ stage: select.value, to_department: select.selectedOptions[0]?.dataset.department, to_user_id: Number(document.getElementById("workflowRecipient").value), note: document.getElementById("workflowNote").value.trim() || null }) }); notify("درخواست انتقال ثبت شد."); await loadOrder(); }
      catch (err) { notify(err.message, "error"); }
    });
  }

  function renderOrder(order, attachments, timings, timeline) {
    document.getElementById("order-detail").innerHTML = `<div class="card shadow-sm border-0"><div class="card-header d-flex justify-content-between"><h4>پرونده #${order.id}</h4><span class="badge bg-primary">${escapeHtml(order.status || "-")}</span></div><div class="card-body">
      <div class="row g-3"><div class="col-md-6"><div class="border rounded p-3"><strong>کد رهگیری:</strong><br><code>${escapeHtml(order.tracking_code)}</code></div></div><div class="col-md-6"><div class="border rounded p-3"><strong>مرحله فعلی:</strong><br>${escapeHtml(stageLabels[order.current_stage] || order.current_stage || "-")}</div></div>
      <div class="col-md-6"><div class="border rounded p-3"><strong>مشتری:</strong><br>${escapeHtml(order.customer_name || "-")}<br>${escapeHtml(order.customer_phone || "-")}</div></div><div class="col-md-6"><div class="border rounded p-3"><strong>دستگاه:</strong><br>${escapeHtml(order.device_brand || "")} ${escapeHtml(order.device_model || "")}<br>سریال: ${escapeHtml(order.device_serial_number || "-")}</div></div></div>
      ${renderTimings(timings, order)}
      <div class="card mt-4"><div class="card-header">تصاویر مرحله‌ای</div><div class="card-body">${renderImages(attachments)}</div></div>
      <div class="card mt-4"><div class="card-header">آپلود فایل مرحله‌ای</div><div class="card-body"><div class="row g-2 align-items-end"><div class="col-md-3"><label class="form-label">مرحله</label><select id="fileStage" class="form-select"><option value="RECEPTION">پذیرش</option><option value="REPAIR">تعمیر</option><option value="TEST">تست</option><option value="DELIVERY">تحویل</option><option value="GENERAL">عمومی</option></select></div><div class="col-md-3"><input id="stageFile" type="file" class="form-control"></div><div class="col-md-4"><input id="fileDescription" class="form-control" placeholder="توضیح فایل"></div><div class="col-md-2"><button id="uploadStageFile" class="btn btn-success w-100">آپلود</button></div></div><div class="mt-3">${renderAttachments(attachments)}</div></div></div>
      <div id="workflow-area"></div>
      <div class="card mt-4"><div class="card-header">تایم‌لاین تصویری پرونده</div><div class="card-body">${renderTimeline(timeline)}</div></div>
      <div class="mt-4"><a class="btn btn-success" href="/reception/repair-orders/${order.id}/receipt" target="_blank">چاپ رسید پذیرش</a> <a class="btn btn-secondary" href="/orders">بازگشت به برد</a></div>
    </div></div>`;
    if (timedStages.has(order.current_stage)) document.getElementById("timingButton")?.addEventListener("click", () => handleTiming(order.current_stage, timings.some(x => x.stage === order.current_stage && x.status === "RUNNING")).catch(e => notify(e.message, "error")));
    document.getElementById("uploadStageFile").addEventListener("click", () => uploadStageFile().catch(e => notify(e.message, "error")));
    document.getElementById("fileStage").value = order.current_stage.includes("REPAIR") ? "REPAIR" : order.current_stage.includes("TEST") ? "TEST" : order.current_stage.includes("DELIVERY") ? "DELIVERY" : "RECEPTION";
  }

  async function loadOrder() {
    if (!token()) return (location.href = "/login");
    try {
      await loadSessionUser();
      const [order, attachments, timings, timeline] = await Promise.all([
        api(`/reception/repair-orders/${orderId}`), api(`/reception/repair-orders/${orderId}/attachments`),
        api(`/api/workflow/orders/${orderId}/timings`), api(`/api/workflow/orders/${orderId}/timeline`)
      ]);
      renderOrder(order, attachments, timings, timeline);
      await renderWorkflow(order);
    } catch (e) { document.getElementById("order-detail").innerHTML = `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`; }
  }
  document.addEventListener("DOMContentLoaded", loadOrder);
})();
