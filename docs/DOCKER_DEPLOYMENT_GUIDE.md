# راهنمای کامل اجرا و انتقال Docker

## 📋 فهرست مطالب

1. [اجرای Docker در سیستم محلی (Windows)](#اجرای-در-سیستم-محلی)
2. [دسترسی به اپلیکیشن در مرورگر](#دسترسی-در-مرورگر)
3. [انتقال به سرور لینوکس](#انتقال-به-سرور-لینوکس)
4. [تست و بررسی](#تست-و-بررسی)
5. [اجرای دستورات در Windows](#اجرای-دستورات-در-windows)

---

## 🖥️ اجرای در سیستم محلی

### پیش‌نیازها

- Docker Desktop نصب و در حال اجرا باشد
- فایل‌های secret در `secrets/` موجود باشند

### مراحل اجرا

#### 1. ساخت فایل‌های Secret (اگر وجود ندارند)

```powershell
# اجرای اسکریپت setup
powershell .\docker-scripts\setup-secrets.ps1 -Force
```

یا به صورت دستی:

```powershell
# ساخت پسورد دیتابیس
Set-Content -Path "secrets\db_password.txt" -Value "BudgetsDB2024!SecurePass#2486" -NoNewline

# ساخت پسورد Redis
Set-Content -Path "secrets\redis_password.txt" -Value "BudgetsRedis2024!SecurePass#7922" -NoNewline

# ساخت Secret Key Django
Set-Content -Path "secrets\django_secret_key.txt" -Value "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" -NoNewline
```

#### 2. ساخت و راه‌اندازی کانتینرها

```powershell
# ساخت image و راه‌اندازی تمام سرویس‌ها
docker compose up -d --build

# بررسی وضعیت سرویس‌ها
docker compose ps

# مشاهده لاگ‌ها
docker compose logs -f web
```

#### 3. اجرای Migration (در صورت نیاز)

```powershell
# اجرای migration
docker compose exec web python manage.py migrate --noinput

# بررسی migration‌های اجرا شده
docker compose exec web python manage.py showmigrations
```

---

## 🌐 دسترسی در مرورگر

پس از راه‌اندازی، اپلیکیشن در آدرس‌های زیر در دسترس است:

- **HTTP (از طریق Nginx):** http://localhost:8080
- **HTTPS (از طریق Nginx):** https://localhost:443
- **مستقیم Django:** http://localhost:8000

### دسترسی به Admin Panel

- URL: http://localhost:8080/admin/
- کاربر پیش‌فرض: `admin`
- پسورد: (در entrypoint.sh ساخته می‌شود یا باید با دستور زیر ساخت)

```powershell
# ساخت superuser
docker compose exec web python manage.py createsuperuser
```

---

## 🚀 انتقال به سرور لینوکس

### روش 1: انتقال با Git (توصیه می‌شود)

#### در سیستم محلی (Windows):

```powershell
# Commit تغییرات
git add .
git commit -m "Docker configuration ready for deployment"
git push origin main
```

#### در سرور لینوکس:

```bash
# کلون پروژه
git clone <repository-url>
cd BudgetsSystem

# ساخت فایل‌های secret
mkdir -p secrets
echo -n "BudgetsDB2024!SecurePass#2486" > secrets/db_password.txt
echo -n "BudgetsRedis2024!SecurePass#7922" > secrets/redis_password.txt
echo -n "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" > secrets/django_secret_key.txt

# تنظیم دسترسی‌ها
chmod 600 secrets/*.txt

# ساخت و راه‌اندازی
docker compose up -d --build

# اجرای migration
docker compose exec web python manage.py migrate --noinput
```

### روش 2: انتقال با SCP/RSYNC

#### در سیستم محلی (Windows):

```powershell
# استفاده از WinSCP یا PowerShell
scp -r "D:\Design & Source Code\Source Coding\BudgetsSystem" user@server:/path/to/destination/
```

#### در سرور لینوکس:

```bash
# انتقال فایل‌ها (از Windows)
# سپس:
cd /path/to/BudgetsSystem

# ساخت فایل‌های secret (مهم!)
mkdir -p secrets
# ... (مثل روش 1)

# راه‌اندازی
docker compose up -d --build
```

### روش 3: استفاده از Docker Registry

#### در سیستم محلی:

```powershell
# Build و Push image
docker compose build web
docker tag budgetssystem-web:latest your-registry.com/budgetssystem-web:latest
docker push your-registry.com/budgetssystem-web:latest
```

#### در سرور:

```bash
# Pull و اجرا
docker pull your-registry.com/budgetssystem-web:latest
docker compose up -d
```

---

## ⚙️ تنظیمات سرور لینوکس

### 1. نصب Docker و Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker

# اضافه کردن کاربر به گروه docker
sudo usermod -aG docker $USER
newgrp docker
```

### 2. تنظیم Firewall

```bash
# باز کردن پورت‌های لازم
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # اگر نیاز دارید
sudo ufw reload
```

### 3. تنظیم Nginx (برای Production)

```bash
# کپی فایل تنظیمات
sudo cp docker/nginx/nginx.conf /etc/nginx/sites-available/budgets-system
sudo ln -s /etc/nginx/sites-available/budgets-system /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔍 تست و بررسی

### بررسی وضعیت سرویس‌ها

```bash
# در سیستم محلی (PowerShell)
docker compose ps

# در سرور لینوکس
docker compose ps
```

### بررسی لاگ‌ها

```bash
# لاگ تمام سرویس‌ها
docker compose logs -f

# لاگ سرویس خاص
docker compose logs -f web
docker compose logs -f db
docker compose logs -f nginx
```

### بررسی اتصال دیتابیس

```bash
# تست اتصال از داخل container
docker compose exec web python manage.py dbshell

# یا
docker compose exec db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db -e "SHOW TABLES;"
```

### بررسی تعداد جداول

```bash
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

---

## 🛠️ دستورات مفید

### راه‌اندازی مجدد

```bash
docker compose restart
docker compose restart web
```

### توقف و حذف

```bash
# توقف
docker compose stop

# توقف و حذف volumes
docker compose down -v

# توقف و حذف همه چیز
docker compose down -v --rmi all
```

### به‌روزرسانی

```bash
# Pull آخرین تغییرات
git pull

# Rebuild و restart
docker compose up -d --build
docker compose exec web python manage.py migrate --noinput
```

### Backup دیتابیس

```bash
# Backup
docker compose exec db mysqldump -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db > backup_$(date +%Y%m%d).sql

# Restore
docker compose exec -T db mysql -ubudgets_user -p$(cat /run/secrets/db_password) budgets_db < backup_20241117.sql
```

---

## 🔐 نکات امنیتی

> **📖 برای راهنمای کامل امنیت‌سازی رمزها و پسوردها، به فایل [`docs/SECURITY_SECRETS_GUIDE.md`](./SECURITY_SECRETS_GUIDE.md) مراجعه کنید.**

1. **فایل‌های Secret:**

   - هرگز `secrets/*.txt` را commit نکنید
   - در سرور، دسترسی را محدود کنید: `chmod 600 secrets/*.txt`
   - **امنیت‌سازی فوری:**
     - Windows: `.\docker-scripts\secure-secrets.ps1`
     - Linux: `bash docker-scripts/secure-secrets.sh`

2. **متغیرهای محیطی:**

   - از `.env` برای تنظیمات محلی استفاده کنید
   - در production از Docker secrets استفاده کنید

3. **پورت‌ها:**
   - در production، پورت‌های داخلی را expose نکنید
   - فقط از طریق Nginx دسترسی دهید

---

## 📞 عیب‌یابی

### مشکل: سرویس‌ها بالا نمی‌آیند

```bash
# بررسی لاگ
docker compose logs

# بررسی وضعیت
docker compose ps

# راه‌اندازی مجدد
docker compose down
docker compose up -d
```

### مشکل: Migration خطا می‌دهد

```bash
# بررسی migration‌های اجرا شده
docker compose exec web python manage.py showmigrations

# اجرای مجدد
docker compose exec web python manage.py migrate --noinput
```

### مشکل: اتصال به دیتابیس برقرار نمی‌شود

```bash
# بررسی secret files
docker compose exec web cat /run/secrets/db_password

# تست اتصال
docker compose exec web python manage.py dbshell
```

---

## ✅ چک‌لیست نهایی

- [ ] Docker Desktop در حال اجرا است
- [ ] فایل‌های secret در `secrets/` موجود هستند
- [ ] تمام سرویس‌ها healthy هستند (`docker compose ps`)
- [ ] Migration‌ها اجرا شده‌اند
- [ ] اپلیکیشن در مرورگر قابل دسترسی است
- [ ] Admin panel کار می‌کند

---

## ⚡ دستورات سریع

### اجرای کامل در یک خط (سیستم محلی)

```powershell
# ساخت secret files (اگر وجود ندارند)
if (-not (Test-Path "secrets\db_password.txt")) { Set-Content -Path "secrets\db_password.txt" -Value "BudgetsDB2024!SecurePass#2486" -NoNewline }
if (-not (Test-Path "secrets\redis_password.txt")) { Set-Content -Path "secrets\redis_password.txt" -Value "BudgetsRedis2024!SecurePass#7922" -NoNewline }
if (-not (Test-Path "secrets\django_secret_key.txt")) { Set-Content -Path "secrets\django_secret_key.txt" -Value "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" -NoNewline }

# راه‌اندازی
docker compose up -d --build

# بررسی وضعیت
docker compose ps
```

### اجرای کامل در یک خط (سرور لینوکس)

```bash
# ساخت secret files
mkdir -p secrets
echo -n "BudgetsDB2024!SecurePass#2486" > secrets/db_password.txt
echo -n "BudgetsRedis2024!SecurePass#7922" > secrets/redis_password.txt
echo -n "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" > secrets/django_secret_key.txt
chmod 600 secrets/*.txt

# راه‌اندازی
docker compose up -d --build

# بررسی وضعیت
docker compose ps
```

---

**نکته:** برای انتقال به سرور، حتماً فایل‌های secret را به صورت امن منتقل کنید و هرگز آن‌ها را در Git commit نکنید!

---

## 💻 اجرای دستورات در Windows

برای راهنمای کامل اجرای دستورات `manage.py` و Shell در Windows، به فایل [`docs/DOCKER_WINDOWS_COMMANDS.md`](./DOCKER_WINDOWS_COMMANDS.md) مراجعه کنید.

### خلاصه دستورات مهم:

#### اجرای دستورات manage.py

```powershell
# Migration
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations

# Shell
docker compose exec web python manage.py shell
docker compose exec web python manage.py dbshell

# User Management
docker compose exec web python manage.py createsuperuser
```

#### انتقال تغییرات به Docker

```powershell
# روش 1: Rebuild (برای تغییرات در requirements.txt یا Dockerfile)
docker compose up -d --build web

# روش 2: Restart (برای تغییرات در کد Python که volume mount شده)
docker compose restart web

# روش 3: Copy Files
docker cp ".\accounts" budgets_web:/app/
```

برای جزئیات بیشتر و مثال‌های عملی، فایل [`DOCKER_WINDOWS_COMMANDS.md`](./DOCKER_WINDOWS_COMMANDS.md) را مطالعه کنید.

روش 2: با SCP/RSYNC

# از Windows به سرور:

scp -r "D:\Design & Source Code\Source Coding\BudgetsSystem" user@server:/path/to/destination/

# سپس در سرور:

cd /path/to/BudgetsSystem

# ... (مثل روش 1)

بررسی علت کمبود 26 جدول و اجرای مجدد migration‌ها:

[5 tools called]

بررسی علت کمبود 26 جدول و اجرای مجدد migration‌ها:

[7 tools called]

ایجاد migration برای `purchase_requests` و سپس اجرای مجدد:

[6 tools called]

بررسی و اجرای migrationهای `purchase_requests`:

[7 tools called]

بررسی و رفع مشکل migration‌ها:

[4 tools called]

fake کردن migration‌های موجود و ساخت migration برای `purchase_requests`:

[4 tools called]

91 جدول ایجاد شد. خلاصه وضعیت و راهنمای اجرا:

## خلاصه وضعیت

- تعداد جداول: 91 جدول ایجاد شد
- Migration‌ها: همه اجرا شدند
- سرویس‌ها: همه در حال اجرا هستند

## راهنمای اجرای Docker

### 1. اجرا در سیستم محلی (Windows)

```powershell
# 1. ساخت فایل‌های secret (اگر وجود ندارند)
if (-not (Test-Path "secrets\db_password.txt")) {
    New-Item -ItemType Directory -Force -Path "secrets" | Out-Null
    Set-Content -Path "secrets\db_password.txt" -Value "BudgetsDB2024!SecurePass#2486" -NoNewline
}
if (-not (Test-Path "secrets\redis_password.txt")) {
    Set-Content -Path "secrets\redis_password.txt" -Value "BudgetsRedis2024!SecurePass#7922" -NoNewline
}
if (-not (Test-Path "secrets\django_secret_key.txt")) {
    Set-Content -Path "secrets\django_secret_key.txt" -Value "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" -NoNewline
}

# 2. راه‌اندازی Docker
docker compose up -d --build

# 3. بررسی وضعیت
docker compose ps

# 4. مشاهده لاگ‌ها
docker compose logs -f web
```

### 2. دسترسی در مرورگر

- HTTP: http://localhost:8080
- HTTPS: https://localhost:443
- Django مستقیم: http://localhost:8000
- Admin Panel: http://localhost:8080/admin/

### 3. انتقال به سرور لینوکس

#### روش 1: با Git (توصیه می‌شود)

```bash
# در سرور لینوکس:
git clone <repository-url>
cd BudgetsSystem

# ساخت فایل‌های secret
mkdir -p secrets
echo -n "BudgetsDB2024!SecurePass#2486" > secrets/db_password.txt
echo -n "BudgetsRedis2024!SecurePass#7922" > secrets/redis_password.txt
echo -n "!z0w58$sax3)7&wgme3bgp(s8@ql*3vex^w$aw5aarzx#4x5^j" > secrets/django_secret_key.txt
chmod 600 secrets/*.txt

# راه‌اندازی
docker compose up -d --build

# بررسی وضعیت
docker compose ps
```

#### روش 2: با SCP/RSYNC

```bash
# از Windows به سرور:
scp -r "D:\Design & Source Code\Source Coding\BudgetsSystem" user@server:/path/to/destination/

# سپس در سرور:
cd /path/to/BudgetsSystem
# ... (مثل روش 1)
```

### 4. دستورات مفید

```bash
# بررسی تعداد جداول
docker compose exec web python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BudgetsSystem.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE()')
print('Total tables:', cursor.fetchone()[0])
"

# راه‌اندازی مجدد
docker compose restart

# توقف
docker compose stop

# توقف و حذف همه چیز
docker compose down -v
```

راهنمای کامل در فایل `docs/DOCKER_DEPLOYMENT_GUIDE.md` ذخیره شد.

نکته: فایل‌های `secrets/*.txt` را هرگز در Git commit نکنید. آن‌ها در `.gitignore` قرار دارند.

آیا می‌خواهید تعداد جداول را به 117 برسانیم یا همین 91 جدول کافی است؟
