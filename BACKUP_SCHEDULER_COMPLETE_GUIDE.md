# راهنمای کامل سیستم اسکچول پشتیبان‌گیری و اعلان‌ها

## ✅ سیستم کامل پیاده‌سازی شده

### **ویژگی‌های اصلی**:
- ✅ **اسکچول خودکار پشتیبان‌گیری**: روزانه، هفتگی، ماهانه، سفارشی
- ✅ **اعلان‌های هوشمند**: به مدیران سیستم
- ✅ **لاگ کامل**: ردیابی تمام عملیات
- ✅ **Admin Interface**: مدیریت آسان
- ✅ **Cron Integration**: اجرای خودکار

## 🎯 مدل‌های جدید

### **1. BackupSchedule**:
```python
class BackupSchedule(models.Model):
    name = models.CharField(max_length=100)  # نام اسکچول
    frequency = models.CharField(max_length=20)  # فرکانس (روزانه، هفتگی، ماهانه)
    database = models.CharField(max_length=10)  # دیتابیس هدف
    format_type = models.CharField(max_length=10)  # فرمت (JSON/SQL)
    encrypt = models.BooleanField(default=False)  # رمزگذاری
    is_active = models.BooleanField(default=True)  # فعال/غیرفعال
    notify_on_success = models.BooleanField(default=True)  # اعلان موفقیت
    notify_on_failure = models.BooleanField(default=True)  # اعلان خطا
    notify_recipients = models.ManyToManyField(CustomUser)  # گیرندگان
```

### **2. BackupLog**:
```python
class BackupLog(models.Model):
    schedule = models.ForeignKey(BackupSchedule)  # اسکچول مربوطه
    status = models.CharField(max_length=20)  # وضعیت (شروع، تکمیل، خطا)
    started_at = models.DateTimeField()  # زمان شروع
    finished_at = models.DateTimeField()  # زمان پایان
    duration = models.DurationField()  # مدت زمان
    file_size = models.BigIntegerField()  # حجم فایل
    error_message = models.TextField()  # پیام خطا
```

### **3. Notification (بهبود یافته)**:
```python
# انواع جدید موجودیت
entity_type = [
    ('BACKUP', 'پشتیبان\u200cگیری'),
    ('SYSTEM', 'سیستم'),
    ('SECURITY', 'امنیت'),
    ('MAINTENANCE', 'نگهداری')
]

# انواع جدید اقدام
action = [
    ('COMPLETED', 'تکمیل'),
    ('FAILED', 'ناموفق'),
    ('SCHEDULED', 'زمان\u200cبندی شده'),
    ('STARTED', 'شروع شده'),
    ('FINISHED', 'پایان یافته')
]
```

## 🔧 توابع جدید

### **1. send_backup_notification()**:
```python
def send_backup_notification(schedule, status, message=None, file_path=None, file_size=None):
    """
    ارسال اعلان پشتیبان‌گیری به مدیران سیستم
    - اعلان شروع پشتیبان‌گیری
    - اعلان موفقیت
    - اعلان خطا با ایمیل
    """
```

### **2. execute_scheduled_backup()**:
```python
def execute_scheduled_backup(schedule_id):
    """
    اجرای پشتیبان‌گیری زمان‌بندی شده
    - ایجاد لاگ
    - اجرای پشتیبان‌گیری
    - بروزرسانی زمان اجرای بعدی
    - ارسال اعلان
    """
```

### **3. check_and_execute_scheduled_backups()**:
```python
def check_and_execute_scheduled_backups():
    """
    بررسی و اجرای پشتیبان‌گیری‌های زمان‌بندی شده
    - پیدا کردن اسکچول‌های آماده اجرا
    - اجرای هر کدام
    """
```

## 📋 Management Commands

### **1. run_backup_scheduler**:
```bash
# اجرای همه اسکچول‌ها
python manage.py run_backup_scheduler

# اجرای اسکچول خاص
python manage.py run_backup_scheduler --schedule-id 1
```

## 🕐 تنظیم Cron

### **1. Linux/Mac**:
```bash
# هر 5 دقیقه یکبار بررسی کن
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر ساعت یکبار بررسی کن
0 * * * * /path/to/python /path/to/scripts/backup_scheduler.py

# هر روز ساعت 2 صبح
0 2 * * * /path/to/python /path/to/scripts/backup_scheduler.py
```

### **2. Windows (Task Scheduler)**:
```batch
# اجرای اسکریپت batch
scripts/backup_scheduler.bat
```

## 🎨 Admin Interface

### **1. BackupSchedule Admin**:
- ✅ **لیست نمایش**: نام، فرکانس، دیتابیس، فرمت، وضعیت
- ✅ **فیلترها**: فرکانس، دیتابیس، فرمت، فعال/غیرفعال
- ✅ **جستجو**: نام، توضیحات
- ✅ **تنظیمات**: گیرندگان اعلان، رمزگذاری

