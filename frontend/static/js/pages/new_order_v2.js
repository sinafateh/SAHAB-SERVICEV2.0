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
var selectedSiteData = null;
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

// ============================================
// تابع بروزرسانی خلاصه اطلاعات (با نمایش کامل سایت)
// ============================================
function updateSummary() {
    var html = '';
    
    // ✅ دریافت نام مشتری
    var customerName = $('#selectedCustomerInfo').data('customer-name') || 'انتخاب نشده';
    html += '<p><strong>مشتری:</strong> ' + customerName + '</p>';
    
    // ✅ نمایش اطلاعات کامل سایت
    if (selectedSiteData) {
        var siteInfo = selectedSiteData.name;
        if (selectedSiteData.address) {
            siteInfo += ' - آدرس: ' + selectedSiteData.address;
        }
        if (selectedSiteData.type) {
            var typeLabels = {
                'RESIDENTIAL': 'مسکونی',
                'OFFICE': 'اداری',
                'COMMERCIAL': 'تجاری',
                'INDUSTRIAL': 'صنعتی',
                'HOSPITAL': 'بیمارستان',
                'HOTEL': 'هتل',
                'FACTORY': 'کارخانه',
                'EDUCATIONAL': 'آموزشی',
                'WAREHOUSE': 'انبار',
                'OTHER': 'سایر'
            };
            siteInfo += ' (' + (typeLabels[selectedSiteData.type] || selectedSiteData.type) + ')';
        }
        html += '<p><strong>محل نصب:</strong> ' + siteInfo + '</p>';
    } else {
        html += '<p><strong>محل نصب:</strong> انتخاب نشده</p>';
    }
    
    html += '<p><strong>پنل:</strong> ' + ($('#selectedPanelInfo').text() || 'انتخاب نشده') + '</p>';
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
// بخش ۲: مشتری (جستجو/ثبت) - جستجو با هر سه المان
// ============================================
// ============================================
// بخش ۲: مشتری (جستجو/ثبت) - جستجو با هر سه المان
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
    
    // ✅ ساخت URL بر اساس نوع جستجو
    var url = '/reception/customers/search-v2?';
    
    if (searchType === 'phone') {
        url += 'phone=' + encodeURIComponent(query);
    } else if (searchType === 'name') {
        url += 'name=' + encodeURIComponent(query);
    } else if (searchType === 'company') {
        url += 'company=' + encodeURIComponent(query);
    } else {
        url += 'q=' + encodeURIComponent(query);
    }
    
    console.log('📡 ارسال درخواست به:', url);
    console.log('🔍 نوع جستجو:', searchType);
    console.log('🔍 عبارت جستجو:', query);
    
    fetch(url, {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        console.log('📡 وضعیت پاسخ:', response.status);
        if (!response.ok) throw new Error('خطا در جستجو');
        return response.json();
    })
    .then(function(data) {
        console.log('📋 نتیجه جستجو:', data);
        
        var results = Array.isArray(data) ? data : (data ? [data] : []);
        
        if (results.length > 0) {
            var html = '<div class="mt-3"><h6>نتایج جستجو (' + results.length + ' مورد):</h6>';
            for (var i = 0; i < results.length; i++) {
                var c = results[i];
                var displayName = '';
                if (c.name && c.last_name) displayName = c.name + ' ' + c.last_name;
                else if (c.name) displayName = c.name;
                if (c.company && displayName !== c.company) {
                    displayName += displayName ? ' (' + c.company + ')' : c.company;
                }
                if (!displayName) displayName = c.phone || 'مشتری';
                
                html += '<div class="customer-result" onclick="selectCustomer(' + c.id + ')">' +
                    '<div class="d-flex justify-content-between align-items-center">' +
                        '<div><strong>' + displayName + '</strong><br>' +
                        '<small class="text-muted">' + c.phone + ' | ' + (c.email || 'بدون ایمیل') + '</small></div>' +
                        '<span class="badge bg-primary">انتخاب</span>' +
                    '</div></div>';
            }
            html += '</div>';
            $('#searchResults').html(html);
        } else {
            $('#searchResults').html('<div class="alert alert-warning mt-3">مشتریی یافت نشد. لطفاً ثبت مشتری جدید را انتخاب کنید.</div>');
        }
    })
    .catch(function(error) {
        console.error('❌ خطا:', error);
        $('#searchResults').html('<div class="alert alert-danger mt-3">خطا در جستجو: ' + error.message + '</div>');
    });
}
// ✅ تابع انتخاب مشتری (با دکمه حذف)
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
            var displayName = '';
            if (customer.name && customer.last_name) displayName = customer.name + ' ' + customer.last_name;
            else if (customer.name) displayName = customer.name;
            if (customer.company && displayName !== customer.company) {
                displayName += displayName ? ' (' + customer.company + ')' : customer.company;
            }
            if (!displayName) displayName = customer.phone || 'مشتری';
            
            var info = displayName + ' - ' + customer.phone;
            
            // ✅ ذخیره نام در data برای استفاده در summary
            $('#selectedCustomerInfo').data('customer-name', displayName);
            
            $('#selectedCustomerInfo').html(
                info + 
                ' <button type="button" class="btn btn-sm btn-danger ms-2" onclick="clearCustomer()">' +
                    '<i class="fas fa-times"></i> حذف' +
                '</button>'
            );
            $('#selectedCustomer').show();
            $('#searchResults').html('');
            $('#customerSearch').val('');
            
            loadSites(customerId);
            updateSummary();
        }
    })
    .catch(function(error) {
        console.error('❌ خطا در دریافت مشتری:', error);
    });
}

