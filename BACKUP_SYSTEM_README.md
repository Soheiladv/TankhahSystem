# سیستم پشتیبان‌گیری بروزرسانی شده

## معرفی
سیستم پشتیبان‌گیری بروزرسانی شده برای پشتیبان‌گیری از هر دو دیتابیس (اصلی و لاگ) طراحی شده است.

## ویژگی‌های جدید

### 🔄 پشتیبان‌گیری دوگانه
- **دیتابیس اصلی**: شامل داده‌های اصلی سیستم
- **دیتابیس لاگ**: شامل داده‌های version_tracker و audit_log

### 📁 مدیریت فایل‌های پشتیبان
- فشرده‌سازی خودکار
- پاکسازی فایل‌های قدیمی
- نمایش آمار حجم و تعداد فایل‌ها

### 🤖 پشتیبان‌گیری خودکار
- اسکریپت‌های خودکار
- بررسی وضعیت پشتیبان‌گیری
- لاگ‌گذاری کامل

## دستورات مدیریت

### پشتیبان‌گیری کامل
```bash
# پشتیبان‌گیری از هر دو دیتابیس
python manage.py backup_all_databases

# پشتیبان‌گیری با فشرده‌سازی
python manage.py backup_all_databases --compress

# پشتیبان‌گیری با رمزگذاری
python manage.py backup_all_databases --encrypt

# پشتیبان‌گیری + پاکسازی فایل‌های قدیمی
python manage.py backup_all_databases --cleanup
```

### بازیابی
```bash
# بازیابی هر دو دیتابیس
python manage.py restore_all_databases --file backup_file.sql

# بازیابی فقط دیتابیس اصلی
python manage.py restore_all_databases --file backup_file.sql --database main

# بازیابی فقط دیتابیس لاگ
python manage.py restore_all_databases --file backup_file.sql --database logs
```

### مدیریت فایل‌های پشتیبان
```bash
# نمایش لیست فایل‌های پشتیبان
python manage.py manage_backups --list

# نمایش حجم فایل‌ها
python manage.py manage_backups --size

# پاکسازی فایل‌های قدیمی‌تر از 7 روز
python manage.py manage_backups --cleanup --days 7
```

## اسکریپت‌های خودکار

### پشتیبان‌گیری خودکار
```bash
# اجرای پشتیبان‌گیری
python scripts/auto_backup.py

# بررسی وضعیت پشتیبان‌گیری
python scripts/auto_backup.py --check

# اجرا در Windows
scripts/backup.bat
```

### تنظیم Task Scheduler (Windows)
1. باز کردن Task Scheduler
2. ایجاد Task جدید
3. تنظیم Trigger: روزانه در ساعت مشخص
4. تنظیم Action: اجرای `scripts/backup.bat`

### تنظیم Cron (Linux/Mac)
```bash
# ویرایش crontab
crontab -e

# اضافه کردن خط زیر برای پشتیبان‌گیری روزانه در ساعت 2 صبح
0 2 * * * /path/to/project/scripts/auto_backup.py
```

## ساختار فایل‌های پشتیبان

```
backups/
├── tankhasystem_20241201_020000.sql.gz    # دیتابیس اصلی
├── tankhah_logs_db_20241201_020000.sql.gz # دیتابیس لاگ
├── tankhasystem_20241202_020000.sql.gz
├── tankhah_logs_db_20241202_020000.sql.gz
└── ...
```

## تنظیمات

### متغیرهای محیطی (.env)
```env
# دیتابیس اصلی
DATABASE_DEFAULT_NAME=tankhasystem
DATABASE_DEFAULT_USER=root
DATABASE_DEFAULT_PASSWORD=
DATABASE_DEFAULT_HOST=127.0.0.1
DATABASE_DEFAULT_PORT=3306

# دیتابیس لاگ
DATABASE_LOGS_NAME=tankhah_logs_db
DATABASE_LOGS_USER=root
DATABASE_LOGS_PASSWORD=
DATABASE_LOGS_HOST=localhost
DATABASE_LOGS_PORT=3306
```

### تنظیمات Django (settings.py)
```python
# تنظیمات پشتیبان‌گیری
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': os.path.join(BASE_DIR, 'backups')}
DBBACKUP_CLEANUP_KEEP_DAYS = 7
DBBACKUP_MAIL_ADMINS = True
```

## نکات مهم

### 🔒 امنیت
- فایل‌های پشتیبان را در مکان امن نگه‌دارید
- از رمزگذاری برای فایل‌های حساس استفاده کنید
- دسترسی به پوشه backups را محدود کنید

### 📊 مانیتورینگ
- لاگ‌های پشتیبان‌گیری را بررسی کنید
- حجم فایل‌های پشتیبان را مانیتور کنید
- تست بازیابی را به صورت منظم انجام دهید

### ⚡ بهینه‌سازی
- فشرده‌سازی برای کاهش حجم فایل‌ها
- پاکسازی منظم فایل‌های قدیمی
- استفاده از پشتیبان‌گیری تفاضلی برای فایل‌های بزرگ

## عیب‌یابی

### مشکل: خطا در اتصال به دیتابیس
- بررسی تنظیمات اتصال در .env
- اطمینان از در دسترس بودن MySQL
- بررسی مجوزهای کاربر دیتابیس

### مشکل: خطا در نوشتن فایل
- بررسی مجوزهای نوشتن در پوشه backups
- اطمینان از وجود فضای کافی دیسک
- بررسی مسیر پوشه backups

### مشکل: فایل‌های پشتیبان خالی
- بررسی تنظیمات DBBACKUP_CONNECTORS
- اطمینان از صحت نام دیتابیس‌ها
- بررسی لاگ‌های خطا

## تغییرات اخیر

### نسخه 2.0.0
- پشتیبان‌گیری از هر دو دیتابیس
- دستورات مدیریت پیشرفته
- اسکریپت‌های خودکار
- بهبود مدیریت فایل‌ها
- لاگ‌گذاری کامل
