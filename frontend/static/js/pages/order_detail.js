// ============================================
// صفحه جزئیات پرونده
// ============================================

function getStatusBadge(status) {
    const colors = {
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
    return `<span class="badge bg-${colors[status] || 'secondary'} status-badge">${status}</span>`;
}

function changeStatus(newStatus, reason = '') {
    const statusMap = {
        'ثبت شده': 'REGISTERED',
        'در انتظار بررسی فنی': 'WAITING_TECHNICAL',
        'در حال عیب‌یابی': 'DIAGNOSING',
        'در انتظار تایید مشتری': 'WAITING_APPROVAL',
        'در حال تعمیر': 'REPAIRING',
        'در حال تست': 'TESTING',
        'کنترل نهایی': 'FINAL_CONTROL',
        'آماده تحویل': 'READY_DELIVERY',
        'تحویل شده': 'DELIVERED',
        'مختومه بدون تعمیر': 'CLOSED_NO_REPAIR'
    };
    
    const englishStatus = statusMap[newStatus];
    if (!englishStatus) {
        showError('وضعیت نامعتبر است');
        return;
    }

    Swal.fire({
        title: 'تغییر وضعیت',
        text: `آیا از تغییر وضعیت به "${newStatus}" مطمئن هستید؟`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#0d6efd',
        cancelButtonColor: '#dc3545',
        confirmButtonText: 'بله، تغییر کن',
        cancelButtonText: 'انصراف'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                url: `/reception/repair-orders/${orderId}/status`,
                method: 'PUT',
                contentType: 'application/json',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                },
                data: JSON.stringify({
                    status: englishStatus,
                    reason: reason || `تغییر وضعیت به ${newStatus}`
                }),
                success: function() {
                    showSuccess('وضعیت با موفقیت تغییر کرد');
                    loadOrder();
                },
                error: function(xhr) {
                    showError(xhr.responseJSON?.detail || 'خطا در تغییر وضعیت');
                }
            });
        }
    });
}

function loadOrder() {
    $.get(`/reception/repair-orders/${orderId}`)
        .done(function(order) {
            $.get(`/reception/repair-orders/${orderId}/history`)
                .done(function(history) {
                    renderOrder(order, history);
                })
                .fail(function() {
                    renderOrder(order, []);
                });
        })
        .fail(function() {
            $('#order-detail').html(`
                <div class="alert alert-danger">
                    <h4><i class="fas fa-exclamation-triangle"></i> خطا در بارگذاری</h4>
                    <a href="/orders" class="btn btn-primary">بازگشت به لیست</a>
                </div>
            `);
        });
}

