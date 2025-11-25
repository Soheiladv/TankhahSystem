# 🚀 راهنمای سریع اجرای Docker

## ⚡ اجرای سریع (3 مرحله)

### 1️⃣ بررسی و آماده‌سازی

```powershell
# بررسی و رفع مشکلات
.\docker-scripts\check-docker-setup.ps1 -Fix
```

### 2️⃣ اجرای Docker

```powershell
# اجرای کامل Docker
.\docker-scripts\run-docker.ps1
```

### 3️⃣ دسترسی به اپلیکیشن

- **Django**: http://localhost:8000
- **Nginx**: http://localhost:8080
- **MySQL**: localhost:3307
- **Redis**: localhost:6379

---

## 📋 مراحل کامل

### پیش‌نیازها

1. ✅ **Docker Desktop نصب شده** و در حال اجرا باشد
2. ✅ **فایل‌های secrets** در پوشه `secrets/` وجود دارند

### گام 1: ایجاد فایل‌های Secrets (اگر وجود ندارند)

```powershell
# استفاده از اسکریپت آماده
.\docker-scripts\setup-secrets.ps1
```

یا به صورت دستی:

```powershell
# ساخت پوشه secrets
mkdir secrets

# ایجاد فایل‌های secrets
"your_db_password" | Out-File -FilePath "secrets\db_password.txt" -NoNewline
"your_redis_password" | Out-File -FilePath "secrets\redis_password.txt" -NoNewline
"your_django_secret_key" | Out-File -FilePath "secrets\django_secret_key.txt" -NoNewline
```

### گام 2: محدود کردن دسترسی Secrets

```powershell
# محدود کردن دسترسی (فقط شما)
.\docker-scripts\secure-secrets.ps1
```

### گام 3: بررسی پیش‌نیازها

```powershell
# بررسی کامل سیستم
.\docker-scripts\check-docker-setup.ps1 -Fix
```

### گام 4: اجرای Docker

```powershell
# اجرای کامل (Build + Run)
.\docker-scripts\run-docker.ps1
```

یا به صورت دستی:

```powershell
# Build و Run
docker compose up -d --build

# مشاهده وضعیت
docker compose ps

# مشاهده لاگ‌ها
docker compose logs -f
```

---

## 🔍 بررسی و Troubleshooting

### بررسی وضعیت سرویس‌ها

```powershell
# وضعیت همه سرویس‌ها
docker compose ps

# استفاده از منابع
docker stats

# لاگ‌های web
docker compose logs -f web

# لاگ‌های دیتابیس
docker compose logs -f db
```

### مشکلات رایج

#### مشکل: کانتینر راه نمی‌افتد

```powershell
# بررسی لاگ‌ها
docker compose logs web

# بررسی خطاهای Docker
docker compose ps -a
```

#### مشکل: خطای اتصال به دیتابیس

```powershell
# بررسی سلامت دیتابیس
docker compose exec db mysqladmin ping -h localhost -uroot -p

# بررسی شبکه Docker
docker network ls
docker network inspect budgets_budgets_network
```

#### مشکل: پورت در حال استفاده است

```powershell
# بررسی پورت‌های استفاده شده
netstat -ano | findstr :8000

# تغییر پورت در docker-compose.yml
# ports:
#   - "8001:8000"  # تغییر پورت خارجی
```

---

## 🛠️ دستورات مفید

### مدیریت کانتینرها

```powershell
# توقف همه سرویس‌ها
docker compose down

# توقف و حذف volumes
docker compose down -v

# راه‌اندازی مجدد
docker compose restart

# راه‌اندازی مجدد یک سرویس خاص
docker compose restart web
```

### دسترسی به Shell

```powershell
# دسترسی به کانتینر web
docker compose exec web bash

# دسترسی به MySQL
docker compose exec db mysql -u root -p
```

### مدیریت Django

```powershell
# اجرای migration
docker compose exec web python manage.py migrate

# ایجاد superuser
docker compose exec web python manage.py createsuperuser

# جمع‌آوری فایل‌های static
docker compose exec web python manage.py collectstatic --noinput

# اجرای shell Django
docker compose exec web python manage.py shell
```

### مدیریت دیتابیس

```powershell
# Backup دیتابیس
docker compose exec db mysqldump -u root -p budgets_db > backup.sql

# Restore دیتابیس
docker compose exec -T db mysql -u root -p budgets_db < backup.sql
```

---

## 📦 انتقال به سیستم دیگر

برای انتقال به سیستم دیگر، به راهنمای کامل مراجعه کنید:

📄 [راهنمای کامل انتقال](./DOCKER_TRANSFER_GUIDE.md)

**خلاصه:**

1. ایجاد پکیج: `.\docker-scripts\create-transfer-package.ps1`
2. انتقال ZIP به سیستم مقصد
3. Extract و اجرای `check-docker-setup.ps1 -Fix`
4. اجرای `run-docker.ps1`

---

## ✅ چک‌لیست

بعد از اجرا، این موارد را بررسی کنید:

- [ ] تمام سرویس‌ها در حال اجرا هستند (`docker compose ps`)
- [ ] اپلیکیشن در مرورگر باز می‌شود
- [ ] دیتابیس به درستی کار می‌کند
- [ ] فایل‌های static بارگذاری می‌شوند
- [ ] لاگ‌ها خطایی نشان نمی‌دهند

---

## 📞 راهنماهای بیشتر

- 📘 [راهنمای کامل Docker Deployment](./DOCKER_DEPLOYMENT_GUIDE.md)
- 🔐 [راهنمای امنیت Secrets](./SECURITY_SECRETS_GUIDE.md)
- 📦 [راهنمای انتقال به سیستم دیگر](./DOCKER_TRANSFER_GUIDE.md)

---

## 🆘 پشتیبانی

اگر مشکلی پیش آمد:

1. بررسی لاگ‌ها: `docker compose logs`
2. بررسی راهنمای Troubleshooting در مستندات
3. بررسی [راهنمای کامل](./DOCKER_DEPLOYMENT_GUIDE.md)
