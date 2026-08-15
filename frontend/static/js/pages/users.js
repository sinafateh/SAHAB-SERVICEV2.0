// ============================================
// صفحه مدیریت کاربران
// ============================================

console.log('✅ users.js شروع به کار کرد');

// ============================================
// تابع بارگذاری کاربران
// ============================================
function loadUsers() {
    console.log('🔄 بارگذاری کاربران...');
    
    $('#users-table').html(
        '<div class="text-center py-5">' +
            '<i class="fas fa-spinner fa-spin fa-2x text-primary"></i>' +
            '<p class="mt-2 text-muted">در حال بارگذاری کاربران...</p>' +
        '</div>'
    );
    
    var token = localStorage.getItem('access_token');
    
    fetch('/auth/users', {
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json'
        }
    })
    .then(function(response) {
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('دسترسی غیرمجاز. فقط مدیران می‌توانند کاربران را مدیریت کنند.');
            }
            throw new Error('خطا در دریافت اطلاعات: ' + response.status);
        }
        return response.json();
    })
    .then(function(users) {
        console.log('📋 کاربران دریافت شدند:', users);
        if (users && users.length > 0) {
            renderUsersTable(users);
        } else {
            $('#users-table').html(
                '<div class="text-center py-4">' +
                    '<i class="fas fa-users fa-3x text-muted mb-3"></i>' +
                    '<p class="text-muted">هیچ کاربری وجود ندارد</p>' +
                '</div>'
            );
        }
    })
    .catch(function(error) {
        console.error('❌ خطا:', error);
        $('#users-table').html(
            '<div class="alert alert-danger">' +
                '<i class="fas fa-exclamation-triangle"></i> ' +
                error.message +
            '</div>'
        );
    });
}

// ============================================
// تابع رندر جدول کاربران
// ============================================
function renderUsersTable(users) {
    var roleLabels = {
        'ADMIN': 'مدیر سیستم',
        'RECEPTION': 'پذیرش',
        'CUSTOMER_RELATIONS': 'روابط با مشتریان',
        'TECHNICAL': 'فنی',
        'MANAGEMENT': 'مدیریت',
        'VIEWER': 'بیننده'
    };
    
    var roleColors = {
        'ADMIN': 'danger',
        'RECEPTION': 'primary',
        'CUSTOMER_RELATIONS': 'info',
        'TECHNICAL': 'warning',
        'MANAGEMENT': 'dark',
        'VIEWER': 'secondary'
    };
    
    var html = '';
    html += '<div class="table-responsive">';
    html += '<table class="table table-hover table-striped">';
    html += '<thead class="table-light">';
    html += '<tr>';
    html += '<th class="text-center">#</th>';
    html += '<th>نام کاربری</th>';
    html += '<th>نام کامل</th>';
    html += '<th>نقش</th>';
    html += '<th>بخش</th>';
    html += '<th>وضعیت</th>';
    html += '<th>آخرین ورود</th>';
    html += '<th class="text-center">عملیات</th>';
    html += '</tr>';
    html += '</thead>';
    html += '<tbody>';
    
    for (var i = 0; i < users.length; i++) {
        var user = users[i];
        var statusBadge = user.is_active ?
            '<span class="badge bg-success">فعال</span>' :
            '<span class="badge bg-danger">غیرفعال</span>';
        
        var roleLabel = roleLabels[user.role] || user.role;
        var roleColor = roleColors[user.role] || 'secondary';
        
        html += '<tr>';
        html += '<td class="text-center">' + (i + 1) + '</td>';
        html += '<td><code class="fw-bold">' + user.username + '</code></td>';
        html += '<td>' + user.full_name + '</td>';
        html += '<td><span class="badge bg-' + roleColor + '">' + roleLabel + '</span></td>';
        html += '<td>' + (user.department || '-') + '</td>';
        html += '<td>' + statusBadge + '</td>';
        html += '<td><small>' + formatDate(user.last_login) + '</small></td>';
        html += '<td class="text-center">';
        html += '<button class="btn btn-sm btn-outline-primary me-1" onclick="editUser(' + user.id + ')">';
        html += '<i class="fas fa-edit"></i>';
        html += '</button>';
        html += '<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(' + user.id + ')">';
        html += '<i class="fas fa-trash"></i>';
        html += '</button>';
        html += '</td>';
        html += '</tr>';
    }
    
    html += '</tbody>';
    html += '</table>';
    html += '</div>';
    html += '<div class="d-flex justify-content-between align-items-center mt-3">';
    html += '<small class="text-muted">' + users.length + ' کاربر</small>';
    html += '</div>';
    
    $('#users-table').html(html);
}

// ============================================
// تابع ویرایش کاربر
// ============================================
function editUser(userId) {
    showInfo('ویرایش کاربر #' + userId + ' (در حال توسعه...)');
}

// ============================================
// تابع حذف کاربر
// ============================================
function deleteUser(userId) {
    Swal.fire({
        title: 'حذف کاربر',
        text: 'آیا از حذف این کاربر مطمئن هستید؟ این عملیات قابل بازگشت نیست.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'بله، حذف کن',
        cancelButtonText: 'انصراف'
    }).then(function(result) {
        if (result.isConfirmed) {
            var token = localStorage.getItem('access_token');
            
            Swal.fire({
                title: 'در حال حذف...',
                allowOutsideClick: false,
                showConfirmButton: false,
                willOpen: function() {
                    Swal.showLoading();
                }
            });
            
            fetch('/auth/users/' + userId, {
                method: 'DELETE',
                headers: {
                    'Authorization': 'Bearer ' + token,
                    'Content-Type': 'application/json'
                }
            })
            .then(function(response) {
                if (!response.ok) {
                    return response.json().then(function(err) {
                        throw new Error(err.detail || 'خطا در حذف کاربر');
                    });
                }
                return response.json();
            })
            .then(function() {
                Swal.close();
                showSuccess('کاربر با موفقیت حذف شد');
                loadUsers();
            })
            .catch(function(error) {
                Swal.close();
                showError(error.message || 'خطا در حذف کاربر');
            });
        }
    });
}

// ============================================
// تابع نمایش مودال افزودن کاربر
// ============================================
function showAddUserModal() {
    showInfo('افزودن کاربر جدید (در حال توسعه...)');
}

// ============================================
// بارگذاری اولیه صفحه
// ============================================
$(document).ready(function() {
    console.log('📄 $(document).ready در users.js اجرا شد');
    
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
    
    // بررسی نقش کاربر (فقط مدیران)
    try {
        var userData = JSON.parse(user);
        console.log('👤 نقش کاربر:', userData.role);
        
        if (userData.role !== 'ADMIN') {
            showError('دسترسی غیرمجاز. فقط مدیران می‌توانند کاربران را مدیریت کنند.');
            setTimeout(function() {
                window.location.href = '/';
            }, 1500);
            return;
        }
    } catch (e) {
        console.error('❌ خطا در parse user:', e);
        window.location.href = '/login';
        return;
    }
    
    // بارگذاری کاربران
    loadUsers();
    
    // دکمه افزودن کاربر
    $('#addUserBtn').on('click', function() {
        showAddUserModal();
    });
    
    console.log('✅ users.js راه‌اندازی شد');
});
