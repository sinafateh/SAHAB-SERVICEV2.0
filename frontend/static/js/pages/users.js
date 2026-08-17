(() => {
  "use strict";
  const token = () => localStorage.getItem("access_token") || "";
  const privilegedRoles = new Set(["ADMIN", "MANAGEMENT"]);
  const roles = [
    ["ADMIN", "مدیرکل", "#dc3545"],
    ["MANAGEMENT", "مدیریت", "#6f42c1"],
    ["TECHNICAL", "فنی", "#0d6efd"],
    ["RECEPTION", "پذیرش", "#198754"],
    ["CUSTOMER_RELATIONS", "ارتباط با مشتریان", "#fd7e14"],
  ];
  let users = [];

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
  const roleMeta = role => {
    const item = roles.find(value => value[0] === role);
    return { label: item?.[1] || role || "-", color: item?.[2] || "#6c757d" };
  };
  const roleLabel = role => roleMeta(role).label;

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
    if (!response.ok) throw new Error(body.detail || "عملیات انجام نشد");
    return body;
  }

  function roleOptions(selected = "TECHNICAL") {
    return roles.map(([value, label]) =>
      `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`
    ).join("");
  }

  function renderUsers() {
    const root = document.getElementById("users-table");
    if (!users.length) {
      root.innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-users-slash fa-3x mb-3"></i><p>کاربری ثبت نشده است.</p></div>';
      return;
    }
    const groups = roles
      .map(([role]) => ({ role, users: users.filter(user => user.role === role) }))
      .filter(group => group.users.length);
    const unknownGroups = [...new Set(users.map(user => user.role))]
      .filter(role => !roles.some(item => item[0] === role))
      .map(role => ({ role, users: users.filter(user => user.role === role) }));

    root.innerHTML = [...groups, ...unknownGroups].map(group => {
      const meta = roleMeta(group.role);
      return `<section class="card shadow-sm mb-3 role-group" style="--role-color:${meta.color}">
        <div class="card-header bg-white d-flex justify-content-between align-items-center">
          <strong class="role-group-title"><span class="role-dot"></span>${escapeHtml(meta.label)}</strong>
          <span class="badge rounded-pill" style="background:${meta.color}">${group.users.length} کاربر</span>
        </div>
        <div class="table-responsive"><table class="table table-hover align-middle mb-0">
          <thead><tr><th>#</th><th>نام کامل</th><th>نام کاربری</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>${group.users.map((user, index) => `<tr>
            <td>${index + 1}</td>
            <td>${escapeHtml(user.full_name)}</td>
            <td><code>${escapeHtml(user.username)}</code></td>
            <td><span class="badge bg-${user.is_active ? "success" : "secondary"}">${user.is_active ? "فعال" : "غیرفعال"}</span></td>
            <td class="text-nowrap">
              <button class="btn btn-sm btn-outline-primary" data-edit-user="${user.id}" title="ویرایش"><i class="fas fa-edit"></i></button>
              <button class="btn btn-sm btn-outline-danger" data-delete-user="${user.id}" title="حذف"><i class="fas fa-trash"></i></button>
            </td>
          </tr>`).join("")}</tbody>
        </table></div>
      </section>`;
    }).join("");
    root.querySelectorAll("[data-edit-user]").forEach(button =>
      button.addEventListener("click", () => editUser(Number(button.dataset.editUser)))
    );
    root.querySelectorAll("[data-delete-user]").forEach(button =>
      button.addEventListener("click", () => deleteUser(Number(button.dataset.deleteUser)))
    );
  }

  async function loadUsers() {
    document.getElementById("users-table").innerHTML = '<div class="text-center text-muted py-5"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';
    try {
      users = await api("/auth/users");
      renderUsers();
    } catch (error) {
      document.getElementById("users-table").innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
    }
  }

  async function addUser() {
    const result = await Swal.fire({
      title: "افزودن کاربر جدید",
      html: `<input id="userFullName" class="swal2-input" placeholder="نام کامل">
        <input id="userUsername" class="swal2-input" placeholder="نام کاربری">
        <input id="userPassword" type="password" class="swal2-input" placeholder="رمز عبور (حداقل ۶ کاراکتر)">
        <select id="userRole" class="swal2-select">${roleOptions()}</select>`,
      showCancelButton: true,
      confirmButtonText: "ثبت کاربر",
      cancelButtonText: "انصراف",
      focusConfirm: false,
      preConfirm: () => {
        const full_name = document.getElementById("userFullName").value.trim();
        const username = document.getElementById("userUsername").value.trim();
        const password = document.getElementById("userPassword").value;
        const role = document.getElementById("userRole").value;
        if (!full_name || !username || password.length < 6) {
          Swal.showValidationMessage("نام کامل، نام کاربری و رمز عبور حداقل ۶ کاراکتری الزامی است.");
          return false;
        }
        return { full_name, username, password, role };
      },
    });
    if (!result.isConfirmed) return;
    try {
      await api("/auth/register", { method: "POST", body: JSON.stringify(result.value) });
      await Swal.fire({ icon: "success", text: "کاربر با موفقیت اضافه شد.", timer: 1600, showConfirmButton: false });
      await loadUsers();
    } catch (error) {
      Swal.fire({ icon: "error", text: error.message });
    }
  }

  async function editUser(userId) {
    const user = users.find(item => item.id === userId);
    if (!user) return;
    const result = await Swal.fire({
      title: `ویرایش ${escapeHtml(user.full_name)}`,
      html: `<input id="editFullName" class="swal2-input" value="${escapeHtml(user.full_name)}" placeholder="نام کامل">
        <select id="editRole" class="swal2-select">${roleOptions(user.role)}</select>
        <select id="editActive" class="swal2-select">
          <option value="true" ${user.is_active ? "selected" : ""}>فعال</option>
          <option value="false" ${!user.is_active ? "selected" : ""}>غیرفعال</option>
        </select>
        <input id="editPassword" type="password" class="swal2-input" placeholder="رمز جدید (اختیاری)">`,
      showCancelButton: true,
      confirmButtonText: "ذخیره تغییرات",
      cancelButtonText: "انصراف",
      preConfirm: () => {
        const full_name = document.getElementById("editFullName").value.trim();
        const password = document.getElementById("editPassword").value;
        if (!full_name || (password && password.length < 6)) {
          Swal.showValidationMessage("نام کامل الزامی است و رمز جدید باید حداقل ۶ کاراکتر باشد.");
          return false;
        }
        return {
          full_name,
          role: document.getElementById("editRole").value,
          is_active: document.getElementById("editActive").value === "true",
          ...(password ? { password } : {}),
        };
      },
    });
    if (!result.isConfirmed) return;
    try {
      await api(`/auth/users/${userId}`, { method: "PUT", body: JSON.stringify(result.value) });
      await Swal.fire({ icon: "success", text: "تغییرات ذخیره شد.", timer: 1500, showConfirmButton: false });
      await loadUsers();
    } catch (error) {
      Swal.fire({ icon: "error", text: error.message });
    }
  }

  async function deleteUser(userId) {
    const user = users.find(item => item.id === userId);
    const result = await Swal.fire({
      icon: "warning",
      title: "حذف کاربر",
      text: `کاربر ${user?.full_name || ""} حذف شود؟`,
      showCancelButton: true,
      confirmButtonText: "بله، حذف شود",
      cancelButtonText: "انصراف",
      confirmButtonColor: "#dc3545",
    });
    if (!result.isConfirmed) return;
    try {
      await api(`/auth/users/${userId}`, { method: "DELETE" });
      await loadUsers();
      Swal.fire({ icon: "success", text: "کاربر حذف شد.", timer: 1400, showConfirmButton: false });
    } catch (error) {
      Swal.fire({ icon: "error", text: error.message });
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    if (!token()) return (location.href = "/login");
    let user = {};
    try {
      const verified = await api("/auth/verify");
      user = verified.user || {};
      localStorage.setItem("user", JSON.stringify({ ...JSON.parse(localStorage.getItem("user") || "{}"), ...user }));
    } catch (_) {
      return (location.href = "/login");
    }
    if (!privilegedRoles.has(user.role)) return (location.href = "/panel");
    document.getElementById("addUserBtn").addEventListener("click", addUser);
    document.getElementById("refreshUsersBtn").addEventListener("click", loadUsers);
    await loadUsers();
  });
})();
