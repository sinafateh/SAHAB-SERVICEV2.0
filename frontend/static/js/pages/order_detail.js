// ============================================
// صفحه جزئیات پرونده
// ============================================

console.log('✅ order_detail.js شروع به کار کرد');

// ============================================
// متغیرهای عمومی
// ============================================
var orderId = 0;

// ============================================
// توابع عمومی
// ============================================

function getStatusBadge(status) {
    var colors = {
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
    return '<span class="badge bg-' + (colors[status] || 'secondary') + ' status-badge fs-6">' + status + '</span>';
}

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

function formatFileSize(bytes) {
    if (!bytes) return '0 KB';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

// ============================================
// تابع تغییر وضعیت
// ============================================
function changeStatus(newStatus, reason) {
    reason = reason || '';

    var statusMap = {
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

    var englishStatus = statusMap[newStatus];
    if (!englishStatus) {
        showError('وضعیت نامعتبر است');
        return;
    }

    if (!reason) {
        Swal.fire({
            title: 'توضیح تغییر وضعیت',
            text: 'لطفاً دلیل تغییر وضعیت را وارد کنید:',
            input: 'text',
            inputPlaceholder: 'دلیل تغییر وضعیت...',
            showCancelButton: true,
            confirmButtonColor: '#0d6efd',
            cancelButtonColor: '#dc3545',
            confirmButtonText: 'تایید',
            cancelButtonText: 'انصراف',
            inputValidator: function(value) {
                if (!value || value.trim().length < 3) {
                    return 'لطفاً حداقل ۳ کاراکتر وارد کنید';
                }
                return null;
            }
        }).then(function(result) {
            if (result.isConfirmed && result.value) {
                changeStatusWithReason(newStatus, englishStatus, result.value.trim());
            }
        });
    } else {
        changeStatusWithReason(newStatus, englishStatus, reason);
    }
}

function changeStatusWithReason(newStatus, englishStatus, reason) {
    Swal.fire({
        title: 'تغییر وضعیت',
        html: 'آیا از تغییر وضعیت به "<strong>' + newStatus + '</strong>" مطمئن هستید؟',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#0d6efd',
        cancelButtonColor: '#dc3545',
        confirmButtonText: 'بله، تغییر کن',
        cancelButtonText: 'انصراف'
    }).then(function(result) {
        if (result.isConfirmed) {
            var token = localStorage.getItem('access_token');

            Swal.fire({
                title: 'در حال تغییر وضعیت...',
                allowOutsideClick: false,
                showConfirmButton: false,
                willOpen: function() {
                    Swal.showLoading();
                }
            });

            fetch('/reception/repair-orders/' + orderId + '/status', {
                method: 'PUT',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    status: newStatus,
                    reason: reason
                })
            })
            .then(function(response) {
                if (!response.ok) {
                    return response.json().then(function(err) {
                        throw new Error(err.detail || 'خطا در تغییر وضعیت');
                    });
                }
                return response.json();
            })
            .then(function(data) {
                Swal.close();
                showSuccess('وضعیت با موفقیت تغییر کرد');
                console.log('✅ وضعیت تغییر کرد:', data);
                loadOrder();
            })
            .catch(function(error) {
                Swal.close();
                showError(error.message || 'خطا در تغییر وضعیت');
            });
        }
    });
}

// ============================================
// تابع بارگذاری پرونده
// ============================================
function loadOrder() {
    console.log('🔄 loadOrder اجرا شد - orderId:', orderId);

    if (!orderId || isNaN(orderId)) {
        $('#order-detail').html(
            '<div class="alert alert-danger">' +
                '<h4><i class="fas fa-exclamation-triangle"></i> شناسه نامعتبر</h4>' +
                '<p>شناسه پرونده وارد شده معتبر نیست.</p>' +
                '<a href="/orders" class="btn btn-primary mt-2">بازگشت به لیست</a>' +
            '</div>'
        );
        return;
    }

    $('#order-detail').html(
        '<div class="text-center text-muted py-5">' +
            '<i class="fas fa-spinner fa-spin fa-3x"></i>' +
            '<p class="mt-3">در حال بارگذاری...</p>' +
        '</div>'
    );

    var token = localStorage.getItem('access_token');

    fetch('/reception/repair-orders/' + orderId, {
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
    .then(function(order) {
        console.log('📋 اطلاعات پرونده:', order);

        return Promise.all([
            Promise.resolve(order),
            fetch('/reception/repair-orders/' + orderId + '/history', {
                headers: { 'Authorization': 'Bearer ' + token }
            }).then(function(r) { return r.ok ? r.json() : []; }),
            fetch('/reception/repair-orders/' + orderId + '/attachments', {
                headers: { 'Authorization': 'Bearer ' + token }
            }).then(function(r) { return r.ok ? r.json() : []; }),
            fetch('/api/workflow/orders/' + orderId + '/history', {
                headers: { 'Authorization': 'Bearer ' + token }
            }).then(function(r) { return r.ok ? r.json() : []; })
        ]);
    })
    .then(function(data) {
        var order = data[0];
        var history = data[1] || [];
        var attachments = data[2] || [];
        var workflowHistory = data[3] || [];
        renderOrder(order, history, attachments, workflowHistory);
    })
    .catch(function(error) {
        console.error('❌ خطا:', error);
        $('#order-detail').html(
            '<div class="alert alert-danger">' +
                '<h4><i class="fas fa-exclamation-triangle"></i> خطا در بارگذاری</h4>' +
                '<p>' + error.message + '</p>' +
                '<a href="/orders" class="btn btn-primary mt-2">بازگشت به لیست</a>' +
            '</div>'
        );
    });
}

// ============================================
// تابع رندر پرونده
// ============================================
function renderOrder(order, history, attachments, workflowHistory) {
    console.log('🎨 رندرینگ پرونده:', order.tracking_code);
    console.log('📋 order.id:', order.id);

    var user = getUser();
    var isTechnical = user && (user.role === 'ADMIN' || user.role === 'TECHNICAL');

    var statusColors = {
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

    // ============================================
    // دکمه‌های تغییر وضعیت
    // ============================================
    var actionButtons = '';

    if (isTechnical) {
        var status = order.status;

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
                <button class="btn btn-danger" onclick="changeStatus('مختومه بدون تعمیر', 'عدم تایید مشتری')">
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
    } else {
        actionButtons = `
            <span class="text-muted">
                <i class="fas fa-info-circle"></i>
                شما دسترسی تغییر وضعیت ندارید
            </span>
        `;
    }

    // ============================================
    // تاریخچه تغییرات
    // ============================================
    var historyHtml = '';
    if (history && history.length > 0) {
        historyHtml = '<div class="mt-4"><h5><i class="fas fa-history text-primary"></i> تاریخچه تغییرات</h5><div class="ps-3">';
        for (var i = 0; i < history.length; i++) {
            var item = history[i];
            var date = formatDate(item.changed_at);
            var oldStatus = item.old_status || 'ثبت شده';
            var newStatus = item.new_status || 'نامشخص';
            var operatorName = item.operator_name || 'سیستم';

            historyHtml +=
                '<div class="mb-3 pb-3 border-bottom">' +
                    '<div class="d-flex justify-content-between align-items-center">' +
                        '<div>' +
                            '<span class="badge bg-secondary">' + oldStatus + '</span>' +
                            '<i class="fas fa-arrow-left mx-2 text-muted"></i>' +
                            '<span class="badge bg-' + (statusColors[newStatus] || 'secondary') + '">' + newStatus + '</span>' +
                        '</div>' +
                        '<small class="text-muted">' + date + '</small>' +
                    '</div>' +
                    '<div class="text-muted small mt-1">' +
                        '<i class="fas fa-quote-right"></i> ' + (item.reason || 'تغییر وضعیت') +
                        '<span class="badge bg-light text-dark ms-2">' +
                            '<i class="fas fa-user"></i> ' + operatorName +
                        '</span>' +
                    '</div>' +
                '</div>';
        }
        historyHtml += '</div></div>';
    } else {
        historyHtml =
            '<div class="mt-4">' +
                '<h5><i class="fas fa-history text-muted"></i> تاریخچه تغییرات</h5>' +
                '<p class="text-muted">تاریخچه‌ای ثبت نشده است</p>' +
            '</div>';
    }

    // ============================================
    // فایل‌های ضمیمه
    // ============================================
    var attachmentsHtml = '';
    if (attachments && attachments.length > 0) {
        attachmentsHtml = '<div class="mt-4"><h5><i class="fas fa-paperclip text-primary"></i> فایل‌های ضمیمه</h5><div class="row g-3 mt-2">';
        for (var j = 0; j < attachments.length; j++) {
            var att = attachments[j];
            var icon = att.file_type === 'photo' ? 'fa-image' :
                       att.file_type === 'pdf' ? 'fa-file-pdf' :
                       att.file_type === 'video' ? 'fa-video' : 'fa-file';
            var color = att.file_type === 'photo' ? 'primary' :
                        att.file_type === 'pdf' ? 'danger' :
                        att.file_type === 'video' ? 'warning' : 'secondary';

            attachmentsHtml +=
                '<div class="col-md-3 col-sm-6">' +
                    '<div class="card attachment-card h-100 text-center p-3">' +
                        '<i class="fas ' + icon + ' fa-3x text-' + color + ' mb-2"></i>' +
                        '<p class="small text-truncate fw-bold">' + att.file_name + '</p>' +
                        '<p class="small text-muted">' + formatFileSize(att.file_size) + '</p>' +
                        '<a href="' + att.file_path + '" target="_blank" class="btn btn-sm btn-outline-primary">' +
                            '<i class="fas fa-download"></i> دانلود' +
                        '</a>' +
                    '</div>' +
                '</div>';
        }
        attachmentsHtml += '</div></div>';
    } else {
        attachmentsHtml =
            '<div class="mt-4">' +
                '<h5><i class="fas fa-paperclip text-muted"></i> فایل‌های ضمیمه</h5>' +
                '<p class="text-muted">هیچ فایلی آپلود نشده است</p>' +
            '</div>';
    }

    // ============================================
    // ✅ دکمه چاپ برگه پذیرش - هم اندازه با سایر دکمه‌ها
    // ============================================
    var printButton = `
        <a href="/reception/repair-orders/${order.id}/receipt" target="_blank" class="btn btn-success">
            <i class="fas fa-print"></i> چاپ برگه پذیرش
        </a>
    `;

    // ============================================
    // HTML نهایی
    // ============================================
    var html =
        '<div class="card shadow-lg border-0">' +
            '<div class="card-header bg-white d-flex justify-content-between align-items-center py-3">' +
                '<h4 class="mb-0"><i class="fas fa-file-alt text-primary"></i> پرونده #' + order.id + '</h4>' +
                '<div>' + getStatusBadge(order.status) + '</div>' +
            '</div>' +
            '<div class="card-body">' +
                '<div class="row g-4">' +
                    '<div class="col-md-6">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-tag"></i> کد رهگیری</h6>' +
                            '<p><code class="fs-5">' + order.tracking_code + '</code></p>' +
                        '</div></div>' +
                    '</div>' +
                    '<div class="col-md-6">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-calendar"></i> تاریخ ثبت</h6>' +
                            '<p>' + formatDate(order.created_at) + '</p>' +
                        '</div></div>' +
                    '</div>' +
                    '<div class="col-md-6">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-user"></i> اطلاعات مشتری</h6>' +
                            '<p><strong>نام:</strong> ' + (order.customer_name || '-') + '</p>' +
                            '<p><strong>شرکت:</strong> ' + (order.customer_company || '-') + '</p>' +
                            '<p><strong>تلفن:</strong> ' + (order.customer_phone || '-') + '</p>' +
                            '<p><strong>آدرس:</strong> ' + (order.customer_address || '-') + '</p>' +
                        '</div></div>' +
                    '</div>' +
                    '<div class="col-md-6">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-microchip"></i> اطلاعات دستگاه</h6>' +
                            '<p><strong>برند:</strong> ' + (order.device_brand || '-') + '</p>' +
                            '<p><strong>مدل:</strong> ' + (order.device_model || '-') + '</p>' +
                            '<p><strong>پارت نامبر:</strong> ' + (order.device_part_number || '-') + '</p>' +
                            '<p><strong>سریال نامبر:</strong> ' + (order.device_serial_number || '-') + '</p>' +
                        '</div></div>' +
                    '</div>' +
                    '<div class="col-12">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-exclamation-triangle"></i> شرح مشکل</h6>' +
                            '<p class="mb-0">' + (order.customer_complaint || 'ثبت نشده') + '</p>' +
                        '</div></div>' +
                    '</div>' +
                    '<div class="col-12">' +
                        '<div class="card bg-light"><div class="card-body">' +
                            '<h6 class="text-primary"><i class="fas fa-sticky-note"></i> یادداشت‌ها</h6>' +
                            '<p class="mb-0">' + (order.notes || 'ثبت نشده') + '</p>' +
                        '</div></div>' +
                    '</div>' +
                '</div>' +
                historyHtml +
                attachmentsHtml +
                '<hr class="my-4">' +
                '<div class="d-flex gap-2 flex-wrap align-items-center">' +
                    actionButtons +
                    printButton +
                    '<a href="/orders" class="btn btn-secondary">' +
                        '<i class="fas fa-arrow-right"></i> بازگشت' +
                    '</a>' +
                '</div>' +
            '</div>' +
        '</div>';

    console.log('✅ HTML ساخته شد، دکمه چاپ اضافه شد');
    
    $('#order-detail').html(html);
    renderWorkflowControls(order, workflowHistory || []);
    
    // بررسی وجود دکمه در DOM
    var checkBtn = document.querySelector('a[href*="receipt"]');
    console.log('🔍 دکمه در DOM:', checkBtn ? '✅ پیدا شد' : '❌ پیدا نشد');
}

function workflowHeaders() {
    var token = localStorage.getItem('access_token') || localStorage.getItem('token') || '';
    return { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' };
}

function renderWorkflowControls(order, workflowHistory) {
    var wrapper = document.querySelector('#order-detail .card-body');
    if (!wrapper) return;

    var historyHtml = (workflowHistory || []).length
        ? workflowHistory.map(function(item) {
            return '<div class="border-bottom py-2">' +
                '<strong>' + (item.from_user_name || '-') + '</strong> <i class="fas fa-arrow-left mx-1"></i> ' +
                '<strong>' + (item.to_user_name || '-') + '</strong>' +
                '<div class="small text-muted">مرحله: ' + (item.stage || '-') + ' | وضعیت: ' + (item.status || '-') +
                ' | ' + formatDate(item.created_at) + '</div>' +
                (item.rejection_reason ? '<div class="text-danger small">دلیل رد: ' + item.rejection_reason + '</div>' : '') +
                '</div>';
        }).join('')
        : '<div class="text-muted">هنوز انتقالی برای این پرونده ثبت نشده است.</div>';

    var card = document.createElement('div');
    card.className = 'card bg-light mt-4';
    card.innerHTML =
        '<div class="card-body">' +
        '<h5 class="text-primary"><i class="fas fa-route"></i> گردش پرونده</h5>' +
        '<div class="small mb-3">مرحله فعلی: <strong>' + (order.current_stage || 'RECEPTION_INTAKE') +
        '</strong> | مسئول فعلی: <strong>' + (order.current_user_id || 'ثبت نشده') + '</strong></div>' +
        '<div id="workflowActionArea" class="mb-3"></div>' +
        '<form id="orderWorkflowForm" class="row g-2 align-items-end">' +
        '<div class="col-md-4"><label class="form-label">مرحله بعد</label><select class="form-select" id="workflowStage" required><option value="">انتخاب کنید</option></select></div>' +
        '<div class="col-md-3"><label class="form-label">بخش</label><input class="form-control" id="workflowDepartment" readonly></div>' +
        '<div class="col-md-3"><label class="form-label">گیرنده</label><select class="form-select" id="workflowRecipient" required><option value="">ابتدا مرحله را انتخاب کنید</option></select></div>' +
        '<div class="col-md-2"><button class="btn btn-primary w-100" type="submit">ارسال انتقال</button></div>' +
        '<div class="col-12"><textarea class="form-control" id="workflowNote" rows="2" placeholder="توضیح انتقال (اختیاری)"></textarea></div>' +
        '</form>' +
        '<hr><h6>تاریخچه انتقال‌ها</h6><div>' + historyHtml + '</div>' +
        '</div>';
    wrapper.appendChild(card);

    var stageSelect = card.querySelector('#workflowStage');
    var deptInput = card.querySelector('#workflowDepartment');
    var recipientSelect = card.querySelector('#workflowRecipient');
    var departmentLabels = { RECEPTION: 'پذیرش', TECHNICAL: 'فنی', MANAGEMENT: 'مدیریت', CUSTOMER_RELATIONS: 'ارتباط با مشتریان' };
    var stages = [];
    renderWorkflowAction(order, card.querySelector('#workflowActionArea'));

    fetch('/api/workflow/stages', { headers: workflowHeaders() })
        .then(function(response) { return response.json(); })
        .then(function(items) {
            stages = items || [];
            stages.forEach(function(item) {
                var option = document.createElement('option');
                option.value = item.code;
                option.textContent = item.label;
                option.dataset.department = item.department;
                stageSelect.appendChild(option);
            });
        });

    stageSelect.addEventListener('change', function() {
        var selected = stages.find(function(item) { return item.code === stageSelect.value; });
        deptInput.value = selected ? (departmentLabels[selected.department] || selected.department) : '';
        recipientSelect.innerHTML = '<option value="">در حال بارگذاری...</option>';
        if (!selected) return;
        fetch('/api/panel/users/by-department/' + encodeURIComponent(selected.department), { headers: workflowHeaders() })
            .then(function(response) { return response.json(); })
            .then(function(users) {
                recipientSelect.innerHTML = '<option value="">انتخاب گیرنده</option>';
                (users || []).forEach(function(user) {
                    var option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.full_name + ' (' + user.username + ')';
                    recipientSelect.appendChild(option);
                });
            });
    });

    card.querySelector('#orderWorkflowForm').addEventListener('submit', function(event) {
        event.preventDefault();
        var payload = {
            to_user_id: Number(recipientSelect.value),
            stage: stageSelect.value,
            to_department: stages.find(function(item) { return item.code === stageSelect.value; })?.department || null,
            note: card.querySelector('#workflowNote').value.trim() || null
        };
        fetch('/api/workflow/orders/' + order.id + '/transfer', {
            method: 'POST',
            headers: workflowHeaders(),
            body: JSON.stringify(payload)
        }).then(function(response) {
            return response.json().then(function(body) {
                if (!response.ok) throw new Error(body.detail || 'انتقال ثبت نشد');
                return body;
            });
        }).then(function() {
            if (typeof showSuccess === 'function') showSuccess('درخواست انتقال ثبت شد و برای گیرنده اعلان ارسال گردید.');
            loadOrder();
        }).catch(function(error) {
            if (typeof showError === 'function') showError(error.message);
        });
    });
}

function renderWorkflowAction(order, container) {
    var definitions = {
        TECHNICAL_DIAGNOSIS: { action: 'DIAGNOSIS', title: 'ثبت نتیجه عیب‌یابی', placeholder: 'شرح عیب و نتیجه بررسی...' },
        MANAGEMENT_PRICING: { action: 'PRICING', title: 'ثبت قیمت پیشنهادی', placeholder: 'توضیحات قیمت‌گذاری...' },
        CUSTOMER_APPROVAL: { action: 'CUSTOMER_DECISION', title: 'ثبت نظر مشتری', placeholder: 'توضیح تماس با مشتری...' },
        TECHNICAL_REPAIR: { action: 'REPAIR_COMPLETE', title: 'ثبت پایان تعمیر', placeholder: 'شرح تعمیرات انجام‌شده...' },
        TECHNICAL_FINAL_TEST: { action: 'FINAL_TEST', title: 'ثبت تست نهایی', placeholder: 'نتیجه تست نهایی...' },
        RECEPTION_DELIVERY: { action: 'DELIVER', title: 'ثبت تحویل دستگاه', placeholder: 'یادداشت تحویل...' }
    };
    var definition = definitions[order.current_stage];
    if (!definition) return;

    var priceField = definition.action === 'PRICING'
        ? '<input id="workflowQuotedPrice" type="number" min="0" step="0.01" class="form-control mb-2" placeholder="مبلغ پیشنهادی">'
        : '';
    var approvalField = definition.action === 'CUSTOMER_DECISION'
        ? '<div class="btn-group mb-2" role="group"><button type="button" class="btn btn-success" data-approval="true">موافقت مشتری</button><button type="button" class="btn btn-outline-danger" data-approval="false">عدم موافقت</button></div>'
        : '';
    var submitField = definition.action === 'CUSTOMER_DECISION'
        ? ''
        : '<button class="btn btn-outline-primary" type="submit">' +
          (definition.action === 'DELIVER' ? 'ثبت تحویل دستگاه' : 'ثبت اقدام') +
          '</button>';

    container.innerHTML =
        '<div class="border rounded p-3 bg-white">' +
        '<h6 class="text-primary"><i class="fas fa-clipboard-check"></i> ' + definition.title + '</h6>' +
        '<form id="workflowActionForm">' +
        priceField +
        '<textarea id="workflowActionNotes" class="form-control mb-2" rows="2" placeholder="' + definition.placeholder + '"></textarea>' +
        approvalField + submitField +
        '</form></div>';

    var submitAction = function(approved) {
        var payload = {
            action: definition.action,
            notes: container.querySelector('#workflowActionNotes').value.trim() || null,
            quoted_price: container.querySelector('#workflowQuotedPrice')?.value
                ? Number(container.querySelector('#workflowQuotedPrice').value) : null,
            approved: approved === undefined ? null : approved
        };
        fetch('/api/workflow/orders/' + order.id + '/action', {
            method: 'POST',
            headers: workflowHeaders(),
            body: JSON.stringify(payload)
        }).then(function(response) {
            return response.json().then(function(body) {
                if (!response.ok) throw new Error(body.detail || 'اقدام ثبت نشد');
                return body;
            });
        }).then(function() {
            if (typeof showSuccess === 'function') showSuccess('اقدام workflow ثبت شد.');
            loadOrder();
        }).catch(function(error) {
            if (typeof showError === 'function') showError(error.message);
        });
    };

    container.querySelector('#workflowActionForm').addEventListener('submit', function(event) {
        event.preventDefault();
        submitAction();
    });
    container.querySelectorAll('[data-approval]').forEach(function(button) {
        button.addEventListener('click', function() {
            submitAction(button.dataset.approval === 'true');
        });
    });
}

// ============================================
// بارگذاری اولیه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در order_detail.js اجرا شد');

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

    // دریافت orderId از URL
    var pathParts = window.location.pathname.split('/');
    orderId = parseInt(pathParts[pathParts.length - 1]);

    if (isNaN(orderId) || orderId <= 0) {
        console.error('❌ orderId نامعتبر است');
        $('#order-detail').html(
            '<div class="alert alert-danger">' +
                '<h4><i class="fas fa-exclamation-triangle"></i> شناسه نامعتبر</h4>' +
                '<a href="/orders" class="btn btn-primary mt-2">بازگشت به لیست</a>' +
            '</div>'
        );
        return;
    }

    loadOrder();
});
