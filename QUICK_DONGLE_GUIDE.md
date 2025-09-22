# 🚀 راهنمای سریع USB Dongle

## ✅ سیستم میانبر ایجاد شد!

حالا می‌توانید با **فقط 2 کلیک** dongle ایجاد کنید!

## 🎯 مراحل استفاده

### **مرحله 1: ذخیره اطلاعات قفل**
```cmd
# اجرای اسکریپت ذخیره
python scripts/save_lock_config.py
```

**یا**
```cmd
# دوبار کلیک روی فایل
scripts\save_lock_config.py
```

### **مرحله 2: ایجاد dongle**
```cmd
# اجرای اسکریپت خودکار
python scripts/auto_write_dongle.py
```

**یا**
```cmd
# دوبار کلیک روی فایل
scripts\auto_write_dongle.py
```

### **مرحله 3: اجرای یکجا (توصیه شده)**
```cmd
# اجرای اسکریپت کامل
scripts\quick_dongle_setup.bat
```

**یا**
```powershell
# اجرای اسکریپت PowerShell
scripts\quick_dongle_setup.ps1
```

## 📁 فایل‌های ایجاد شده

### **فایل کد شده**:
- `scripts/lock_config.json` - اطلاعات قفل کد شده

### **اسکریپت‌ها**:
- `scripts/save_lock_config.py` - ذخیره اطلاعات قفل
- `scripts/auto_write_dongle.py` - نوشتن dongle روی فلش
- `scripts/quick_dongle_setup.bat` - اجرای کامل (Batch)
- `scripts/quick_dongle_setup.ps1` - اجرای کامل (PowerShell)

## 🔧 نحوه کار

### **1. ذخیره اطلاعات قفل**:
```python
# اطلاعات قفل از دیتابیس خوانده می‌شود
lock_config = {
    'organization_name': 'توسعه گردشگری ایران',
    'software_id': 'RCMS',
    'expiry_date': '2026-09-20',
    'max_users': 10,
    'lock_key': 'کلید اصلی',
    'salt': 'نمک',
    'hash_value': 'هش'
}

# کد کردن و ذخیره
config_encoded = base64.b64encode(json.dumps(lock_config))
```

### **2. نوشتن dongle**:
```python
# خواندن اطلاعات از فایل کد شده
lock_config = load_lock_config()

# نوشتن روی فلش
dongle_manager.write_dongle_to_multiple_sectors(
    device_path,
    lock_config['lock_key'],
    lock_config['organization_name'],
    lock_config['software_id'],
    lock_config['expiry_date']
)
```

## 🎯 مزایای سیستم میانبر

### **✅ سرعت**:
- فقط 2 کلیک برای ایجاد dongle
- نیازی به دسترسی ادمین نیست
- اجرای خودکار

### **✅ امنیت**:
- اطلاعات قفل کد شده ذخیره می‌شود
- Checksum برای بررسی یکپارچگی
- رمزگذاری Base64

### **✅ راحتی**:
- نیازی به وارد کردن اطلاعات نیست
- اجرای یکجا
- پشتیبانی از Batch و PowerShell

## 🔍 عیب‌یابی

### **مشکل: فایل کد شده یافت نشد**
```
راه‌حل: ابتدا اسکریپت save_lock_config.py را اجرا کنید
```

### **مشکل: هیچ درایو USB یافت نشد**
```
راه‌حل: یک فلش USB را به سیستم متصل کنید
```

### **مشکل: خطای Access Denied**
```
راه‌حل: Django را به عنوان Administrator اجرا کنید
```

## 📋 چک‌لیست کامل

### **قبل از شروع**:
- [ ] Django در حال اجرا است
- [ ] قفل فعال در دیتابیس وجود دارد
- [ ] فلش USB متصل است
- [ ] فلش فرمت شده (FAT32 یا NTFS)

### **در حین کار**:
- [ ] اسکریپت save_lock_config.py اجرا شد
- [ ] فایل lock_config.json ایجاد شد
- [ ] اسکریپت auto_write_dongle.py اجرا شد
- [ ] پیام موفقیت نمایش داده شد

### **بعد از ایجاد**:
- [ ] dongle معتبر است
- [ ] سکتورها به عنوان "valid" نمایش داده می‌شوند
- [ ] اطلاعات شرکت صحیح نمایش داده می‌شود
- [ ] سیستم خودکار چک می‌کند

## 🎉 نتیجه

**با سیستم میانبر**:
- ✅ **سرعت بالا** - فقط 2 کلیک
- ✅ **راحتی** - نیازی به وارد کردن اطلاعات نیست
- ✅ **امنیت** - اطلاعات کد شده ذخیره می‌شود
- ✅ **قابلیت اطمینان** - اجرای خودکار

**حالا می‌توانید**:
- ✅ با 2 کلیک dongle ایجاد کنید
- ✅ اطلاعات قفل را کد شده ذخیره کنید
- ✅ dongle را خودکار روی فلش بنویسید
- ✅ از سیستم مدیریت کنید

**سیستم کاملاً آماده و بهینه است!** 🚀

## 📞 پشتیبانی

اگر مشکلی داشتید:
1. لاگ‌ها را بررسی کنید
2. فلش را فرمت کنید
3. از فلش دیگری استفاده کنید
4. Django را به عنوان Administrator اجرا کنید

**موفق باشید!** ✨
