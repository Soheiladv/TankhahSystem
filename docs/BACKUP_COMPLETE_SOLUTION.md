# راهنمای کامل سیستم Backup با قابلیت‌های جدید

## ✅ مشکلات رفع شده

### **1. خطای `admin:index`**
- **مشکل**: `Reverse for 'index' not found`
- **راه‌حل**: تغییر به URL استاتیک `/admin/`

### **2. عدم وجود Restore**
- **اضافه شده**: دکمه و صفحه بازگردانی
- **URL**: `{% url 'backup:restore' file.file_name %}`

### **3. عدم وجود MySQL استاندارد**
- **اضافه شده**: پشتیبان‌گیری MySQL استاندارد
- **URL**: `{% url 'backup:mysql' %}`

## 🚀 URL های جدید اضافه شده

### **سیستم Backup جدید**:
```python
# در version_tracker/backup_urls.py
urlpatterns = [
    path('', backup_list_view, name='list'),                    # /backup/
    path('create/', backup_create_view, name='create'),         # /backup/create/
    path('delete/<str:file_name>/', backup_delete_view, name='delete'),
    path('encrypt/<str:file_name>/', backup_encrypt_view, name='encrypt'),
    path('restore/<str:file_name>/', backup_restore_view, name='restore'),  # جدید
    path('mysql/', backup_mysql_view, name='mysql'),            # جدید
]
```

### **URL های کامل**:
| نام | URL | توضیح |
|-----|-----|--------|
| `backup:list` | `/backup/` | لیست فایل‌های backup |
| `backup:create` | `/backup/create/` | ایجاد backup جدید |
| `backup:mysql` | `/backup/mysql/` | **MySQL استاندارد** |
| `backup:restore` | `/backup/restore/<file>/` | **بازگردانی فایل** |
| `backup:delete` | `/backup/delete/<file>/` | حذف فایل |
| `backup:encrypt` | `/backup/encrypt/<file>/` | رمزگذاری فایل |

## 🎯 قابلیت‌های جدید

### **1. بازگردانی (Restore)**
- **دکمه**: در جدول فایل‌ها
- **رنگ**: زرد (Warning)
- **آیکون**: `fas fa-undo`
- **تأیید**: پیام تأیید قبل از بازگردانی
- **Template**: `templates/admin/backup_restore.html`

### **2. MySQL استاندارد**
- **دکمه**: در صفحه اصلی و Dashboard
- **رنگ**: سبز (Success)
- **آیکون**: `fas fa-database`
- **ویژگی**: استفاده از `mysqldump`
- **Template**: `templates/admin/backup_mysql.html`

## 🎨 تغییرات UI

### **صفحه اصلی Backup**:
```html
<!-- دکمه‌های عملیات -->
<div class="action-buttons">
    <a href="{% url 'backup:create' %}" class="btn btn-primary">
        <i class="fas fa-plus"></i> ایجاد پشتیبان‌گیری جدید
    </a>
    <a href="{% url 'backup:mysql' %}" class="btn btn-success">  <!-- جدید -->
        <i class="fas fa-database"></i> MySQL استاندارد
    </a>
    <a href="/admin/" class="btn btn-secondary">
        <i class="fas fa-arrow-left"></i> بازگشت به ادمین
    </a>
</div>
```

### **جدول فایل‌ها**:
```html
<!-- عملیات فایل‌ها -->
<div class="file-actions">
    <a href="{% url 'backup:delete' file.file_name %}" class="btn btn-danger btn-sm">
        <i class="fas fa-trash"></i> حذف
    </a>
    <a href="{% url 'backup:restore' file.file_name %}" class="btn btn-warning btn-sm">  <!-- جدید -->
        <i class="fas fa-undo"></i> بازگردانی
    </a>
    <!-- رمزگذاری و دانلود -->
</div>
```

