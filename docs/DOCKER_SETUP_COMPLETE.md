# ✅ تکمیل آماده‌سازی Docker برای پروژه بودجه

## 📦 فایل‌های ایجاد شده

### اسکریپت‌های PowerShell
| فایل | توضیحات |
|------|---------|
| `docker-scripts/docker-menu.ps1` | منوی اصلی تعاملی برای مدیریت |
| `docker-scripts/docker-setup.ps1` | راه‌اندازی اولیه پروژه |
| `docker-scripts/docker-deploy.ps1` | استقرار پروژه |
| `docker-scripts/docker-update.ps1` | به‌روزرسانی پروژه |
| `docker-scripts/docker-manage.ps1` | مدیریت روزانه |
| `docker-scripts/README.md` | راهنمای اسکریپت‌ها |

### فایل‌های Docker
| فایل | توضیحات |
|------|---------|
| `Dockerfile` | تعریف image برای Django |
| `docker-compose.yml` | پیکربندی محیط توسعه |
| `docker-compose.prod.yml` | پیکربندی محیط production |
| `.dockerignore` | فایل‌های حذف شده از build |
| `docker/entrypoint.sh` | اسکریپت راه‌اندازی کانتینر |
| `docker/healthcheck.sh` | بررسی سلامت سیستم |

### فایل‌های Nginx
| فایل | توضیحات |
|------|---------|
| `nginx/nginx.conf` | پیکربندی اصلی Nginx |
| `nginx/conf.d/budgets.conf` | پیکربندی server blocks |

### مستندات
| فایل | توضیحات |
|------|---------|
| `DOCKER_GUIDE.md` | راهنمای کامل Docker |
| `DOCKER_QUICK_START.md` | راهنمای سریع |
| `env.example` | نمونه فایل تنظیمات |
| `DOCKER_SETUP_COMPLETE.md` | این فایل |

---

## 🚀 شروع کار

### روش 1: استفاده از منوی تعاملی (پیشنهاد می‌شود)

```powershell
cd docker-scripts
.\docker-menu.ps1
```

### روش 2: راه‌اندازی مستقیم

```powershell
# تنظیم فایل .env
Copy-Item env.example .env
notepad .env  # ویرایش تنظیمات

# راه‌اندازی
.\docker-scripts\docker-setup.ps1
```

### روش 3: استفاده از Docker Compose

```powershell
# ساخت images
docker-compose build

# راه‌اندازی
docker-compose up -d

# اجرای migrations
docker-compose exec web python manage.py migrate

# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 📋 دستورات کلیدی

### مدیریت پایه
```powershell
# وضعیت کانتینرها
.\docker-scripts\docker-manage.ps1 -Action status

# نمایش لاگ‌ها
.\docker-scripts\docker-manage.ps1 -Action logs

# راه‌اندازی مجدد
.\docker-scripts\docker-manage.ps1 -Action restart

# توقف
.\docker-scripts\docker-manage.ps1 -Action stop
```

### به‌روزرسانی پروژه
```powershell
# دریافت آخرین تغییرات
git pull origin main

# به‌روزرسانی Docker
.\docker-scripts\docker-update.ps1 -Action update

# یا با حذف image های قدیمی
.\docker-scripts\docker-update.ps1 -Action update -Force
```

### پشتیبان‌گیری
```powershell
# ایجاد پشتیبان
.\docker-scripts\docker-manage.ps1 -Action backup

# بازگردانی
.\docker-scripts\docker-manage.ps1 -Action restore
```

### اجرای دستورات Django
```powershell
# Migrations
docker-compose exec web python manage.py migrate

# Shell
docker-compose exec web python manage.py shell

# ایجاد superuser
docker-compose exec web python manage.py createsuperuser

# Collect static
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 🌐 دسترسی به سیستم

پس از راه‌اندازی:

```
🌐 وب‌سایت:    http://localhost:8080
🔐 ادمین:     http://localhost:8080/admin
📊 API:       http://localhost:8080/api/
🏥 Health:     http://localhost:8080/health/
```

---

## ⚙️ تنظیمات مهم

### فایل .env
حتماً موارد زیر را تنظیم کنید:

```env
# کلید امنیتی
SECRET_KEY=your-strong-secret-key-here

# دیتابیس
DB_PASSWORD=your-strong-password-here

# Redis
REDIS_PASSWORD=your-strong-redis-password

# در production این مورد را غیرفعال کنید:
DEBUG=False
```

### ساخت SECRET_KEY
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 📚 مستندات

برای اطلاعات بیشتر:

- **راهنمای کامل**: `DOCKER_GUIDE.md`
- **راهنمای سریع**: `DOCKER_QUICK_START.md`
- **راهنمای اسکریپت‌ها**: `docker-scripts/README.md`

---

## 🐛 عیب‌یابی

### مشکل در راه‌اندازی

1. بررسی Docker Desktop:
   ```powershell
   docker ps
   ```

2. بررسی لاگ‌ها:
   ```powershell
   .\docker-scripts\docker-manage.ps1 -Action logs
   ```

3. بررسی وضعیت:
   ```powershell
   .\docker-scripts\docker-manage.ps1 -Action status
   ```

### مشکل در اتصال

1. بررسی پورت‌ها:
   ```powershell
   netstat -ano | findstr :8080
   ```

2. راه‌اندازی مجدد:
   ```powershell
   .\docker-scripts\docker-manage.ps1 -Action restart
   ```

### پاک‌سازی و شروع مجدد

```powershell
# توقف کانتینرها
docker-compose down

# پاک‌سازی
.\docker-scripts\docker-manage.ps1 -Action clean

# راه‌اندازی مجدد
.\docker-scripts\docker-setup.ps1
```

---

## ⚠️ نکات مهم

### قبل از راه‌اندازی

✅ مطمئن شوید Docker Desktop نصب و در حال اجرا است
✅ فایل `.env` را ایجاد و تنظیم کرده‌اید
✅ پورت‌های 8080, 8000, 5432, 6379 آزاد هستند
✅ حداقل 10GB فضای خالی دارید

### در محیط Production

✅ `DEBUG=False` تنظیم کنید
✅ `SECRET_KEY` قوی استفاده کنید
✅ رمزهای عبور قوی برای دیتابیس و Redis
✅ SSL/HTTPS فعال کنید
✅ پشتیبان‌گیری منظم داشته باشید

### به‌روزرسانی پروژه

✅ همیشه قبل از به‌روزرسانی پشتیبان بگیرید
✅ فایل `.env` را تغییر ندهید در به‌روزرسانی
✅ لاگ‌ها را بعد از به‌روزرسانی بررسی کنید

---

## 📊 خلاصه سرویس‌ها

### کانتینرهای اصلی

| سرویس | توضیحات | پورت |
|-------|---------|------|
| `web` | Django Application | 8000 |
| `nginx` | Reverse Proxy | 8080 |
| `db` | PostgreSQL Database | 5432 |
| `redis` | Cache & Sessions | 6379 |

### کانتینرهای اختیاری (غیرفعال)

| سرویس | توضیحات |
|-------|---------|
| `celery` | Background Tasks |
| `celery-beat` | Scheduled Tasks |

---

## 🎉 آماده است!

پروژه شما آماده اجرا در Docker است. برای شروع:

```powershell
cd docker-scripts
.\docker-menu.ps1
```

یا برای راهنمای سریع:

```powershell
Get-Content DOCKER_QUICK_START.md
```

---

**نکته**: در صورت بروز هر گونه مشکل، ابتدا مستندات و راهنمای عیب‌یابی را بررسی کنید.

**موفق باشید! 🚀**
