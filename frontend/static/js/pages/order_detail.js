(() => {
  "use strict";

  const orderId =
    Number(window.orderId) ||
    Number(window.location.pathname.split("/").filter(Boolean).pop());
  const token = () =>
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    "";
  const headers = () => ({
    Authorization: `Bearer ${token()}`,
    "Content-Type": "application/json",
  });
  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]));
  const date = (value) =>
    value ? new Date(value).toLocaleString("fa-IR") : "-";

  async function getJson(url) {
    const response = await fetch(url, { headers: headers() });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || "خطا در دریافت اطلاعات");
    }
    return body;
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || "عملیات انجام نشد");
    }
    return body;
  }

  function message(text, type = "success") {
    if (typeof window.Swal !== "undefined") {
      window.Swal.fire({
        icon: type,
        text,
        timer: type === "success" ? 2200 : undefined,
        showConfirmButton: type !== "success",
      });
    } else {
      window.alert(text);
    }
  }

  function statusBadge(status) {
    const colors = {
      "ثبت شده": "secondary",
      "در حال عیب‌یابی": "info",
      "در انتظار تایید مشتری": "primary",
      "در حال تعمیر": "warning",
      "کنترل نهایی": "secondary",
      "آماده تحویل": "success",
      "تحویل شده": "success",
      "مختومه بدون تعمیر": "danger",
    };
    return `<span class="badge bg-${colors[status] || "secondary"}">${escapeHtml(
      status || "-"
    )}</span>`;
  }

  function renderAttachments(items) {
    if (!items?.length) {
      return '<p class="text-muted mb-0">فایلی برای این پرونده ثبت نشده است.</p>';
    }
    return `<div class="row g-2">${items
      .map(
        (item) => `
        <div class="col-md-4">
          <div class="border rounded p-2 h-100">
            <div class="small text-truncate">${escapeHtml(item.file_name)}</div>
            <a class="btn btn-sm btn-outline-primary mt-2" href="${escapeHtml(
              item.file_path
            )}" target="_blank">مشاهده فایل</a>
          </div>
        </div>`
      )
      .join("")}</div>`;
  }

  function renderWorkflowHistory(items) {
    if (!items?.length) {
      return '<p class="text-muted mb-0">هنوز انتقالی برای این پرونده ثبت نشده است.</p>';
    }
    return items
      .map(
        (item) => `
        <div class="border-bottom py-2">
          <div><strong>${escapeHtml(item.from_user_name || "-")}</strong>
          <i class="fas fa-arrow-left mx-2"></i>
          <strong>${escapeHtml(item.to_user_name || "-")}</strong></div>
          <div class="small text-muted">
            مرحله: ${escapeHtml(item.stage || "-")} |
            وضعیت انتقال: ${escapeHtml(item.status || "-")} |
            ${date(item.created_at)}
          </div>
          ${
            item.rejection_reason
              ? `<div class="small text-danger">دلیل رد: ${escapeHtml(
                  item.rejection_reason
                )}</div>`
              : ""
          }
        </div>`
      )
      .join("");
  }

  function actionDefinition(stage) {
    return {
      TECHNICAL_DIAGNOSIS: {
        action: "DIAGNOSIS",
        title: "ثبت نتیجه عیب‌یابی",
        placeholder: "شرح عیب و نتیجه بررسی فنی",
      },
      MANAGEMENT_PRICING: {
        action: "PRICING",
        title: "ثبت قیمت پیشنهادی",
        placeholder: "توضیحات مربوط به قیمت‌گذاری",
      },
      CUSTOMER_APPROVAL: {
        action: "CUSTOMER_DECISION",
        title: "ثبت نظر مشتری",
        placeholder: "توضیح تماس و تصمیم مشتری",
      },
      TECHNICAL_REPAIR: {
        action: "REPAIR_COMPLETE",
        title: "ثبت پایان تعمیر",
        placeholder: "شرح تعمیرات انجام‌شده",
      },
      TECHNICAL_FINAL_TEST: {
        action: "FINAL_TEST",
        title: "ثبت نتیجه تست نهایی",
        placeholder: "نتیجه تست نهایی",
      },
      RECEPTION_DELIVERY: {
        action: "DELIVER",
        title: "ثبت تحویل دستگاه",
        placeholder: "یادداشت تحویل دستگاه",
      },
    }[stage];
  }

  async function renderWorkflow(order, history) {
    const wrapper = document.getElementById("workflow-area");
    if (!wrapper) return;

    const stages = await getJson("/api/workflow/stages");
    const departments = {
      RECEPTION: "پذیرش",
      TECHNICAL: "فنی",
      MANAGEMENT: "مدیریت",
      CUSTOMER_RELATIONS: "ارتباط با مشتریان",
    };

    wrapper.innerHTML = `
      <div class="card shadow-sm mt-4">
        <div class="card-header bg-white">
          <strong><i class="fas fa-route text-primary"></i> گردش پرونده</strong>
        </div>
        <div class="card-body">
          <div class="small text-muted mb-3">
            مرحله فعلی: <strong>${escapeHtml(order.current_stage || "-")}</strong>
          </div>
          <div id="workflow-action"></div>
          <form id="transfer-form" class="row g-2 align-items-end mt-3">
            <div class="col-md-4">
              <label class="form-label">مرحله بعد</label>
              <select class="form-select" id="workflow-stage" required>
                <option value="">انتخاب مرحله</option>
                ${stages
                  .map(
                    (item) =>
                      `<option value="${item.code}" data-department="${item.department}">${escapeHtml(
                        item.label
                      )}</option>`
                  )
                  .join("")}
              </select>
            </div>
            <div class="col-md-3">
              <label class="form-label">بخش</label>
              <input class="form-control" id="workflow-department" readonly>
            </div>
            <div class="col-md-3">
              <label class="form-label">تکنسین/کاربر مقصد</label>
              <select class="form-select" id="workflow-recipient" required>
                <option value="">ابتدا مرحله را انتخاب کنید</option>
              </select>
            </div>
            <div class="col-md-2">
              <button class="btn btn-primary w-100" type="submit">ارسال انتقال</button>
            </div>
            <div class="col-12">
              <textarea class="form-control" id="workflow-note" rows="2" placeholder="توضیح انتقال (اختیاری)"></textarea>
            </div>
          </form>
          <hr>
          <h6>تاریخچه انتقال‌ها</h6>
          <div>${renderWorkflowHistory(history)}</div>
        </div>
      </div>`;

    const stageSelect = document.getElementById("workflow-stage");
    const departmentInput = document.getElementById("workflow-department");
    const recipientSelect = document.getElementById("workflow-recipient");
    const actionContainer = document.getElementById("workflow-action");

    const definition = actionDefinition(order.current_stage);
    if (definition) {
      const priceField =
        definition.action === "PRICING"
          ? '<input id="quoted-price" type="number" min="0" step="0.01" class="form-control mb-2" placeholder="مبلغ پیشنهادی">'
          : "";
      const approvalField =
        definition.action === "CUSTOMER_DECISION"
          ? `<div class="d-flex gap-2">
               <button type="button" class="btn btn-success" data-approval="true">مشتری موافق است</button>
               <button type="button" class="btn btn-outline-danger" data-approval="false">مشتری مخالف است</button>
             </div>`
          : '<button class="btn btn-outline-primary" type="submit">ثبت اقدام</button>';

      actionContainer.innerHTML = `
        <div class="border rounded p-3 bg-light">
          <h6 class="text-primary">${definition.title}</h6>
          <form id="action-form">
            ${priceField}
            <textarea id="action-notes" class="form-control mb-2" rows="2" placeholder="${definition.placeholder}"></textarea>
            ${approvalField}
          </form>
        </div>`;

      const submitAction = async (approved = null) => {
        try {
          const price = document.getElementById("quoted-price")?.value;
          await postJson(`/api/workflow/orders/${order.id}/action`, {
            action: definition.action,
            notes: document.getElementById("action-notes")?.value.trim() || null,
            quoted_price: price ? Number(price) : null,
            approved,
          });
          message("اقدام workflow با موفقیت ثبت شد.");
          await loadOrder();
        } catch (error) {
          message(error.message, "error");
        }
      };

      document
        .getElementById("action-form")
        .addEventListener("submit", (event) => {
          event.preventDefault();
          submitAction();
        });
      actionContainer.querySelectorAll("[data-approval]").forEach((button) => {
        button.addEventListener("click", () =>
          submitAction(button.dataset.approval === "true")
        );
      });
    }

    stageSelect.addEventListener("change", async () => {
      const option = stageSelect.selectedOptions[0];
      const department = option?.dataset.department || "";
      departmentInput.value = departments[department] || department;
      recipientSelect.innerHTML =
        '<option value="">در حال بارگذاری کاربران...</option>';
      if (!department) return;
      try {
        const users = await getJson(
          `/api/panel/users/by-department/${encodeURIComponent(department)}`
        );
        recipientSelect.innerHTML =
          '<option value="">انتخاب گیرنده</option>' +
          users
            .map(
              (user) =>
                `<option value="${user.id}">${escapeHtml(
                  user.full_name
                )} (${escapeHtml(user.username)})</option>`
            )
            .join("");
      } catch (error) {
        recipientSelect.innerHTML = '<option value="">کاربری پیدا نشد</option>';
        message(error.message, "error");
      }
    });

    document
      .getElementById("transfer-form")
      .addEventListener("submit", async (event) => {
        event.preventDefault();
        const selected = stageSelect.selectedOptions[0];
        try {
          await postJson(`/api/workflow/orders/${order.id}/transfer`, {
            to_user_id: Number(recipientSelect.value),
            to_department: selected?.dataset.department || null,
            stage: stageSelect.value,
            note: document.getElementById("workflow-note").value.trim() || null,
          });
          message("درخواست انتقال ثبت شد و برای گیرنده اعلان ارسال گردید.");
          await loadOrder();
        } catch (error) {
          message(error.message, "error");
        }
      });
  }

  function renderOrder(order, attachments, history) {
    const container = document.getElementById("order-detail");
    container.innerHTML = `
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white d-flex justify-content-between align-items-center">
          <h4 class="mb-0">پرونده #${order.id}</h4>
          ${statusBadge(order.status)}
        </div>
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-6"><div class="border rounded p-3"><strong>کد رهگیری:</strong><br><code>${escapeHtml(order.tracking_code)}</code></div></div>
            <div class="col-md-6"><div class="border rounded p-3"><strong>مرحله فعلی:</strong><br>${escapeHtml(order.current_stage || "-")}</div></div>
            <div class="col-md-6"><div class="border rounded p-3"><strong>مشتری:</strong><br>${escapeHtml(order.customer_name || "-")}<br>${escapeHtml(order.customer_phone || "-")}</div></div>
            <div class="col-md-6"><div class="border rounded p-3"><strong>دستگاه:</strong><br>${escapeHtml(order.device_brand || "-")} ${escapeHtml(order.device_model || "")}<br>سریال: ${escapeHtml(order.device_serial_number || "-")}</div></div>
            <div class="col-12"><div class="border rounded p-3"><strong>شرح مشکل:</strong><br>${escapeHtml(order.customer_complaint || "-")}</div></div>
          </div>
          <div class="mt-4"><h5>فایل‌های ضمیمه</h5>${renderAttachments(attachments)}</div>
          <div id="workflow-area"></div>
          <div class="mt-4 d-flex gap-2 flex-wrap">
            <a class="btn btn-success" href="/reception/repair-orders/${order.id}/receipt" target="_blank"><i class="fas fa-print"></i> چاپ برگ پذیرش</a>
            <a class="btn btn-secondary" href="/orders">بازگشت به پرونده‌ها</a>
          </div>
        </div>
      </div>`;
  }

  async function loadOrder() {
    if (!token()) {
      window.location.href = "/login";
      return;
    }
    if (!orderId || Number.isNaN(orderId)) {
      document.getElementById("order-detail").innerHTML =
        '<div class="alert alert-danger">شناسه پرونده معتبر نیست.</div>';
      return;
    }

    try {
      const [order, attachments, workflowHistory] = await Promise.all([
        getJson(`/reception/repair-orders/${orderId}`),
        getJson(`/reception/repair-orders/${orderId}/attachments`),
        getJson(`/api/workflow/orders/${orderId}/history`),
      ]);
      renderOrder(order, attachments, workflowHistory);
      await renderWorkflow(order, workflowHistory);
    } catch (error) {
      document.getElementById(
        "order-detail"
      ).innerHTML = `<div class="alert alert-danger">${escapeHtml(
        error.message
      )}</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", loadOrder);
})();
