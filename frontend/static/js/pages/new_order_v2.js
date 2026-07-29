// ============================================
// صفحه ثبت پرونده جدید - نسخه ۲
// ============================================

console.log('✅ new_order_v2.js شروع به کار کرد');

// ============================================
// متغیرهای عمومی
// ============================================
var currentStep = 1;
var totalSteps = 10;
var selectedCustomerId = null;
var selectedSiteId = null;
var selectedPanelId = null;
var boards = [];
var damagePhotos = [];
var uploadedPhotoPaths = [];

// ============================================
// مدیریت استپ‌ها
// ============================================
function goToStep(step) {
    if (step < 1 || step > totalSteps) return;
    
    // مخفی کردن همه بخش‌ها
    $('.form-section').removeClass('active');
    
    // نمایش بخش مورد نظر
    $('[data-section="' + step + '"]').addClass('active');
    
    // بروزرسانی استپ‌ها
    $('.step').removeClass('active').removeClass('completed');
    for (var i = 1; i <= totalSteps; i++) {
        if (i < step) {
            $('[data-step="' + i + '"]').addClass('completed');
        } else if (i === step) {
            $('[data-step="' + i + '"]').addClass('active');
        }
    }
    
    currentStep = step;
    updateButtons();
    updateSummary();
}

function nextStep() {
    if (currentStep < totalSteps) {
        goToStep(currentStep + 1);
    }
}

function prevStep() {
    if (currentStep > 1) {
        goToStep(currentStep - 1);
    }
}

function updateButtons() {
    $('button[onclick="prevStep()"]').prop('disabled', currentStep === 1);
    $('button[onclick="nextStep()"]').text(currentStep === totalSteps ? 'ثبت نهایی' : 'بعدی');
}

function updateSummary() {
    var html = '';
    html += '<p><strong>مشتری:</strong> ' + ($('#selectedCustomerInfo').text() || 'انتخاب نشده') + '</p>';
    html += '<p><strong>محل نصب:</strong> ' + ($('#selectedSiteInfo')?.text() || 'انتخاب نشده') + '</p>';
    html += '<p><strong>پنل:</strong> ' + ($('#selectedPanelInfo')?.text() || 'انتخاب نشده') + '</p>';
    html += '<p><strong>تعداد بردها:</strong> ' + boards.length + '</p>';
    html += '<p><strong>تعداد عکس‌ها:</strong> ' + damagePhotos.length + '</p>';
    $('#summaryInfo').html(html);
}

// ============================================
// بخش ۱: اطلاعات پذیرش (Auto)
// ============================================
function loadReceptionInfo() {
    var user = getUser();
    if (user) {
        $('#operatorName').val(user.full_name || 'کاربر');
    }
    
    var now = new Date();
    var dateStr = now.toLocaleDateString('fa-IR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    $('#receptionDate').val(dateStr);
}

// ============================================
// بخش ۲: مشتری (جستجو/ثبت)
// ============================================
function searchCustomer() {
    var query = $('#customerSearch').val().trim();
    var searchType = $('#searchType').val();
    
    if (!query || query.length < 2) {
        showError('لطفاً حداقل ۲ کاراکتر وارد کنید');
        return;
    }
    
    $('#searchResults').html('<div class="text-center"><i class="fas fa-spinner fa-spin"></i> در حال جستجو...</div>');
    
    var token = localStorage.getItem('access_token');
    var url = '/reception/customers/search?q=' + encodeURIComponent(query);
    
    fetch(url, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        if (!response.ok) throw new Error('خطا در جستجو');
        return response.json();
    })
    .then(function(data) {
        if (data && data.length > 0) {
            var html = '<div class="mt-3"><h6>نتایج جستجو:</h6>';
            for (var i = 0; i < data.length; i++) {
                var customer = data[i];
                var displayName = customer.name;
                if (customer.company) displayName += ' (' + customer.company + ')';
                html +=
                    '<div class="customer-result" onclick="selectCustomer(' + customer.id + ')">' +
                        '<div class="d-flex justify-content-between align-items-center">' +
                            '<div>' +
                                '<strong>' + displayName + '</strong><br>' +
                                '<small class="text-muted">' + customer.phone + ' | ' + (customer.email || 'بدون ایمیل') + '</small>' +
                            '</div>' +
                            '<span class="badge bg-primary">انتخاب</span>' +
                        '</div>' +
                    '</div>';
            }
            html += '</div>';
            $('#searchResults').html(html);
        } else {
            $('#searchResults').html(
                '<div class="alert alert-warning mt-3">' +
                    'مشتریی یافت نشد. لطفاً ثبت مشتری جدید را انتخاب کنید.' +
                '</div>'
            );
        }
    })
    .catch(function(error) {
        $('#searchResults').html(
            '<div class="alert alert-danger mt-3">خطا در جستجو: ' + error.message + '</div>'
        );
    });
}

