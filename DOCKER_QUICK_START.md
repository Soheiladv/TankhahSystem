# ⚡ راهنمای سریع Docker

این راهنمای سریع شامل دستورات ضروری برای شروع کار با پروژه است.

## 🚀 شروع سریع (3 دقیقه)

### 1. نصب Docker Desktop
```powershell
# دانلود از: https://www.docker.com/products/docker-desktop
# نصب و راه‌اندازی
```

### 2. تنظیم پروژه
```powershell
# رفتن به پوشه پروژه
cd "D:\Design & Source Code\Source Coding\BudgetsSystem"

# کپی فایل .env
Copy-Item env.example .env

# ویرایش فایل .env (مهم!)
notepad .env
```

### 3. راه‌اندازی
```powershell
# استفاده از منوی تعاملی
cd docker-scripts
.\docker-menu.ps1

# یا راه‌اندازی مستقیم
.\docker-setup.ps1
```

### 4. دسترسی
```
🌐 وب‌سایت: http://localhost:8080
🔐 ادمین: http://localhost:8080/admin
📊 API: http://localhost:8080/api/
```

---

## 📋 دستورات ضروری

### مدیریت پایه
```powershell
# وضعیت
.\docker-manage.ps1 -Action status

# لاگ‌ها
.\docker-manage.ps1 -Action logs -Service web

# راه‌اندازی مجدد
.\docker-manage.ps1 -Action restart

# توقف
.\docker-manage.ps1 -Action stop
```

### به‌روزرسانی
```powershell
# دریافت آخرین تغییرات
git pull origin main

# به‌روزرسانی Docker
.\docker-update.ps1 -Action update

# راه‌اندازی مجدد
.\docker-manage.ps1 -Action restart
```

### پشتیبان‌گیری
```powershell
# ایجاد پشتیبان
.\docker-manage.ps1 -Action backup

# بازگردانی
.\docker-manage.ps1 -Action restore
```

### اجرای دستورات Django
```powershell
# Migrations
docker-compose exec web python manage.py migrate

# Shell
docker-compose exec web python manage.py shell

# Superuser
docker-compose exec web python manage.py createsuperuser

# Collectstatic
docker-compose exec web python manage.py collectstatic --noinput
```

---

## ⚙️ تنظیمات مهم

### فایل .env
```env
# حتماً این موارد را تغییر دهید!
SECRET_KEY=your-strong-secret-key-here
DB_PASSWORD=your-strong-database-password
REDIS_PASSWORD=your-strong-redis-password
```

### ساخت SECRET_KEY
```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 🐛 حل مشکلات رایج

### مشکل 1: پورت 8080 اشغال است
```powershell
# تغییر پورت در docker-compose.yml
ports:
  - "8081:80"  # به جای 8080:80
```

### مشکل 2: کانتینر راه‌اندازی نمی‌شود
```powershell
# بررسی لاگ‌ها
.\docker-manage.ps1 -Action logs

# پاک‌سازی و شروع مجدد
.\docker-manage.ps1 -Action clean
.\docker-setup.ps1
```

### مشکل 3: دیتابیس اتصال برقرار نمی‌کند
```powershell
# بررسی وضعیت دیتابیس
docker-compose ps db

# بررسی لاگ‌ها
.\docker-manage.ps1 -Action logs -Service db

# راه‌اندازی مجدد
docker-compose restart db
```

---

## 📊 بررسی سلامت

```powershell
# بررسی وضعیت
.\docker-manage.ps1 -Action status

# بررسی سلامت
.\docker-deploy.ps1 -Action health

# بررسی اطلاعات
.\docker-manage.ps1 -Action info
```

---

## 🔗 لینک‌های مفید

- **منوی اصلی**: `.\docker-menu.ps1`
- **مستندات کامل**: `DOCKER_GUIDE.md`
- **README اسکریپت‌ها**: `docker-scripts/README.md`

---

## ⚡ نکات سریع

1. **همیشه قبل از به‌روزرسانی پشتیبان بگیرید**
   ```powershell
   .\docker-manage.ps1 -Action backup
   ```

2. **DEBUG را در production غیرفعال کنید**
   ```env
   DEBUG=False
   ```

3. **از رمزهای عبور قوی استفاده کنید**
   - دیتابیس: 16+ کاراکتر
   - Redis: 16+ کاراکتر
   - SECRET_KEY: استفاده از دستور Python

4. **منظم لاگ‌ها را بررسی کنید**
   ```powershell
   .\docker-manage.ps1 -Action logs -Service web
   ```

5. **در صورت مشکل، لاگ‌ها را بررسی کنید**
   ```powershell
   .\docker-manage.ps1 -Action logs
   ```

---

**✅ آماده است! لذت ببرید! 🎉**


