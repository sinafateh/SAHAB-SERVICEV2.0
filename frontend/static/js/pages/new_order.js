// ============================================
// صفحه ثبت پرونده جدید
// ============================================

$(document).ready(function() {
    if (!checkAuth()) return;
    
    $('#orderForm').on('submit', function(e) {
        e.preventDefault();
        
        const submitBtn = $(this).find('button[type="submit"]');
        submitBtn.html('<i class="fas fa-spinner fa-spin"></i> در حال ثبت...').prop('disabled', true);
        
        // 1. ثبت مشتری
        const customerData = {
            name: $('#customerName').val(),
            company: $('#customerCompany').val() || null,
            phone: $('#customerPhone').val(),
            email: $('#customerEmail').val() || null,
            address: $('#customerAddress').val() || null
        };
        
        $.post('/reception/customers', customerData)
            .done(function(customer) {
                // 2. ثبت دستگاه
                const deviceData = {
                    brand: $('#deviceBrand').val(),
                    model: $('#deviceModel').val(),
                    part_number: $('#devicePartNumber').val(),
                    serial_number: $('#deviceSerialNumber').val(),
                    firmware_version: $('#deviceFirmware').val() || null,
                    customer_id: customer.id
                };
                return $.post('/reception/devices', deviceData);
            })
            .done(function(device) {
                // 3. ثبت پرونده
                const orderData = {
                    customer_id: device.customer_id,
                    device_id: device.id,
                    customer_complaint: $('#customerComplaint').val(),
                    priority: 0
                };
                return $.post('/reception/repair-orders', orderData);
            })
            .done(function(order) {
                showSuccess(
                    `پرونده با موفقیت ثبت شد!<br>
                    کد رهگیری: <strong>${order.tracking_code}</strong><br>
                    وضعیت: <span class="badge bg-secondary">${order.status}</span>`
                );
                setTimeout(() => {
                    window.location.href = `/order/${order.id}`;
                }, 1500);
            })
            .fail(function(xhr) {
                let errorMsg = 'خطا در ثبت اطلاعات';
                if (xhr.responseJSON && xhr.responseJSON.detail) {
                    errorMsg = xhr.responseJSON.detail;
                }
                showError(errorMsg);
            })
            .always(function() {
                submitBtn.html('<i class="fas fa-save"></i> ثبت پرونده').prop('disabled', false);
            });
    });
});