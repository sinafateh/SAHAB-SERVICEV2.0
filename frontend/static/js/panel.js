(() => {
  "use strict";

  const token = () => localStorage.getItem("access_token") || localStorage.getItem("token") || "";
  const headers = () => ({ Authorization: `Bearer ${token()}`, "Content-Type": "application/json" });
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[c]));
  const date = (value) => value ? new Date(value).toLocaleString("fa-IR") : "-";
  const roles = { ADMIN: "مدیر سیستم", RECEPTION: "پذیرش", TECHNICAL: "فنی", MANAGEMENT: "مدیریت", CUSTOMER_RELATIONS: "ارتباط با مشتریان", VIEWER: "مشاهده‌گر" };
  const departments = { RECEPTION: "پذیرش", TECHNICAL: "فنی", MANAGEMENT: "مدیریت", CUSTOMER_RELATIONS: "ارتباط با مشتریان" };

  async function api(url, options = {}) {
    if (!token()) { location.href = "/login"; return null; }
    const response = await fetch(url, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
    if (response.status === 401) { localStorage.clear(); location.href = "/login"; return null; }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "خطا در ارتباط با سامانه");
    return body;
  }

  function showError(message) {
    document.getElementById("alertBox").innerHTML = `<div class="alert alert-danger">${escapeHtml(message)}</div>`;
  }

  function renderUser(user) {
    document.getElementById("fullNameText").textContent = user.full_name || "-";
    document.getElementById("roleBadge").textContent = roles[user.role] || user.role || "-";
    document.getElementById("profileFullName").textContent = user.full_name || "-";
    document.getElementById("profileUsername").textContent = user.username || "-";
    document.getElementById("profileDepartment").textContent = departments[user.department] || user.department || roles[user.role] || "-";
    document.getElementById("profileEmail").textContent = user.email || "-";
    document.getElementById("profilePhone").textContent = user.phone || "-";
    document.getElementById("profileStatus").textContent = user.is_active ? "فعال" : "غیرفعال";
    if (user.role !== "ADMIN") {
      document.getElementById("usersMenuItem").style.display = "none";
      document.getElementById("dashboardMenuItem").style.display = "none";
    }
  }

  function renderNotifications(items) {
    const list = document.getElementById("notificationsList");
    if (!items.length) { list.innerHTML = '<div class="text-muted text-center py-4">اعلانی وجود ندارد.</div>'; return; }
    list.innerHTML = items.map((item) => `
      <div class="notification-item ${item.is_read ? "" : "notification-unread"}">
        <div class="d-flex justify-content-between gap-2">
          <div><strong>${escapeHtml(item.title)}</strong><p class="mb-1 text-muted">${escapeHtml(item.message)}</p><small class="text-muted">${date(item.created_at)}</small></div>
          <div class="d-flex flex-column gap-1">
            ${item.repair_order_id ? `<a class="btn btn-sm btn-outline-dark" href="/order/${item.repair_order_id}">پرونده</a>` : ""}
            ${item.is_read ? "" : `<button class="btn btn-sm btn-outline-success" data-read="${item.id}">خواندم</button>`}
          </div>
        </div>
      </div>`).join("");
    list.querySelectorAll("[data-read]").forEach((button) => button.addEventListener("click", async () => {
      await api(`/api/panel/notifications/${button.dataset.read}/read`, { method: "POST" });
      await refresh();
    }));
  }

  function renderTasks(tasks) {
    const list = document.getElementById("tasksList");
    document.getElementById("activeTasksCount").textContent = tasks.length;
    if (!tasks.length) { list.innerHTML = '<div class="text-muted text-center py-4">درخواست دریافت فعالی وجود ندارد.</div>'; return; }
    list.innerHTML = tasks.map((task) => `
      <div class="task-item mb-3">
        <div class="d-flex justify-content-between flex-wrap gap-2">
          <div>
            <strong>پرونده #${escapeHtml(task.repair_order_id)}</strong>
            <div class="text-muted small mt-1">فرستنده: ${escapeHtml(task.from_user_name || "-")}</div>
            <div class="text-muted small">مرحله: ${escapeHtml(task.stage || "-")} | زمان: ${date(task.created_at)}</div>
            <div class="mt-2">${escapeHtml(task.note || "بدون توضیح")}</div>
          </div>
          <div class="d-flex gap-2 align-items-start">
            <a class="btn btn-sm btn-outline-dark" href="/order/${task.repair_order_id}">مشاهده پرونده</a>
            <button class="btn btn-sm btn-success" data-receive="${task.transition_id}">دریافت</button>
            <button class="btn btn-sm btn-outline-danger" data-reject="${task.transition_id}">رد</button>
          </div>
        </div>
      </div>`).join("");
    list.querySelectorAll("[data-receive]").forEach((button) => button.addEventListener("click", async () => {
      await api(`/api/workflow/transitions/${button.dataset.receive}/receive`, { method: "POST" });
      await refresh();
    }));
    list.querySelectorAll("[data-reject]").forEach((button) => button.addEventListener("click", async () => {
      const reason = prompt("دلیل رد انتقال را وارد کنید:");
      if (!reason) return;
      await api(`/api/workflow/transitions/${button.dataset.reject}/reject`, { method: "POST", body: JSON.stringify({ reason }) });
      await refresh();
    }));
  }

  async function refresh() {
    try {
      const [user, summary, notifications, tasks] = await Promise.all([
        api("/api/panel/me"), api("/api/panel/summary"), api("/api/panel/notifications"), api("/api/workflow/my-tasks")
      ]);
      renderUser(user);
      document.getElementById("unreadNotificationsCount").textContent = summary.unread_notifications_count || 0;
      document.getElementById("totalNotificationsCount").textContent = summary.total_notifications_count || 0;
      renderNotifications(notifications || []);
      renderTasks(tasks || []);
    } catch (error) { showError(error.message); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("refreshNotificationsBtn").addEventListener("click", refresh);
    document.getElementById("logoutBtn").addEventListener("click", (event) => { event.preventDefault(); localStorage.clear(); location.href = "/login"; });
    refresh();
  });
})();