// ✅ تابع لغو انتخاب مشتری (با پیام تایید)
function clearCustomer() {
    selectedCustomerId = null;
    $('#selectedCustomer').hide();
    $('#selectedCustomerInfo').text('');
    $('#siteList').html('');
    $('#newSiteForm').hide();
    updateSummary();
    
    // ✅ پیام تایید
    Swal.fire({
        icon: 'info',
        title: 'مشتری لغو شد',
        text: 'انتخاب مشتری با موفقیت لغو شد',
        timer: 1500,
        showConfirmButton: false
    });
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
// بخش ۳: محل نصب (Site) - با دکمه حذف
// ============================================

// ============================================
// بارگذاری لیست سایت‌ها (با ارسال اطلاعات کامل)
// ============================================
function loadSites(customerId) {
    var token = localStorage.getItem('access_token');
    
    fetch('/reception/customers/' + customerId + '/sites', {
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        var html = '';
        var isFormOpen = $('#newSiteForm').is(':visible');
        
        // ✅ نمایش پیام انتخاب شده با دکمه حذف
        if (selectedSiteId && selectedSiteData) {
            var siteInfo = selectedSiteData.name;
            if (selectedSiteData.address) {
                siteInfo += ' - ' + selectedSiteData.address;
            }
            html += '<div class="alert alert-success mb-2">' +
                '<i class="fas fa-check-circle"></i> محل نصب انتخاب شد: <strong>' + siteInfo + '</strong>' +
                ' <button type="button" class="btn btn-sm btn-danger ms-2" onclick="clearSite()">' +
                    '<i class="fas fa-times"></i> حذف' +
                '</button>' +
                '</div>';
        }
        
        if (data && data.length > 0) {
            html += '<h6 class="mt-2">محل‌های نصب موجود:</h6><div class="list-group">';
            for (var i = 0; i < data.length; i++) {
                var site = data[i];
                var isSelected = (selectedSiteId === site.id);
                var siteDisplay = site.name;
                if (site.address) {
                    siteDisplay += ' - ' + site.address;
                }
                html += '<div class="list-group-item list-group-item-action ' + (isSelected ? 'active' : '') + '" onclick="selectSiteFromList(' + site.id + ')">' +
                    '<div class="d-flex justify-content-between align-items-center">' +
                        '<div>' +
                            '<strong>' + siteDisplay + '</strong><br>' +
                            '<small class="text-muted">' + site.type + ' | ' + (site.address || 'بدون آدرس') + '</small>' +
                        '</div>' +
                        (isSelected ? '<span class="badge bg-success">✓ انتخاب شده</span>' : '<span class="badge bg-primary">انتخاب</span>') +
                    '</div></div>';
            }
            html += '</div>';
        } else {
            html += '<div class="alert alert-info">هیچ محلی ثبت نشده است. لطفاً محل جدید ثبت کنید.</div>';
        }
        
        // ✅ دکمه "محل جدید" فقط در صورتی نمایش داده شود که فرم باز نباشد
        if (!isFormOpen) {
            html += '<button type="button" class="btn btn-success mt-2" onclick="showNewSite()">' +
                '<i class="fas fa-plus"></i> محل جدید' +
            '</button>';
        }
        
        $('#siteList').html(html);
        updateSummary();
    });
}

// ✅ تابع جدید برای انتخاب سایت از لیست (با اطلاعات کامل)
function selectSiteFromList(siteId) {
    var token = localStorage.getItem('access_token');
    
    fetch('/reception/sites/' + siteId, {
        headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
    })
    .then(function(response) { 
        if (!response.ok) {
            throw new Error('خطا در دریافت اطلاعات سایت');
        }
        return response.json(); 
    })
    .then(function(site) {
        if (site) {
            // ✅ ذخیره اطلاعات کامل سایت
            selectedSiteId = site.id;
            selectedSiteData = site;
            
            // ✅ ذخیره نام در data
            $('#selectedSiteInfo').data('site-name', site.name);
            $('#selectedSiteInfo').text('محل انتخاب شد');
            
            // ✅ بروزرسانی لیست سایت‌ها
            if (selectedCustomerId) {
                loadSites(selectedCustomerId);
            }
            
            // ✅ بروزرسانی خلاصه اطلاعات
            updateSummary();
            
            // ✅ نمایش پیام تایید (فقط یک بار)
            Swal.fire({
                icon: 'success',
                title: 'محل نصب انتخاب شد',
                text: site.name + ' با موفقیت انتخاب شد',
                timer: 1500,
                showConfirmButton: false
            });
        }
    })
    .catch(function(error) {
        console.error('❌ خطا در دریافت سایت:', error);
        showError('خطا در دریافت اطلاعات سایت');
    });
}

// ✅ تابع لغو انتخاب سایت (با پیام تایید)
// ============================================
// تابع لغو انتخاب سایت
// ============================================
function clearSite() {
    selectedSiteId = null;
    selectedSiteData = null; // ✅ پاک کردن اطلاعات کامل
    $('#selectedSiteInfo').text('');
    $('#selectedSiteInfo').removeData('site-name');
    
    Swal.fire({
        icon: 'info',
        title: 'محل نصب لغو شد',
        text: 'انتخاب محل نصب با موفقیت لغو شد',
        timer: 1500,
        showConfirmButton: false
    });
    
    if (selectedCustomerId) loadSites(selectedCustomerId);
    updateSummary();
}

// ✅ تابع نمایش فرم ثبت محل جدید
function showNewSite() {
    // ✅ نمایش فرم
    $('#newSiteForm').show();
    
    // ✅ پاک کردن کامل فیلدها
    $('#siteName').val('');
    $('#siteAddress').val('');
    $('#siteLocation').val('');
    $('#siteDescription').val('');
    $('#buildingName').val('');
    $('#buildingManager').val('');
    $('#managerPhone').val('');
    $('#lobbyPhone').val('');
    $('#responsibleName').val('');
    $('#responsiblePosition').val('');
    $('#responsiblePhone').val('');
    
    // ✅ تنظیم نوع محل به پیش‌فرض
    $('#siteType').val('RESIDENTIAL');
    $('#siteResidentialFields').show();
    $('#siteOrganizationFields').hide();
    
    // ✅ رفرش لیست سایت‌ها (بدون دکمه "محل جدید")
    if (selectedCustomerId) loadSites(selectedCustomerId);
}

// ✅ تابع لغو ثبت محل جدید
function cancelNewSite() {
    $('#newSiteForm').hide();
    // ✅ نمایش مجدد دکمه "محل جدید"
    if (selectedCustomerId) loadSites(selectedCustomerId);
}

// ✅ تابع ثبت محل جدید
function saveSite() {
    if (!selectedCustomerId) {
        showError('لطفاً ابتدا مشتری را انتخاب کنید');
        return;
    }
    
    var data = {
        name: $('#siteName').val().trim(),
        type: $('#siteType').val(),
        address: $('#siteAddress').val().trim() || null,
        location: $('#siteLocation').val().trim() || null,
        description: $('#siteDescription').val().trim() || null,
        customer_id: selectedCustomerId
    };
    
    if (!data.name) {
        showError('لطفاً نام محل را وارد کنید');
        $('#siteName').focus();
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
        selectedSiteId = site.id;
        $('#selectedSiteInfo').text('محل انتخاب شد');
        cancelNewSite();
        if (selectedCustomerId) loadSites(selectedCustomerId);
        updateSummary();
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
// بخش ۱۰: ثبت نهایی (نسخه بهبود یافته کامل)
// ============================================

// ============================================
// تابع ثبت پرونده (جدا شده از رویداد submit)
// ============================================
function submitOrder() {
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
        customer_complaint: $('#customerComplaint').val().trim(),
        boards: boards
    };
    
    console.log('📦 داده‌های نهایی:', orderData);
    
    // نمایش لودینگ
    Swal.fire({
        title: 'در حال ثبت پرونده...',
        text: 'لطفاً صبر کنید',
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
        
        // ✅ نمایش پیام موفقیت با جزئیات کامل
        var successHtml = 
            '<div class="text-center">' +
                '<div class="mb-3 p-3 bg-light rounded">' +
                    '<strong class="text-muted">کد رهگیری</strong><br>' +
                    '<code class="fs-1 text-primary fw-bold">' + data.tracking_code + '</code>' +
                '</div>' +
                '<div class="row g-2 mb-3">' +
                    '<div class="col-6">' +
                        '<div class="p-2 bg-success bg-opacity-10 rounded">' +
                            '<strong class="text-muted">شماره پرونده</strong><br>' +
                            '<span class="fs-4 fw-bold text-success">#' + data.id + '</span>' +
                        '</div>' +
                    '</div>' +
                    '<div class="col-6">' +
                        '<div class="p-2 bg-info bg-opacity-10 rounded">' +
                            '<strong class="text-muted">وضعیت</strong><br>' +
                            '<span class="badge bg-secondary fs-6">ثبت شده</span>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<div class="row g-2 mb-3">' +
                    '<div class="col-6">' +
                        '<div class="p-2 bg-warning bg-opacity-10 rounded">' +
                            '<strong class="text-muted">تعداد عکس‌ها</strong><br>' +
                            '<span class="fs-5">' + (data.photos_count || 0) + '</span>' +
                        '</div>' +
                    '</div>' +
                    '<div class="col-6">' +
                        '<div class="p-2 bg-primary bg-opacity-10 rounded">' +
                            '<strong class="text-muted">تعداد بردها</strong><br>' +
                            '<span class="fs-5">' + (data.boards_count || 0) + '</span>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                '<hr>' +
                '<div class="d-grid gap-2 d-md-flex justify-content-md-center">' +
                    '<button class="btn btn-primary me-md-2" onclick="window.open(\'/print/' + data.id + '\', \'_blank\')">' +
                        '<i class="fas fa-print"></i> چاپ برگه پذیرش' +
                    '</button>' +
                    '<button class="btn btn-success" onclick="window.location.href=\'/order/' + data.id + '\'">' +
                        '<i class="fas fa-eye"></i> مشاهده پرونده' +
                    '</button>' +
                '</div>' +
            '</div>';
        
        Swal.fire({
            icon: 'success',
            title: '✅ پرونده با موفقیت ثبت شد!',
            html: successHtml,
            showConfirmButton: false,
            timer: 8000,
            timerProgressBar: true,
            allowOutsideClick: true,
            didOpen: function() {
                // اضافه کردن استایل برای دکمه‌ها
                var buttons = document.querySelectorAll('.swal2-html-container .btn');
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].style.margin = '5px';
                }
            }
        });
        
        // ✅ هدایت خودکار به صفحه پرونده بعد از ۴ ثانیه
        setTimeout(function() {
            window.location.href = '/order/' + data.id;
        }, 4000);
    })
    .catch(function(error) {
        Swal.close();
        
        // ✅ نمایش خطای کاربرپسند
        Swal.fire({
            icon: 'error',
            title: '❌ خطا در ثبت پرونده',
            text: error.message || 'خطای ناشناخته رخ داده است. لطفاً دوباره تلاش کنید.',
            confirmButtonColor: '#dc3545',
            confirmButtonText: 'تلاش مجدد'
        });
    });
}

