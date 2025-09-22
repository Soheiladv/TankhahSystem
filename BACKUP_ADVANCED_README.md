# سیستم پشتیبان‌گیری پیشرفته - راهنمای کامل

## 🎯 ویژگی‌های جدید

### ✅ رابط ادمین برای مدیریت
- **URL**: `http://127.0.0.1:8000/backup-admin/`
- حذف فایل‌های پشتیبان
- رمزگذاری فایل‌ها
- دانلود فایل‌های پشتیبان
- نمایش آمار کامل

### 🔐 رمزگذاری امن
- رمزگذاری فایل‌های پشتیبان
- استفاده از کتابخانه `cryptography`
- ذخیره فایل‌های رمزگذاری شده در پوشه جداگانه

### 📁 مدیریت پوشه‌ها
- پوشه اصلی: `backups/`
- پوشه رمزگذاری شده: `backups/encrypted/`
- امکان تنظیم پوشه سفارشی

### ⏰ پشتیبان‌گیری دوره‌ای
- پشتیبان‌گیری خودکار روزانه/هفتگی/ماهانه
- اجرای در پس‌زمینه
- پاکسازی خودکار فایل‌های قدیمی

### 🛡️ امنیت پیشرفته
- عدم نمایش خطاهای mysqldump
- پشتیبان‌گیری امن بدون وابستگی به mysqldump
- لاگ‌گذاری کامل

## 🚀 دستورات جدید

### 1. پشتیبان‌گیری امن
```bash
# پشتیبان‌گیری از هر دو دیتابیس (بدون نمایش خطا)
python manage.py secure_backup --database both --format json

# پشتیبان‌گیری با رمزگذاری
python manage.py secure_backup --database both --encrypt --password "your_password"

# پشتیبان‌گیری در پوشه سفارشی
python manage.py secure_backup --database both --output-dir "/path/to/backup"

# حالت سکوت (بدون نمایش جزئیات)
python manage.py secure_backup --database both --quiet
```

### 2. پشتیبان‌گیری دوره‌ای
```bash
# پشتیبان‌گیری روزانه در ساعت 2 صبح
python manage.py scheduled_backup --schedule-type daily --time "02:00"

# پشتیبان‌گیری هفتگی
python manage.py scheduled_backup --schedule-type weekly --time "02:00"

# پشتیبان‌گیری با رمزگذاری
python manage.py scheduled_backup --schedule-type daily --encrypt --password "your_password"

# پاکسازی فایل‌های قدیمی‌تر از 30 روز
python manage.py scheduled_backup --schedule-type daily --cleanup-days 30
```

### 3. پشتیبان‌گیری خودکار پیشرفته
```bash
# اجرای در پس‌زمینه
python manage.py auto_backup_advanced --daemon --interval 24

# پشتیبان‌گیری با رمزگذاری و پاکسازی
python manage.py auto_backup_advanced --encrypt --password "your_password" --cleanup-days 30

# تنظیم پوشه خروجی
python manage.py auto_backup_advanced --output-dir "/custom/backup/path"
```

### 4. مدیریت فایل‌های پشتیبان
```bash
# نمایش لیست فایل‌ها
python manage.py manage_backups --list --size

# پاکسازی فایل‌های قدیمی‌تر از 7 روز
python manage.py manage_backups --cleanup --days 7

# نمایش آمار کامل
python manage.py manage_backups --list --size
```

## 🌐 رابط ادمین

### دسترسی به رابط ادمین
```
URL: http://127.0.0.1:8000/backup-admin/
```

### ویژگی‌های رابط ادمین:
- **نمایش آمار**: تعداد فایل‌ها، حجم کل، فایل‌های اصلی و لاگ
- **مدیریت فایل‌ها**: حذف، دانلود، رمزگذاری
- **ایجاد پشتیبان‌گیری جدید**: با تنظیمات سفارشی
- **نمایش تاریخ**: قدیمی‌ترین و جدیدترین فایل‌ها

### عملیات موجود:
1. **حذف فایل**: با تأیید امنیتی
2. **رمزگذاری**: با رمز عبور سفارشی
3. **دانلود**: فایل‌های پشتیبان
4. **ایجاد جدید**: پشتیبان‌گیری با تنظیمات

## 📊 ساختار فایل‌ها

```
backups/
├── main_20250920_071624.json          # دیتابیس اصلی
├── logs_20250920_071624.json          # دیتابیس لاگ
├── main_20250920_071624.json.encrypted # فایل رمزگذاری شده
├── logs_20250920_071624.json.encrypted # فایل رمزگذاری شده
├── encrypted/                         # پوشه فایل‌های رمزگذاری شده
│   ├── main_20250920_071624.json.encrypted
│   └── logs_20250920_071624.json.encrypted
└── backup_log.json                   # لاگ پشتیبان‌گیری
```

## 🔧 تنظیمات پیشرفته