function selectCustomer(customerId) {
    selectedCustomerId = customerId;
    
    var token = localStorage.getItem('access_token');
    fetch('/reception/customers/search?id=' + customerId, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(customer) {
        if (customer) {
            var info = customer.name;
            if (customer.company) info += ' (' + customer.company + ')';
            info += ' - ' + customer.phone;
            $('#selectedCustomerInfo').text(info);
            $('#selectedCustomer').show();
            $('#searchResults').html('');
            $('#customerSearch').val('');
            
            // بارگذاری سایت‌های مشتری
            loadSites(customerId);
            updateSummary();
        }
    });
}

function clearCustomer() {
    selectedCustomerId = null;
    $('#selectedCustomer').hide();
    $('#selectedCustomerInfo').text('');
    $('#siteList').html('');
    updateSummary();
}

function showNewCustomer() {
    $('#newCustomerForm').show();
    $('#searchResults').html('');
}

function cancelNewCustomer() {
    $('#newCustomerForm').hide();
    $('#customerName').val('');
    $('#customerLastName').val('');
    $('#customerCompany').val('');
    $('#customerMobile').val('');
    $('#customerPhone').val('');
    $('#customerEmail').val('');
}

function saveCustomer() {
    var type = $('#customerType').val();
    var data = {};
    
    if (type === 'person') {
        data.name = $('#customerName').val().trim();
        data.last_name = $('#customerLastName').val().trim() || null;
        data.phone = $('#customerMobile').val().trim();
        data.email = $('#customerEmail').val().trim() || null;  // ✅ خالی = null
        data.address = $('#customerAddress').val().trim() || null;
    } else {
        data.name = $('#customerCompany').val().trim();
        data.company = $('#customerCompany').val().trim();
        data.phone = $('#customerPhone').val().trim();
        data.email = $('#customerEmail').val().trim() || null;  // ✅ خالی = null
        data.website = $('#customerWebsite').val().trim() || null;
        data.address = $('#customerAddress').val().trim() || null;
    }
    
    if (!data.phone || data.phone.length < 10) {
        showError('لطفاً شماره تماس معتبر وارد کنید');
        return;
    }
    
    var token = localStorage.getItem('access_token');
    
    fetch('/reception/customers', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {
        if (!response.ok) {
            // ✅ مدیریت خطای 422 (اعتبارسنجی)
            return response.json().then(function(err) {
                var errorMsg = 'خطا در ثبت مشتری';
                if (err.detail) {
                    if (typeof err.detail === 'string') {
                        errorMsg = err.detail;
                    } else if (Array.isArray(err.detail)) {
                        // خطاهای اعتبارسنجی Pydantic
                        var messages = [];
                        for (var i = 0; i < err.detail.length; i++) {
                            var field = err.detail[i].loc[err.detail[i].loc.length - 1];
                            var msg = err.detail[i].msg;
                            messages.push(field + ': ' + msg);
                        }
                        errorMsg = messages.join('\n');
                    }
                }
                throw new Error(errorMsg);
            });
        }
        return response.json();
    })
    .then(function(customer) {
        showSuccess('مشتری با موفقیت ثبت شد');
        selectCustomer(customer.id);
        cancelNewCustomer();
    })
    .catch(function(error) {
        showError(error.message || 'خطا در ثبت مشتری');
    });
}

