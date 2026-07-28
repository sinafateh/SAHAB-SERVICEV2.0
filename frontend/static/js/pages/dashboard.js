// ============================================
// صفحه داشبورد
// ============================================

// ✅ تعریف STATUS_COLORS در همین فایل
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

$(document).ready(function() {
    // دریافت آمار
    $.get('/reception/stats')
        .done(function(stats) {
            $('#total-orders').text(stats.total || 0);
            $('#repairing-orders').text(stats.repairing || 0);
            $('#waiting-orders').text(stats.waiting_approval || 0);
            $('#ready-orders').text(stats.ready_delivery || 0);
        })
        .fail(function() {
            console.error('خطا در دریافت آمار');
        });
    
    // دریافت آخرین پرونده‌ها
    $.get('/reception/repair-orders?limit=10')
        .done(function(data) {
            if (data && data.length > 0) {
                let html = '<div class="list-group">';
                data.forEach(order => {
                    const color = STATUS_COLORS[order.status] || 'secondary';
                    html += `
                        <a href="/order/${order.id}" class="list-group-item list-group-item-action">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <code>${order.tracking_code}</code>
                                    <span class="badge bg-${color} ms-2">${order.status}</span>
                                </div>
                                <div>
                                    <small class="text-muted">${order.customer_name || '-'}</small>
                                    <small class="text-muted ms-2">${formatDate(order.created_at)}</small>
                                </div>
                            </div>
                        </a>
                    `;
                });
                html += '</div>';
                $('#recent-orders').html(html);
            } else {
                $('#recent-orders').html('<p class="text-muted py-3">هیچ پرونده‌ای وجود ندارد</p>');
            }
        })
        .fail(function() {
            $('#recent-orders').html('<p class="text-danger">خطا در بارگذاری اطلاعات</p>');
        });
});