### **2. BackupLog Admin**:
- ✅ **لیست نمایش**: اسکچول، وضعیت، زمان شروع، مدت زمان
- ✅ **فیلترها**: وضعیت، زمان، اسکچول
- ✅ **رنگ‌بندی**: وضعیت‌ها با رنگ‌های مختلف
- ✅ **جزئیات**: مسیر فایل، حجم، پیام خطا

### **3. Notification Admin**:
- ✅ **لیست نمایش**: گیرنده، فعل، نوع، اولویت، خوانده‌نشده
- ✅ **فیلترها**: نوع، اولویت، خوانده‌نشده، زمان
- ✅ **رنگ‌بندی**: اولویت‌ها با رنگ‌های مختلف
- ✅ **جستجو**: گیرنده، فعل، توضیحات

## 📍 دسترسی‌ها

### **1. Admin Panel**:
```
http://127.0.0.1:8000/admin/notificationApp/
```

### **2. مدل‌های موجود**:
- **NotificationRule**: قوانین اعلان
- **Notification**: اعلان‌ها
- **BackupSchedule**: اسکچول‌های پشتیبان‌گیری
- **BackupLog**: لاگ‌های پشتیبان‌گیری

## 🚀 نحوه استفاده

### **1. ایجاد اسکچول جدید**:
1. وارد Admin Panel شوید
2. به بخش "BackupSchedule" بروید
3. روی "Add" کلیک کنید
4. اطلاعات را پر کنید:
   - **نام**: نام اسکچول
   - **فرکانس**: روزانه، هفتگی، ماهانه
   - **دیتابیس**: اصلی، لاگ، یا هر دو
   - **فرمت**: JSON یا SQL
   - **گیرندگان اعلان**: کاربران مورد نظر

### **2. تنظیم Cron**:
```bash
# اضافه کردن به crontab
crontab -e

# اضافه کردن خط زیر
*/5 * * * * /path/to/python /path/to/scripts/backup_scheduler.py
```

### **3. بررسی لاگ‌ها**:
1. وارد Admin Panel شوید
2. به بخش "BackupLog" بروید
3. وضعیت اجراها را بررسی کنید

## 📧 اعلان‌ها

### **1. انواع اعلان**:
- ✅ **شروع پشتیبان‌گیری**: اطلاع‌رسانی شروع
- ✅ **موفقیت**: اطلاع‌رسانی تکمیل موفق
- ✅ **خطا**: اطلاع‌رسانی خطا + ایمیل

### **2. کانال‌های اعلان**:
- ✅ **درون‌برنامه**: اعلان در سیستم
- ✅ **ایمیل**: ارسال ایمیل
- ✅ **WebSocket**: اعلان real-time

### **3. اولویت‌ها**:
- ✅ **LOW**: موفقیت (سبز)
- ✅ **MEDIUM**: شروع (نارنجی)
- ✅ **HIGH**: خطا (قرمز)
- ✅ **WARNING**: هشدار (زرد)
- ✅ **ERROR**: خطا (قرمز)
- ✅ **LOCKED**: قفل‌شده (بنفش)

## ✨ ویژگی‌های پیشرفته

### **1. Cron سفارشی**:
```python
# مثال‌های cron
"0 2 * * *"  # هر روز ساعت 2 صبح
"0 */6 * * *"  # هر 6 ساعت
"0 0 * * 0"  # هر یکشنبه
"0 0 1 * *"  # اول هر ماه
```

### **2. رمزگذاری خودکار**:
- ✅ **رمزگذاری فایل‌ها**: با رمز عبور
- ✅ **امنیت بالا**: حفاظت از داده‌ها

### **3. لاگ کامل**:
- ✅ **ردیابی کامل**: تمام عملیات
- ✅ **جزئیات**: زمان، حجم، خطاها
- ✅ **تاریخچه**: نگهداری لاگ‌ها

## 🎯 نتیجه

**سیستم کامل اسکچول پشتیبان‌گیری و اعلان‌ها پیاده‌سازی شد!**

**ویژگی‌های نهایی**:
- ✅ **اسکچول خودکار**: روزانه، هفتگی، ماهانه، سفارشی
- ✅ **اعلان‌های هوشمند**: به مدیران سیستم
- ✅ **لاگ کامل**: ردیابی تمام عملیات
- ✅ **Admin Interface**: مدیریت آسان
- ✅ **Cron Integration**: اجرای خودکار
- ✅ **امنیت**: رمزگذاری و حفاظت
- ✅ **انعطاف**: تنظیمات کامل

**حالا می‌توانید اسکچول‌های پشتیبان‌گیری را تنظیم کنید و اعلان‌های خودکار دریافت کنید!** 🚀
