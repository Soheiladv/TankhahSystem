# راهنمای اسکریپت‌های Docker

این پوشه شامل اسکریپت‌های مدیریتی برای پروژه Docker است.

## 📁 فایل‌های موجود

### اسکریپت‌های اصلی
- **`docker-menu.ps1`** - منوی اصلی مدیریت (شروع از اینجا)
- **`docker-setup.ps1`** - راه‌اندازی اولیه پروژه
- **`docker-deploy.ps1`** - استقرار پروژه
- **`docker-update.ps1`** - به‌روزرسانی پروژه
- **`docker-manage.ps1`** - مدیریت روزانه

## 🚀 شروع سریع

### 1. راه‌اندازی اولیه
```powershell
.\docker-menu.ps1
```
یا
```powershell
.\docker-setup.ps1
```

### 2. بررسی وضعیت
```powershell
.\docker-manage.ps1 -Action status
```

### 3. نمایش لاگ‌ها
```powershell
.\docker-manage.ps1 -Action logs
```

## 📋 دستورات مفید

### مدیریت کانتینرها
```powershell
# راه‌اندازی
docker-compose up -d

# توقف
docker-compose down

# راه‌اندازی مجدد
docker-compose restart

# وضعیت
docker-compose ps
```

### اجرای دستورات Django
```powershell
# Migrations
docker-compose exec web python manage.py migrate

# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic

# ایجاد superuser
docker-compose exec web python manage.py createsuperuser

# Shell Django
docker-compose exec web python manage.py shell
```

### مدیریت دیتابیس
```powershell
# ورود به دیتابیس
docker-compose exec db psql -U budgets_user -d budgets_db

# پشتیبان‌گیری
docker-compose exec -T db pg_dump -U budgets_user -d budgets_db > backup.sql

# بازگردانی
docker-compose exec -T db psql -U budgets_user -d budgets_db < backup.sql
```

## 🔧 اسکریپت‌های موجود

### docker-menu.ps1
منوی اصلی با گزینه‌های زیر:
- راه‌اندازی اولیه - Start New Docker
- بررسی وضعیت      - Status Docker 
- نمایش لاگ‌ها       - View Docker Logs
- به‌روزرسانی       - Update Dockers
- پشتیبان‌گیری      - Backups Dockers 
- بازگردانی        - Restore Dockers
- راه‌اندازی مجدد   - Restart Dockers
- توقف سیستم       - Stop Dockers
- پاک‌سازی          - Clean Dockers
- نمایش اطلاعات     - Detials Dockers
- اجرای دستور      - Run Commands Dockers
- ورود به shell    - Shell Run in Dockers
- نمایش دستورات مفید   - View Commands Dockers

### docker-setup.ps1
راه‌اندازی اولیه پروژه:
- بررسی Docker و Docker Compose
- بررسی فایل‌های ضروری
- ایجاد دایرکتوری‌های مورد نیاز
- ساخت Docker image ها
- اجرای کانتینرها
- اجرای migrations
- جمع‌آوری فایل‌های static
- بررسی دسترسی به وب‌سایت

### docker-deploy.ps1
استقرار پروژه:
- استقرار development
- استقرار production
- پشتیبان‌گیری
- بررسی سلامت سیستم
- نمایش اطلاعات سیستم

### docker-update.ps1
به‌روزرسانی پروژه:
- پشتیبان‌گیری
- توقف کانتینرها
- حذف image های قدیمی
- ساخت image های جدید
- اجرای migrations
- جمع‌آوری فایل‌های static
- راه‌اندازی کانتینرها
- بررسی وضعیت

### docker-manage.ps1
مدیریت روزانه:
- نمایش وضعیت
- نمایش لاگ‌ها
- اجرای دستورات
- پشتیبان‌گیری
- بازگردانی
- پاک‌سازی
- نمایش اطلاعات
- راه‌اندازی مجدد
- ورود به shell
- نمایش دستورات مفید

## 🌐 دسترسی به وب‌سایت

پس از راه‌اندازی، وب‌سایت در آدرس زیر در دسترس است:
- **Development**: http://localhost:8080
- **Production**: http://localhost:8080

## 📊 پورت‌های مورد استفاده

- **8080**: Nginx (وب‌سایت)
- **8000**: Django (مستقیم)
- **5432**: PostgreSQL
- **6379**: Redis

## 🗂️ ساختار فایل‌ها

```
docker-scripts/
├── docker-menu.ps1      # منوی اصلی
├── docker-setup.ps1     # راه‌اندازی اولیه
├── docker-deploy.ps1    # استقرار
├── docker-update.ps1    # به‌روزرسانی
├── docker-manage.ps1    # مدیریت روزانه
└── README.md            # این فایل
```

## ⚠️ نکات مهم

1. **قبل از اجرا**: مطمئن شوید Docker Desktop نصب و راه‌اندازی شده است
2. **فایل .env**: تنظیمات را در فایل `.env` بررسی کنید
3. **پورت‌ها**: مطمئن شوید پورت‌های مورد استفاده آزاد هستند
4. **پشتیبان‌گیری**: قبل از به‌روزرسانی حتماً پشتیبان تهیه کنید
5. **لاگ‌ها**: در صورت مشکل، لاگ‌ها را بررسی کنید

## 🆘 عیب‌یابی

### مشکل در راه‌اندازی
1. بررسی Docker Desktop
2. بررسی فایل‌های ضروری
3. بررسی پورت‌های آزاد
4. بررسی لاگ‌ها

### مشکل در دسترسی
1. بررسی وضعیت کانتینرها
2. بررسی لاگ‌های Nginx
3. بررسی لاگ‌های Django
4. بررسی تنظیمات فایل .env

### مشکل در دیتابیس
1. بررسی وضعیت کانتینر دیتابیس
2. بررسی لاگ‌های PostgreSQL
3. بررسی اتصال شبکه
4. بررسی تنظیمات دیتابیس

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌ها را بررسی کنید: `.\docker-manage.ps1 -Action logs`
2. وضعیت کانتینرها را چک کنید: `.\docker-manage.ps1 -Action status`
3. تنظیمات را بررسی کنید: `Get-Content ..\.env`
4. در صورت نیاز، سیستم را راه‌اندازی مجدد کنید: `.\docker-manage.ps1 -Action restart`
5. برای راهنمای کامل، فایل `..\DOCKER_GUIDE.md` را مطالعه کنید

## 📚 مستندات کامل

- **راهنمای کامل**: `..\DOCKER_GUIDE.md` - شامل تمام جزئیات
- **راهنمای سریع**: `..\DOCKER_QUICK_START.md` - دستورات ضروری
- **خلاصه تکمیل**: `..\DOCKER_SETUP_COMPLETE.md` - فهرست کامل فایل‌ها
