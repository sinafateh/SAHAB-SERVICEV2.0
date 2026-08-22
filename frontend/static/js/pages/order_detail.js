(() => {
  "use strict";

  const orderId = Number(window.orderId) || Number(location.pathname.split("/").filter(Boolean).pop());
  const token = () => localStorage.getItem("access_token") || "";
  const privilegedRoles = new Set(["ADMIN", "MANAGEMENT"]);
  const timedStages = new Set(["TECHNICAL_DIAGNOSIS", "TECHNICAL_REPAIR", "TECHNICAL_FINAL_TEST"]);
  const stageDepartments = {
    RECEPTION_INTAKE: "RECEPTION",
    TECHNICAL_DIAGNOSIS: "TECHNICAL",
    MANAGEMENT_PRICING: "MANAGEMENT",
    CUSTOMER_APPROVAL: "CUSTOMER_RELATIONS",
    TECHNICAL_REPAIR: "TECHNICAL",
    TECHNICAL_FINAL_TEST: "TECHNICAL",
    RECEPTION_DELIVERY: "RECEPTION",
  };
  let sessionUser = {};

  const stageLabels = {
    RECEPTION: "پذیرش",
    REPAIR: "تعمیر",
    TEST: "تست",
    DELIVERY: "تحویل",
    GENERAL: "عمومی",
    RECEPTION_INTAKE: "پذیرش",
    TECHNICAL_DIAGNOSIS: "عیب‌یابی فنی",
    MANAGEMENT_PRICING: "قیمت‌گذاری مدیریت",
    CUSTOMER_APPROVAL: "تأیید مشتری",
    TECHNICAL_REPAIR: "تعمیر فنی",
    TECHNICAL_FINAL_TEST: "تست نهایی فنی",
    RECEPTION_DELIVERY: "آماده تحویل",
  };

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));
  const date = (value) => value ? new Date(value).toLocaleString("fa-IR") : "-";
  const shortDate = (value) => value ? new Date(value).toLocaleDateString("fa-IR") : "-";
  const currentUser = () => sessionUser?.id ? sessionUser : (() => {
    try { return JSON.parse(localStorage.getItem("user") || "{}"); } catch { return {}; }
  })();
  const isPrivileged = () => privilegedRoles.has(currentUser().role);
  const effectiveDepartment = () => currentUser().department || ({
    RECEPTION: "RECEPTION",
    TECHNICAL: "TECHNICAL",
    MANAGEMENT: "MANAGEMENT",
    CUSTOMER_RELATIONS: "CUSTOMER_RELATIONS",
  }[currentUser().role] || null);
  const canOperateCurrentStage = (order) => {
    if (isPrivileged()) return true;
    const department = stageDepartments[order?.current_stage];
    const assignedToCurrentUser = !order?.current_user_id
      || Number(order.current_user_id) === Number(currentUser().id);
    return Boolean(department && effectiveDepartment() === department && assignedToCurrentUser);
  };
  const uploadStageForOrder = (order) => ({
    RECEPTION_INTAKE: "RECEPTION",
    TECHNICAL_DIAGNOSIS: "REPAIR",
    TECHNICAL_REPAIR: "REPAIR",
    TECHNICAL_FINAL_TEST: "TEST",
    RECEPTION_DELIVERY: "DELIVERY",
  }[order?.current_stage] || null);
  const isClosed = (order) =>
    order.current_stage === "COMPLETED" ||
    order.current_stage === "CLOSED_NO_REPAIR" ||
    order.status === "تحویل شده" ||
    order.status === "مختومه بدون تعمیر";

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${token()}`,
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) {
      localStorage.clear();
      location.href = "/login";
      throw new Error("نشست شما منقضی شده است.");
    }
    if (!response.ok) throw new Error(body.detail || "عملیات انجام نشد.");
    return body;
  }

  async function loadSessionUser() {
    if (sessionUser?.id) return sessionUser;
    const body = await api("/auth/verify");
    sessionUser = body.user || {};
    const saved = JSON.parse(localStorage.getItem("user") || "{}");
    localStorage.setItem("user", JSON.stringify({ ...saved, ...sessionUser }));
    return sessionUser;
  }

  function notify(text, icon = "success") {
    if (window.Swal) {
      return Swal.fire({
        icon,
        text,
        timer: icon === "success" ? 1800 : undefined,
        showConfirmButton: icon !== "success",
      });
    }
    alert(text);
  }

  function detailRow(label, value) {
    return `<div class="case-detail-row"><span class="case-detail-label">${escapeHtml(label)}</span><span class="case-detail-value">${escapeHtml(value || "-")}</span></div>`;
  }

  function section(title, body) {
    return `<section class="case-info-section"><h5><i class="fas fa-angle-left"></i> ${escapeHtml(title)}</h5>${body}</section>`;
  }

  function diagnosisStatusLabel(status) {
    return status === "SUBMITTED" ? "نهایی‌شده" : "پیش‌نویس";
  }

  function renderDiagnosisSummary(diagnosisData) {
    const report = diagnosisData?.report;
    if (!report) {
      return section(
        "گزارش حرفه‌ای عیب‌یابی",
        '<div class="text-muted">گزارش حرفه‌ای عیب‌یابی هنوز ثبت نشده است.</div>',
      );
    }
    const parts = report.parts || [];
    const partsHtml = parts.length
      ? `<div class="table-responsive"><table class="table table-sm align-middle mb-0">
          <thead><tr><th>قطعه</th><th>تعداد</th><th>قیمت واحد</th><th>تلورانس</th><th>منبع</th></tr></thead>
          <tbody>${parts.map((part) => `<tr>
            <td>${escapeHtml(part.part_name)}${part.part_number ? `<small class="d-block text-muted">${escapeHtml(part.part_number)}</small>` : ""}</td>
            <td>${escapeHtml(part.quantity)}</td>
            <td>${escapeHtml(part.unit_price ?? "-")}</td>
            <td>${escapeHtml(part.price_tolerance_percent ?? "-")}%</td>
            <td>${part.price_source_url ? `<a href="${escapeHtml(part.price_source_url)}" target="_blank" rel="noopener">مشاهده منبع</a>` : "-"}</td>
          </tr>`).join("")}</tbody>
        </table></div>`
      : '<div class="text-muted">قطعه‌ای ثبت نشده است.</div>';
    return section(
      "گزارش حرفه‌ای عیب‌یابی",
      `<div class="d-flex flex-wrap gap-2 mb-3">
        <span class="badge ${report.status === "SUBMITTED" ? "bg-success" : "bg-warning text-dark"}">${diagnosisStatusLabel(report.status)}</span>
        <span class="badge bg-primary">نسخه ${escapeHtml(report.version)}</span>
        <span class="badge bg-info text-dark">مدت: ${escapeHtml(report.estimated_duration_hours)} ساعت ± ${escapeHtml(report.duration_tolerance_percent)}%</span>
        <span class="badge bg-secondary">اطمینان: ${escapeHtml(report.confidence_percent)}%</span>
      </div>
      ${detailRow("تکنسین عیب‌یاب", report.technician_name)}
      ${detailRow("علت اصلی", report.root_cause)}
      ${detailRow("یافته‌های فنی", report.findings)}
      ${detailRow("محدوده و مسیر پیشنهادی تعمیر", report.repair_scope)}
      <div class="mt-3"><strong>قطعات و اقلام موردنیاز</strong>${partsHtml}</div>`,
    );
  }

  function badges(values, className = "bg-light text-dark") {
    if (!values?.length) return '<span class="text-muted">ثبت نشده</span>';
    return values.map(value => `<span class="badge ${className} me-1 mb-1">${escapeHtml(value)}</span>`).join("");
  }

  function renderCaseDetails(order, diagnosisData) {
    const customer = order.customer || {};
    const site = order.site || {};
    const panel = order.panel || {};
    const boards = order.boards || [];
    const boardHtml = boards.length
      ? boards.map(board => `<div class="border rounded p-2 mb-2">
          <div class="fw-semibold">${escapeHtml(board.board_type)}</div>
          <small class="text-muted">PN: ${escapeHtml(board.part_number)} · SN: ${escapeHtml(board.serial_number)}${board.revision ? ` · Rev: ${escapeHtml(board.revision)}` : ""}</small>
          ${board.description ? `<div class="small mt-1">${escapeHtml(board.description)}</div>` : ""}
        </div>`).join("")
      : '<span class="text-muted">بردی ثبت نشده است.</span>';

    return `<div class="case-receipt">
      <div class="case-receipt-header">
        <div>
          <div class="text-muted small">کد رهگیری</div>
          <code class="tracking-code">${escapeHtml(order.tracking_code)}</code>
        </div>
        <div class="text-end">
          <span class="badge bg-primary">${escapeHtml(order.status || "-")}</span>
          <div class="small text-muted mt-2">ثبت: ${date(order.reception_date || order.created_at)}</div>
          <div class="small text-muted">اپراتور: ${escapeHtml(order.operator_name || "-")}</div>
        </div>
      </div>
      ${section("اطلاعات مشتری", [
        detailRow("نام", customer.name || order.customer_name),
        detailRow("شرکت", customer.company || order.customer_company),
        detailRow("شماره تماس", customer.phone || order.customer_phone),
        detailRow("آدرس", customer.address || order.customer_address),
      ].join(""))}
      ${section("مسئول و نحوه ارسال", [
        detailRow("نام ارسال‌کننده", order.sender_name),
        detailRow("سمت", order.sender_position),
        detailRow("تلفن ارسال‌کننده", order.sender_phone),
        detailRow("تلفن ثابت", order.sender_landline),
        detailRow("روش ارسال/تحویل", order.delivery_method),
        detailRow("شرکت پیک", order.courier_company),
        detailRow("کد پیگیری ارسال", order.courier_tracking),
      ].join(""))}
      ${section("محل نصب", [
        detailRow("نام محل", site.name),
        detailRow("نوع محل", site.type),
        detailRow("آدرس", site.address),
        detailRow("ساختمان", site.building_name),
        detailRow("مدیر ساختمان", site.building_manager),
        detailRow("تلفن مدیر", site.manager_phone),
        detailRow("تلفن لابی", site.lobby_phone),
        detailRow("مسئول محل", site.responsible_name),
        detailRow("سمت مسئول", site.responsible_position),
        detailRow("تلفن مسئول", site.responsible_phone),
      ].join(""))}
      ${section("اطلاعات پنل", [
        detailRow("برند", panel.brand || order.device_brand),
        detailRow("مدل", panel.model || order.device_model),
        detailRow("شماره سریال", panel.serial_number || order.device_serial_number),
        detailRow("شماره پارت", panel.part_number || order.device_part_number),
        detailRow("نسخه firmware", panel.firmware_version),
        detailRow("نسخه سخت‌افزار", panel.hardware_version),
        detailRow("تعداد loop", panel.loops_count),
        detailRow("تعداد zone", panel.zones_count),
        detailRow("سال نصب", panel.installation_year),
      ].join(""))}
      ${section("ساختار بردها", boardHtml)}
      ${section("وضعیت ظاهری", `<div class="mb-2">${badges(order.physical_damages, "bg-danger-subtle text-danger-emphasis")}</div>${detailRow("توضیحات", order.physical_description)}`)}
      ${section("متعلقات", `<div class="mb-2">${badges(order.accessories, "bg-info-subtle text-info-emphasis")}</div>${detailRow("توضیحات", order.accessories_description)}`)}
      ${section("شرح مشکل مشتری", `<div class="case-note">${escapeHtml(order.customer_complaint || "ثبت نشده")}</div>`)}
      ${renderDiagnosisSummary(diagnosisData)}
      ${section("یادداشت‌ها و تصمیم‌ها", [
        detailRow("یادداشت پرونده", order.notes),
        detailRow("یادداشت عیب‌یابی", order.diagnosis_notes),
        detailRow("قیمت تعیین‌شده", order.quoted_price),
        detailRow("یادداشت قیمت", order.price_notes),
        detailRow("تصمیم مشتری", order.customer_approval),
        detailRow("یادداشت تصمیم مشتری", order.customer_approval_note),
        detailRow("یادداشت تعمیر", order.repair_notes),
        detailRow("یادداشت تست نهایی", order.final_test_notes),
      ].join(""))}
      ${section("مسئولان فنی", [
        detailRow("عیب‌یابی", order.diagnosed_by_user_name),
        detailRow("تعمیر", order.repaired_by_user_name),
        detailRow("تست نهایی", order.final_tested_by_user_name),
        detailRow("مسئول فعلی", order.current_user_name),
      ].join(""))}
      ${section("تاریخ‌های کلیدی", [
        detailRow("ثبت پرونده", order.reception_date || order.created_at ? date(order.reception_date || order.created_at) : null),
        detailRow("شروع بررسی فنی", date(order.technical_review_date)),
        detailRow("ثبت عیب‌یابی", date(order.diagnosis_date)),
        detailRow("شروع تعمیر", date(order.repair_start_date)),
        detailRow("پایان تعمیر", date(order.repair_complete_date)),
        detailRow("تعیین قیمت", date(order.price_decided_at)),
        detailRow("پاسخ مشتری", date(order.customer_response_at)),
        detailRow("تحویل نهایی", date(order.delivered_at || order.final_delivery_date)),
      ].join(""))}
    </div>`;
  }

  function renderImages(items) {
    const images = (items || []).filter(item => item.file_type === "photo" || (item.mime_type || "").startsWith("image/"));
    if (!images.length) return '<div class="text-muted py-3">تصویری برای نمایش ثبت نشده است.</div>';
    return `<div id="caseImageCarousel" class="carousel slide" data-bs-ride="false">
      <div class="carousel-inner rounded">${images.map((item, index) => `<div class="carousel-item ${index === 0 ? "active" : ""}">
        <img src="${escapeHtml(item.file_path)}" class="d-block w-100" style="max-height:420px;object-fit:contain;background:#f8f9fa" alt="${escapeHtml(item.file_name)}">
        <div class="carousel-caption d-block bg-dark bg-opacity-50 rounded">
          <span>${escapeHtml(stageLabels[item.stage] || item.stage || "عمومی")}</span> · ${escapeHtml(item.file_name)}
        </div>
      </div>`).join("")}</div>
      <button class="carousel-control-prev" type="button" data-bs-target="#caseImageCarousel" data-bs-slide="prev"><span class="carousel-control-prev-icon"></span></button>
      <button class="carousel-control-next" type="button" data-bs-target="#caseImageCarousel" data-bs-slide="next"><span class="carousel-control-next-icon"></span></button>
    </div>`;
  }

  function renderAttachments(items) {
    if (!items?.length) return '<div class="text-muted">فایلی برای این پرونده ثبت نشده است.</div>';
    return `<div class="row g-3">${items.map(item => `<div class="col-md-6 col-xl-4">
      <div class="border rounded p-3 h-100 ${item.is_delivery_receipt ? "border-success" : ""}">
        <div class="d-flex justify-content-between gap-2">
          <div class="fw-semibold text-truncate" title="${escapeHtml(item.file_name)}">${escapeHtml(item.file_name)}</div>
          ${item.is_delivery_receipt ? '<span class="badge bg-success">رسید تحویل</span>' : ""}
        </div>
        <div class="small text-muted mt-2">${escapeHtml(stageLabels[item.stage] || item.stage || "عمومی")} · ${date(item.uploaded_at)}</div>
        <div class="small mt-1">آپلودکننده: <strong>${escapeHtml(item.uploaded_by_name || "نامشخص")}</strong></div>
        <div class="small text-muted">بخش: ${escapeHtml(item.uploaded_by_department || "نامشخص")}</div>
        ${item.description ? `<div class="small mt-2">${escapeHtml(item.description)}</div>` : ""}
        <div class="d-flex gap-2 mt-3">
          <a class="btn btn-sm btn-outline-primary" target="_blank" href="${escapeHtml(item.file_path)}">مشاهده</a>
          ${item.can_delete ? `<button type="button" class="btn btn-sm btn-outline-danger" data-delete-attachment="${item.id}">حذف</button>` : ""}
        </div>
      </div>
    </div>`).join("")}</div>`;
  }

  function renderTimeline(items) {
    if (!items?.length) return '<div class="text-muted py-3">رویدادی برای نمایش ثبت نشده است.</div>';
    return `<div class="case-timeline">${items.map(item => `<div class="case-timeline-item">
      <div class="case-timeline-dot"></div>
      <div class="case-timeline-content">
        <div class="d-flex justify-content-between gap-2"><strong>${escapeHtml(item.title)}</strong><small class="text-muted">${date(item.created_at)}</small></div>
        <div class="small text-muted">${escapeHtml(stageLabels[item.stage] || item.stage || "")}${item.actor_name ? ` · ${escapeHtml(item.actor_name)}` : ""}</div>
        ${item.description ? `<div class="mt-1">${escapeHtml(item.description)}</div>` : ""}
      </div>
    </div>`).join("")}</div>`;
  }

  function formatDuration(seconds) {
    if (seconds == null) return "در حال اجرا";
    const total = Math.max(0, Number(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    return hours ? `${hours} ساعت و ${minutes} دقیقه` : `${minutes} دقیقه`;
  }

  function renderTimings(items, order) {
    if (!timedStages.has(order.current_stage) && !items?.length) return "";
    const running = items?.find(item => item.stage === order.current_stage && item.status === "RUNNING");
    const canControl = canOperateCurrentStage(order);
    return `<div class="card border-primary mb-3"><div class="card-header bg-primary text-white"><i class="fas fa-stopwatch"></i> زمان‌سنجی مراحل فنی</div>
      <div class="card-body">
        ${timedStages.has(order.current_stage) && canControl ? `<div class="d-flex justify-content-between align-items-center mb-3"><span>مرحله فعال: <strong>${escapeHtml(stageLabels[order.current_stage])}</strong></span>
          <button id="timingButton" class="btn ${running ? "btn-danger" : "btn-success"}">${running ? "پایان مرحله" : "شروع مرحله"}</button></div>` : ""}
        <div class="table-responsive"><table class="table table-sm mb-0"><thead><tr><th>مرحله</th><th>تکنسین</th><th>شروع</th><th>پایان</th><th>مدت</th></tr></thead>
          <tbody>${items?.length ? items.map(item => `<tr><td>${escapeHtml(stageLabels[item.stage] || item.stage)}</td><td>${escapeHtml(item.user_name || "-")}</td><td>${date(item.started_at)}</td><td>${date(item.completed_at)}</td><td>${formatDuration(item.duration_seconds)}</td></tr>`).join("") : '<tr><td colspan="5" class="text-muted">زمان‌سنجی ثبت نشده است.</td></tr>'}</tbody>
        </table></div>
      </div></div>`;
  }

  async function handleTiming(stage, running) {
    const result = running
      ? await Swal.fire({ title: "یادداشت پایان مرحله", input: "textarea", showCancelButton: true, confirmButtonText: "ثبت پایان", cancelButtonText: "انصراف" })
      : { isConfirmed: true, value: "" };
    if (!result.isConfirmed) return;
    await api(`/api/workflow/orders/${orderId}/timing/${running ? "complete" : "start"}`, {
      method: "POST",
      body: JSON.stringify({ stage, note: result.value || null }),
    });
    notify(running ? "پایان مرحله ثبت شد." : "شروع مرحله ثبت شد.");
    await loadOrder();
  }

  async function uploadStageFile() {
    const input = document.getElementById("stageFile");
    const file = input?.files?.[0];
    if (!file) return notify("یک فایل انتخاب کنید.", "warning");
    const form = new FormData();
    form.append("file", file);
    form.append("stage", document.getElementById("fileStage").value);
    form.append("description", document.getElementById("fileDescription").value.trim());
    form.append("is_delivery_receipt", document.getElementById("isDeliveryReceipt").checked ? "true" : "false");
    const response = await fetch(`/reception/repair-orders/${orderId}/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token()}` },
      body: form,
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "آپلود انجام نشد.");
    notify("فایل با موفقیت ثبت شد.");
    await loadOrder();
  }

  async function deleteAttachment(attachmentId) {
    const result = await Swal.fire({
      icon: "warning",
      title: "حذف فایل",
      text: "این فایل حذف شود؟ حذف فایل در تاریخچه پرونده ثبت خواهد شد.",
      showCancelButton: true,
      confirmButtonText: "بله، حذف شود",
      cancelButtonText: "انصراف",
      confirmButtonColor: "#dc3545",
    });
    if (!result.isConfirmed) return;
    try {
      await api(`/reception/attachments/${attachmentId}`, { method: "DELETE" });
      notify("فایل حذف شد.");
      await loadOrder();
    } catch (error) {
      notify(error.message, "error");
    }
  }

  function renderDiagnosisHistory(revisions) {
    if (!revisions?.length) {
      return '<div class="text-muted small">هنوز نسخه قبلی برای این گزارش ثبت نشده است.</div>';
    }
    return `<div class="diagnosis-history">${revisions.map((revision) => {
      const snapshot = revision.snapshot || {};
      return `<details class="diagnosis-history-item mb-2">
        <summary class="d-flex justify-content-between gap-2">
          <span><strong>نسخه ${escapeHtml(revision.version)}</strong> — ${escapeHtml(revision.changed_by_name || "کاربر سامانه")}</span>
          <small class="text-muted">${date(revision.created_at)}</small>
        </summary>
        <div class="small mt-2">
          <div class="text-muted mb-2">${escapeHtml(revision.change_summary || "بدون توضیح تغییر")}</div>
          ${snapshot.root_cause ? `<div><strong>علت اصلی:</strong> ${escapeHtml(snapshot.root_cause)}</div>` : ""}
          ${snapshot.findings ? `<div><strong>یافته‌ها:</strong> ${escapeHtml(snapshot.findings)}</div>` : ""}
          ${snapshot.estimated_duration_hours ? `<div><strong>برآورد زمان:</strong> ${escapeHtml(snapshot.estimated_duration_hours)} ساعت ± ${escapeHtml(snapshot.duration_tolerance_percent || 0)}%</div>` : ""}
          <div><strong>تعداد قطعات:</strong> ${escapeHtml((snapshot.parts || []).length)}</div>
        </div>
      </details>`;
    }).join("")}</div>`;
  }

  function diagnosisPartRow(part = {}, editable = true) {
    const disabled = editable ? "" : "disabled";
    return `<div class="diagnosis-part-row row g-2 align-items-end mb-2">
      <div class="col-md-3"><label class="form-label small">نام قطعه</label><input data-part-field="part_name" class="form-control" value="${escapeHtml(part.part_name || "")}" ${disabled} required></div>
      <div class="col-md-2"><label class="form-label small">شماره قطعه</label><input data-part-field="part_number" class="form-control" value="${escapeHtml(part.part_number || "")}" ${disabled}></div>
      <div class="col-md-1"><label class="form-label small">تعداد</label><input data-part-field="quantity" type="number" min="0.01" step="0.01" class="form-control" value="${escapeHtml(part.quantity ?? 1)}" ${disabled} required></div>
      <div class="col-md-2"><label class="form-label small">قیمت واحد</label><input data-part-field="unit_price" type="number" min="0" step="0.01" class="form-control" value="${escapeHtml(part.unit_price ?? "")}" ${disabled}></div>
      <div class="col-md-1"><label class="form-label small">تلورانس٪</label><input data-part-field="price_tolerance_percent" type="number" min="0" max="100" step="0.01" class="form-control" value="${escapeHtml(part.price_tolerance_percent ?? "")}" ${disabled}></div>
      <div class="col-md-2"><label class="form-label small">وضعیت تهیه</label><select data-part-field="availability" class="form-select" ${disabled}>
        <option value="">تعیین نشده</option>
        <option value="AVAILABLE" ${part.availability === "AVAILABLE" ? "selected" : ""}>موجود</option>
        <option value="ORDER_REQUIRED" ${part.availability === "ORDER_REQUIRED" ? "selected" : ""}>نیازمند سفارش</option>
        <option value="UNKNOWN" ${part.availability === "UNKNOWN" ? "selected" : ""}>نامشخص</option>
      </select></div>
      <div class="col-md-1"><button type="button" class="btn btn-outline-danger w-100" data-remove-part ${disabled ? "disabled" : ""}><i class="fas fa-trash"></i></button></div>
      <div class="col-md-5"><label class="form-label small">لینک منبع قیمت</label><input data-part-field="price_source_url" type="url" class="form-control" value="${escapeHtml(part.price_source_url || "")}" ${disabled}></div>
      <div class="col-md-7"><label class="form-label small">یادداشت قطعه</label><input data-part-field="notes" class="form-control form-control-sm" placeholder="جایگزین یا وضعیت تهیه" value="${escapeHtml(part.notes || "")}" ${disabled}></div>
    </div>`;
  }

  function renderDiagnosisForm(diagnosisData) {
    const report = diagnosisData?.report || {};
    const editable = Boolean(diagnosisData?.can_edit);
    const disabled = editable ? "" : "disabled";
    const customerComplaint = report.customer_complaint
      || diagnosisData?.customer_complaint
      || report.symptom_summary
      || "ثبت نشده";
    const parts = report.parts?.length ? report.parts : [{}];
    return `<div class="diagnosis-workspace">
      <div class="diagnosis-header d-flex justify-content-between align-items-start gap-3 flex-wrap mb-3">
        <div>
          <h5 class="mb-1"><i class="fas fa-stethoscope"></i> گزارش حرفه‌ای عیب‌یابی</h5>
          <p class="text-muted small mb-0">اطلاعات فنی، برآورد زمان و قطعات موردنیاز را کامل ثبت کنید تا مرحله بعدی بدون دوباره‌کاری انجام شود.</p>
        </div>
        <div class="d-flex gap-2">
          ${report.status ? `<span class="badge ${report.status === "SUBMITTED" ? "bg-success" : "bg-warning text-dark"}">${diagnosisStatusLabel(report.status)}</span>` : '<span class="badge bg-secondary">ثبت نشده</span>'}
          ${report.version ? `<span class="badge bg-primary">نسخه ${escapeHtml(report.version)}</span>` : ""}
        </div>
      </div>
      <form id="diagnosisReportForm" class="diagnosis-form">
        <fieldset ${disabled}>
          <div class="row g-3">
            <div class="col-12"><label class="form-label">خلاصه علائم و درخواست مشتری</label><textarea class="form-control" rows="3" readonly>${escapeHtml(customerComplaint)}</textarea><div class="form-text">این متن مستقیماً از شرح ثبت‌شده هنگام پذیرش پرونده نمایش داده می‌شود.</div></div>
            <div class="col-md-6"><label class="form-label">یافته‌های فنی و علائم مشاهده‌شده</label><textarea name="findings" class="form-control" rows="4" required>${escapeHtml(report.findings || "")}</textarea></div>
            <div class="col-md-6"><label class="form-label">علت اصلی یا ریشه خرابی</label><textarea name="root_cause" class="form-control" rows="4" required>${escapeHtml(report.root_cause || "")}</textarea></div>
            <div class="col-12"><label class="form-label">محدوده و مسیر پیشنهادی تعمیر</label><textarea name="repair_scope" class="form-control" rows="5" required>${escapeHtml(report.repair_scope || "")}</textarea></div>
            <div class="col-md-4"><label class="form-label">برآورد زمان تعمیر (ساعت)</label><input name="estimated_duration_hours" type="number" min="0.01" step="0.01" class="form-control" value="${escapeHtml(report.estimated_duration_hours ?? "")}" required></div>
            <div class="col-md-4"><label class="form-label">تلورانس زمانی (درصد)</label><input name="duration_tolerance_percent" type="number" min="0" max="100" step="0.01" class="form-control" value="${escapeHtml(report.duration_tolerance_percent ?? "")}" required></div>
            <div class="col-md-4"><label class="form-label">درصد اطمینان برآورد</label><input name="confidence_percent" type="number" min="0" max="100" step="0.01" class="form-control" value="${escapeHtml(report.confidence_percent ?? "")}" required></div>
          </div>
          <div class="diagnosis-parts mt-4">
            <div class="d-flex justify-content-between align-items-center gap-2 flex-wrap mb-2">
              <div><h6 class="mb-1">قطعات و اقلام موردنیاز</h6><small class="text-muted">قیمت، تلورانس و منبع قیمت هر قطعه را جدا ثبت کنید.</small></div>
              ${editable ? '<button type="button" id="addDiagnosisPart" class="btn btn-sm btn-outline-primary"><i class="fas fa-plus"></i> افزودن قطعه</button>' : ""}
            </div>
            <div id="diagnosisParts">${parts.map((part) => diagnosisPartRow(part, editable)).join("")}</div>
          </div>
        </fieldset>
        ${editable ? `<div class="d-flex flex-wrap gap-2 mt-4">
          <button type="submit" class="btn btn-outline-primary" data-diagnosis-save><i class="fas fa-save"></i> ذخیره پیش‌نویس</button>
          <button type="button" class="btn btn-success" data-diagnosis-submit><i class="fas fa-check-double"></i> ثبت نهایی عیب‌یابی</button>
        </div>` : '<div class="alert alert-secondary mt-4 mb-0"><i class="fas fa-lock"></i> گزارش عیب‌یابی در این مرحله فقط قابل مشاهده است.</div>'}
      </form>
      <div class="diagnosis-history-box mt-4">
        <h6><i class="fas fa-clock-rotate-left"></i> تاریخچه نسخه‌های گزارش</h6>
        ${renderDiagnosisHistory(diagnosisData?.revisions)}
      </div>
    </div>`;
  }

  function collectDiagnosisPayload(submit = false) {
    const form = document.getElementById("diagnosisReportForm");
    const value = (name) => form.querySelector(`[name="${name}"]`)?.value.trim() || null;
    const number = (name) => {
      const raw = form.querySelector(`[name="${name}"]`)?.value;
      return raw === "" || raw == null ? null : Number(raw);
    };
    const parts = [...form.querySelectorAll(".diagnosis-part-row")].map((row) => {
      const field = (name) => row.querySelector(`[data-part-field="${name}"]`)?.value.trim() || null;
      const numeric = (name) => {
        const raw = row.querySelector(`[data-part-field="${name}"]`)?.value;
        return raw === "" || raw == null ? null : Number(raw);
      };
      return {
        part_name: field("part_name"),
        part_number: field("part_number"),
        quantity: numeric("quantity") || 1,
        unit_price: numeric("unit_price"),
        price_tolerance_percent: numeric("price_tolerance_percent"),
        price_source_url: field("price_source_url"),
        availability: field("availability"),
        notes: field("notes"),
      };
    }).filter((part) => part.part_name);
    return {
      findings: value("findings"),
      root_cause: value("root_cause"),
      repair_scope: value("repair_scope"),
      estimated_duration_hours: number("estimated_duration_hours"),
      duration_tolerance_percent: number("duration_tolerance_percent"),
      confidence_percent: number("confidence_percent"),
      parts,
      submit,
      change_summary: submit ? "گزارش برای ادامه فرآیند نهایی شد." : "پیش‌نویس گزارش به‌روزرسانی شد.",
    };
  }

  async function saveDiagnosisReport(submit = false) {
    const form = document.getElementById("diagnosisReportForm");
    if (!form.reportValidity()) return;
    const payload = collectDiagnosisPayload(submit);
    await api(`/api/workflow/orders/${orderId}/diagnosis-report`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    if (submit) {
      await api(`/api/workflow/orders/${orderId}/action`, {
        method: "POST",
        body: JSON.stringify({ action: "DIAGNOSIS", notes: payload.findings }),
      });
      notify("گزارش عیب‌یابی نهایی و اقدام پرونده ثبت شد.");
    } else {
      notify("پیش‌نویس گزارش عیب‌یابی ذخیره شد.");
    }
    await loadOrder();
  }

  function bindDiagnosisForm() {
    document.getElementById("addDiagnosisPart")?.addEventListener("click", () => {
      document.getElementById("diagnosisParts")?.insertAdjacentHTML("beforeend", diagnosisPartRow({}, true));
      bindPartRemoveButtons();
    });
    bindPartRemoveButtons();
    document.getElementById("diagnosisReportForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      saveDiagnosisReport(false).catch((error) => notify(error.message, "error"));
    });
    document.querySelector("[data-diagnosis-submit]")?.addEventListener("click", () => {
      saveDiagnosisReport(true).catch((error) => notify(error.message, "error"));
    });
  }

  function bindPartRemoveButtons() {
    document.querySelectorAll("[data-remove-part]").forEach((button) => {
      button.onclick = () => {
        const rows = document.querySelectorAll(".diagnosis-part-row");
        if (rows.length > 1) button.closest(".diagnosis-part-row")?.remove();
      };
    });
  }

  async function renderWorkflow(order, diagnosisData, timings) {
    const holder = document.getElementById("workflow-area");
    if (isClosed(order) && !isPrivileged()) {
      holder.innerHTML = '<div class="alert alert-secondary"><i class="fas fa-lock"></i> این پرونده مختومه است و فقط مدیریت می‌تواند آن را تغییر دهد.</div>';
      return;
    }
    const stages = await api("/api/workflow/stages");
    const canOperate = canOperateCurrentStage(order);
    const timingMarkup = renderTimings(timings, order);
    holder.innerHTML = `<div class="small text-muted mb-3">مرحله فعلی: <strong>${escapeHtml(stageLabels[order.current_stage] || order.current_stage || "-")}</strong></div>
      <div id="workflow-action"></div>
      <form id="transferForm" class="row g-2 align-items-end mt-3">
        <div class="col-md-4"><label class="form-label">مرحله بعد</label><select id="workflowStage" class="form-select" required><option value="">انتخاب مرحله</option>${stages.map(item => `<option value="${item.code}" data-department="${item.department}">${escapeHtml(item.label)}</option>`).join("")}</select></div>
        <div class="col-md-4"><label class="form-label">گیرنده</label><select id="workflowRecipient" class="form-select" required><option value="">ابتدا مرحله را انتخاب کنید</option></select></div>
        <div class="col-md-4"><button class="btn btn-primary w-100">ارسال درخواست انتقال</button></div>
        <div class="col-12"><textarea id="workflowNote" class="form-control" rows="2" placeholder="یادداشت انتقال (اختیاری)"></textarea></div>
      </form>`;
    holder.innerHTML = timingMarkup + holder.innerHTML;

    const definition = {
      TECHNICAL_DIAGNOSIS: ["DIAGNOSIS", "ثبت نتیجه عیب‌یابی"],
      MANAGEMENT_PRICING: ["PRICING", "ثبت قیمت پیشنهادی"],
      CUSTOMER_APPROVAL: ["CUSTOMER_DECISION", "ثبت نظر مشتری"],
      TECHNICAL_REPAIR: ["REPAIR_COMPLETE", "ثبت پایان تعمیر"],
      TECHNICAL_FINAL_TEST: ["FINAL_TEST", "ثبت تست نهایی"],
      RECEPTION_DELIVERY: ["DELIVER", "ثبت تحویل به مشتری"],
    }[order.current_stage];

    if (definition) {
      if (definition[0] === "DIAGNOSIS") {
        document.getElementById("workflow-action").innerHTML = renderDiagnosisForm(diagnosisData);
        bindDiagnosisForm();
      } else {
      document.getElementById("workflow-action").innerHTML = `<form id="actionForm" class="border rounded p-3 bg-light">
        <h6>${definition[1]}</h6>
        ${definition[0] === "PRICING" ? '<input id="quotedPrice" type="number" min="0" step="0.01" class="form-control mb-2" placeholder="مبلغ پیشنهادی">' : ""}
        <textarea id="actionNotes" class="form-control mb-2" rows="2" placeholder="توضیحات"></textarea>
        ${definition[0] === "CUSTOMER_DECISION"
          ? '<button type="button" class="btn btn-success me-2" data-approved="true">مشتری موافق است</button><button type="button" class="btn btn-outline-danger" data-approved="false">مشتری مخالف است</button>'
          : '<button class="btn btn-outline-primary">ثبت اقدام</button>'}
      </form>`;
      const submit = async (approved) => {
        await api(`/api/workflow/orders/${orderId}/action`, {
          method: "POST",
          body: JSON.stringify({
            action: definition[0],
            notes: document.getElementById("actionNotes").value.trim() || null,
            quoted_price: document.getElementById("quotedPrice")?.value ? Number(document.getElementById("quotedPrice").value) : null,
            approved,
          }),
        });
        notify("اقدام پرونده ثبت شد.");
        await loadOrder();
      };
      document.getElementById("actionForm").addEventListener("submit", (event) => {
        event.preventDefault();
        submit(null).catch(error => notify(error.message, "error"));
      });
      document.querySelectorAll("[data-approved]").forEach(button =>
        button.addEventListener("click", () => submit(button.dataset.approved === "true").catch(error => notify(error.message, "error")))
      );
      }
    }

    if (!canOperate) {
      document.getElementById("actionForm")?.classList.add("d-none");
      document.getElementById("transferForm")?.classList.add("d-none");
      document.getElementById("workflow-action")?.insertAdjacentHTML(
        "beforeend",
        '<div class="alert alert-secondary mt-3 mb-0"><i class="fas fa-lock"></i> ط§ط®طھغŒط§ط± ط§ظ†ط¬ط§ظ… ط§ظ‚ط¯ط§ظ… غŒط§ ط§ظ†طھظ‚ط§ظ„ ط¯ط± ط§غŒظ† ظ…ط±ط­ظ„ظ‡ ط¨ط±ط§غŒ ط´ظ…ط§ ظپط¹ط§ظ„ ظ†غŒط³طھ.</div>',
      );
      const permissionAlert = document.querySelector("#workflow-action .alert-secondary.mt-3");
      if (permissionAlert) permissionAlert.innerHTML = '<i class="fas fa-lock"></i> اختیار انجام اقدام یا انتقال در این مرحله برای شما فعال نیست.';
    }

    document.getElementById("workflowStage")?.addEventListener("change", async (event) => {
      const stage = event.target.value;
      const department = event.target.selectedOptions[0]?.dataset.department;
      const recipient = document.getElementById("workflowRecipient");
      recipient.innerHTML = "<option>در حال بارگذاری...</option>";
      if (!department) {
        recipient.innerHTML = '<option value="">انتخاب گیرنده</option>';
        return;
      }
      try {
        let users = await api(`/api/panel/users/by-department/${encodeURIComponent(department)}`);
        if (stage === "TECHNICAL_REPAIR") {
          users = users.filter(user => Number(user.id) === Number(order.diagnosed_by_user_id));
        }
        if (stage === "TECHNICAL_FINAL_TEST") {
          const excluded = new Set([order.diagnosed_by_user_id, order.repaired_by_user_id].filter(Boolean).map(Number));
          users = users.filter(user => !excluded.has(Number(user.id)));
        }
        recipient.innerHTML = '<option value="">انتخاب گیرنده</option>' +
          users.map(user => `<option value="${user.id}">${escapeHtml(user.full_name)} (${escapeHtml(user.username)})</option>`).join("");
        if (!users.length) recipient.innerHTML = '<option value="">تکنسین مجاز پیدا نشد</option>';
      } catch (error) {
        recipient.innerHTML = '<option value="">کاربری پیدا نشد</option>';
        notify(error.message, "error");
      }
    });

    document.getElementById("transferForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const stage = document.getElementById("workflowStage").value;
      try {
        await api(`/api/workflow/orders/${orderId}/transfer`, {
          method: "POST",
          body: JSON.stringify({
            stage,
            to_department: document.getElementById("workflowStage").selectedOptions[0]?.dataset.department,
            to_user_id: Number(document.getElementById("workflowRecipient").value),
            note: document.getElementById("workflowNote").value.trim() || null,
          }),
        });
        notify("درخواست انتقال ثبت شد و کارت در وضعیت «در انتظار انتقال» قرار گرفت.");
        await loadOrder();
      } catch (error) {
        notify(error.message, "error");
      }
    });
  }

  function renderOrder(order, attachments, timings, timeline, diagnosisData) {
    const closed = isClosed(order);
    document.getElementById("order-detail").innerHTML = `<div class="card shadow-sm border-0">
      <div class="card-header d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div><h4 class="mb-1">پرونده ${escapeHtml(order.tracking_code || `#${order.id}`)}</h4><small class="text-muted">شناسه پرونده: ${order.id}</small></div>
        <div class="d-flex align-items-center gap-2"><span class="badge ${closed ? "bg-secondary" : "bg-primary"}">${escapeHtml(order.status || "-")}</span>${closed ? '<span class="badge bg-dark"><i class="fas fa-lock"></i> مختومه</span>' : ""}</div>
      </div>
      <div class="card-body">
        <ul class="nav nav-pills case-tabs mb-4" role="tablist">
          <li class="nav-item"><button class="nav-link active" data-bs-toggle="pill" data-bs-target="#caseDetailsTab" type="button">جزئیات برگه پذیرش</button></li>
          <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#caseFilesTab" type="button">تصاویر و فایل‌ها <span class="badge bg-secondary">${attachments.length}</span></button></li>
          <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#caseWorkflowTab" type="button">گردش پرونده</button></li>
          <li class="nav-item"><button class="nav-link" data-bs-toggle="pill" data-bs-target="#caseTimelineTab" type="button">تایم‌لاین تصویری</button></li>
        </ul>
        <div class="tab-content">
          <div class="tab-pane fade show active" id="caseDetailsTab">${renderCaseDetails(order, diagnosisData)}</div>
          <div class="tab-pane fade" id="caseFilesTab">
            <div class="card border-0 bg-light mb-4"><div class="card-body">
              <h6><i class="fas fa-upload"></i> افزودن عکس یا فایل مرحله‌ای</h6>
              ${closed && !isPrivileged() ? '<div class="alert alert-secondary mb-0">پرونده مختومه است؛ فقط مدیریت می‌تواند فایل اضافه کند.</div>' : `<div class="row g-2 align-items-end">
                <div class="col-md-3"><label class="form-label">مرحله</label><select id="fileStage" class="form-select"><option value="RECEPTION">پذیرش</option><option value="REPAIR">تعمیر</option><option value="TEST">تست</option><option value="DELIVERY">تحویل</option></select></div>
                <div class="col-md-3"><label class="form-label">فایل</label><input id="stageFile" type="file" class="form-control"></div>
                <div class="col-md-4"><label class="form-label">توضیح</label><input id="fileDescription" class="form-control" placeholder="توضیح فایل"></div>
                <div class="col-md-2"><button id="uploadStageFile" class="btn btn-success w-100">آپلود</button></div>
                <div class="col-12 form-check mt-2"><input id="isDeliveryReceipt" class="form-check-input" type="checkbox"><label class="form-check-label" for="isDeliveryReceipt">این فایل رسید تحویل مشتری است</label></div>
              </div>`}
            </div></div>
            <div class="mb-4"><h6>تصاویر مرحله‌ای</h6>${renderImages(attachments)}</div>
            <div><h6>فایل‌های ثبت‌شده</h6>${renderAttachments(attachments)}</div>
          </div>
          <div class="tab-pane fade" id="caseWorkflowTab"><div id="workflow-area"></div></div>
          <div class="tab-pane fade" id="caseTimelineTab">${renderTimeline(timeline)}</div>
        </div>
        <div class="mt-4 d-flex flex-wrap gap-2">
          <a class="btn btn-success" href="/reception/repair-orders/${order.id}/receipt" target="_blank"><i class="fas fa-print"></i> چاپ برگه پذیرش</a>
          <a class="btn btn-secondary" href="/orders">بازگشت به پرونده‌ها</a>
          ${isPrivileged() ? '<button id="deleteOrderBtn" class="btn btn-outline-danger"><i class="fas fa-trash"></i> حذف پرونده</button>' : ""}
        </div>
      </div>
    </div>`;

    document.getElementById("timingButton")?.addEventListener("click", () => {
      const running = timings.some(item => item.stage === order.current_stage && item.status === "RUNNING");
      handleTiming(order.current_stage, running).catch(error => notify(error.message, "error"));
    });
    document.getElementById("uploadStageFile")?.addEventListener("click", () => uploadStageFile().catch(error => notify(error.message, "error")));
    document.getElementById("fileStage")?.addEventListener("change", (event) => {
      const receiptToggle = document.getElementById("isDeliveryReceipt");
      const receiptWrapper = receiptToggle?.closest(".form-check");
      const isDelivery = event.target.value === "DELIVERY";
      if (receiptWrapper) receiptWrapper.classList.toggle("d-none", !isDelivery);
      if (!isDelivery && receiptToggle) receiptToggle.checked = false;
    });
    document.querySelectorAll("[data-delete-attachment]").forEach(button =>
      button.addEventListener("click", () => deleteAttachment(Number(button.dataset.deleteAttachment)))
    );
    document.getElementById("deleteOrderBtn")?.addEventListener("click", () => deleteOrder(order));
    const fileStage = document.getElementById("fileStage");
    const allowedUploadStage = uploadStageForOrder(order);
    const receiptToggle = document.getElementById("isDeliveryReceipt");
    const receiptWrapper = receiptToggle?.closest(".form-check");
    if (fileStage) {
      if (!isPrivileged() && allowedUploadStage) {
        fileStage.innerHTML = `<option value="${allowedUploadStage}">${stageLabels[allowedUploadStage]}</option>`;
        fileStage.value = allowedUploadStage;
        fileStage.disabled = true;
      } else if (allowedUploadStage) {
        fileStage.value = allowedUploadStage;
      }
      const uploadRow = fileStage.closest(".row");
      if (!isPrivileged() && !allowedUploadStage) {
        uploadRow?.classList.add("d-none");
        uploadRow?.insertAdjacentHTML(
          "afterend",
          '<div class="alert alert-secondary mb-0">در مرحله فعلی امکان ثبت تصویر مرحله‌ای وجود ندارد.</div>',
        );
      }
    }
    const isDeliveryStage = fileStage?.value === "DELIVERY";
    receiptWrapper?.classList.toggle("d-none", !isDeliveryStage);
  }

  async function deleteOrder(order) {
    const result = await Swal.fire({
      icon: "warning",
      title: "حذف پرونده",
      html: `این عملیات فقط با تأیید مدیر انجام می‌شود.<br>برای تأیید عبارت <code>DELETE_REPAIR_ORDER</code> را وارد کنید.<input id="deleteConfirmation" class="swal2-input" placeholder="عبارت تأیید">`,
      showCancelButton: true,
      confirmButtonText: "تأیید مدیر و حذف",
      cancelButtonText: "انصراف",
      confirmButtonColor: "#dc3545",
      preConfirm: () => {
        const confirmation = document.getElementById("deleteConfirmation").value.trim();
        if (confirmation !== "DELETE_REPAIR_ORDER") {
          Swal.showValidationMessage("عبارت تأیید صحیح نیست.");
          return false;
        }
        return { confirmation };
      },
    });
    if (!result.isConfirmed) return;
    try {
      await api(`/reception/repair-orders/${order.id}`, { method: "DELETE", body: JSON.stringify(result.value) });
      await Swal.fire({ icon: "success", text: "پرونده حذف شد.", timer: 1400, showConfirmButton: false });
      location.href = "/orders";
    } catch (error) {
      notify(error.message, "error");
    }
  }

  async function loadOrder() {
    if (!token()) return (location.href = "/login");
    try {
      await loadSessionUser();
      const [order, attachments, timings, timeline, diagnosisData] = await Promise.all([
        api(`/reception/repair-orders/${orderId}`),
        api(`/reception/repair-orders/${orderId}/attachments`),
        api(`/api/workflow/orders/${orderId}/timings`),
        api(`/api/workflow/orders/${orderId}/timeline`),
        api(`/api/workflow/orders/${orderId}/diagnosis-report`),
      ]);
      renderOrder(order, attachments, timings, timeline, diagnosisData);
      await renderWorkflow(order, diagnosisData, timings);
    } catch (error) {
      document.getElementById("order-detail").innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", loadOrder);
})();