// ============================================
// تابع انتخاب مشتری (اصلاح شده)
// ============================================
function selectCustomer(customerId) {
    selectedCustomerId = customerId;
    
    var token = localStorage.getItem('access_token');
    fetch('/reception/customers/search-v2?id=' + customerId, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(customer) {
        if (customer) {
            // ✅ نمایش صحیح اطلاعات مشتری
            var displayName = '';
            
            // اگر شخص است و نام و نام خانوادگی دارد
            if (customer.name && customer.last_name) {
                displayName = customer.name + ' ' + customer.last_name;
            } else if (customer.name) {
                displayName = customer.name;
            }
            
            // اگر شرکت دارد
            if (customer.company) {
                displayName += ' (' + customer.company + ')';
            }
            
            // اگر فقط شرکت دارد
            if (!displayName && customer.company) {
                displayName = customer.company;
            }
            
            // اگر هیچکدام نبود، از phone استفاده کن
            if (!displayName) {
                displayName = customer.phone || 'مشتری';
            }
            
            // نمایش با شماره تماس
            var info = displayName + ' - ' + customer.phone;
            $('#selectedCustomerInfo').text(info);
            $('#selectedCustomer').show();
            $('#searchResults').html('');
            $('#customerSearch').val('');
            
            // بارگذاری سایت‌های مشتری
            loadSites(customerId);
            updateSummary();
        }
    })
    .catch(function(error) {
        console.error('❌ خطا در دریافت مشتری:', error);
    });
}

// ============================================
// تابع لغو ثبت مشتری جدید (اصلاح شده)
// ============================================
function cancelNewCustomer() {
    $('#newCustomerForm').hide();
    $('#customerName').val('');
    $('#customerLastName').val('');
    $('#customerCompany').val('');
    $('#customerMobile').val('');
    $('#customerPhone').val('');
    $('#customerEmail').val('');
    $('#customerWebsite').val('');
    $('#customerAddress').val('');
}

// ============================================
// بخش ۳: محل نصب (Site)
// ============================================
function loadSites(customerId) {
    var token = localStorage.getItem('access_token');
    fetch('/reception/customers/' + customerId + '/sites', {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data && data.length > 0) {
            var html = '<h6>محل‌های نصب موجود:</h6><div class="list-group">';
            for (var i = 0; i < data.length; i++) {
                var site = data[i];
                html +=
                    '<div class="list-group-item list-group-item-action" onclick="selectSite(' + site.id + ')">' +
                        '<div class="d-flex justify-content-between">' +
                            '<div>' +
                                '<strong>' + site.name + '</strong><br>' +
                                '<small class="text-muted">' + site.type + ' | ' + (site.address || 'بدون آدرس') + '</small>' +
                            '</div>' +
                            '<span class="badge bg-primary">انتخاب</span>' +
                        '</div>' +
                    '</div>';
            }
            html += '</div>';
            html += '<button type="button" class="btn btn-outline-success mt-2" onclick="showNewSite()">' +
                        '<i class="fas fa-plus"></i> محل جدید' +
                    '</button>';
            $('#siteList').html(html);
        } else {
            $('#siteList').html(
                '<div class="alert alert-info">هیچ محلی ثبت نشده است. لطفاً محل جدید ثبت کنید.</div>' +
                '<button type="button" class="btn btn-success" onclick="showNewSite()">' +
                    '<i class="fas fa-plus"></i> ثبت محل جدید' +
                '</button>'
            );
        }
    });
}

function selectSite(siteId) {
    selectedSiteId = siteId;
    $('#selectedSiteInfo').text('محل انتخاب شد');
    updateSummary();
}

function showNewSite() {
    $('#newSiteForm').show();
}

function cancelNewSite() {
    $('#newSiteForm').hide();
    $('#siteName').val('');
    $('#siteAddress').val('');
}

