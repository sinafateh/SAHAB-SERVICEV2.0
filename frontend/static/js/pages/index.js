// ============================================
// صفحه اصلی
// ============================================

$(document).ready(function() {
    console.log('🏠 صفحه اصلی لود شد');
    
    // اگر کاربر وارد شده باشد، اطلاعات را نمایش بده
    if (isAuthenticated()) {
        const user = getUser();
        $('#userDisplay').text(user.full_name + ' (' + ROLE_LABELS[user.role] + ')');
        
        // نمایش منوی مدیریت کاربران فقط برای مدیران
        if (user.role === 'ADMIN') {
            $('#usersMenu').show();
        }
    } else {
        // اگر وارد نشده، به لاگین هدایت کن
        window.location.href = '/login';
    }
});