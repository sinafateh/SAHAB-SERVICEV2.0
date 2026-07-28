// ============================================
// صفحه لیست پرونده‌ها
// ============================================

console.log('✅ orders.js شروع به کار کرد');

// ============================================
// تابع بارگذاری پرونده‌ها
// ============================================
function loadOrders() {
    console.log('🔄 تابع loadOrders اجرا شد');
    
    var search = $('#searchInput').val().trim();
    var status = $('#statusFilter').val();
    
    // نمایش لودینگ
    $('#orders-table').html(
        '<div class="text-center py-5">' +
            '<i class="fas fa-spinner fa-spin fa-3x text-primary"></i>' +
            '<p class="mt-3 text-muted">در حال بارگذاری...</p>' +
        '</div>'
    );
    
    var url = '/reception/repair-orders';
    var params = new URLSearchParams();
    params.append('skip', '0');
    params.append('limit', '100');
    
    if (status) {
        params.append('status', status);
    }
    
    if (search) {
        url = '/reception/repair-orders/search';
        params.append('q', search);
    }
    
    url += '?' + params.toString();
    console.log('📡 درخواست به:', url);
    
    var token = localStorage.getItem('access_token');
    console.log('🔑 توکن:', token ? 'وجود دارد' : 'ندارد');
    
    fetch(url, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        console.log('📡 پاسخ دریافت شد:', response.status);
        if (!response.ok) {
            throw new Error('HTTP Error: ' + response.status);
        }
        return response.json();
    })
    .then(function(data) {
        console.log('📋 داده دریافت شد:', data);
        renderOrders(data);
    })
    .catch(function(error) {
        console.error('❌ خطا:', error);
        $('#orders-table').html(
            '<div class="alert alert-danger">' +
                '<i class="fas fa-exclamation-triangle"></i> ' +
                'خطا در بارگذاری اطلاعات: ' + error.message +
            '</div>'
        );
    });
}

// ============================================
// تابع رندر کردن پرونده‌ها
// ============================================
function renderOrders(data) {
    console.log('🎨 رندرینگ داده‌ها:', data.length, 'پرونده');
    
    // ✅ استفاده از STATUS_COLORS از window (global)
    var colors = window.STATUS_COLORS || {
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
    
    if (data && data.length > 0) {
        var html = '';
        html += '<div class="table-responsive">';
        html += '<table class="table table-hover table-striped">';
        html += '<thead class="table-light">';
        html += '<tr>';
        html += '<th class="text-center">#</th>';
        html += '<th>کد رهگیری</th>';
        html += '<th>وضعیت</th>';
        html += '<th>نام مشتری</th>';
        html += '<th>دستگاه</th>';
        html += '<th>تاریخ ثبت</th>';
        html += '<th class="text-center">عملیات</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody>';
        
        for (var i = 0; i < data.length; i++) {
            var order = data[i];
            var color = colors[order.status] || 'secondary';
            var deviceInfo = (order.device_brand && order.device_model) ? 
                order.device_brand + ' ' + order.device_model : '-';
            
            html += '<tr>';
            html += '<td class="text-center">' + (i + 1) + '</td>';
            html += '<td><code class="fw-bold">' + order.tracking_code + '</code></td>';
            html += '<td><span class="badge bg-' + color + '">' + order.status + '</span></td>';
            html += '<td>' + (order.customer_name || '-') + '</td>';
            html += '<td><small>' + deviceInfo + '</small></td>';
            html += '<td><small>' + formatDateShort(order.created_at) + '</small></td>';
            html += '<td class="text-center">';
            html += '<a href="/order/' + order.id + '" class="btn btn-sm btn-outline-primary">';
            html += '<i class="fas fa-eye"></i> مشاهده';
            html += '</a>';
            html += '</td>';
            html += '</tr>';
        }
        
        html += '</tbody>';
        html += '</table>';
        html += '</div>';
        html += '<div class="d-flex justify-content-between align-items-center mt-3">';
        html += '<small class="text-muted">' + data.length + ' پرونده نمایش داده شده</small>';
        html += '</div>';
        
        $('#orders-table').html(html);
    } else {
        $('#orders-table').html(
            '<div class="text-center py-5">' +
                '<i class="fas fa-inbox fa-4x text-muted mb-3"></i>' +
                '<h5 class="text-muted">هیچ پرونده‌ای وجود ندارد</h5>' +
                '<p class="text-muted">برای ثبت پرونده جدید، روی دکمه زیر کلیک کنید</p>' +
                '<a href="/new-order" class="btn btn-success mt-2">' +
                    '<i class="fas fa-plus"></i> ثبت اولین پرونده' +
                '</a>' +
            '</div>'
        );
    }
}

// ============================================
// بارگذاری اولیه صفحه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در orders.js اجرا شد');
    
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
    
    // بارگذاری اولیه
    loadOrders();
    
    // دکمه جستجو
    $('#searchBtn').on('click', function() {
        loadOrders();
    });
    
    // جستجو با Enter
    $('#searchInput').on('keyup', function(e) {
        if (e.which === 13) {
            loadOrders();
        }
    });
    
    // فیلتر وضعیت
    $('#statusFilter').on('change', function() {
        loadOrders();
    });
    
    // دکمه پرونده جدید
    $('#newOrderBtn').on('click', function() {
        window.location.href = '/new-order';
    });
    
    console.log('✅ orders.js راه‌اندازی شد');
});