function saveSite() {
    if (!selectedCustomerId) {
        showError('لطفاً ابتدا مشتری را انتخاب کنید');
        return;
    }
    
    var data = {
        name: $('#siteName').val().trim(),
        type: $('#siteType').val(),
        address: $('#siteAddress').val().trim(),
        location: $('#siteLocation').val().trim(),
        description: $('#siteDescription').val().trim(),
        customer_id: selectedCustomerId
    };
    
    if (!data.name) {
        showError('لطفاً نام محل را وارد کنید');
        return;
    }
    
    var token = localStorage.getItem('access_token');
    fetch('/reception/sites', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت محل');
            });
        }
        return response.json();
    })
    .then(function(site) {
        showSuccess('محل نصب با موفقیت ثبت شد');
        selectSite(site.id);
        cancelNewSite();
        loadSites(selectedCustomerId);
    })
    .catch(function(error) {
        showError(error.message);
    });
}

// ============================================
// بخش ۴: مسئول ارسال پنل
// ============================================
$('#deliveryMethod').on('change', function() {
    var val = $(this).val();
    if (val === 'COURIER') {
        $('#courierFields').show();
        $('#courierTrackingField').show();
    } else {
        $('#courierFields').hide();
        $('#courierTrackingField').hide();
        $('#courierCompany').val('');
        $('#courierTracking').val('');
    }
});

// ============================================
// بخش ۵: اطلاعات پنل (جستجو/ثبت)
// ============================================
function searchPanel() {
    var query = $('#panelSearch').val().trim();
    var searchType = $('#panelSearchType').val();
    
    if (!query || query.length < 2) {
        showError('لطفاً حداقل ۲ کاراکتر وارد کنید');
        return;
    }
    
    $('#panelSearchResults').html('<div class="text-center"><i class="fas fa-spinner fa-spin"></i> در حال جستجو...</div>');
    
    var token = localStorage.getItem('access_token');
    var url = '/reception/panels/search?q=' + encodeURIComponent(query) + '&type=' + searchType;
    
    fetch(url, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data && data.length > 0) {
            var html = '<div class="mt-3"><h6>نتایج جستجو:</h6>';
            for (var i = 0; i < data.length; i++) {
                var panel = data[i];
                html +=
                    '<div class="customer-result" onclick="selectPanel(' + panel.id + ')">' +
                        '<div class="d-flex justify-content-between align-items-center">' +
                            '<div>' +
                                '<strong>' + panel.brand + ' ' + panel.model + '</strong><br>' +
                                '<small class="text-muted">SN: ' + panel.serial_number + ' | PN: ' + panel.part_number + '</small>' +
                            '</div>' +
                            '<span class="badge bg-primary">انتخاب</span>' +
                        '</div>' +
                    '</div>';
            }
            html += '</div>';
            $('#panelSearchResults').html(html);
        } else {
            $('#panelSearchResults').html(
                '<div class="alert alert-warning mt-3">پنلی یافت نشد. لطفاً پنل جدید ثبت کنید.</div>'
            );
        }
    })
    .catch(function(error) {
        $('#panelSearchResults').html(
            '<div class="alert alert-danger mt-3">خطا در جستجو: ' + error.message + '</div>'
        );
    });
}

function selectPanel(panelId) {
    selectedPanelId = panelId;
    
    var token = localStorage.getItem('access_token');
    fetch('/reception/panels/' + panelId, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) { return response.json(); })
    .then(function(panel) {
        if (panel) {
            var info = panel.brand + ' ' + panel.model + ' - SN: ' + panel.serial_number;
            $('#selectedPanelInfo').text(info);
            $('#selectedPanel').show();
            $('#panelSearchResults').html('');
            $('#panelSearch').val('');
            updateSummary();
        }
    });
}

function clearPanel() {
    selectedPanelId = null;
    $('#selectedPanel').hide();
    $('#selectedPanelInfo').text('');
    updateSummary();
}

function showNewPanel() {
    $('#newPanelForm').show();
    $('#panelSearchResults').html('');
}

function cancelNewPanel() {
    $('#newPanelForm').hide();
    $('#panelBrand').val('');
    $('#panelModel').val('');
    $('#panelSerial').val('');
    $('#panelPartNumber').val('');
}

