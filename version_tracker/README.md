# Version Tracker - سیستم مدیریت نسخه

## معرفی
سیستم `version_tracker` برای مدیریت خودکار نسخه‌های نرم‌افزار طراحی شده است. این سیستم تغییرات فایل‌ها را ردیابی کرده و نسخه‌های جدید را به صورت خودکار ایجاد می‌کند.

## ویژگی‌ها
- **ردیابی خودکار تغییرات**: تغییرات فایل‌های `.py`, `.html`, `.js`, `.css` را ردیابی می‌کند
- **مدیریت نسخه**: نسخه‌های Major، Minor، Patch و Build را مدیریت می‌کند
- **بهینه‌سازی دیتابیس**: بدون ذخیره محتوای فایل‌ها برای کاهش حجم دیتابیس
- **کش کردن**: استفاده از کش برای بهبود عملکرد
- **گزارش‌گیری**: گزارش‌های تفصیلی از تغییرات

## مدل‌ها

### AppVersion
نسخه‌های اپلیکیشن‌ها
- `app_name`: نام اپلیکیشن
- `version_number`: شماره نسخه (مثل 1.2.3.4)
- `version_type`: نوع نسخه (major, minor, patch, build)
- `code_hash`: هش کل کدها
- `changed_files`: لیست فایل‌های تغییر یافته
- `system_info`: اطلاعات سیستم

### FileHash
هش فایل‌ها (بدون ذخیره محتوا)
- `file_path`: مسیر فایل
- `hash_value`: مقدار هش
- `timestamp`: زمان ایجاد

### CodeChangeLog
لاگ تغییرات کد (بدون ذخیره محتوا)
- `file_name`: نام فایل
- `change_type`: نوع تغییر (ADDED, MODIFIED, DELETED)
- `change_date`: تاریخ تغییر

### FinalVersion
نسخه نهایی پروژه
- `version_number`: شماره نسخه نهایی
- `release_date`: تاریخ انتشار

## دستورات مدیریت

### به‌روزرسانی نسخه‌ها
```bash
python manage.py update_versions
```

### پاکسازی داده‌های قدیمی
```bash
# حذف داده‌های قدیمی‌تر از 30 روز
python manage.py cleanup_old_data --days 30

# نگه داشتن فقط 10 نسخه اخیر
python manage.py cleanup_old_data --keep-versions 10

# حالت تست (بدون حذف واقعی)
python manage.py cleanup_old_data --dry-run
```

### بهینه‌سازی دیتابیس
```bash
# تحلیل حجم دیتابیس
python manage.py optimize_database --analyze

# بهینه‌سازی دیتابیس
python manage.py optimize_database --optimize
```

## تنظیمات

### اپلیکیشن‌های تحت نظارت
در `models.py`:
```python
monitored_apps = {'tankhah', 'core', 'reports', 'budgets', 'accounts', 'version_tracker'}
```

### انواع فایل‌های تحت نظارت
```python
valid_extensions = ('.py', '.html', '.js', '.css')
```

### پوشه‌های مستثنی
```python
excluded_dirs = ('__pycache__', 'migrations', 'static', 'staticfiles', 'venv', 'media')
```

## بهینه‌سازی‌ها

### کاهش حجم دیتابیس
- حذف فیلد `content` از `FileHash`
- حذف فیلدهای `old_code` و `new_code` از `CodeChangeLog`
- استفاده از فیلد `change_type` به جای ذخیره محتوا

### بهبود عملکرد
- استفاده از کش برای هش فایل‌ها
- ایندکس‌گذاری مناسب
- bulk operations برای درج داده‌ها

## نکات مهم

1. **پاکسازی منظم**: از دستور `cleanup_old_data` به صورت منظم استفاده کنید
2. **مانیتورینگ حجم**: از دستور `optimize_database --analyze` برای بررسی حجم استفاده کنید
3. **بکاپ**: قبل از پاکسازی داده‌ها، حتماً بکاپ تهیه کنید
4. **نسخه‌های مهم**: نسخه‌های مهم را با `is_final=True` علامت‌گذاری کنید

## عیب‌یابی

### مشکل: نسخه‌ها ایجاد نمی‌شوند
- بررسی کنید که signal ها فعال هستند
- دستور `update_versions` را به صورت دستی اجرا کنید
- لاگ‌ها را بررسی کنید

### مشکل: حجم دیتابیس زیاد است
- از دستور `cleanup_old_data` استفاده کنید
- تنظیمات `keep_versions` را کاهش دهید
- فایل‌های غیرضروری را از `monitored_apps` حذف کنید

## تغییرات اخیر

### نسخه 2.0.0
- حذف ذخیره محتوای فایل‌ها
- بهینه‌سازی مدل‌ها
- اضافه کردن دستورات پاکسازی و بهینه‌سازی
- بهبود عملکرد و کاهش حجم دیتابیس
