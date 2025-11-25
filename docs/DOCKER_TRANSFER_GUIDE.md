# 📦 راهنمای کامل انتقال Docker به سیستم دیگر

## 📋 فهرست مطالب

1. [انتقال از Windows به Windows](#انتقال-از-windows-به-windows)
2. [انتقال از Windows به Linux](#انتقال-از-windows-به-linux)
3. [انتقال به سرور Remote](#انتقال-به-سرور-remote)
4. [چک‌لیست انتقال](#چک‌لیست-انتقال)
5. [راهنمای Troubleshooting](#troubleshooting)

---

## 🔄 انتقال از Windows به Windows

### روش 1: استفاده از فایل‌های پروژه (توصیه می‌شود)

این روش برای انتقال به کامپیوتر دیگر در همان شبکه یا از طریق USB/Network Drive مناسب است.

#### گام 1: آماده‌سازی در سیستم مبدا

```powershell
# 1. توقف Docker
docker compose down

# 2. بررسی فایل‌های مهم
# اطمینان حاصل کنید که فایل‌های زیر وجود دارند:
# - docker-compose.yml
# - Dockerfile
# - requirements.txt
# - .env (یا env.example)
# - secrets/*.txt
# - docker/entrypoint.sh
# - docker/healthcheck.sh
```

#### گام 2: ایجاد پکیج انتقال

```powershell
# ایجاد یک پکیج ZIP شامل تمام فایل‌های لازم
# اسکریپت همه اپلیکیشن‌ها و پوشه‌های پروژه را به‌صورت خودکار انتخاب می‌کند
# (به‌جز اقلامی مثل venv، __pycache__، node_modules، .git و فایل‌های موقتی)
.\docker-scripts\create-transfer-package.ps1
```

یا به صورت دستی:

```powershell
# لیست فایل‌ها و پوشه‌هایی که باید منتقل شوند:
$itemsToTransfer = @(
    "BudgetsSystem",
    "accounts",
    "budgets",
    "core",
    "tankhah",
    "notificationApp",
    "purchase_requests",
    "reports",
    "templates",
    "static",
    "media",
    "config",
    "docker",
    "docker-scripts",
    "nginx",
    "secrets",
    "logs",
    "backups",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "manage.py",
    "env.example",
    ".gitignore",
    "README.md",
    "docs",
    "version_tracker",
    "usb_key_validator"
)

# ایجاد ZIP
Compress-Archive -Path $itemsToTransfer -DestinationPath "BudgetsSystem-Docker-Transfer.zip"
```

#### گام 3: انتقال به سیستم مقصد

1. **کپی فایل ZIP** به سیستم مقصد (USB, Network, Cloud)
2. **Extract کردن** در محل مناسب
3. **نصب Docker Desktop** در سیستم مقصد (اگر نصب نیست)

#### گام 4: راه‌اندازی در سیستم مقصد

```powershell
# 1. رفتن به پوشه پروژه
cd "مسیر\به\پروژه"

# 2. بررسی و ایجاد فایل‌های لازم
.\docker-scripts\check-docker-setup.ps1 -Fix

# 3. اجرای Docker
.\docker-scripts\run-docker.ps1
```

---

## 🐧 انتقال از Windows به Linux

### روش 1: استفاده از Git (توصیه می‌شود)

این روش بهترین است اگر پروژه در Git repository است.

#### گام 1: در سیستم Windows

```powershell
# 1. بررسی .gitignore (فایل‌های حساس نباید commit شوند)
git status

# 2. Commit تغییرات (فقط فایل‌های کد)
git add .
git commit -m "Prepare for Linux deployment"

# 3. Push به repository
git push origin main
```

#### گام 2: در سیستم Linux

```bash
# 1. Clone پروژه
git clone <repository-url>
cd BudgetsSystem

# 2. ایجاد فایل‌های secrets (مهم!)
mkdir -p secrets
echo "your_db_password" > secrets/db_password.txt
echo "your_redis_password" > secrets/redis_password.txt
echo "your_django_secret_key" > secrets/django_secret_key.txt

# محدود کردن دسترسی
chmod 600 secrets/*.txt
chmod 700 secrets

# 3. ایجاد فایل .env از env.example
cp env.example .env
nano .env  # ویرایش تنظیمات

# 4. اجرای Docker
docker compose up -d --build
```

### روش 2: انتقال مستقیم (بدون Git)

```powershell
# در Windows: ایجاد tar archive
tar -czf BudgetsSystem-Linux.tar.gz --exclude='venv' --exclude='__pycache__' --exclude='node_modules' --exclude='.git' .
```

```bash
# در Linux: دریافت و extract
# از طریق SCP:
scp user@windows-ip:/path/to/BudgetsSystem-Linux.tar.gz .

# یا از طریق USB

# Extract
tar -xzf BudgetsSystem-Linux.tar.gz
cd BudgetsSystem

# ادامه مانند روش 1
```

---

## 🌐 انتقال به سرور Remote (Production)

### روش 1: استفاده از Git + CI/CD (بهترین)

#### گام 1: Setup در سرور

```bash
# SSH به سرور
ssh user@server-ip

# نصب Docker (اگر نصب نیست)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker

# Clone پروژه
cd /opt
sudo git clone <repository-url> BudgetsSystem
cd BudgetsSystem
sudo chown -R $USER:$USER .
```

#### گام 2: تنظیم Secrets در سرور

```bash
# ایجاد فایل‌های secrets (مهم: از رمزهای قوی استفاده کنید)
mkdir -p secrets
nano secrets/db_password.txt  # وارد کردن رمز قوی
nano secrets/redis_password.txt
nano secrets/django_secret_key.txt

# محدود کردن دسترسی (بسیار مهم!)
sudo chown root:root secrets/*.txt
sudo chmod 600 secrets/*.txt
sudo chmod 700 secrets
```

#### گام 3: تنظیم .env برای Production

```bash
# کپی از env.example
cp env.example .env

# ویرایش برای Production
nano .env
```

تغییرات مهم در `.env`:

```env
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SECRET_KEY=  # خالی بگذارید، از secrets استفاده می‌شود
DB_HOST=db
```

#### گام 4: اجرا در Production

```bash
# Build و اجرا
docker compose -f docker-compose.yml up -d --build

# بررسی وضعیت
docker compose ps
docker compose logs -f
```

### روش 2: استفاده از Docker Registry

اگر می‌خواهید image را در Docker Hub یا Registry دیگر push کنید:

```powershell
# در سیستم مبدا: Build و Tag
docker compose build
docker tag budgets-web:latest your-registry/budgets-web:latest
docker push your-registry/budgets-web:latest
```

```bash
# در سرور: Pull و اجرا
docker pull your-registry/budgets-web:latest
# تغییر docker-compose.yml برای استفاده از image
docker compose up -d
```

---

## 📋 چک‌لیست انتقال

### قبل از انتقال

- [ ] فایل‌های `secrets/*.txt` وجود دارند و پر هستند
- [ ] فایل `.env` تنظیم شده است (یا `env.example` موجود است)
- [ ] فایل‌های Docker (`Dockerfile`, `docker-compose.yml`) موجود هستند
- [ ] `requirements.txt` به‌روز است
- [ ] فایل‌های `.gitignore` درست تنظیم شده‌اند
- [ ] Docker در سیستم مقصد نصب است

### فایل‌های ضروری برای انتقال

```
BudgetsSystem/
├── BudgetsSystem/          # پوشه اصلی Django
├── accounts/               # اپلیکیشن‌های Django
├── budgets/
├── core/
├── templates/              # تمپلیت‌ها
├── static/                 # فایل‌های استاتیک
├── media/                  # فایل‌های رسانه (اختیاری برای انتقال)
├── docker/                 # اسکریپت‌های Docker
│   ├── entrypoint.sh
│   ├── healthcheck.sh
│   └── init-db.sh
├── docker-scripts/         # اسکریپت‌های PowerShell/Bash
├── nginx/                  # تنظیمات Nginx
├── secrets/                # ⚠ فایل‌های حساس (حتمی!)
│   ├── db_password.txt
│   ├── redis_password.txt
│   └── django_secret_key.txt
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
├── .env                    # یا env.example
└── .gitignore
```

### فایل‌هایی که نباید منتقل شوند

- `venv/` - Virtual environment (در Docker rebuild می‌شود)
- `__pycache__/` - Python cache
- `node_modules/` - Node modules (اگر وجود دارد)
- `.git/` - Git history (مگر اینکه از Git استفاده می‌کنید)
- `*.pyc` - Compiled Python files
- `logs/*.log` - فایل‌های لاگ قدیمی
- `db.sqlite3` - دیتابیس SQLite (اگر استفاده می‌کنید)

---

## 🔧 اسکریپت‌های کمکی

### اسکریپت ایجاد پکیج انتقال (Windows)

ایجاد `docker-scripts/create-transfer-package.ps1`:

```powershell
# ایجاد پکیج برای انتقال
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$excludeItems = @("venv", "__pycache__", "*.pyc", ".git", "node_modules", "*.log")

Get-ChildItem -Path $projectRoot -Exclude $excludeItems |
    Compress-Archive -DestinationPath "BudgetsSystem-Transfer-$(Get-Date -Format 'yyyyMMdd-HHmmss').zip"
```

### اسکریپت راه‌اندازی در Linux

ایجاد `docker-scripts/setup-linux.sh`:

```bash
#!/bin/bash
# اسکریپت راه‌اندازی در Linux

echo "🔧 راه‌اندازی Budgets System در Linux..."

# بررسی Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker نصب نشده است!"
    exit 1
fi

# بررسی فایل‌های secrets
if [ ! -d "secrets" ]; then
    echo "📁 ایجاد پوشه secrets..."
    mkdir -p secrets
fi

# بررسی فایل‌های secrets
for secret in db_password.txt redis_password.txt django_secret_key.txt; do
    if [ ! -f "secrets/$secret" ]; then
        echo "⚠ فایل secrets/$secret پیدا نشد. لطفاً ایجاد کنید."
        exit 1
    fi
done

# محدود کردن دسترسی
chmod 600 secrets/*.txt
chmod 700 secrets

# اجرای Docker
echo "🚀 اجرای Docker..."
docker compose up -d --build

echo "✅ راه‌اندازی کامل شد!"
```

---

## 🆘 Troubleshooting

### مشکل: Docker نمی‌تواند فایل‌های secrets را بخواند

**راه حل:**

```bash
# بررسی دسترسی فایل‌ها
ls -la secrets/

# تنظیم دسترسی صحیح
chmod 600 secrets/*.txt
chmod 700 secrets
```

### مشکل: خطا در اتصال به دیتابیس

**راه حل:**

```bash
# بررسی وضعیت سرویس‌ها
docker compose ps

# بررسی لاگ دیتابیس
docker compose logs db

# بررسی شبکه Docker
docker network ls
docker network inspect budgets_budgets_network
```

### مشکل: پورت در حال استفاده است

**راه حل:**

```bash
# بررسی پورت‌های استفاده شده
netstat -tulpn | grep :8000

# تغییر پورت در docker-compose.yml
# ports:
#   - "8001:8000"  # تغییر پورت خارجی
```

### مشکل: فایل‌های static جمع‌آوری نمی‌شوند

**راه حل:**

```bash
# اجرای دستی collectstatic
docker compose exec web python manage.py collectstatic --noinput
```

---

## 📞 دستورات مفید

### بررسی وضعیت

```bash
# وضعیت کانتینرها
docker compose ps

# استفاده از منابع
docker stats

# لاگ‌ها
docker compose logs -f
docker compose logs -f web
```

### مدیریت دیتابیس

```bash
# Backup دیتابیس
docker compose exec db mysqldump -u root -p budgets_db > backup.sql

# Restore دیتابیس
docker compose exec -T db mysql -u root -p budgets_db < backup.sql
```

### دسترسی به Shell

```bash
# دسترسی به کانتینر web
docker compose exec web bash

# دسترسی به کانتینر db
docker compose exec db mysql -u root -p
```

---

## ✅ چک‌لیست نهایی

بعد از انتقال، این موارد را بررسی کنید:

- [ ] تمام سرویس‌ها در حال اجرا هستند (`docker compose ps`)
- [ ] اپلیکیشن در مرورگر باز می‌شود
- [ ] دیتابیس به درستی کار می‌کند
- [ ] فایل‌های static بارگذاری می‌شوند
- [ ] لاگ‌ها خطایی نشان نمی‌دهند
- [ ] Health checks موفق هستند

---

## 📚 منابع بیشتر

- [راهنمای Docker Deployment](./DOCKER_DEPLOYMENT_GUIDE.md)
- [راهنمای امنیت Secrets](./SECURITY_SECRETS_GUIDE.md)
- [راهنمای سریع فارسی](./RESUMEN_FA_SECRETS.md)