function savePanel() {
    var data = {
        brand: $('#panelBrand').val().trim(),
        model: $('#panelModel').val().trim(),
        serial_number: $('#panelSerial').val().trim(),
        part_number: $('#panelPartNumber').val().trim(),
        firmware_version: $('#panelFirmware').val().trim() || null,
        hardware_version: $('#panelHardware').val().trim() || null,
        loops_count: parseInt($('#panelLoops').val()) || 0,
        zones_count: parseInt($('#panelZones').val()) || 0,
        installation_year: $('#panelYear').val() || null
    };
    
    if (!data.brand || !data.model || !data.serial_number || !data.part_number) {
        showError('لطفاً تمام فیلدهای ضروری را پر کنید');
        return;
    }
    
    var token = localStorage.getItem('access_token');
    fetch('/reception/panels', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت پنل');
            });
        }
        return response.json();
    })
    .then(function(panel) {
        showSuccess('پنل با موفقیت ثبت شد');
        selectPanel(panel.id);
        cancelNewPanel();
    })
    .catch(function(error) {
        showError(error.message);
    });
}

// ============================================
// بخش ۶: ساختار بردها (Dynamic)
// ============================================
function addBoard() {
    var boardType = $('#boardType').val();
    var partNumber = $('#boardPartNumber').val().trim();
    var serial = $('#boardSerial').val().trim();
    var revision = $('#boardRevision').val().trim();
    
    if (!partNumber || !serial) {
        showError('لطفاً Part Number و Serial را وارد کنید');
        return;
    }
    
    var board = {
        type: boardType,
        part_number: partNumber,
        serial_number: serial,
        revision: revision || null
    };
    
    boards.push(board);
    renderBoards();
    
    // پاک کردن فرم
    $('#boardPartNumber').val('');
    $('#boardSerial').val('');
    $('#boardRevision').val('');
    updateSummary();
}

function removeBoard(index) {
    boards.splice(index, 1);
    renderBoards();
    updateSummary();
}

function renderBoards() {
    if (boards.length === 0) {
        $('#boardsList').html('<p class="text-muted">هیچ بردی اضافه نشده است</p>');
        return;
    }
    
    var typeLabels = {
        'MOTHER': 'Mother Board',
        'POWER': 'Power Board',
        'DISPLAY': 'Display',
        'CPU': 'CPU',
        'LOOP': 'Loop Card',
        'NETWORK': 'Network',
        'BATTERY_CHARGER': 'Battery Charger',
        'OTHER': 'سایر'
    };
    
    var html = '<div class="row">';
    for (var i = 0; i < boards.length; i++) {
        var board = boards[i];
        html +=
            '<div class="col-md-6">' +
                '<div class="board-item">' +
                    '<button type="button" class="btn btn-sm btn-danger remove-board" onclick="removeBoard(' + i + ')">' +
                        '<i class="fas fa-times"></i>' +
                    '</button>' +
                    '<strong>' + (typeLabels[board.type] || board.type) + '</strong><br>' +
                    '<small>PN: ' + board.part_number + ' | SN: ' + board.serial_number + '</small><br>' +
                    (board.revision ? '<small class="text-muted">Rev: ' + board.revision + '</small>' : '') +
                '</div>' +
            '</div>';
    }
    html += '</div>';
    $('#boardsList').html(html);
}

// ============================================
// بخش ۷: وضعیت ظاهری
// ============================================
$('#damagePhotos').on('change', function() {
    var files = this.files;
    damagePhotos = [];
    $('#damagePhotoPreview').html('');
    
    for (var i = 0; i < files.length; i++) {
        var file = files[i];
        damagePhotos.push(file);
        var reader = new FileReader();
        reader.onload = function(e) {
            $('#damagePhotoPreview').append(
                '<img src="' + e.target.result + '" class="photo-preview">'
            );
        };
        reader.readAsDataURL(file);
    }
    
    updateSummary();
});

