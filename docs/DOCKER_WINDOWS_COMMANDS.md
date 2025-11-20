# راهنمای اجرای دستورات Docker در Windows

## 📋 فهرست مطالب

1. [اجرای دستورات manage.py](#اجرای-دستورات-managepy)
2. [اجرای دستورات Shell](#اجرای-دستورات-shell)
3. [انتقال تغییرات به Docker](#انتقال-تغییرات-به-docker)
4. [دستورات مفید](#دستورات-مفید)

---

## 🔧 اجرای دستورات manage.py

### روش کلی

```powershell
docker compose exec web python manage.py <command>
```

### مثال‌های رایج

#### Migration
```powershell
# اجرای migration
docker compose exec web python manage.py migrate

# اجرای migration بدون تایید
docker compose exec web python manage.py migrate --noinput

# نمایش migration‌های اجرا شده
docker compose exec web python manage.py showmigrations

# ساخت migration جدید
docker compose exec web python manage.py makemigrations

# ساخت migration برای app خاص
docker compose exec web python manage.py makemigrations accounts
```

#### Shell و Database
```powershell
# باز کردن Django shell
docker compose exec web python manage.py shell

# باز کردن database shell
docker compose exec web python manage.py dbshell

# بررسی سیستم
docker compose exec web python manage.py check

# بررسی دیتابیس
docker compose exec web python manage.py check --database default
```

#### User Management
```powershell
# ساخت superuser
docker compose exec web python manage.py createsuperuser

# تغییر پسورد کاربر
docker compose exec web python manage.py changepassword admin
```

#### Static Files
```powershell
# جمع‌آوری فایل‌های static
docker compose exec web python manage.py collectstatic --noinput

# پاک کردن فایل‌های static
docker compose exec web python manage.py collectstatic --clear --noinput
```

#### Custom Commands
```powershell
# اجرای دستورات سفارشی
docker compose exec web python manage.py update_versions
docker compose exec web python manage.py cleanup_old_data
```

---

## 🐚 اجرای دستورات Shell

### دستورات عمومی

```powershell
# اجرای دستور در container
docker compose exec web <command>

# اجرای دستور در container با shell
docker compose exec web sh -c "<command>"

# اجرای دستور در container با bash
docker compose exec web bash -c "<command>"
```

### مثال‌های کاربردی

#### بررسی فایل‌ها
```powershell
# لیست فایل‌ها
docker compose exec web ls -la /app

# مشاهده محتوای فایل
docker compose exec web cat /app/manage.py

# جستجو در فایل‌ها
docker compose exec web grep -r "pattern" /app
```

#### بررسی Environment Variables
```powershell
# نمایش تمام متغیرهای محیطی
docker compose exec web env

# نمایش متغیر خاص
docker compose exec web sh -c "echo \$DJANGO_SETTINGS_MODULE"
```

#### بررسی Logs
```powershell
# مشاهده لاگ‌های Django
docker compose exec web tail -f /app/logs/application_errors.log

# مشاهده لاگ‌های سیستم
docker compose exec web dmesg | tail -20
```

#### بررسی Database
```powershell
# اتصال به MySQL
docker compose exec db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db

# نمایش جداول
docker compose exec db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db -e "SHOW TABLES;"

# تعداد جداول
docker compose exec db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'budgets_db';"
```

#### بررسی Redis
```powershell
# اتصال به Redis CLI
docker compose exec redis redis-cli -a $(cat /run/secrets/redis_password)

# بررسی کلیدها
docker compose exec redis redis-cli -a $(cat /run/secrets/redis_password) KEYS "*"
```

---

## 🔄 انتقال تغییرات به Docker

### روش 1: Rebuild Image (توصیه می‌شود)

```powershell
# 1. توقف container
docker compose stop web

# 2. Rebuild image
docker compose build web

# 3. راه‌اندازی مجدد
docker compose up -d web

# یا همه در یک خط:
docker compose up -d --build web
```

### روش 2: Volume Mount (برای Development)

اگر فایل‌های پروژه به صورت volume mount شده‌اند (که در `docker-compose.yml` تعریف شده)، تغییرات به صورت خودکار اعمال می‌شوند:

```powershell
# فقط restart کنید
docker compose restart web
```

### روش 3: Copy Files

```powershell
# کپی فایل از host به container
docker cp ".\path\to\file.py" budgets_web:/app/path/to/file.py

# کپی فایل از container به host
docker cp budgets_web:/app/path/to/file.py ".\path\to\file.py"

# کپی دایرکتوری
docker cp ".\accounts" budgets_web:/app/
```

### روش 4: Live Reload (برای Development)

برای تغییرات در کد Python، می‌توانید از `--reload` استفاده کنید:

```powershell
# در docker-compose.yml، command را تغییر دهید:
# command: python manage.py runserver 0.0.0.0:8000 --reload
```

---

## 📦 دستورات مفید

### مدیریت Containers

```powershell
# مشاهده وضعیت
docker compose ps

# مشاهده لاگ‌ها
docker compose logs -f web
docker compose logs -f db
docker compose logs -f  # همه سرویس‌ها

# راه‌اندازی مجدد
docker compose restart web
docker compose restart  # همه سرویس‌ها

# توقف
docker compose stop

# توقف و حذف
docker compose down

# توقف و حذف volumes
docker compose down -v
```

### بررسی Health

```powershell
# بررسی health status
docker compose ps

# بررسی health check
docker compose exec web /docker-healthcheck.sh
```

### بررسی تعداد جداول

```powershell
docker compose exec web python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()')
print('Total tables:', cursor.fetchone()[0])
"
```

### بررسی Migration‌ها

```powershell
# نمایش migration‌های اجرا شده
docker compose exec web python manage.py showmigrations

# نمایش migration‌های اجرا نشده
docker compose exec web python manage.py showmigrations | Select-String -Pattern "\[ \]"
```

### Backup و Restore

```powershell
# Backup دیتابیس
docker compose exec db mysqldump -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Restore دیتابیس
Get-Content backup_20241117.sql | docker compose exec -T db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db
```

### پاکسازی

```powershell
# حذف container‌های متوقف شده
docker compose rm

# حذف image‌های استفاده نشده
docker image prune

# حذف همه چیز (مراقب باشید!)
docker compose down -v --rmi all
```

---

## 🎯 مثال‌های عملی

### سناریو 1: تغییر در Model و نیاز به Migration

```powershell
# 1. تغییر در models.py (در سیستم محلی)

# 2. ساخت migration
docker compose exec web python manage.py makemigrations

# 3. بررسی migration
docker compose exec web python manage.py showmigrations

# 4. اجرای migration
docker compose exec web python manage.py migrate

# 5. بررسی تعداد جداول
docker compose exec web python -c "import os, django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings'); django.setup(); from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()'); print('Total tables:', cursor.fetchone()[0])"
```

### سناریو 2: تغییر در Settings

```powershell
# 1. تغییر در settings.py

# 2. Rebuild image
docker compose up -d --build web

# 3. بررسی لاگ‌ها
docker compose logs -f web
```

### سناریو 3: اضافه کردن Package جدید

```powershell
# 1. اضافه کردن به requirements.txt

# 2. Rebuild image
docker compose build web

# 3. راه‌اندازی مجدد
docker compose up -d web
```

### سناریو 4: Debugging

```powershell
# 1. مشاهده لاگ‌های real-time
docker compose logs -f web

# 2. اجرای shell برای بررسی
docker compose exec web python manage.py shell

# 3. بررسی database
docker compose exec web python manage.py dbshell

# 4. بررسی environment variables
docker compose exec web env | Select-String "DJANGO"
```

---

## ⚠️ نکات مهم

1. **همیشه از `--noinput` استفاده کنید** برای دستوراتی که نیاز به تایید ندارند (مثل migrate در production)

2. **برای تغییرات در کد Python**، اگر volume mount شده، فقط restart کنید. در غیر این صورت rebuild کنید.

3. **برای تغییرات در requirements.txt**، حتماً rebuild کنید.

4. **برای تغییرات در docker-compose.yml**، حتماً `docker compose down` و سپس `docker compose up -d` کنید.

5. **برای migration‌های جدید**، ابتدا `makemigrations` و سپس `migrate` کنید.

---

## 🔗 لینک‌های مفید

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Management Commands](https://docs.djangoproject.com/en/stable/ref/django-admin/)
- [Docker Exec Documentation](https://docs.docker.com/engine/reference/commandline/exec/)

