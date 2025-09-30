# 🌐 راهنمای کامل مدیریت مسیرهای پشتیبان‌گیری شبکه

## 🎯 قابلیت‌های جدید

### **✅ پشتیبانی از دیسک شبکه**:
- **مسیرهای محلی**: `D:\Backups\BudgetsSystem`
- **مسیرهای شبکه**: `\\server\backups\budgets`
- **مسیرهای ابری**: `/mnt/cloud/backups`
- **مسیرهای خارجی**: `E:\External\Backups`

### **✅ مدیریت کامل مسیرها**:
- ایجاد، ویرایش، حذف مسیرها
- تست اتصال به مسیرها
- تنظیم مسیر پیش‌فرض
- فعال/غیرفعال کردن مسیرها
- نمایش اطلاعات فضای دیسک

## 🚀 URL های جدید

### **📁 مدیریت مسیرها**:
- `http://127.0.0.1:8000/backup/locations/` - لیست مسیرها
- `http://127.0.0.1:8000/backup/locations/create/` - ایجاد مسیر جدید
- `http://127.0.0.1:8000/backup/locations/1/` - جزئیات مسیر
- `http://127.0.0.1:8000/backup/locations/1/edit/` - ویرایش مسیر
- `http://127.0.0.1:8000/backup/locations/1/test/` - تست اتصال
- `http://127.0.0.1:8000/backup/locations/1/set-default/` - تنظیم پیش‌فرض

## 🔧 تنظیمات جدید

### **در `settings.py`**:
```python
# مسیرهای پشتیبان‌گیری (محلی و شبکه)
BACKUP_LOCATIONS = {
    'local': os.path.join(BASE_DIR, 'backups'),
    'network': os.getenv('BACKUP_NETWORK_PATH', '\\\\server\\backups\\budgets'),
    'secondary': os.getenv('BACKUP_SECONDARY_PATH', 'D:\\Backups\\BudgetsSystem'),
}
```

### **متغیرهای محیطی**:
```bash
# در فایل .env
BACKUP_NETWORK_PATH=\\server\backups\budgets
BACKUP_SECONDARY_PATH=D:\Backups\BudgetsSystem
```

## 📋 مدل جدید

### **`BackupLocation`**:
```python
class BackupLocation(models.Model):
    name = models.CharField(max_length=100)  # نام مسیر
    path = models.CharField(max_length=500)  # مسیر کامل
    location_type = models.CharField(choices=[
        ('LOCAL', 'محلی'),
        ('NETWORK', 'شبکه'),
        ('CLOUD', 'ابر'),
        ('EXTERNAL', 'خارجی'),
    ])
    status = models.CharField(choices=[
        ('ACTIVE', 'فعال'),
        ('INACTIVE', 'غیرفعال'),
        ('ERROR', 'خطا'),
        ('TESTING', 'در حال تست'),
    ])
    is_default = models.BooleanField(default=False)  # مسیر پیش‌فرض
    is_encrypted = models.BooleanField(default=False)  # رمزگذاری
    max_size_gb = models.IntegerField(null=True)  # حداکثر حجم
    description = models.TextField(blank=True)  # توضیحات
    created_by = models.ForeignKey(User)  # ایجادکننده
    created_at = models.DateTimeField(auto_now_add=True)
    last_tested = models.DateTimeField(null=True)  # آخرین تست
    last_error = models.TextField(blank=True)  # آخرین خطا
```

## 🎨 تمپلیت‌های جدید

### **1. `backup_locations_list.html`**:
- لیست تمام مسیرهای پشتیبان‌گیری
- آمار کلی (کل، فعال، شبکه)
- فیلتر و جستجو
- عملیات سریع (تست، ویرایش، حذف)

### **2. `backup_location_detail.html`**:
- جزئیات کامل مسیر
- اطلاعات فضای دیسک
- لیست فایل‌های پشتیبان
- عملیات مدیریتی

