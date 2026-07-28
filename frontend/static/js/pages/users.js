// ============================================
// صفحه مدیریت کاربران
// ============================================

function loadUsers() {
    $('#users-table').html('<i class="fas fa-spinner fa-spin"></i> در حال بارگذاری...');
    
    $.ajax({
        url: '/auth/users',
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        },
        success: function(users) {
            if (users && users.length > 0) {
                let html = `
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>شناسه</th>
                                    <th>نام کاربری</th>
                                    <th>نام کامل</th>
                                    <th>نقش</th>
                                    <th>وضعیت</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                users.forEach(user => {
                    const roleLabels = {
                        'ADMIN': 'مدیر سیستم',
                        'RECEPTION': 'پذیرش',
                        'CUSTOMER_RELATIONS': 'روابط با مشتریان',
                        'TECHNICAL': 'فنی',
                        'VIEWER': 'بیننده'
                    };
                    const statusBadge = user.is_active ? 
                        '<span class="badge bg-success">فعال</span>' : 
                        '<span class="badge bg-danger">غیرفعال</span>';
                    
                    html += `
                        <tr>
                            <td>#${user.id}</td>
                            <td><code>${user.username}</code></td>
                            <td>${user.full_name}</td>
                            <td><span class="badge bg-primary">${roleLabels[user.role] || user.role}</span></td>
                            <td>${statusBadge}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="editUser(${user.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${user.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                });
                html += '</tbody></table></div>';
                $('#users-table').html(html);
            } else {
                $('#users-table').html('<p class="text-muted py-3">هیچ کاربری وجود ندارد</p>');
            }
        },
        error: function(xhr) {
            if (xhr.status === 403) {
                showError('دسترسی غیرمجاز');
            } else {
                showError('خطا در بارگذاری کاربران');
            }
        }
    });
}

function editUser(userId) {
    showSuccess('ویرایش کاربر #' + userId + ' (در حال توسعه...)');
}

function deleteUser(userId) {
    Swal.fire({
        title: 'حذف کاربر',
        text: 'آیا از حذف این کاربر مطمئن هستید؟',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'بله، حذف کن',
        cancelButtonText: 'انصراف'
    }).then((result) => {
        if (result.isConfirmed) {
            $.ajax({
                url: `/auth/users/${userId}`,
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                },
                success: function() {
                    showSuccess('کاربر با موفقیت حذف شد');
                    loadUsers();
                },
                error: function() {
                    showError('خطا در حذف کاربر');
                }
            });
        }
    });
}

$(document).ready(function() {
    if (!checkAuth()) return;
    
    // فقط مدیران
    const user = getUser();
    if (user && user.role !== 'ADMIN') {
        showError('دسترسی غیرمجاز');
        window.location.href = '/';
        return;
    }
    
    loadUsers();
    
    $('#addUserBtn').click(function() {
        showSuccess('افزودن کاربر جدید (در حال توسعه...)');
    });
});