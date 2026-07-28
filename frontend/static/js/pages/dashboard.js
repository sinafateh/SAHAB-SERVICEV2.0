// ============================================
// صفحه داشبورد
// ============================================

console.log('✅ dashboard.js شروع به کار کرد');

// ============================================
// تابع بارگذاری آمار
// ============================================
function loadStats() {
    console.log('🔄 بارگذاری آمار...');
    
    // استفاده از fetch به جای $.get برای کنترل بهتر
    var token = localStorage.getItem('access_token');
    
    fetch('/reception/stats', {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        if (!response.ok) {
            throw new Error('خطا در دریافت آمار: ' + response.status);
        }
        return response.json();
    })
    .then(function(stats) {
        console.log('📊 آمار دریافت شد:', stats);
        $('#total-orders').text(stats.total || 0);
        $('#repairing-orders').text(stats.repairing || 0);
        $('#waiting-orders').text(stats.waiting_approval || 0);
        $('#ready-orders').text(stats.ready_delivery || 0);
    })
    .catch(function(error) {
        console.error('❌ خطا در دریافت آمار:', error);
        $('#total-orders').text('?');
        $('#repairing-orders').text('?');
        $('#waiting-orders').text('?');
        $('#ready-orders').text('?');
    });
}

// ============================================
// تابع بارگذاری آخرین پرونده‌ها
// ============================================
function loadRecentOrders() {
    console.log('🔄 بارگذاری آخرین پرونده‌ها...');
    
    $('#recent-orders').html(
        '<div class="text-center py-4">' +
            '<i class="fas fa-spinner fa-spin fa-2x text-primary"></i>' +
            '<p class="mt-2 text-muted">در حال بارگذاری...</p>' +
        '</div>'
    );
    
    var token = localStorage.getItem('access_token');
    
    fetch('/reception/repair-orders?limit=10', {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        if (!response.ok) {
            throw new Error('خطا در دریافت اطلاعات: ' + response.status);
        }
        return response.json();
    })
    .then(function(data) {
        console.log('📋 آخرین پرونده‌ها:', data);
        
        if (data && data.length > 0) {
            var html = '<div class="list-group list-group-flush">';
            for (var i = 0; i < data.length; i++) {
                var order = data[i];
                var color = STATUS_COLORS[order.status] || 'secondary';
                html +=
                    '<a href="/order/' + order.id + '" class="list-group-item list-group-item-action">' +
                        '<div class="d-flex justify-content-between align-items-center">' +
                            '<div>' +
                                '<code class="fw-bold">' + order.tracking_code + '</code>' +
                                '<span class="badge bg-' + color + ' ms-2">' + order.status + '</span>' +
                            '</div>' +
                            '<div class="text-end">' +
                                '<small class="text-muted d-block">' + (order.customer_name || '-') + '</small>' +
                                '<small class="text-muted">' + formatDate(order.created_at) + '</small>' +
                            '</div>' +
                        '</div>' +
                    '</a>';
            }
            html += '</div>';
            $('#recent-orders').html(html);
        } else {
            $('#recent-orders').html(
                '<div class="text-center py-4">' +
                    '<i class="fas fa-inbox fa-2x text-muted mb-2"></i>' +
                    '<p class="text-muted">هیچ پرونده‌ای وجود ندارد</p>' +
                    '<a href="/new-order" class="btn btn-sm btn-success">' +
                        '<i class="fas fa-plus"></i> ثبت اولین پرونده' +
                    '</a>' +
                '</div>'
            );
        }
    })
    .catch(function(error) {
        console.error('❌ خطا در بارگذاری آخرین پرونده‌ها:', error);
        $('#recent-orders').html(
            '<div class="alert alert-danger">' +
                '<i class="fas fa-exclamation-triangle"></i> ' +
                'خطا در بارگذاری اطلاعات' +
            '</div>'
        );
    });
}

// ============================================
// بارگذاری اولیه صفحه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در dashboard.js اجرا شد');
    
    // بررسی احراز هویت
    var token = localStorage.getItem('access_token');
    var user = localStorage.getItem('user');
    
    console.log('🔍 بررسی احراز هویت:');
    console.log('  - توکن:', token ? '✅ موجود' : '❌ ناموجود');
    console.log('  - کاربر:', user ? '✅ موجود' : '❌ ناموجود');
    
    if (!token || !user) {
        console.warn('⚠️ احراز هویت نشده، هدایت به لاگین...');
        window.location.href = '/login';
        return;
    }
    
    // بارگذاری داده‌ها
    loadStats();
    loadRecentOrders();
    
    // بارگذاری خودکار هر 30 ثانیه
    setInterval(function() {
        loadStats();
    }, 30000);
    
    console.log('✅ dashboard.js راه‌اندازی شد');
});