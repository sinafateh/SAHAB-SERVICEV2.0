// ============================================
// صفحه لیست پرونده‌ها
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

function loadOrders() {
    console.log('🔄 در حال بارگذاری پرونده‌ها...');
    
    const search = $('#searchInput').val().trim();
    const status = $('#statusFilter').val();
    
    let url = '/reception/repair-orders';
    
    $('#orders-table').html('<i class="fas fa-spinner fa-spin"></i> در حال بارگذاری...');
    
    fetch(url)
        .then(response => {
            console.log('📡 پاسخ دریافت شد:', response.status);
            if (!response.ok) {
                throw new Error('HTTP error! status: ' + response.status);
            }
            return response.json();
        })
        .then(data => {
            console.log('📋 داده‌های پرونده‌ها:', data);
            
            if (data && data.length > 0) {
                let html = `
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>شناسه</th>
                                    <th>کد رهگیری</th>
                                    <th>وضعیت</th>
                                    <th>نام مشتری</th>
                                    <th>تاریخ ثبت</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                data.forEach(order => {
                    const color = STATUS_COLORS[order.status] || 'secondary';
                    html += `
                        <tr>
                            <td>#${order.id}</td>
                            <td><code>${order.tracking_code}</code></td>
                            <td><span class="badge bg-${color}">${order.status}</span></td>
                            <td>${order.customer_name || '-'}</td>
                            <td>${formatDate(order.created_at)}</td>
                            <td>
                                <a href="/order/${order.id}" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-eye"></i> مشاهده
                                </a>
                            </td>
                        </tr>
                    `;
                });
                html += '</tbody></table></div>';
                $('#orders-table').html(html);
            } else {
                $('#orders-table').html(`
                    <div class="text-center py-4">
                        <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                        <p class="text-muted">هیچ پرونده‌ای وجود ندارد</p>
                        <a href="/new-order" class="btn btn-success">
                            <i class="fas fa-plus"></i> ثبت اولین پرونده
                        </a>
                    </div>
                `);
            }
        })
        .catch(error => {
            console.error('❌ خطا:', error);
            $('#orders-table').html(`
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    خطا در بارگذاری اطلاعات: ${error.message}
                </div>
            `);
        });
}

$(document).ready(function() {
    console.log('📄 صفحه orders لود شد');
    loadOrders();
    
    $('#searchBtn').click(loadOrders);
    $('#searchInput, #statusFilter').keypress(function(e) {
        if (e.which === 13) loadOrders();
    });
});