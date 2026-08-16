(() => {
  "use strict";

  if (window.location.pathname === "/login" || window.location.pathname === "/") {
    return;
  }

  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
      return null;
    }
  })();

  const path = window.location.pathname;
  const active = (prefix) => path === prefix || path.startsWith(`${prefix}/`);
  const roleLabel = {
    ADMIN: "مدیر سیستم",
    RECEPTION: "پذیرش",
    TECHNICAL: "فنی",
    MANAGEMENT: "مدیریت",
    CUSTOMER_RELATIONS: "ارتباط با مشتریان",
    VIEWER: "مشاهده‌گر",
  };

  const style = document.createElement("style");
  style.textContent = `
    body.has-app-sidebar { padding-right: 250px; }
    .app-sidebar {
      position: fixed; inset: 0 0 0 auto; width: 250px; z-index: 1040;
      background: #111827; color: #fff; overflow-y: auto;
      box-shadow: -4px 0 18px rgba(15, 23, 42, .12);
    }
    .app-sidebar-brand { padding: 1.25rem 1rem; border-bottom: 1px solid #374151; font-weight: 700; }
    .app-sidebar-user { padding: .8rem 1rem; color: #cbd5e1; font-size: .85rem; border-bottom: 1px solid #1f2937; }
    .app-sidebar a {
      color: #d1d5db; text-decoration: none; display: block; padding: .85rem 1rem;
      transition: background .15s ease, color .15s ease;
    }
    .app-sidebar a:hover, .app-sidebar a.active { color: #fff; background: #1f2937; }
    .app-sidebar .sidebar-divider { height: 1px; background: #374151; margin: .5rem 0; }
    .app-sidebar .sidebar-logout { color: #fca5a5; }
    @media (max-width: 768px) {
      body.has-app-sidebar { padding-right: 0; padding-top: 58px; }
      .app-sidebar { inset: 0 0 auto 0; width: 100%; height: auto; max-height: 58px; overflow: hidden; }
      .app-sidebar.is-open { max-height: 100vh; }
      .app-sidebar-toggle { display: block !important; }
      .app-sidebar-nav { display: none; }
      .app-sidebar.is-open .app-sidebar-nav { display: block; }
    }
    .app-sidebar-toggle { display: none; float: left; border: 0; background: transparent; color: #fff; font-size: 1.2rem; }
  `;
  document.head.appendChild(style);

  document.querySelectorAll("body > nav").forEach((nav) => nav.remove());

  const aside = document.createElement("aside");
  aside.className = "app-sidebar";
  aside.innerHTML = `
    <div class="app-sidebar-brand">
      <button class="app-sidebar-toggle" type="button" aria-label="نمایش منو">
        <i class="fas fa-bars"></i>
      </button>
      <i class="fas fa-screwdriver-wrench me-2"></i> سامانه خدمات صحاب
    </div>
    <div class="app-sidebar-user">
      <i class="fas fa-user-circle me-1"></i>
      ${user?.full_name || "کاربر سامانه"}
      <small class="d-block mt-1">${roleLabel[user?.role] || user?.role || ""}</small>
    </div>
    <nav class="app-sidebar-nav">
      <a href="/panel" class="${active("/panel") ? "active" : ""}"><i class="fas fa-user me-2"></i> پنل من</a>
      <a href="/orders" class="${active("/orders") || active("/order") ? "active" : ""}"><i class="fas fa-folder-open me-2"></i> پرونده‌ها</a>
      <a href="/new-order" class="${active("/new-order") ? "active" : ""}"><i class="fas fa-plus-circle me-2"></i> پرونده جدید</a>
      <a href="/dashboard" class="${active("/dashboard") ? "active" : ""}" data-admin-only><i class="fas fa-chart-line me-2"></i> داشبورد مدیریتی</a>
      <a href="/users" class="${active("/users") ? "active" : ""}" data-admin-only><i class="fas fa-users me-2"></i> کاربران</a>
      <div class="sidebar-divider"></div>
      <a href="/login" class="sidebar-logout" data-logout><i class="fas fa-sign-out-alt me-2"></i> خروج</a>
    </nav>`;

  document.body.classList.add("has-app-sidebar");
  document.body.prepend(aside);

  if (user?.role !== "ADMIN") {
    aside.querySelectorAll("[data-admin-only]").forEach((item) => item.remove());
  }
  aside.querySelector("[data-logout]")?.addEventListener("click", () => {
    localStorage.clear();
  });
  aside.querySelector(".app-sidebar-toggle")?.addEventListener("click", () => {
    aside.classList.toggle("is-open");
  });
})();
