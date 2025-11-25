# 📋 خلاصه تنظیمات Docker

## ✅ کارهای انجام شده

### 1. بررسی و اصلاح فایل‌ها

- ✅ **entrypoint.sh**: اصلاح شد تا از Docker Secrets به درستی استفاده کند
- ✅ **Dockerfile**: بررسی شد و مشکلی ندارد
- ✅ **docker-compose.yml**: بررسی شد و پیکربندی صحیح است

### 2. اسکریپت‌های PowerShell ایجاد شده

#### `check-docker-setup.ps1`

- بررسی نصب Docker
- بررسی فایل‌های secrets
- بررسی فایل .env
- بررسی فایل‌های Docker
- بررسی پورت‌های استفاده شده

**استفاده:**

```powershell
.\docker-scripts\check-docker-setup.ps1
.\docker-scripts\check-docker-setup.ps1 -Fix  # رفع مشکلات خودکار
```

#### `run-docker.ps1`

- بررسی پیش‌نیازها
- توقف کانتینرهای قبلی
- ساخت image
- راه‌اندازی سرویس‌ها
- بررسی سلامت سرویس‌ها

**استفاده:**

```powershell
.\docker-scripts\run-docker.ps1
.\docker-scripts\run-docker.ps1 -SkipCheck  # بدون بررسی اولیه
```

#### `create-transfer-package.ps1`

- ایجاد پکیج ZIP برای انتقال
- حذف فایل‌های غیرضروری
- شامل کردن فایل‌های لازم

**استفاده:**

```powershell
.\docker-scripts\create-transfer-package.ps1
```

### 3. اسکریپت‌های Linux ایجاد شده

#### `setup-linux.sh`

- بررسی Docker و Docker Compose
- بررسی فایل‌های secrets
- محدود کردن دسترسی
- بررسی پیش‌نیازها

**استفاده:**

```bash
chmod +x docker-scripts/setup-linux.sh
./docker-scripts/setup-linux.sh
```

### 4. مستندات ایجاد شده

- ✅ **DOCKER_TRANSFER_GUIDE.md**: راهنمای کامل انتقال به سیستم دیگر
- ✅ **DOCKER_QUICK_START_FA.md**: راهنمای سریع اجرا
- ✅ **RESUMEN_FA_SECRETS.md**: راهنمای مدیریت Secrets (از قبل)
- ✅ **DOCKER_SETUP_SUMMARY.md**: این فایل (خلاصه تنظیمات)

---

## 🚀 نحوه اجرا

### روش سریع (توصیه می‌شود)

```powershell
# 1. بررسی و آماده‌سازی
.\docker-scripts\check-docker-setup.ps1 -Fix

# 2. اجرای Docker
.\docker-scripts\run-docker.ps1
```

### روش دستی

```powershell
# 1. بررسی فایل‌های secrets
dir secrets\*.txt

# 2. Build و Run
docker compose up -d --build

# 3. بررسی وضعیت
docker compose ps

# 4. مشاهده لاگ‌ها
docker compose logs -f
```

---

## 📦 نحوه انتقال به سیستم دیگر

### از Windows به Windows

1. **ایجاد پکیج:**

   ```powershell
   .\docker-scripts\create-transfer-package.ps1
   ```

2. **انتقال فایل ZIP** به سیستم مقصد

3. **Extract** و اجرا:
   ```powershell
   .\docker-scripts\check-docker-setup.ps1 -Fix
   .\docker-scripts\run-docker.ps1
   ```

### از Windows به Linux

1. **استفاده از Git** (بهترین روش):

   ```bash
   git clone <repository-url>
   cd BudgetsSystem
   ./docker-scripts/setup-linux.sh
   docker compose up -d --build
   ```

2. **انتقال مستقیم:**
   - ایجاد ZIP در Windows
   - انتقال و Extract در Linux
   - اجرای `setup-linux.sh`

---

## 🔐 نکات امنیتی

### فایل‌های Secrets

- ✅ فایل‌های secrets در `.gitignore` هستند
- ✅ دسترسی محدود شده (فقط مالک)
- ✅ در Docker از Docker Secrets استفاده می‌شود
- ⚠️ هرگز فایل‌های secrets را در Git commit نکنید

### محدود کردن دسترسی

```powershell
# Windows
.\docker-scripts\secure-secrets.ps1

# Linux
chmod 600 secrets/*.txt
chmod 700 secrets
```

---

## 🗂️ ساختار فایل‌ها

```
BudgetsSystem/
├── docker-scripts/
│   ├── check-docker-setup.ps1      # بررسی پیش‌نیازها
│   ├── run-docker.ps1              # اجرای Docker
│   ├── create-transfer-package.ps1 # ایجاد پکیج انتقال
│   ├── setup-linux.sh              # راه‌اندازی در Linux
│   ├── setup-secrets.ps1           # ایجاد secrets (از قبل)
│   └── secure-secrets.ps1          # محدود کردن دسترسی (از قبل)
├── docker/
│   ├── entrypoint.sh               # اصلاح شده ✅
│   ├── healthcheck.sh
│   └── init-db.sh
├── docs/
│   ├── DOCKER_TRANSFER_GUIDE.md    # راهنمای انتقال
│   ├── DOCKER_QUICK_START_FA.md    # راهنمای سریع
│   ├── RESUMEN_FA_SECRETS.md       # راهنمای Secrets
│   └── DOCKER_SETUP_SUMMARY.md     # این فایل
├── secrets/                         # فایل‌های حساس
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🆘 Troubleshooting

### مشکل: Docker راه نمی‌افتد

```powershell
# بررسی لاگ‌ها
docker compose logs

# بررسی وضعیت
docker compose ps

# بررسی خطاهای Docker
docker info
```

### مشکل: خطای اتصال به دیتابیس

```powershell
# بررسی سلامت دیتابیس
docker compose exec db mysqladmin ping -h localhost -uroot -p

# بررسی شبکه
docker network inspect budgets_budgets_network
```

### مشکل: پورت در حال استفاده است

```powershell
# بررسی پورت
netstat -ano | findstr :8000

# تغییر در docker-compose.yml
# ports:
#   - "8001:8000"
```

---

## 📚 راهنماهای بیشتر

- 📘 [راهنمای سریع اجرا](./DOCKER_QUICK_START_FA.md)
- 📦 [راهنمای انتقال به سیستم دیگر](./DOCKER_TRANSFER_GUIDE.md)
- 🔐 [راهنمای امنیت Secrets](./RESUMEN_FA_SECRETS.md)
- 📖 [راهنمای کامل Deployment](./DOCKER_DEPLOYMENT_GUIDE.md)

---

## ✅ چک‌لیست نهایی

قبل از اجرا:

- [ ] Docker Desktop نصب و در حال اجرا است
- [ ] فایل‌های secrets موجود هستند
- [ ] دسترسی secrets محدود شده
- [ ] فایل .env موجود است (یا env.example)

بعد از اجرا:

- [ ] تمام سرویس‌ها در حال اجرا هستند
- [ ] اپلیکیشن در مرورگر باز می‌شود
- [ ] دیتابیس کار می‌کند
- [ ] لاگ‌ها خطایی ندارند

---

**آماده برای استفاده! 🎉**