// ============================================
// رویداد submit فرم (با اعتبارسنجی کامل)
// ============================================
$('#orderForm').on('submit', function(e) {
    e.preventDefault();
    
    // ============================================
    // 1. اعتبارسنجی اطلاعات ضروری
    // ============================================
    
    // بررسی مشتری
    if (!selectedCustomerId) {
        Swal.fire({
            icon: 'warning',
            title: 'مشتری انتخاب نشده',
            text: 'لطفاً ابتدا مشتری را انتخاب کنید',
            confirmButtonColor: '#0d6efd',
            confirmButtonText: 'رفتن به بخش مشتری'
        }).then(function() {
            goToStep(2);
            $('#customerSearch').focus();
        });
        return;
    }
    
    // بررسی پنل
    if (!selectedPanelId) {
        Swal.fire({
            icon: 'warning',
            title: 'پنل انتخاب نشده',
            text: 'لطفاً ابتدا پنل را انتخاب یا ثبت کنید',
            confirmButtonColor: '#0d6efd',
            confirmButtonText: 'رفتن به بخش پنل'
        }).then(function() {
            goToStep(5);
            $('#panelSearch').focus();
        });
        return;
    }
    
    // بررسی شرح مشتری
    var complaint = $('#customerComplaint').val().trim();
    if (!complaint || complaint.length < 3) {
        Swal.fire({
            icon: 'warning',
            title: 'شرح مشکل وارد نشده',
            text: 'لطفاً شرح مشکل را از زبان مشتری وارد کنید (حداقل ۳ کاراکتر)',
            confirmButtonColor: '#0d6efd',
            confirmButtonText: 'رفتن به بخش شرح مشتری'
        }).then(function() {
            goToStep(9);
            $('#customerComplaint').focus();
        });
        return;
    }
    
    // ============================================
    // 2. هشدار برای فیلدهای اختیاری
    // ============================================
    
    // بررسی مسئول ارسال (اختیاری ولی توصیه شده)
    var senderName = $('#senderName').val().trim();
    var senderPhone = $('#senderMobile').val().trim();
    
    if (!senderName || !senderPhone) {
        Swal.fire({
            icon: 'question',
            title: 'اطلاعات مسئول ارسال',
            html: 'آیا از ثبت پرونده بدون مشخصات کامل مسئول ارسال مطمئن هستید؟<br>' +
                  '<small class="text-muted">تکمیل این اطلاعات برای ارتباط با مشتری ضروری است</small>',
            showCancelButton: true,
            confirmButtonColor: '#ffc107',
            cancelButtonColor: '#6c757d',
            confirmButtonText: 'بله، ثبت کن',
            cancelButtonText: 'برگشت و تکمیل'
        }).then(function(result) {
            if (result.isConfirmed) {
                submitOrder();
            } else {
                goToStep(4);
                $('#senderName').focus();
            }
        });
        return;
    }
    
    // ============================================
    // 3. تایید نهایی کاربر
    // ============================================
    
    // نمایش خلاصه اطلاعات برای تایید نهایی
    var customerName = $('#selectedCustomerInfo').data('customer-name') || 'مشتری انتخاب شده';
    var panelInfo = $('#selectedPanelInfo').text() || 'پنل انتخاب شده';
    var siteInfo = selectedSiteData ? selectedSiteData.name : 'محل انتخاب نشده';
    
    Swal.fire({
        title: 'تایید نهایی',
        html: 
            '<div class="text-start">' +
                '<p><strong>👤 مشتری:</strong> ' + customerName + '</p>' +
                '<p><strong>📍 محل نصب:</strong> ' + siteInfo + '</p>' +
                '<p><strong>🔧 پنل:</strong> ' + panelInfo + '</p>' +
                '<p><strong>📦 تعداد بردها:</strong> ' + boards.length + '</p>' +
                '<p><strong>🖼️ تعداد عکس‌ها:</strong> ' + damagePhotos.length + '</p>' +
                '<hr>' +
                '<p class="text-muted small">آیا از صحت اطلاعات وارد شده مطمئن هستید؟</p>' +
            '</div>',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#198754',
        cancelButtonColor: '#dc3545',
        confirmButtonText: '✅ بله، ثبت نهایی',
        cancelButtonText: '🔙 بررسی مجدد'
    }).then(function(result) {
        if (result.isConfirmed) {
            submitOrder();
        }
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