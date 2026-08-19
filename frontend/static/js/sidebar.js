(() => {
  "use strict";

  if (
    window.location.pathname === "/login" ||
    window.location.pathname === "/" ||
    window.location.pathname === "/panel"
  ) {
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
    body.has-app-sidebar { padding-right: 274px; }
    .app-sidebar {
      position: fixed; inset: 0 0 0 auto; width: 274px; z-index: 1040;
      background: linear-gradient(180deg, rgba(22,75,131,.76), rgba(45,123,200,.58));
      color: #fff; overflow-y: auto; border: 1px solid rgba(255,255,255,.24); border-top: 0; border-bottom: 0; border-radius: 0 0 0 28px;
      backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
      box-shadow: -8px 0 28px rgba(34, 83, 132, .18);
    }
    .app-sidebar-brand { padding: 1.35rem 1rem; border-bottom: 1px solid rgba(255,255,255,.16); font-weight: 700; }
    .app-sidebar-user { margin: .8rem .75rem; padding: .85rem .9rem; color: #e6f2ff; font-size: .85rem; border: 1px solid rgba(255,255,255,.15); border-radius: 16px; background: rgba(255,255,255,.08); }
    .app-sidebar a {
      color: #e7f2ff; text-decoration: none; display: block; margin: .25rem .7rem; padding: .82rem .95rem;
      border-radius: 15px; transition: background .15s ease, color .15s ease, transform .15s ease;
    }
    .app-sidebar a:hover, .app-sidebar a.active { color: #174d8c; background: #fff; transform: translateX(-2px); }
    .app-sidebar .sidebar-divider { height: 1px; background: rgba(255,255,255,.18); margin: .8rem 1rem; }
    .app-sidebar .sidebar-logout { color: #ffe0e4; }
    .app-sidebar .sidebar-logout:hover { color: #a51d32; }
    @media (max-width: 768px) {
      body.has-app-sidebar { padding-right: 0; padding-top: 62px; }
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
      <a href="/closed-orders" class="${active("/closed-orders") ? "active" : ""}"><i class="fas fa-folder-closed me-2"></i> پرونده‌های بسته شده</a>
      <a href="/new-order" class="${active("/new-order") ? "active" : ""}"><i class="fas fa-plus-circle me-2"></i> پرونده جدید</a>
      <a href="/dashboard" class="${active("/dashboard") ? "active" : ""}" data-admin-only><i class="fas fa-chart-line me-2"></i> داشبورد مدیریتی</a>
      <a href="/users" class="${active("/users") ? "active" : ""}" data-admin-only><i class="fas fa-users me-2"></i> کاربران</a>
      <div class="sidebar-divider"></div>
      <a href="/login" class="sidebar-logout" data-logout><i class="fas fa-sign-out-alt me-2"></i> خروج</a>
    </nav>`;

  document.body.classList.add("has-app-sidebar");
  document.body.prepend(aside);

  if (!["ADMIN", "MANAGEMENT"].includes(user?.role)) {
    aside
      .querySelectorAll("[data-admin-only]")
      .forEach((item) => item.remove());
  }
  aside.querySelector("[data-logout]")?.addEventListener("click", () => {
    localStorage.clear();
  });
  aside.querySelector(".app-sidebar-toggle")?.addEventListener("click", () => {
    aside.classList.toggle("is-open");
  });
})();
