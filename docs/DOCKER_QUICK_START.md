# 🚀 راهنمای سریع شروع Docker

## ✅ چک‌لیست قبل از شروع

قبل از شروع، مطمئن شوید:
- [x] Docker Desktop نصب شده است
- [x] Docker Compose نصب شده است
- [ ] فایل `.env` ایجاد شده است
- [ ] رمزهای عبور در `.env` تنظیم شده‌اند

---

## 📝 مرحله 1: ایجاد و تنظیم فایل .env

### گام 1: کپی کردن از env.example

```powershell
# در دایرکتوری اصلی پروژه
Copy-Item env.example .env
```

### گام 2: ویرایش فایل .env

فایل `.env` را باز کنید و موارد زیر را تنظیم کنید:

```env
# ⚠️ مهم: این مقادیر را تغییر دهید!

# 1. SECRET_KEY - یک کلید منحصر به فرد ایجاد کنید
SECRET_KEY=your-super-secret-key-here-change-this-immediately

# 2. رمز عبور دیتابیس
DB_PASSWORD=your-strong-database-password-here

# 3. رمز عبور Redis
REDIS_PASSWORD=your-strong-redis-password-here

# 4. DEBUG - برای development از True استفاده کنید
DEBUG=True

# 5. ALLOWED_HOSTS - آدرس‌های مجاز
ALLOWED_HOSTS=localhost,127.0.0.1
```

**💡 نکته**: برای ایجاد SECRET_KEY قوی:
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🎯 مرحله 2: انتخاب روش راه‌اندازی

### روش 1: استفاده از منوی تعاملی (پیشنهادی) ⭐

```powershell
# رفتن به دایرکتوری اسکریپت‌ها
cd docker-scripts

# اجرای منوی اصلی
.\docker-menu.ps1
```

سپس گزینه **1️⃣ راه‌اندازی اولیه** را انتخاب کنید.

### روش 2: استفاده از اسکریپت مستقیم

```powershell
# رفتن به دایرکتوری اسکریپت‌ها
cd docker-scripts

# اجرای اسکریپت راه‌اندازی
.\docker-setup.ps1
```

### روش 3: استفاده از دستورات Docker مستقیم

```powershell
# در دایرکتوری اصلی پروژه

# 1. ساخت image ها
docker-compose build

# 2. اجرای کانتینرها
docker-compose up -d

# 3. بررسی وضعیت
docker-compose ps

# 4. مشاهده لاگ‌ها
docker-compose logs
```

---

## 🔍 مرحله 3: بررسی وضعیت

### بررسی کانتینرها

```powershell
# استفاده از اسکریپت
cd docker-scripts
.\docker-manage.ps1 -Action status

# یا مستقیم
docker-compose ps
```

### بررسی لاگ‌ها

```powershell
# استفاده از اسکریپت
.\docker-manage.ps1 -Action logs

# یا مستقیم
docker-compose logs -f
```

### بررسی دسترسی به وب‌سایت

```powershell
# باز کردن مرورگر و رفتن به:
http://localhost:8080

# یا استفاده از PowerShell
Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing
```

---

## 🛠️ دستورات مفید

### مدیریت کانتینرها

```powershell
# توقف
docker-compose down

# راه‌اندازی
docker-compose up -d

# راه‌اندازی مجدد
docker-compose restart

# مشاهده لاگ‌ها
docker-compose logs -f web
```

### اجرای دستورات Django

```powershell
# اجرای migrations
docker-compose exec web python manage.py migrate

# ایجاد superuser
docker-compose exec web python manage.py createsuperuser

# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic --noinput

# ورود به shell Django
docker-compose exec web python manage.py shell
```

### مدیریت دیتابیس

```powershell
# ورود به دیتابیس
docker-compose exec db psql -U budgets_user -d budgets_db

# پشتیبان‌گیری از دیتابیس
docker-compose exec db pg_dump -U budgets_user -d budgets_db > backup.sql
```

---

## 🐛 عیب‌یابی مشکلات رایج

### مشکل: کانتینرها راه‌اندازی نمی‌شوند

```powershell
# بررسی لاگ‌ها
docker-compose logs

# بررسی وضعیت
docker-compose ps

# بررسی استفاده از پورت‌ها
netstat -ano | findstr :8080
netstat -ano | findstr :8000
```

### مشکل: خطا در اتصال به دیتابیس

```powershell
# بررسی فایل .env
Get-Content .env | Select-String "DB_"

# بررسی کانتینر دیتابیس
docker-compose logs db

# راه‌اندازی مجدد دیتابیس
docker-compose restart db
```

### مشکل: فایل‌های static بارگذاری نمی‌شوند

```powershell
# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic --noinput

# بررسی volume
docker volume inspect budgetssystem_static_volume
```

---

## 📚 راهنماهای بیشتر

- **DOCKER_GUIDE.md** - راهنمای کامل Docker
- **DOCKER_REVIEW_REPORT.md** - گزارش مشکلات و راه‌حل‌ها
- **DOCKER_FIXES_SUMMARY.md** - خلاصه تغییرات

---

## ✅ چک‌لیست پس از راه‌اندازی

- [ ] تمام کانتینرها در حال اجرا هستند
- [ ] وب‌سایت در `http://localhost:8080` در دسترس است
- [ ] لاگ‌ها بدون خطا هستند
- [ ] migrations اجرا شده‌اند
- [ ] فایل‌های static جمع‌آوری شده‌اند
- [ ] superuser ایجاد شده است

---

## 🎉 موفق باشید!

اگر مشکلی پیش آمد، به بخش عیب‌یابی مراجعه کنید یا لاگ‌ها را بررسی کنید.

**نکته**: برای استقرار در production، از `docker-compose.prod.yml` استفاده کنید و تنظیمات امنیتی را بررسی کنید.
