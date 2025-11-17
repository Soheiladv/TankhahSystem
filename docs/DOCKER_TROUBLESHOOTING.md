# 🐛 راهنمای عیب‌یابی Docker

## ⚠️ مشکلات رایج و راه‌حل‌ها

### مشکل 1: Docker Desktop در حال اجرا نیست

**خطا:**

```
error during connect: Head "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping":
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**راه‌حل:**

1. Docker Desktop را از منوی Start باز کنید
2. منتظر بمانید تا آیکون Docker در system tray (کنار ساعت) سبز شود
3. بررسی کنید که Docker Desktop به طور کامل راه‌اندازی شده است:
   ```powershell
   docker info
   ```
4. اگر خطا داشت، Docker Desktop را Restart کنید

---

### مشکل 2: متغیرهای محیطی تنظیم نشده‌اند

**خطا:**

```
level=warning msg="The \"DB_PASSWORD\" variable is not set. Defaulting to a blank string."
level=warning msg="The \"REDIS_PASSWORD\" variable is not set. Defaulting to a blank string."
```

**راه‌حل:**

1. فایل `.env` را باز کنید
2. مقادیر زیر را تنظیم کنید:
   ```env
   SECRET_KEY=your-secret-key-here
   DB_PASSWORD=your-database-password
   REDIS_PASSWORD=your-redis-password
   ```
3. برای ایجاد SECRET_KEY:
   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

---

### مشکل 3: پورت‌ها در حال استفاده هستند

**خطا:**

```
Error: bind: address already in use
```

**راه‌حل:**

1. بررسی کنید کدام برنامه از پورت استفاده می‌کند:
   ```powershell
   netstat -ano | findstr :8080
   netstat -ano | findstr :8000
   netstat -ano | findstr :5432
   ```
2. برنامه را متوقف کنید یا پورت را در `docker-compose.yml` تغییر دهید

---

### مشکل 4: خطا در ساخت Docker image

**خطا:**

```
ERROR: failed to solve: ...
```

**راه‌حل:**

1. بررسی کنید که اینترنت متصل است
2. Docker Desktop را Restart کنید
3. Cache را پاک کنید و دوباره build کنید:
   ```powershell
   docker-compose build --no-cache
   ```

---

### مشکل 5: کانتینرها راه‌اندازی نمی‌شوند

**راه‌حل:**

1. بررسی لاگ‌ها:
   ```powershell
   docker-compose logs
   ```
2. بررسی وضعیت کانتینرها:
   ```powershell
   docker-compose ps
   ```
3. راه‌اندازی مجدد:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

---

### مشکل 6: خطا در اتصال به دیتابیس

**خطا:**

```
FATAL: password authentication failed for user
```

**راه‌حل:**

1. بررسی فایل `.env` - مطمئن شوید `DB_PASSWORD` تنظیم شده است
2. بررسی کانتینر دیتابیس:
   ```powershell
   docker-compose logs db
   ```
3. راه‌اندازی مجدد دیتابیس:
   ```powershell
   docker-compose restart db
   ```

---

### مشکل 7: فایل‌های static بارگذاری نمی‌شوند

**راه‌حل:**

1. جمع‌آوری فایل‌های static:
   ```powershell
   docker-compose exec web python manage.py collectstatic --noinput
   ```
2. بررسی volume:
   ```powershell
   docker volume inspect budgetssystem_static_volume
   ```

---

### مشکل 8: خطا در migrations

**راه‌حل:**

1. بررسی وضعیت migrations:
   ```powershell
   docker-compose exec web python manage.py showmigrations
   ```
2. اجرای migrations:
   ```powershell
   docker-compose exec web python manage.py migrate
   ```
3. اگر نیاز به reset است:
   ```powershell
   docker-compose down -v
   docker-compose up -d
   docker-compose exec web python manage.py migrate
   ```

---

### مشکل 9: فایل‌های Secrets ایجاد نشده‌اند

**نشانه‌ها:**

- `docker compose up` پیام می‌دهد فایل `./secrets/db_password.txt` یا مشابه پیدا نشد
- سرویس Redis بدون رمز راه‌اندازی می‌شود یا healthcheck خطای عدم احراز هویت می‌دهد

**راه‌حل:**

1. اجرای اسکریپت تولید Secrets:
   ```powershell
   cd docker-scripts
   .\setup-secrets.ps1
   cd ..
   ```
2. اطمینان از اینکه فایل‌های زیر ایجاد شده‌اند (همگی محرمانه هستند):
   - `secrets/db_password.txt`
   - `secrets/redis_password.txt`
   - `secrets/django_secret_key.txt`
3. اجرای مجدد سرویس‌ها:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```
4. برای اطمینان از امنیت، محتویات فایل‌ها را هرگز در مخزن گیت Commit نکنید.

---

## 🔍 دستورات مفید برای عیب‌یابی

### بررسی وضعیت Docker

```powershell
# بررسی نسخه Docker
docker --version
docker-compose --version

# بررسی وضعیت Docker Desktop
docker info

# بررسی کانتینرها
docker-compose ps

# بررسی لاگ‌ها
docker-compose logs
docker-compose logs web
docker-compose logs db
```

### مدیریت کانتینرها

```powershell
# توقف تمام کانتینرها
docker-compose down

# راه‌اندازی مجدد
docker-compose restart

# راه‌اندازی مجدد یک سرویس خاص
docker-compose restart web

# حذف کانتینرها و volumes
docker-compose down -v
```

### بررسی منابع

```powershell
# بررسی استفاده از منابع
docker stats

# بررسی image ها
docker images

# بررسی volume ها
docker volume ls

# پاک‌سازی سیستم
docker system prune -a
```

---

## 📞 دریافت کمک

اگر مشکل شما حل نشد:

1. **لاگ‌ها را بررسی کنید:**

   ```powershell
   docker-compose logs > logs.txt
   ```

2. **وضعیت سیستم را بررسی کنید:**

   ```powershell
   docker-compose ps
   docker info
   ```

3. **مشکلات را مستند کنید:**
   - خطای کامل
   - خروجی `docker-compose ps`
   - خروجی `docker-compose logs`
   - نسخه Docker: `docker --version`

---

## ✅ چک‌لیست عیب‌یابی

- [ ] Docker Desktop نصب شده است
- [ ] Docker Desktop در حال اجرا است
- [ ] فایل `.env` ایجاد شده است
- [ ] متغیرهای ضروری در `.env` تنظیم شده‌اند
- [ ] پورت‌ها آزاد هستند
- [ ] اینترنت متصل است
- [ ] WSL2 نصب شده است (برای Windows)

---

**نکته**: در صورت نیاز به کمک بیشتر، به `DOCKER_GUIDE.md` مراجعه کنید.
