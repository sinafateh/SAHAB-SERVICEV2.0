const loginForm = document.getElementById("loginForm");
const alertBox = document.getElementById("alertBox");
const passwordInput = document.getElementById("password");
const passwordToggle = document.getElementById("passwordToggle");

passwordToggle?.addEventListener("click", () => {
  if (!passwordInput) return;
  const visible = passwordInput.type === "text";
  passwordInput.type = visible ? "password" : "text";
  passwordToggle.setAttribute("aria-label", visible ? "نمایش رمز عبور" : "مخفی کردن رمز عبور");
  passwordToggle.setAttribute("title", visible ? "نمایش رمز عبور" : "مخفی کردن رمز عبور");
  const icon = passwordToggle.querySelector("i");
  if (icon) icon.className = visible ? "fas fa-eye" : "fas fa-eye-slash";
});

async function redirectAuthenticatedUser() {
  const token = localStorage.getItem("access_token");
  if (!token) return;

  try {
    const response = await fetch("/auth/verify", {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.ok) {
      window.location.replace("/panel");
      return;
    }
  } catch (error) {
    console.warn("Could not verify existing session:", error);
  }

  localStorage.removeItem("access_token");
  localStorage.removeItem("token");
  localStorage.removeItem("sahab_token");
  localStorage.removeItem("user");
}

redirectAuthenticatedUser();

function showLoginAlert(message, type = "danger") {
  if (!alertBox) {
    alert(message);
    return;
  }

  alertBox.innerHTML = `
    <div class="alert alert-${type}" role="alert">
      ${message}
    </div>
  `;
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value.trim();

    const password = document.getElementById("password").value;

    if (!username || !password) {
      showLoginAlert("نام کاربری و رمز عبور را وارد کنید.");
      return;
    }

    const formData = new URLSearchParams();

    formData.append("username", username);
    formData.append("password", password);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "نام کاربری یا رمز عبور صحیح نیست.");
      }

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("sahab_token", data.access_token);

      if (data.full_name) {
        localStorage.setItem("user_full_name", data.full_name);
      }

      if (data.role) {
        localStorage.setItem("user_role", data.role);
      }
      localStorage.setItem("user", JSON.stringify({
        id: data.id,
        username: data.username,
        full_name: data.full_name,
        role: data.role,
        department: data.department || null,
      }));

      window.location.replace("/panel");
    } catch (error) {
      console.error(error);
      showLoginAlert(error.message || "خطا در ورود به سیستم.");
    }
  });
}