### **3. `backup_location_form.html`**:
- فرم ایجاد/ویرایش مسیر
- راهنمای مسیرهای مختلف
- اعتبارسنجی مسیر
- انتخاب نوع مسیر

## 🔧 دستورات جدید

### **ایجاد مسیرهای پیش‌فرض**:
```bash
python manage.py setup_backup_locations --username admin
```

### **تست مسیرها**:
```bash
python manage.py setup_backup_locations --username admin --force
```

## 📊 ویژگی‌های پیشرفته

### **✅ تست اتصال خودکار**:
- بررسی وجود مسیر
- تست نوشتن فایل
- محاسبه فضای خالی
- تشخیص خطاهای اتصال

### **✅ مدیریت فضای دیسک**:
- نمایش فضای کل، استفاده شده، خالی
- درصد استفاده
- هشدار کمبود فضا
- محدودیت حجم

### **✅ امنیت**:
- رمزگذاری فایل‌ها
- کنترل دسترسی
- لاگ عملیات
- تأیید حذف

## 🌐 پشتیبانی از مسیرهای شبکه

### **ویندوز**:
```
\\server\share\folder
\\192.168.1.100\backups\budgets
\\fileserver\departments\budgets
```

### **لینوکس**:
```
/mnt/backup/budgets
/mnt/network/backups
/var/backups/budgets
```

### **مثال‌های کاربردی**:
```
# مسیر محلی
D:\Backups\BudgetsSystem

# مسیر شبکه ویندوز
\\server\backups\budgets

# مسیر شبکه لینوکس
/mnt/backup/budgets

# مسیر خارجی
E:\External\Backups
```

## 🎯 نحوه استفاده

### **1. ایجاد مسیر جدید**:
1. برو به `http://127.0.0.1:8000/backup/locations/create/`
2. نام مسیر را وارد کن
3. نوع مسیر را انتخاب کن (شبکه، محلی، ابر)
4. مسیر کامل را وارد کن
5. روی "ایجاد" کلیک کن

### **2. تست اتصال**:
1. در لیست مسیرها، روی آیکون "تست" کلیک کن
2. سیستم اتصال را بررسی می‌کند
3. نتیجه تست نمایش داده می‌شود

### **3. تنظیم پیش‌فرض**:
1. روی آیکون "ستاره" کلیک کن
2. مسیر به عنوان پیش‌فرض تنظیم می‌شود
3. سایر مسیرها غیرفعال می‌شوند

## 🔍 عیب‌یابی

### **خطاهای رایج**:

**1. خطای دسترسی**:
```
خطا: [Errno 13] Permission denied
```
**راه‌حل**: بررسی دسترسی نوشتن به مسیر

**2. خطای مسیر شبکه**:
```
خطا: [Errno 2] No such file or directory
```
**راه‌حل**: بررسی اتصال شبکه و وجود مسیر

**3. خطای فضای دیسک**:
```
خطا: [Errno 28] No space left on device
```
**راه‌حل**: آزاد کردن فضای دیسک

## 📈 آمار و گزارش‌ها

### **در داشبورد اصلی**:
- تعداد کل مسیرها
- مسیرهای فعال
- مسیرهای شبکه
- مسیر پیش‌فرض

### **در جزئیات مسیر**:
- فضای کل دیسک
- فضای استفاده شده
- فضای خالی
- درصد استفاده
- تعداد فایل‌های پشتیبان

## 🎉 نتیجه

**حالا می‌توانید**:
- ✅ **مسیرهای شبکه** اضافه کنید
- ✅ **مسیرهای محلی** مدیریت کنید
- ✅ **مسیرهای ابری** پیکربندی کنید
- ✅ **تست اتصال** انجام دهید
- ✅ **فضای دیسک** نظارت کنید
- ✅ **مسیر پیش‌فرض** تنظیم کنید

**همه چیز در تمپلیت‌ها پیاده‌سازی شده و آماده استفاده است!** 🚀