function renderOrder(order, history) {
    const statusColors = {
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

    // دکمه‌های تغییر وضعیت
    let actionButtons = '';
    const status = order.status;

    if (status === 'ثبت شده') {
        actionButtons = `
            <button class="btn btn-warning" onclick="changeStatus('در انتظار بررسی فنی')">
                <i class="fas fa-tools"></i> تحویل به واحد فنی
            </button>
        `;
    } else if (status === 'در انتظار بررسی فنی') {
        actionButtons = `
            <button class="btn btn-info" onclick="changeStatus('در حال عیب‌یابی')">
                <i class="fas fa-search"></i> شروع عیب‌یابی
            </button>
        `;
    } else if (status === 'در حال عیب‌یابی') {
        actionButtons = `
            <button class="btn btn-primary" onclick="changeStatus('در انتظار تایید مشتری')">
                <i class="fas fa-clock"></i> اعلام هزینه
            </button>
        `;
    } else if (status === 'در انتظار تایید مشتری') {
        actionButtons = `
            <button class="btn btn-success" onclick="changeStatus('در حال تعمیر')">
                <i class="fas fa-wrench"></i> شروع تعمیر
            </button>
            <button class="btn btn-danger" onclick="changeStatus('مختومه بدون تعمیر')">
                <i class="fas fa-times"></i> عدم تایید مشتری
            </button>
        `;
    } else if (status === 'در حال تعمیر') {
        actionButtons = `
            <button class="btn btn-info" onclick="changeStatus('در حال تست')">
                <i class="fas fa-check-circle"></i> اتمام تعمیر - شروع تست
            </button>
        `;
    } else if (status === 'در حال تست') {
        actionButtons = `
            <button class="btn btn-secondary" onclick="changeStatus('کنترل نهایی')">
                <i class="fas fa-clipboard-check"></i> تایید تست - کنترل نهایی
            </button>
        `;
    } else if (status === 'کنترل نهایی') {
        actionButtons = `
            <button class="btn btn-success" onclick="changeStatus('آماده تحویل')">
                <i class="fas fa-check-double"></i> تایید نهایی - آماده تحویل
            </button>
        `;
    } else if (status === 'آماده تحویل') {
        actionButtons = `
            <button class="btn btn-success" onclick="changeStatus('تحویل شده')">
                <i class="fas fa-handshake"></i> تحویل به مشتری
            </button>
        `;
    }

    // تاریخچه تغییرات
    let historyHtml = '';
    if (history && history.length > 0) {
        historyHtml = '<div class="mt-4"><h5><i class="fas fa-history"></i> تاریخچه تغییرات</h5><div class="timeline">';
        history.forEach(item => {
            const date = formatDate(item.changed_at);
            const oldStatus = item.old_status || 'ثبت شده';
            const operatorName = item.operator_name || 'نامشخص';
            historyHtml += `
                <div class="timeline-item">
                    <div class="d-flex justify-content-between">
                        <span>
                            <span class="badge bg-secondary">${oldStatus}</span>
                            <i class="fas fa-arrow-left"></i>
                            <span class="badge bg-${statusColors[item.new_status] || 'secondary'}">${item.new_status}</span>
                        </span>
                        <small class="text-muted">${date}</small>
                    </div>
                    <div class="text-muted small mt-1">
                        ${item.reason || ''}
                        <span class="badge bg-light text-dark ms-2">
                            <i class="fas fa-user"></i> ${operatorName}
                        </span>
                    </div>
                </div>
            `;
        });
        historyHtml += '</div></div>';
    }

    // فایل‌های ضمیمه
    let attachmentsHtml = '';
    $.ajax({
        url: `/reception/repair-orders/${orderId}/attachments`,
        method: 'GET',
        async: false,
        success: function(attachments) {
            if (attachments && attachments.length > 0) {
                attachmentsHtml = `
                    <div class="mt-4">
                        <h5><i class="fas fa-paperclip text-primary"></i> فایل‌های ضمیمه</h5>
                        <div class="row g-3 mt-2">
                `;
                attachments.forEach(att => {
                    const icon = att.file_type === 'photo' ? 'fa-image' :
                                att.file_type === 'pdf' ? 'fa-file-pdf' :
                                att.file_type === 'video' ? 'fa-video' : 'fa-file';
                    const color = att.file_type === 'photo' ? 'primary' :
                                 att.file_type === 'pdf' ? 'danger' :
                                 att.file_type === 'video' ? 'warning' : 'secondary';
                    attachmentsHtml += `
                        <div class="col-md-3">
                            <div class="card attachment-card h-100">
                                <div class="card-body text-center">
                                    <i class="fas ${icon} fa-3x text-${color} mb-2"></i>
                                    <p class="small text-truncate">${att.file_name}</p>
                                    <p class="small text-muted">${formatFileSize(att.file_size)}</p>
                                    <a href="${att.file_path}" target="_blank" class="btn btn-sm btn-outline-primary">
                                        <i class="fas fa-download"></i>
                                    </a>
                                </div>
                            </div>
                        </div>
                    `;
                });
                attachmentsHtml += '</div></div>';
            }
        }
    });

    const html = `
        <div class="card shadow-lg border-0">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0">
                    <i class="fas fa-file-alt text-primary"></i>
                    پرونده #${order.id}
                </h4>
                <div>
                    <span class="badge bg-${statusColors[status] || 'secondary'} status-badge">
                        <i class="fas fa-circle"></i> ${status}
                    </span>
                </div>
            </div>
            <div class="card-body">
                <div class="row g-4">
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-tag"></i> کد رهگیری</h6>
                                <p><code class="fs-5">${order.tracking_code}</code></p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-calendar"></i> تاریخ ثبت</h6>
                                <p>${formatDate(order.created_at)}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-user"></i> اطلاعات مشتری</h6>
                                <p><strong>نام:</strong> ${order.customer_name || '-'}</p>
                                <p><strong>شرکت:</strong> ${order.customer_company || '-'}</p>
                                <p><strong>تلفن:</strong> ${order.customer_phone || '-'}</p>
                                <p><strong>آدرس:</strong> ${order.customer_address || '-'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-microchip"></i> اطلاعات دستگاه</h6>
                                <p><strong>برند:</strong> ${order.device_brand || '-'}</p>
                                <p><strong>مدل:</strong> ${order.device_model || '-'}</p>
                                <p><strong>پارت نامبر:</strong> ${order.device_part_number || '-'}</p>
                                <p><strong>سریال نامبر:</strong> ${order.device_serial_number || '-'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-exclamation-triangle"></i> شرح مشکل</h6>
                                <p>${order.customer_complaint || 'ثبت نشده'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="card bg-light">
                            <div class="card-body">
                                <h6 class="text-primary"><i class="fas fa-sticky-note"></i> یادداشت‌ها</h6>
                                <p>${order.notes || 'ثبت نشده'}</p>
                            </div>
                        </div>
                    </div>
                </div>

                ${historyHtml}
                ${attachmentsHtml}

                <hr>

                <div class="d-flex gap-2 flex-wrap">
                    ${actionButtons}
                </div>
            </div>
        </div>
    `;

    $('#order-detail').html(html);
}

$(document).ready(function() {
    if (!checkAuth()) return;
    loadOrder();
});