// ============================================
// بخش ۱۰: ثبت نهایی
// ============================================
$('#orderForm').on('submit', function(e) {
    e.preventDefault();
    
    // بررسی اطلاعات ضروری
    if (!selectedCustomerId) {
        showError('لطفاً مشتری را انتخاب کنید');
        goToStep(2);
        return;
    }
    
    if (!selectedPanelId) {
        showError('لطفاً پنل را انتخاب کنید');
        goToStep(5);
        return;
    }
    
    var complaint = $('#customerComplaint').val().trim();
    if (!complaint || complaint.length < 3) {
        showError('لطفاً شرح مشکل را وارد کنید');
        goToStep(9);
        return;
    }
    
    // جمع‌آوری داده‌ها
    var damages = [];
    $('.damage-checkbox:checked').each(function() {
        damages.push($(this).val());
    });
    
    var accessories = [];
    $('.accessory-checkbox:checked').each(function() {
        accessories.push($(this).val());
    });
    
    var orderData = {
        customer_id: selectedCustomerId,
        site_id: selectedSiteId,
        panel_id: selectedPanelId,
        sender_name: $('#senderName').val().trim() || null,
        sender_position: $('#senderPosition').val() || null,
        sender_phone: $('#senderMobile').val().trim() || null,
        sender_landline: $('#senderPhone').val().trim() || null,
        delivery_method: $('#deliveryMethod').val() || null,
        courier_company: $('#courierCompany').val().trim() || null,
        courier_tracking: $('#courierTracking').val().trim() || null,
        physical_damages: damages,
        physical_description: $('#physicalDescription').val().trim() || null,
        accessories: accessories,
        accessories_description: $('#accessoriesDescription').val().trim() || null,
        customer_complaint: complaint,
        boards: boards,
        photos: damagePhotos
    };
    
    console.log('📦 داده‌های نهایی:', orderData);
    
    // نمایش لودینگ
    Swal.fire({
        title: 'در حال ثبت پرونده...',
        allowOutsideClick: false,
        showConfirmButton: false,
        willOpen: function() {
            Swal.showLoading();
        }
    });
    
    // ارسال به سرور
    var token = localStorage.getItem('access_token');
    var formData = new FormData();
    formData.append('data', JSON.stringify(orderData));
    
    // اضافه کردن عکس‌ها
    for (var i = 0; i < damagePhotos.length; i++) {
        formData.append('photos', damagePhotos[i]);
    }
    
    fetch('/reception/repair-orders-v2', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token
        },
        body: formData
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت پرونده');
            });
        }
        return response.json();
    })
    .then(function(data) {
        Swal.close();
        showSuccess(
            'پرونده با موفقیت ثبت شد!<br><br>' +
            '<div class="text-center">' +
                '<strong>کد رهگیری:</strong><br>' +
                '<code class="fs-3 text-primary fw-bold">' + data.tracking_code + '</code><br><br>' +
                '<strong>شماره پرونده:</strong> #' + data.id +
            '</div>'
        );
        
        setTimeout(function() {
            window.location.href = '/order/' + data.id;
        }, 3000);
    })
    .catch(function(error) {
        Swal.close();
        showError('خطا در ثبت پرونده: ' + error.message);
    });
});

// ============================================
// بارگذاری اولیه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در new_order_v2.js اجرا شد');
    
    // بررسی احراز هویت
    var token = localStorage.getItem('access_token');
    var user = localStorage.getItem('user');
    
    if (!token || !user) {
        window.location.href = '/login';
        return;
    }
    
    // بارگذاری اطلاعات پذیرش
    loadReceptionInfo();
    
    // نمایش استپ اول
    goToStep(1);
    
    // رویداد تغییر نوع مشتری
    $('#customerType').on('change', function() {
        if ($(this).val() === 'person') {
            $('#lastNameField').show();
            $('#companyField').hide();
            $('#websiteField').hide();
        } else {
            $('#lastNameField').hide();
            $('#companyField').show();
            $('#websiteField').show();
        }
    });
    
    // رویداد تغییر نوع محل
    $('#siteType').on('change', function() {
        var val = $(this).val();
        if (val === 'RESIDENTIAL') {
            $('#siteResidentialFields').show();
            $('#siteOrganizationFields').hide();
        } else if (val === 'OFFICE' || val === 'COMMERCIAL' || val === 'INDUSTRIAL' || val === 'HOSPITAL' || val === 'HOTEL' || val === 'FACTORY' || val === 'EDUCATIONAL') {
            $('#siteResidentialFields').hide();
            $('#siteOrganizationFields').show();
        } else {
            $('#siteResidentialFields').hide();
            $('#siteOrganizationFields').hide();
        }
    });
    
    console.log('✅ new_order_v2.js راه‌اندازی شد');
});