### **Dashboard**:
```html
<!-- کارت سیستم جدید -->
<div class="d-grid gap-2">
    <a href="{% url 'backup:list' %}" class="btn btn-primary">مشاهده فایل‌ها</a>
    <a href="{% url 'backup:create' %}" class="btn btn-outline-primary">ایجاد بک‌آپ جدید</a>
    <a href="{% url 'backup:mysql' %}" class="btn btn-outline-success">MySQL استاندارد</a>  <!-- جدید -->
</div>
```

## 🔧 View های جدید

### **1. backup_restore_view**:
```python
def backup_restore_view(request, file_name):
    """بازگردانی فایل پشتیبان"""
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            call_command('dbrestore', '--database=default', f'--input-filename={file_name}')
            messages.success(request, f"فایل {file_name} با موفقیت بازگردانی شد")
        except Exception as e:
            messages.error(request, f"خطا در بازگردانی: {str(e)}")
        return redirect('backup:list')
    
    return render(request, 'admin/backup_restore.html', {
        'file_name': file_name,
        'backup_admin': backup_admin_instance
    })
```

### **2. backup_mysql_view**:
```python
def backup_mysql_view(request):
    """ایجاد پشتیبان‌گیری MySQL استاندارد"""
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            call_command('dbbackup', '--database=default', '--format=sql')
            call_command('dbbackup', '--database=logs', '--format=sql')
            messages.success(request, "پشتیبان‌گیری MySQL استاندارد ایجاد شد")
        except Exception as e:
            messages.error(request, f"خطا در ایجاد پشتیبان‌گیری MySQL: {str(e)}")
        return redirect('backup:list')
    
    return render(request, 'admin/backup_mysql.html', {
        'backup_admin': backup_admin_instance
    })
```

## 📁 فایل‌های جدید

### **Templates**:
- `templates/admin/backup_restore.html` - صفحه بازگردانی
- `templates/admin/backup_mysql.html` - صفحه MySQL استاندارد

### **URLs**:
- `version_tracker/backup_urls.py` - بروزرسانی شده

### **Views**:
- `version_tracker/admin_backup.py` - view های جدید اضافه شده

## 🎯 دسترسی‌های موجود

### **1. سیستم Backup جدید**:
```
http://127.0.0.1:8000/backup/
```

**قابلیت‌ها**:
- ✅ مشاهده فایل‌ها
- ✅ ایجاد backup جدید
- ✅ **MySQL استاندارد** (جدید)
- ✅ **بازگردانی فایل‌ها** (جدید)
- ✅ حذف فایل‌ها
- ✅ رمزگذاری فایل‌ها
- ✅ دانلود فایل‌ها

### **2. Dashboard**:
```
http://127.0.0.1:8000/accounts/new_databasebackup/
```

**مراحل**:
1. تب "عملیات دیتابیس"
2. تب "مدیریت بک‌آپ"
3. انتخاب سیستم مورد نظر

### **3. سیستم قدیمی**:
```
http://127.0.0.1:8000/backup-admin/
```

## ✨ مزایای جدید

### **1. بازگردانی کامل**:
- بازگردانی فایل‌های JSON و SQL
- تأیید امنیتی قبل از بازگردانی
- پیام‌های واضح موفقیت/خطا

### **2. MySQL استاندارد**:
- سازگار با تمام ابزارهای MySQL
- قابل بازگردانی با `mysql` command
- فشرده‌سازی خودکار
- پشتیبان‌گیری از هر دو دیتابیس

### **3. UI بهبود یافته**:
- دکمه‌های واضح و رنگی
- آیکون‌های مناسب
- پیام‌های تأیید
- طراحی ریسپانسیو

## 🎉 نتیجه

**سیستم backup کاملاً تکمیل شد!** 

**قابلیت‌های موجود**:
- ✅ **ایجاد backup** (JSON + MySQL)
- ✅ **بازگردانی backup** (جدید)
- ✅ **MySQL استاندارد** (جدید)
- ✅ **مدیریت فایل‌ها** (حذف، رمزگذاری، دانلود)
- ✅ **Dashboard یکپارچه**
- ✅ **UI مدرن و کاربرپسند**

**دسترسی اصلی**: `http://127.0.0.1:8000/backup/` 🚀
