(() => {
  "use strict";

  const token = () =>
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    "";
  const date = (value) =>
    value ? new Date(value).toLocaleString("fa-IR") : "-";
  const escapeHtml = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]));

  const roles = {
    ADMIN: "مدیر سیستم",
    RECEPTION: "پذیرش",
    TECHNICAL: "فنی",
    MANAGEMENT: "مدیریت",
    CUSTOMER_RELATIONS: "ارتباط با مشتریان",
    VIEWER: "مشاهده‌گر",
  };
  const departments = {
    RECEPTION: "پذیرش",
    TECHNICAL: "فنی",
    MANAGEMENT: "مدیریت",
    CUSTOMER_RELATIONS: "ارتباط با مشتریان",
  };

  async function api(url, options = {}) {
    if (!token()) {
      window.location.href = "/login";
      return null;
    }

    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${token()}`,
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (response.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
      return null;
    }

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(body.detail || "خطا در ارتباط با سامانه");
    }
    return body;
  }

  function showError(message) {
    const alertBox = document.getElementById("alertBox");
    if (alertBox) {
      alertBox.innerHTML = `<div class="alert alert-danger">${escapeHtml(message)}</div>`;
    }
  }

  function renderUser(user) {
    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value || "-";
    };

    setText("fullNameText", user.full_name);
    setText("roleBadge", roles[user.role] || user.role);
    setText("profileFullName", user.full_name);
    setText("profileUsername", user.username);
    setText(
      "profileDepartment",
      departments[user.department] || user.department || roles[user.role]
    );
    setText("profileEmail", user.email);
    setText("profilePhone", user.phone);
    setText("profileStatus", user.is_active ? "فعال" : "غیرفعال");

    if (user.role !== "ADMIN") {
      const usersMenu = document.getElementById("usersMenuItem");
      const dashboardMenu = document.getElementById("dashboardMenuItem");
      if (usersMenu) usersMenu.style.display = "none";
      if (dashboardMenu) dashboardMenu.style.display = "none";
    }
  }

  function renderNotifications(items) {
    const list = document.getElementById("notificationsList");
    if (!list) return;

    if (!items.length) {
      list.innerHTML =
        '<div class="text-muted text-center py-4">اعلانی وجود ندارد.</div>';
      return;
    }

    list.innerHTML = items
      .map(
        (item) => `
        <div class="notification-item ${item.is_read ? "" : "notification-unread"}">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div class="flex-grow-1">
              <strong>${escapeHtml(item.title)}</strong>
              <p class="mb-1 text-muted">${escapeHtml(item.message)}</p>
              <small class="text-muted">${date(item.created_at)}</small>
            </div>
            <div class="d-flex flex-wrap gap-1 justify-content-end">
              ${
                item.repair_order_id
                  ? `<a class="btn btn-sm btn-outline-dark" href="/order/${item.repair_order_id}">پرونده</a>`
                  : ""
              }
              ${
                item.is_read
                  ? ""
                  : `<button class="btn btn-sm btn-outline-success" data-read="${item.id}">خواندم</button>`
              }
              <button class="btn btn-sm btn-outline-danger" data-delete-notification="${item.id}">حذف</button>
            </div>
          </div>
        </div>`
      )
      .join("");

    list.querySelectorAll("[data-read]").forEach((button) => {
      button.addEventListener("click", async () => {
        await api(`/api/panel/notifications/${button.dataset.read}/read`, {
          method: "POST",
        });
        await refresh();
      });
    });

    list.querySelectorAll("[data-delete-notification]").forEach((button) => {
      button.addEventListener("click", async () => {
        await api(
          `/api/panel/notifications/${button.dataset.deleteNotification}`,
          { method: "DELETE" }
        );
        await refresh();
      });
    });
  }

  function caseTitle(item) {
    return `پرونده #${escapeHtml(item.repair_order_id)} — ${escapeHtml(
      item.tracking_code || "-"
    )}`;
  }

  function renderCaseList(elementId, items, emptyText, options = {}) {
    const list = document.getElementById(elementId);
    if (!list) return;

    if (!items.length) {
      list.innerHTML = `<div class="text-muted text-center py-4">${emptyText}</div>`;
      return;
    }

    list.innerHTML = items
      .map(
        (item) => `
        <div class="case-item mb-3">
          <div class="d-flex justify-content-between flex-wrap gap-2">
            <div>
              <strong>${caseTitle(item)}</strong>
              <div class="text-muted small mt-1">
                مرحله: ${escapeHtml(item.current_stage || item.stage || "-")}
                | وضعیت: ${escapeHtml(item.status || "-")}
              </div>
              <div class="text-muted small">
                ${escapeHtml(item.panel_name || "دستگاه ثبت نشده")}
                ${item.serial_number ? ` | سریال: ${escapeHtml(item.serial_number)}` : ""}
              </div>
              ${
                item.to_user_name
                  ? `<div class="small mt-1">گیرنده: ${escapeHtml(item.to_user_name)}</div>`
                  : ""
              }
              <div class="small text-muted mt-1">${date(
                item.transferred_at || item.updated_at || item.created_at
              )}</div>
            </div>
            <div class="d-flex align-items-start gap-2">
              <a class="btn btn-sm btn-outline-dark" href="/order/${item.repair_order_id}">مشاهده پرونده</a>
              ${
                options.showReceive && item.transition_id
                  ? `<button class="btn btn-sm btn-success" data-receive="${item.transition_id}">دریافت</button>
                     <button class="btn btn-sm btn-outline-danger" data-reject="${item.transition_id}">رد</button>`
                  : ""
              }
            </div>
          </div>
          ${
            item.note
              ? `<div class="mt-2 small">${escapeHtml(item.note)}</div>`
              : ""
          }
        </div>`
      )
      .join("");

    list.querySelectorAll("[data-receive]").forEach((button) => {
      button.addEventListener("click", async () => {
        await api(`/api/workflow/transitions/${button.dataset.receive}/receive`, {
          method: "POST",
        });
        await refresh();
      });
    });

    list.querySelectorAll("[data-reject]").forEach((button) => {
      button.addEventListener("click", async () => {
        const reason = window.prompt("دلیل رد انتقال را وارد کنید:");
        if (!reason) return;
        await api(`/api/workflow/transitions/${button.dataset.reject}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason }),
        });
        await refresh();
      });
    });
  }

  function renderPanelCases(cases) {
    const pendingTasks = cases.pending_tasks || [];
    const inProgress = cases.in_progress || [];
    const transferred = cases.transferred || [];

    renderCaseList(
      "openCasesList",
      cases.open || [],
      "پرونده‌ی بازی در اختیار شما نیست."
    );
    renderCaseList(
      "transferredCasesList",
      transferred,
      "پرونده‌ای به مرحله‌ی بعد منتقل نکرده‌اید."
    );
    renderCaseList(
      "tasksList",
      [...pendingTasks, ...inProgress],
      "وظیفه یا پرونده‌ی در جریان فعالی ندارید.",
      { showReceive: true }
    );

    const activeTasksCount = document.getElementById("activeTasksCount");
    if (activeTasksCount) {
      activeTasksCount.textContent = pendingTasks.length + inProgress.length;
    }
  }

  async function refresh() {
    try {
      const [user, summary, notifications, cases] = await Promise.all([
        api("/api/panel/me"),
        api("/api/panel/summary"),
        api("/api/panel/notifications"),
        api("/api/panel/cases"),
      ]);

      if (!user || !summary || !cases) return;
      renderUser(user);
      document.getElementById("unreadNotificationsCount").textContent =
        summary.unread_notifications_count || 0;
      document.getElementById("totalNotificationsCount").textContent =
        summary.total_notifications_count || 0;
      document.getElementById("openCasesCount").textContent =
        (cases.open || []).length;
      document.getElementById("transferredCasesCount").textContent =
        (cases.transferred || []).length;
      renderNotifications(notifications || []);
      renderPanelCases(cases);
    } catch (error) {
      showError(error.message);
    }
  }

  async function runNotificationAction(button, action) {
    if (!button) return;
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = "در حال انجام...";
    try {
      await action();
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
      button.textContent = originalText;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document
      .getElementById("refreshNotificationsBtn")
      ?.addEventListener("click", (event) =>
        runNotificationAction(event.currentTarget, refresh)
      );
    document
      .getElementById("markAllNotificationsBtn")
      ?.addEventListener("click", (event) =>
        runNotificationAction(event.currentTarget, async () => {
          await api("/api/panel/notifications/read-all", { method: "POST" });
          await refresh();
        })
      );
    document
      .getElementById("deleteAllNotificationsBtn")
      ?.addEventListener("click", (event) =>
        runNotificationAction(event.currentTarget, async () => {
          if (!window.confirm("همه‌ی اعلان‌ها حذف شوند؟")) return;
          await api("/api/panel/notifications", { method: "DELETE" });
          await refresh();
        })
      );
    document.getElementById("logoutBtn")?.addEventListener("click", (event) => {
      event.preventDefault();
      localStorage.clear();
      window.location.href = "/login";
    });
    refresh();
  });
})();
