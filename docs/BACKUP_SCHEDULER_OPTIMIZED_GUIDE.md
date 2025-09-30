# راهنمای کامل سیستم اسکچول پشتیبان‌گیری بهینه‌شده

## ✅ سیستم کامل و بهینه‌شده

### **ویژگی‌های بهینه‌شده**:
- ✅ **اسکریپت‌های قابل تنظیم**: بدون hardcode
- ✅ **فایل تنظیمات مرکزی**: `scripts/config.py`
- ✅ **اسکریپت‌های خودکار**: پیدا کردن مسیر پروژه
- ✅ **تست کامل**: `scripts/test_backup_scheduler.py`
- ✅ **نصب خودکار**: `scripts/setup_backup_scheduler.py`
- ✅ **مستندات کامل**: فایل‌های نمونه cron و Windows Task

## 🎯 فایل‌های جدید

### **1. scripts/config.py**:
```python
# تنظیمات مرکزی برای تمام اسکریپت‌ها
PROJECT_ROOT = Path(__file__).parent.parent  # خودکار
LOGS_DIR = PROJECT_ROOT / 'logs'
DJANGO_SETTINGS_MODULE = 'BudgetsSystem.settings'

# تنظیمات لاگ
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': LOGS_DIR / 'backup_scheduler.log',
    'max_size': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
}

# تنظیمات پشتیبان‌گیری
BACKUP_CONFIG = {
    'default_format': 'json',
    'default_database': 'both',
    'encryption_enabled': True,
    'retention_days': 30,
}
```

### **2. scripts/backup_scheduler.py (بهینه‌شده)**:
```python
# ویژگی‌های جدید:
- پیدا کردن خودکار مسیر پروژه
- استفاده از فایل config.py
- پارامترهای command line
- logging پیشرفته
- error handling بهتر

# استفاده:
python scripts/backup_scheduler.py --schedule-id 1
python scripts/backup_scheduler.py --log-level DEBUG
python scripts/backup_scheduler.py --dry-run
```

### **3. scripts/backup_scheduler.bat (بهینه‌شده)**:
```batch
# ویژگی‌های جدید:
- پیدا کردن خودکار مسیر پروژه
- بررسی وجود manage.py
- پشتیبانی از پارامترها
- error handling بهتر
- پیام‌های واضح

# استفاده:
scripts/backup_scheduler.bat --schedule-id 1
scripts/backup_scheduler.bat --dry-run
```

### **4. scripts/test_backup_scheduler.py**:
```python
# تست کامل سیستم:
- تست مدل‌ها
- تست توابع utils
- تست admin interface
- تست management commands

# اجرا:
python scripts/test_backup_scheduler.py
```

### **5. scripts/setup_backup_scheduler.py**:
```python
# نصب خودکار:
- ایجاد اسکچول نمونه
- ایجاد قوانین اعلان نمونه
- ایجاد فایل‌های cron نمونه
- ایجاد Windows Task نمونه

# اجرا:
python scripts/setup_backup_scheduler.py
```

## 🔧 فایل‌های نمونه

### **1. scripts/cron_example.txt**:
```bash
# هر 5 دقیقه یکبار بررسی کن
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر ساعت یکبار بررسی کن
0 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر روز ساعت 2 صبح
0 2 * * * /path/to/python /path/to/scripts/backup_scheduler.py

# اجرای اسکچول خاص
0 1 * * * /path/to/python /path/to/scripts/backup_scheduler.py --schedule-id 1

# اجرای تستی
0 0 * * * /path/to/python /path/to/scripts/backup_scheduler.py --dry-run
```

### **2. scripts/windows_task_example.xml**:
```xml
<!-- فایل XML برای Windows Task Scheduler -->
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>اجرای خودکار پشتیبان‌گیری‌های زمان‌بندی شده</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2024-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT5M</Interval>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>python</Command>
      <Arguments>scripts/backup_scheduler.py</Arguments>
      <WorkingDirectory>D:\Design & Source Code\Source Coding\BudgetsSystem</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

## 🚀 نحوه استفاده

### **1. نصب اولیه**:
```bash
# اجرای اسکریپت نصب
python scripts/setup_backup_scheduler.py

# تست سیستم
python scripts/test_backup_scheduler.py
```

### **2. تنظیم Cron (Linux/Mac)**:
```bash
# ویرایش crontab
crontab -e

# اضافه کردن خط زیر
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py
```

### **3. تنظیم Windows Task Scheduler**:
```batch
# اجرای Task Scheduler
taskschd.msc

# Import کردن فایل XML
# فایل: scripts/windows_task_example.xml
```

### **4. اجرای دستی**:
```bash
# اجرای همه اسکچول‌ها
python scripts/backup_scheduler.py

# اجرای اسکچول خاص
python scripts/backup_scheduler.py --schedule-id 1

# اجرای تستی
python scripts/backup_scheduler.py --dry-run

# با سطح لاگ بالا
python scripts/backup_scheduler.py --log-level DEBUG
```

## 📊 Admin Interface

### **دسترسی**:
```
http://127.0.0.1:8000/admin/notificationApp/
```

### **مدل‌های موجود**:
- **BackupSchedule**: اسکچول‌های پشتیبان‌گیری
- **BackupLog**: لاگ‌های اجرا
- **Notification**: اعلان‌ها
- **NotificationRule**: قوانین اعلان

## 🎯 ویژگی‌های بهینه‌شده

### **1. بدون Hardcode**:
- ✅ **مسیر پروژه**: خودکار پیدا می‌شود
- ✅ **تنظیمات**: در فایل config.py
- ✅ **انعطاف**: قابل تنظیم از environment variables

### **2. Error Handling**:
- ✅ **بررسی مسیر**: وجود manage.py
- ✅ **Logging کامل**: تمام عملیات
- ✅ **پیام‌های واضح**: خطاها و موفقیت‌ها

### **3. تست و نصب**:
- ✅ **تست کامل**: تمام اجزا
- ✅ **نصب خودکار**: اسکچول‌ها و قوانین نمونه
- ✅ **فایل‌های نمونه**: cron و Windows Task

### **4. مستندات**:
- ✅ **راهنمای کامل**: تمام مراحل
- ✅ **مثال‌های عملی**: cron و Windows Task
- ✅ **توضیحات واضح**: هر فایل و تابع

## ✨ نتیجه

**سیستم اسکچول پشتیبان‌گیری کاملاً بهینه‌شده و آماده استفاده!**

**مزایای بهینه‌سازی**:
- ✅ **بدون Hardcode**: قابل انتقال به هر محیط
- ✅ **خودکار**: پیدا کردن مسیرها و تنظیمات
- ✅ **قابل تست**: اسکریپت‌های تست کامل
- ✅ **قابل نصب**: نصب خودکار و آسان
- ✅ **مستندات کامل**: راهنمای جامع
- ✅ **انعطاف**: تنظیمات قابل تغییر

**حالا می‌توانید سیستم را در هر محیطی نصب و استفاده کنید!** 🚀
