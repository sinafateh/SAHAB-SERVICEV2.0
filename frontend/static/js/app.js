// ============================================
// فایل اصلی JavaScript - مدیریت عمومی
// ============================================

console.log('✅ app.js شروع به کار کرد');

// ============================================
// 1. تنظیمات و پیکربندی
// ============================================

var CONFIG = {
    TOKEN_KEY: 'access_token',
    USER_KEY: 'user',
    LOGIN_URL: '/login',
    HOME_URL: '/'
};

// ============================================
// 2. توابع مدیریت توکن و کاربر
// ============================================

function getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
}

function removeToken() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
}

function getUser() {
    var userStr = localStorage.getItem(CONFIG.USER_KEY);
    if (userStr) {
        try {
            return JSON.parse(userStr);
        } catch (e) {
            return null;
        }
    }
    return null;
}

function setUser(user) {
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
}

function removeUser() {
    localStorage.removeItem(CONFIG.USER_KEY);
}

function isAuthenticated() {
    return !!getToken() && !!getUser();
}

// ============================================
// 3. مدیریت خروج و هدایت
// ============================================

function logout() {
    removeToken();
    removeUser();
    window.location.href = CONFIG.LOGIN_URL;
}

function redirectToLogin() {
    removeToken();
    removeUser();
    window.location.href = CONFIG.LOGIN_URL;
}

function checkAuth() {
    if (!isAuthenticated()) {
        redirectToLogin();
        return false;
    }
    return true;
}

// ============================================
// 4. نمایش اطلاعات کاربر در Navbar
// ============================================

var ROLE_LABELS = {
    'ADMIN': 'مدیر سیستم',
    'RECEPTION': 'پذیرش',
    'CUSTOMER_RELATIONS': 'روابط با مشتریان',
    'TECHNICAL': 'فنی',
    'VIEWER': 'بیننده'
};

function displayUserInfo() {
    var user = getUser();
    if (!user) return;
    
    var userDisplay = document.getElementById('userDisplay');
    if (userDisplay) {
        var roleLabel = ROLE_LABELS[user.role] || user.role;
        userDisplay.textContent = user.full_name + ' (' + roleLabel + ')';
    }
    
    var usersMenu = document.getElementById('usersMenu');
    if (usersMenu) {
        usersMenu.style.display = user.role === 'ADMIN' ? 'block' : 'none';
    }
}

// ============================================
// 5. توابع نمایش پیام
// ============================================

function showSuccess(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'success',
            title: 'موفق!',
            text: message,
            confirmButtonColor: '#198754',
            timer: 3000,
            showConfirmButton: true
        });
    } else {
        alert('✅ ' + message);
    }
}

function showError(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'error',
            title: 'خطا!',
            text: message,
            confirmButtonColor: '#dc3545'
        });
    } else {
        alert('❌ ' + message);
    }
}

function showWarning(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'warning',
            title: 'توجه!',
            text: message,
            confirmButtonColor: '#ffc107'
        });
    } else {
        alert('⚠️ ' + message);
    }
}

function showInfo(message) {
    if (typeof Swal !== 'undefined') {
        Swal.fire({
            icon: 'info',
            title: 'اطلاعات',
            text: message,
            confirmButtonColor: '#0d6efd'
        });
    } else {
        alert('ℹ️ ' + message);
    }
}

// ============================================
// 6. توابع فرمت‌دهی
// ============================================

function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        var date = new Date(dateString);
        return date.toLocaleDateString('fa-IR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

function formatDateShort(dateString) {
    if (!dateString) return '-';
    try {
        var date = new Date(dateString);
        return date.toLocaleDateString('fa-IR', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

function formatFileSize(bytes) {
    if (!bytes) return '0 KB';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

// ============================================
// 7. رنگ‌های وضعیت
// ============================================

var STATUS_COLORS = {
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

function getStatusBadge(status) {
    var color = STATUS_COLORS[status] || 'secondary';
    return '<span class="badge bg-' + color + ' status-badge">' + status + '</span>';
}

// ============================================
// 8. بررسی نقش کاربر
// ============================================

function hasRole(role) {
    var user = getUser();
    if (!user) return false;
    if (user.role === 'ADMIN') return true;
    return user.role === role;
}

function isAdmin() {
    var user = getUser();
    return user && user.role === 'ADMIN';
}

function isTechnical() {
    var user = getUser();
    return user && (user.role === 'ADMIN' || user.role === 'TECHNICAL');
}

function isReception() {
    var user = getUser();
    return user && (user.role === 'ADMIN' || user.role === 'RECEPTION' || user.role === 'CUSTOMER_RELATIONS');
}

// ============================================
// 9. بارگذاری اولیه
// ============================================

$(document).ready(function() {
    console.log('📄 $(document).ready در app.js اجرا شد');
    
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
// ============================================
// 10. قرار دادن متغیرها در Scope Global
// ============================================

// اطمینان از اینکه همه توابع در همه جا در دسترس هستند
window.STATUS_COLORS = STATUS_COLORS;
window.getToken = getToken;
window.getUser = getUser;
window.logout = logout;
window.checkAuth = checkAuth;
window.formatDate = formatDate;
window.formatDateShort = formatDateShort;
window.formatFileSize = formatFileSize;
window.getStatusBadge = getStatusBadge;
window.showSuccess = showSuccess;
window.showError = showError;
window.showWarning = showWarning;
window.showInfo = showInfo;
window.isAdmin = isAdmin;
window.isTechnical = isTechnical;
window.isReception = isReception;
window.hasRole = hasRole;
window.ROLE_LABELS = ROLE_LABELS;

console.log('✅ متغیرهای عمومی در window ثبت شدند');
console.log('  - STATUS_COLORS:', typeof STATUS_COLORS);
console.log('  - checkAuth:', typeof checkAuth);
console.log('  - getToken:', typeof getToken);
console.log('  - getUser:', typeof getUser);