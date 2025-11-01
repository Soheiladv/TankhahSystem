# 📘 راهنمای کامل Docker برای سیستم بودجه

این راهنما شامل تمام مراحل نصب، راه‌اندازی، مدیریت و عیب‌یابی پروژه در محیط Docker است.

## 📑 فهرست مطالب

1. [پیش‌نیازها](#پیش-نیازها)
2. [نصب Docker](#نصب-docker)
3. [راه‌اندازی اولیه](#راه-اندازی-اولیه)
4. [مدیریت پروژه](#مدیریت-پروژه)
5. [اسکریپت‌های مفید](#اسکریپت-های-مفید)
6. [عیب‌یابی](#عیب-یابی)
7. [امنیت](#امنیت)

---

## 🔧 پیش‌نیازها

### سخت‌افزار مورد نیاز
- **CPU**: حداقل 2 هسته (پیشنهاد: 4 هسته)
- **RAM**: حداقل 4GB (پیشنهاد: 8GB)
- **فضای دیسک**: حداقل 10GB فضای خالی

### نرم‌افزار مورد نیاز
- **Windows 10/11** با قابلیت WSL2
- **Docker Desktop** (نسخه 4.0 یا جدیدتر)
- **PowerShell 5.1** یا بالاتر
- **Git** برای دریافت به‌روزرسانی‌ها

---

## 🐳 نصب Docker

### مرحله 1: بررسی WSL2

```powershell
wsl --list --verbose
```

اگر WSL2 نصب نیست، آن را نصب کنید:

```powershell
# نصب WSL2
wsl --install

# بازنشانی سیستم (پس از نصب)
Restart-Computer
```

### مرحله 2: دانلود و نصب Docker Desktop

1. به آدرس زیر مراجعه کنید:
   ```
   https://www.docker.com/products/docker-desktop
   ```

2. Docker Desktop را دانلود کنید

3. فایل نصب را اجرا کنید و Docker Desktop را نصب کنید

4. پس از نصب، Docker Desktop را باز کنید

### مرحله 3: تأیید نصب

```powershell
docker --version
docker-compose --version
```

اگر هر دو دستور نسخه را نمایش دادند، نصب موفق بوده است.

---

## 🚀 راه‌اندازی اولیه

### گام 1: دانلود پروژه

```powershell
# کلون کردن از Git
git clone [URL_REPOSITORY]

# یا استفاده از کد موجود
cd "D:\Design & Source Code\Source Coding\BudgetsSystem"
```

### گام 2: تنظیم فایل محیط

کپی فایل `env.example` به `.env`:

```powershell
Copy-Item env.example .env
```

ویرایش فایل `.env` و تنظیم موارد زیر:

```env
# تنظیمات اصلی
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# تنظیمات دیتابیس
DB_NAME=budgets_db
DB_USER=budgets_user
DB_PASSWORD=your-strong-password
DB_HOST=db
DB_PORT=5432

# تنظیمات Redis
REDIS_PASSWORD=your-strong-redis-password
```

### گام 3: راه‌اندازی با اسکریپت

```powershell
# راه‌اندازی با منوی تعاملی
cd docker-scripts
.\docker-menu.ps1

# یا راه‌اندازی مستقیم
.\docker-setup.ps1
```

### گام 4: بررسی وضعیت

```powershell
# بررسی وضعیت کانتینرها
.\docker-manage.ps1 -Action status

# بررسی لاگ‌ها
.\docker-manage.ps1 -Action logs
```

---

## 📋 مدیریت پروژه

### استفاده از منوی اصلی

```powershell
cd docker-scripts
.\docker-menu.ps1
```

این منو شامل گزینه‌های زیر است:

1. 🚀 راه‌اندازی اولیه
2. 📊 بررسی وضعیت سیستم
3. 📋 نمایش لاگ‌ها
4. 🔄 به‌روزرسانی پروژه
5. 📦 پشتیبان‌گیری
6. 🔄 بازگردانی
7. 🔄 راه‌اندازی مجدد
8. ⏹ توقف سیستم
9. 🧹 پاک‌سازی سیستم
10. 📊 نمایش اطلاعات سیستم
11. 🔧 اجرای دستور در کانتینر
12. 🐚 ورود به shell کانتینر
13. 📚 نمایش دستورات مفید

### دستورات مدیریتی

#### بررسی وضعیت

```powershell
# وضعیت تمام کانتینرها
.\docker-manage.ps1 -Action status

# وضعیت یک سرویس خاص
.\docker-manage.ps1 -Action info -Service web
```

#### نمایش لاگ‌ها

```powershell
# لاگ‌های تمام سرویس‌ها
.\docker-manage.ps1 -Action logs

# لاگ‌های یک سرویس خاص
.\docker-manage.ps1 -Action logs -Service web

# لاگ‌های زنده (دنبال کردن)
.\docker-manage.ps1 -Action logs -Service web -Follow
```

#### راه‌اندازی و توقف

```powershell
# توقف تمام کانتینرها
.\docker-manage.ps1 -Action stop

# راه‌اندازی تمام کانتینرها
docker-compose up -d

# راه‌اندازی مجدد
.\docker-manage.ps1 -Action restart

# راه‌اندازی مجدد یک سرویس خاص
.\docker-manage.ps1 -Action restart -Service web
```

#### اجرای دستورات Django

```powershell
# اجرای migrations
docker-compose exec web python manage.py migrate

# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic --noinput

# ایجاد superuser
docker-compose exec web python manage.py createsuperuser

# ورود به Django shell
docker-compose exec web python manage.py shell

# یا استفاده از اسکریپت
.\docker-manage.ps1 -Action exec -Service web
```

#### پشتیبان‌گیری و بازگردانی

```powershell
# پشتیبان‌گیری
.\docker-manage.ps1 -Action backup

# بازگردانی
.\docker-manage.ps1 -Action restore
```

---

## 🔄 به‌روزرسانی پروژه

### به‌روزرسانی کد پروژه

```powershell
# 1. دریافت آخرین تغییرات از Git
git pull origin main

# 2. به‌روزرسانی پروژه در Docker
.\docker-update.ps1 -Action update

# یا با حذف image های قدیمی
.\docker-update.ps1 -Action update -Force
```

### به‌روزرسانی Docker images

```powershell
# بررسی نسخه images
docker images

# بازسازی image ها
docker-compose build --no-cache

# راه‌اندازی مجدد
docker-compose up -d
```

---

## 🔧 اسکریپت‌های مفید

### اسکریپت‌های موجود

| فایل | توضیحات |
|------|---------|
| `docker-menu.ps1` | منوی اصلی تعاملی |
| `docker-setup.ps1` | راه‌اندازی اولیه پروژه |
| `docker-deploy.ps1` | استقرار پروژه |
| `docker-update.ps1` | به‌روزرسانی پروژه |
| `docker-manage.ps1` | مدیریت روزانه پروژه |

### استفاده از اسکریپت‌ها

```powershell
# دستورات docker-setup.ps1
.\docker-setup.ps1                              # راه‌اندازی اولیه
.\docker-setup.ps1 -Environment production      # استقرار production

# دستورات docker-deploy.ps1
.\docker-deploy.ps1 -Action deploy              # استقرار
.\docker-deploy.ps1 -Action backup              # پشتیبان‌گیری
.\docker-deploy.ps1 -Action health              # بررسی سلامت
.\docker-deploy.ps1 -Action info                # اطلاعات سیستم

# دستورات docker-update.ps1
.\docker-update.ps1 -Action update              # به‌روزرسانی
.\docker-update.ps1 -Action update -Force       # به‌روزرسانی با پاکسازی
.\docker-update.ps1 -Action status              # وضعیت
.\docker-update.ps1 -Action logs                # لاگ‌ها
.\docker-update.ps1 -Action clean               # پاک‌سازی

# دستورات docker-manage.ps1
.\docker-manage.ps1 -Action status              # وضعیت
.\docker-manage.ps1 -Action logs -Service web    # لاگ‌های وب
.\docker-manage.ps1 -Action backup               # پشتیبان‌گیری
.\docker-manage.ps1 -Action restore             # بازگردانی
.\docker-manage.ps1 -Action clean                # پاک‌سازی
.\docker-manage.ps1 -Action shell -Service web   # ورود به shell
.\docker-manage.ps1 -Action commands             # دستورات مفید
```

---

## 🐛 عیب‌یابی

### مشکل: کانتینرها راه‌اندازی نمی‌شوند

**علت**: ممکن است پورت‌ها اشغال باشند یا Docker Desktop اجرا نشده باشد.

**راه‌حل**:
```powershell
# بررسی Docker Desktop
docker ps

# بررسی استفاده از پورت‌ها
netstat -ano | findstr :8080
netstat -ano | findstr :8000

# بررسی لاگ‌ها
.\docker-manage.ps1 -Action logs
```

### مشکل: اتصال به دیتابیس برقرار نمی‌شود

**علت**: کانتینر دیتابیس راه‌اندازی نشده یا کاربر/رمز عبور اشتباه است.

**راه‌حل**:
```powershell
# بررسی وضعیت کانتینر دیتابیس
docker-compose ps db

# بررسی لاگ‌های دیتابیس
.\docker-manage.ps1 -Action logs -Service db

# بررسی فایل .env
Get-Content .env
```

### مشکل: فایل‌های static بارگذاری نمی‌شوند

**علت**: فایل‌های static جمع‌آوری نشده‌اند.

**راه‌حل**:
```powershell
# جمع‌آوری فایل‌های static
docker-compose exec web python manage.py collectstatic --noinput

# بررسی volume
docker volume inspect budgetssystem_static_volume
```

### مشکل: خطا در migrations

**علت**: ساختار دیتابیس قدیمی یا ناهماهنگ است.

**راه‌حل**:
```powershell
# بررسی وضعیت migrations
docker-compose exec web python manage.py showmigrations

# اجرای migrations
docker-compose exec web python manage.py migrate

# اگر نیاز به reset است
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
```

### مشکل: عدم دسترسی به وب‌سایت

**علت**: Nginx یا Django در حال اجرا نیست.

**راه‌حل**:
```powershell
# بررسی وضعیت کانتینرها
docker-compose ps

# بررسی لاگ‌های Nginx
.\docker-manage.ps1 -Action logs -Service nginx

# بررسی لاگ‌های Django
.\docker-manage.ps1 -Action logs -Service web

# راه‌اندازی مجدد
.\docker-manage.ps1 -Action restart
```

### مشکل: مصرف زیاد حافظه

**علت**: image های قدیمی یا کانتینرهای متوقف وجود دارد.

**راه‌حل**:
```powershell
# پاک‌سازی سیستم
.\docker-manage.ps1 -Action clean

# بررسی استفاده از حافظه
.\docker-manage.ps1 -Action status
```

---

## 🔒 امنیت

### توصیه‌های امنیتی

1. **غیرفعال کردن DEBUG در production**:
   ```env
   DEBUG=False
   ```

2. **استفاده از SECRET_KEY قوی**:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. **تنظیم ALLOWED_HOSTS**:
   ```env
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

4. **استفاده از رمزهای عبور قوی**:
   - دیتابیس: حداقل 16 کاراکتر، ترکیبی از حروف بزرگ/کوچک، اعداد و نمادها
   - Redis: حداقل 16 کاراکتر

5. **فعال‌سازی HTTPS**:
   - تنظیم SSL در Nginx
   - استفاده از Let's Encrypt برای گواهینامه

6. **پشتیبان‌گیری منظم**:
   ```powershell
   # افزودن به Windows Task Scheduler
   .\docker-manage.ps1 -Action backup
   ```

### کنترل دسترسی

```powershell
# محدود کردن دسترسی به Docker
net stop docker

# بررسی لاگ‌های امنیتی
.\docker-manage.ps1 -Action logs -Service web | Select-String "ERROR\|WARNING"
```

---

## 📞 پشتیبانی

### دسترسی به منابع

- **وب‌سایت**: http://localhost:8080
- **ادمین**: http://localhost:8080/admin
- **API**: http://localhost:8080/api/

### بررسی سلامت سیستم

```powershell
# بررسی سلامت تمام سرویس‌ها
.\docker-deploy.ps1 -Action health

# بررسی جزئیات
.\docker-manage.ps1 -Action info
```

### گزارش مشکل

برای گزارش مشکل، اطلاعات زیر را آماده کنید:

1. خروجی `.\docker-manage.ps1 -Action status`
2. خروجی `.\docker-manage.ps1 -Action logs`
3. نسخه Docker: `docker --version`
4. سیستم عامل: `Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion`
5. پیغام خطای کامل

---

## 📚 منابع اضافی

- [Docker Documentation](https://docs.docker.com/)
- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)

---

**🎉 تبریک! پروژه شما آماده است!**

اگر سوالی دارید یا به کمک نیاز دارید، با تیم پشتیبانی تماس بگیرید.
