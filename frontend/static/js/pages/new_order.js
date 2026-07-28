// ============================================
// صفحه ثبت پرونده جدید
// ============================================

console.log('✅ new_order.js شروع به کار کرد');

// ============================================
// تابع اعتبارسنجی فرم
// ============================================
function validateForm() {
    var name = $('#customerName').val().trim();
    var phone = $('#customerPhone').val().trim();
    var brand = $('#deviceBrand').val().trim();
    var model = $('#deviceModel').val().trim();
    var partNumber = $('#devicePartNumber').val().trim();
    var serialNumber = $('#deviceSerialNumber').val().trim();
    var complaint = $('#customerComplaint').val().trim();
    
    // اعتبارسنجی نام
    if (!name || name.length < 2) {
        showError('لطفاً نام مشتری را وارد کنید (حداقل ۲ کاراکتر)');
        $('#customerName').focus();
        return false;
    }
    
    // اعتبارسنجی شماره تماس
    var phoneRegex = /^[0-9]{10,15}$/;
    if (!phone || !phoneRegex.test(phone.replace(/[^0-9]/g, ''))) {
        showError('لطفاً شماره تماس معتبر وارد کنید (۱۰ تا ۱۵ رقم)');
        $('#customerPhone').focus();
        return false;
    }
    
    // اعتبارسنجی برند
    if (!brand || brand.length < 1) {
        showError('لطفاً برند دستگاه را وارد کنید');
        $('#deviceBrand').focus();
        return false;
    }
    
    // اعتبارسنجی مدل
    if (!model || model.length < 1) {
        showError('لطفاً مدل دستگاه را وارد کنید');
        $('#deviceModel').focus();
        return false;
    }
    
    // اعتبارسنجی پارت نامبر
    if (!partNumber || partNumber.length < 1) {
        showError('لطفاً پارت نامبر را وارد کنید');
        $('#devicePartNumber').focus();
        return false;
    }
    
    // اعتبارسنجی سریال نامبر
    if (!serialNumber || serialNumber.length < 1) {
        showError('لطفاً سریال نامبر را وارد کنید');
        $('#deviceSerialNumber').focus();
        return false;
    }
    
    // اعتبارسنجی شرح مشکل
    if (!complaint || complaint.length < 3) {
        showError('لطفاً شرح مشکل را وارد کنید (حداقل ۳ کاراکتر)');
        $('#customerComplaint').focus();
        return false;
    }
    
    return true;
}

// ============================================
// تابع ثبت پرونده
// ============================================
function submitOrder() {
    var submitBtn = $('#orderForm').find('button[type="submit"]');
    submitBtn.html('<i class="fas fa-spinner fa-spin"></i> در حال ثبت...').prop('disabled', true);
    
    var token = localStorage.getItem('access_token');
    
    // 1. ثبت مشتری
    var customerData = {
        name: $('#customerName').val().trim(),
        company: $('#customerCompany').val().trim() || null,
        phone: $('#customerPhone').val().trim(),
        phone_alternative: null,
        email: $('#customerEmail').val().trim() || null,
        address: $('#customerAddress').val().trim() || null
    };
    
    fetch('/reception/customers', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(customerData)
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت مشتری');
            });
        }
        return response.json();
    })
    .then(function(customer) {
        console.log('✅ مشتری ثبت شد:', customer);
        
        // 2. ثبت دستگاه
        var deviceData = {
            brand: $('#deviceBrand').val().trim(),
            model: $('#deviceModel').val().trim(),
            part_number: $('#devicePartNumber').val().trim(),
            serial_number: $('#deviceSerialNumber').val().trim(),
            firmware_version: $('#deviceFirmware').val().trim() || null,
            customer_id: customer.id
        };
        
        return fetch('/reception/devices', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(deviceData)
        });
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت دستگاه');
            });
        }
        return response.json();
    })
    .then(function(device) {
        console.log('✅ دستگاه ثبت شد:', device);
        
        // 3. ثبت پرونده
        var orderData = {
            customer_id: device.customer_id,
            device_id: device.id,
            customer_complaint: $('#customerComplaint').val().trim(),
            notes: null,
            priority: 0
        };
        
        return fetch('/reception/repair-orders', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(orderData)
        });
    })
    .then(function(response) {
        if (!response.ok) {
            return response.json().then(function(err) {
                throw new Error(err.detail || 'خطا در ثبت پرونده');
            });
        }
        return response.json();
    })
.then(function(order) {
    console.log('✅ پرونده ثبت شد:', order);
    console.log('📌 کد رهگیری:', order.tracking_code);
    
    showSuccess(
        'پرونده با موفقیت ثبت شد!<br><br>' +
        '<div class="text-center">' +
            '<strong>کد رهگیری:</strong><br>' +
            '<code class="fs-3 text-primary fw-bold">' + order.tracking_code + '</code><br><br>' +
            '<strong>وضعیت:</strong> <span class="badge bg-secondary">' + order.status + '</span>' +
        '</div>'
    );
    
    setTimeout(function() {
        window.location.href = '/order/' + order.id;
    }, 2000);
})
    .catch(function(error) {
        console.error('❌ خطا:', error);
        showError(error.message || 'خطا در ثبت اطلاعات. لطفاً دوباره تلاش کنید.');
    })
    .finally(function() {
        submitBtn.html('<i class="fas fa-save"></i> ثبت پرونده').prop('disabled', false);
    });
}

// ============================================
// بارگذاری اولیه صفحه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در new_order.js اجرا شد');
    
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
    
    // رویداد Submit فرم
    $('#orderForm').on('submit', function(e) {
        e.preventDefault();
        
        if (validateForm()) {
            // تایید نهایی
            Swal.fire({
                title: 'ثبت پرونده جدید',
                text: 'آیا از صحت اطلاعات وارد شده مطمئن هستید؟',
                icon: 'question',
                showCancelButton: true,
                confirmButtonColor: '#198754',
                cancelButtonColor: '#dc3545',
                confirmButtonText: 'بله، ثبت کن',
                cancelButtonText: 'بررسی مجدد'
            }).then(function(result) {
                if (result.isConfirmed) {
                    submitOrder();
                }
            });
        }
    });
    
    // اعتبارسنجی بلادرنگ برای شماره تماس
    $('#customerPhone').on('input', function() {
        var value = $(this).val().replace(/[^0-9]/g, '');
        $(this).val(value);
    });
    
    // دکمه نمونه‌سازی داده
    $('#sampleDataBtn').on('click', function() {
        $('#customerName').val('علی محمدی');
        $('#customerCompany').val('شرکت سها');
        $('#customerPhone').val('09123456789');
        $('#customerEmail').val('ali@example.com');
        $('#customerAddress').val('تهران، خیابان آزادی');
        $('#deviceBrand').val('Honeywell');
        $('#deviceModel').val('FireBase 2000');
        $('#devicePartNumber').val('FB-2000-X');
        $('#deviceSerialNumber').val('SN' + Math.floor(Math.random() * 1000000));
        $('#deviceFirmware').val('v2.1.3');
        $('#customerComplaint').val('دستگاه روشن نمی‌شود و بوی سوختگی می‌دهد');
        showSuccess('اطلاعات نمونه وارد شد!');
    });
    
    console.log('✅ new_order.js راه‌اندازی شد');
});