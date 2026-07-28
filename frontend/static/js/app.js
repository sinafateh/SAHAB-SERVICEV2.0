// ============================================
// توابع عمومی - app.js
// ============================================

// دریافت توکن
function getToken() {
    return localStorage.getItem('access_token');
}

// دریافت اطلاعات کاربر
function getUser() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            return JSON.parse(userStr);
        } catch {
            return null;
        }
    }
    return null;
}

// خروج از سیستم
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
}

// نمایش پیام موفقیت
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'موفق!',
        text: message,
        confirmButtonColor: '#198754',
        timer: 3000,
        showConfirmButton: true
    });
}

// نمایش پیام خطا
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'خطا!',
        text: message,
        confirmButtonColor: '#dc3545'
    });
}

// فرمت تاریخ
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fa-IR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch {
        return dateString;
    }
}

// نقش‌ها و برچسب‌ها
const ROLE_LABELS = {
    'ADMIN': 'مدیر سیستم',
    'RECEPTION': 'پذیرش',
    'CUSTOMER_RELATIONS': 'روابط با مشتریان',
    'TECHNICAL': 'فنی',
    'VIEWER': 'بیننده'
};

// رنگ‌های وضعیت
const STATUS_COLORS = {
    'ثبت شده': 'secondary',
    'در انتظار بررسی فنی': 'warning',
    'در حال عیب‌یابی': 'info',
    'در انتظار تایید مشتری': 'primary',
    'در حال تعمیر': 'warning',
    'در حال تست': 'info',
    'کنترل نهایی': 'secondary',
    'آماده تحویل': 'success',
    'تحویل شده': 'success',
    'مختومه بدون تعمیر': 'danger'
};

// بررسی احراز هویت - نسخه ساده شده
function checkAuth() {
    const token = getToken();
    const user = getUser();
    
    if (!token || !user) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// نمایش اطلاعات کاربر در Navbar
function displayUserInfo() {
    const user = getUser();
    if (!user) return;
    
    const userDisplay = document.getElementById('userDisplay');
    if (userDisplay) {
        const roleLabel = ROLE_LABELS[user.role] || user.role;
        userDisplay.textContent = user.full_name + ' (' + roleLabel + ')';
    }
    
    // نمایش منوی مدیریت کاربران فقط برای مدیران
    const usersMenu = document.getElementById('usersMenu');
    if (usersMenu) {
        usersMenu.style.display = user.role === 'ADMIN' ? 'block' : 'none';
    }
}

// بارگذاری اولیه - با تاخیر برای اطمینان از لود شدن DOM
$(document).ready(function() {
    // اگر در صفحه login هستیم، نیازی به بررسی نیست
    if (window.location.pathname === '/login') {
        return;
    }
    
    // بررسی احراز هویت
    if (!checkAuth()) {
        return;
    }
    
    // نمایش اطلاعات کاربر
    displayUserInfo();
    
    console.log('✅ سیستم آماده است!');
    console.log('👤 کاربر:', getUser());
    console.log('🔑 توکن:', getToken() ? 'وجود دارد' : 'ندارد');
});