### متغیرهای محیطی (.env)
```env
# دیتابیس اصلی
DATABASE_DEFAULT_NAME=tankhasystem
DATABASE_DEFAULT_USER=root
DATABASE_DEFAULT_PASSWORD=your_password
DATABASE_DEFAULT_HOST=127.0.0.1
DATABASE_DEFAULT_PORT=3306

# دیتابیس لاگ
DATABASE_LOGS_NAME=tankhah_logs_db
DATABASE_LOGS_USER=root
DATABASE_LOGS_PASSWORD=your_password
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

# تنظیمات پشتیبان‌گیری برای دیتابیس لاگ
DBBACKUP_CONNECTORS = {
    'default': {
        'CONNECTOR': 'dbbackup.db.mysql.MysqlDumpConnector',
        'NAME': os.getenv('DATABASE_DEFAULT_NAME', 'tankhasystem'),
        'USER': os.getenv('DATABASE_DEFAULT_USER', 'root'),
        'PASSWORD': os.getenv('DATABASE_DEFAULT_PASSWORD', ''),
        'HOST': os.getenv('DATABASE_DEFAULT_HOST', '127.0.0.1'),
        'PORT': os.getenv('DATABASE_DEFAULT_PORT', '3306'),
    },
    'logs': {
        'CONNECTOR': 'dbbackup.db.mysql.MysqlDumpConnector',
        'NAME': os.getenv('DATABASE_LOGS_NAME', 'tankhah_logs_db'),
        'USER': os.getenv('DATABASE_LOGS_USER', 'root'),
        'PASSWORD': os.getenv('DATABASE_LOGS_PASSWORD', ''),
        'HOST': os.getenv('DATABASE_LOGS_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_LOGS_PORT', '3306'),
    }
}
```

## 🤖 خودکارسازی

### Task Scheduler (Windows)
1. باز کردن Task Scheduler
2. ایجاد Task جدید
3. تنظیم Trigger: روزانه در ساعت مشخص
4. تنظیم Action: اجرای `python manage.py auto_backup_advanced --daemon`

### Cron (Linux/Mac)
```bash
# ویرایش crontab
crontab -e

# اضافه کردن خط زیر برای پشتیبان‌گیری روزانه در ساعت 2 صبح
0 2 * * * /path/to/project/python manage.py auto_backup_advanced --daemon
```

### Systemd Service (Linux)
```ini
[Unit]
Description=Database Backup Service
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/project
ExecStart=/path/to/python manage.py auto_backup_advanced --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔍 مانیتورینگ و لاگ‌ها

### فایل لاگ پشتیبان‌گیری
```json
{
  "timestamp": "20250920_071624",
  "status": "success",
  "message": "پشتیبان‌گیری خودکار با موفقیت انجام شد",
  "backup_dir": "/path/to/backups"
}
```

### بررسی وضعیت
```bash
# بررسی لاگ‌های پشتیبان‌گیری
cat backups/backup_log.json

# بررسی فایل‌های پشتیبان
python manage.py manage_backups --list --size
```

## 🛠️ عیب‌یابی

### مشکل: خطای mysqldump
**راه‌حل**: استفاده از `secure_backup` به جای `dbbackup`
```bash
python manage.py secure_backup --database both --quiet
```

### مشکل: خطا در رمزگذاری
**راه‌حل**: نصب کتابخانه cryptography
```bash
pip install cryptography
```

### مشکل: خطا در دسترسی به فایل‌ها
**راه‌حل**: بررسی مجوزهای پوشه backups
```bash
chmod 755 backups/
chown your_user:your_group backups/
```

### مشکل: خطا در پشتیبان‌گیری دوره‌ای
**راه‌حل**: بررسی لاگ‌ها و تنظیمات
```bash
# بررسی لاگ‌ها
tail -f backups/backup_log.json

# تست پشتیبان‌گیری
python manage.py secure_backup --database both --quiet
```

## 📈 آمار و گزارش‌ها

### آمار فایل‌های پشتیبان
- تعداد کل فایل‌ها
- حجم کل (MB)
- فایل‌های دیتابیس اصلی
- فایل‌های دیتابیس لاگ
- قدیمی‌ترین و جدیدترین فایل

### گزارش‌های عملکرد
- موفقیت/شکست پشتیبان‌گیری
- زمان اجرای پشتیبان‌گیری
- حجم فایل‌های ایجاد شده
- فایل‌های حذف شده در پاکسازی

## 🔒 امنیت

### رمزگذاری فایل‌ها
- استفاده از Fernet encryption
- کلید تولید شده از رمز عبور
- ذخیره فایل‌های رمزگذاری شده در پوشه جداگانه

### کنترل دسترسی
- محدودیت دسترسی به پوشه backups
- تأیید امنیتی برای حذف فایل‌ها
- لاگ‌گذاری تمام عملیات

### پاکسازی امن
- حذف فایل‌های قدیمی با تأیید
- نگه‌داری تعداد محدود فایل‌ها
- پاکسازی خودکار بر اساس تاریخ

## 🎉 نتیجه

سیستم پشتیبان‌گیری پیشرفته حالا شامل:
- ✅ رابط ادمین کامل
- ✅ رمزگذاری امن
- ✅ پشتیبان‌گیری دوره‌ای
- ✅ مدیریت فایل‌ها
- ✅ امنیت پیشرفته
- ✅ مانیتورینگ کامل

**همه چیز آماده و کار می‌کند!** 🚀
