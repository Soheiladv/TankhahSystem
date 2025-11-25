# 🔐 راهنمای امنیتی: مدیریت رمزها و پسوردها

## 📍 مکان فعلی رمزها در سیستم

رمزها و پسوردهای سیستم در پوشه `secrets/` ذخیره شده‌اند:

```
secrets/
├── db_password.txt          # رمز دیتابیس MySQL
├── redis_password.txt       # رمز Redis
└── django_secret_key.txt    # کلید مخفی Django (SECRET_KEY)
```

### چگونگی استفاده در Docker

این فایل‌ها از طریق Docker Secrets به کانتینرها منتقل می‌شوند:

1. **در `docker-compose.yml`:**

   ```yaml
   secrets:
     db_password:
       file: ./secrets/db_password.txt
     redis_password:
       file: ./secrets/redis_password.txt
     django_secret_key:
       file: ./secrets/django_secret_key.txt
   ```

2. **داخل کانتینرها:**
   - فایل‌ها در مسیر `/run/secrets/` قرار می‌گیرند
   - از طریق متغیرهای محیطی `*_FILE` قابل دسترسی هستند
   - هیچ‌گاه در لاگ‌ها یا environment variables نمایش داده نمی‌شوند

---

## 🖥️ مخفی کردن رمزها در Windows (سیستم محلی)

### روش 1: تنظیم دسترسی فایل‌ها (توصیه می‌شود)

```powershell
# محدود کردن دسترسی فقط به کاربر جاری
icacls "secrets\*.txt" /inheritance:r
icacls "secrets\*.txt" /grant:r "%USERNAME%:F"

# حذف دسترسی از گروه Everyone
icacls "secrets\*.txt" /remove "Everyone"
icacls "secrets\*.txt" /remove "Users"
icacls "secrets\*.txt" /remove "Authenticated Users"
```

### روش 2: استفاده از متغیرهای محیطی سیستم

می‌توانید رمزها را در متغیرهای محیطی Windows ذخیره کنید:

```powershell
# تنظیم متغیرهای محیطی کاربر (فقط برای کاربر جاری)
[System.Environment]::SetEnvironmentVariable("DB_PASSWORD", "your_secure_password", [System.EnvironmentVariableTarget]::User)
[System.Environment]::SetEnvironmentVariable("REDIS_PASSWORD", "your_redis_password", [System.EnvironmentVariableTarget]::User)
[System.Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", "your_secret_key", [System.EnvironmentVariableTarget]::User)

# خواندن متغیرها
$env:DB_PASSWORD
```

سپس فایل‌های `secrets/*.txt` را از روی دیسک حذف کنید و از متغیرهای محیطی استفاده کنید.

### روش 3: استفاده از Windows Credential Manager

```powershell
# نصب ماژول CredentialManager (یک بار)
Install-Module -Name CredentialManager -Force

# ذخیره رمزها
Set-StoredCredential -Target "BudgetsSystem_DB" -UserName "db_user" -Password "your_db_password" -Persist LocalMachine
Set-StoredCredential -Target "BudgetsSystem_Redis" -UserName "redis" -Password "your_redis_password" -Persist LocalMachine

# خواندن رمزها
$dbCred = Get-StoredCredential -Target "BudgetsSystem_DB"
$dbPassword = $dbCred.Password
```

### روش 4: رمزنگاری فایل‌های secrets

```powershell
# رمزنگاری فایل با Windows EFS
cipher /e /a secrets\*.txt

# یا استفاده از PowerShell برای رمزنگاری
$secureString = Read-Host "Enter password" -AsSecureString
$encrypted = ConvertFrom-SecureString $secureString
Set-Content -Path "secrets\db_password.encrypted" -Value $encrypted

# رمزگشایی
$encrypted = Get-Content "secrets\db_password.encrypted"
$secureString = ConvertTo-SecureString $encrypted
$password = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureString))
```

### روش 5: استفاده از فایل‌های محافظت شده (Protected Files)

```powershell
# ساخت فایل محافظت شده
$password = "your_password" | ConvertTo-SecureString -AsPlainText -Force
$password | Export-Clixml -Path "secrets\db_password.xml"

# خواندن فایل محافظت شده (فقط در همان سیستم و با همان کاربر)
$password = Import-Clixml -Path "secrets\db_password.xml"
$plainText = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($password))
```

---

## 🐧 مخفی کردن رمزها در Linux (سرور)

### روش 1: تنظیم دسترسی فایل‌ها (روش استاندارد)

```bash
# محدود کردن دسترسی فقط به مالک فایل
chmod 600 secrets/*.txt

# فقط مالک و گروه خاص
chmod 640 secrets/*.txt
chgrp docker secrets/*.txt

# اطمینان از اینکه فقط root یا کاربر خاص دسترسی دارد
sudo chown root:docker secrets/*.txt
sudo chmod 600 secrets/*.txt
```

### روش 2: استفاده از متغیرهای محیطی سیستم

```bash
# اضافه کردن به ~/.bashrc یا ~/.profile (برای کاربر خاص)
export DB_PASSWORD="your_secure_password"
export REDIS_PASSWORD="your_redis_password"
export DJANGO_SECRET_KEY="your_secret_key"

# یا برای تمام کاربران سیستم در /etc/environment
sudo nano /etc/environment
# اضافه کردن:
# DB_PASSWORD="your_secure_password"
# REDIS_PASSWORD="your_redis_password"

# برای systemd service
sudo systemctl edit docker
# اضافه کردن:
# [Service]
# Environment="DB_PASSWORD=your_secure_password"
```

### روش 3: استفاده از Docker Secrets (برای Production)

```bash
# ایجاد Docker Secret
echo "your_db_password" | docker secret create db_password -
echo "your_redis_password" | docker secret create redis_password -
echo "your_secret_key" | docker secret create django_secret_key -

# استفاده در docker-compose.yml
# secrets:
#   db_password:
#     external: true
```

### روش 4: استفاده از Keychain/Keyring

```bash
# نصب secret-tool (معمولاً پیش‌نصب است)
# ذخیره رمز
secret-tool store --label="DB Password" service budgets-system key db_password

# خواندن رمز
DB_PASSWORD=$(secret-tool lookup service budgets-system key db_password)
```

### روش 5: استفاده از HashiCorp Vault

```bash
# نصب Vault
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo apt-get update && sudo apt-get install vault

# راه‌اندازی Vault
vault server -dev

# ذخیره رمزها
vault kv put secret/budgetssystem db_password="your_password" redis_password="your_password"

# خواندن
vault kv get secret/budgetssystem
```

---

## 🔒 بهترین روش‌های امنیتی

### 1. برای محیط Development (لوکال)

✅ **توصیه می‌شود:**

- استفاده از فایل‌های `secrets/*.txt` با دسترسی محدود
- اضافه کردن `secrets/` به `.gitignore` (✅ انجام شده)
- استفاده از متغیرهای محیطی کاربر (نه سیستم)

```powershell
# Windows
# محدود کردن دسترسی
icacls "secrets" /inheritance:r
icacls "secrets" /grant:r "%USERNAME%:F"
```

```bash
# Linux
chmod 700 secrets
chmod 600 secrets/*.txt
```

### 2. برای محیط Production (سرور)

✅ **توصیه می‌شود:**

- استفاده از Docker Secrets (external)
- یا متغیرهای محیطی systemd
- یا Vault برای رمزهای حساس
- **هرگز** فایل‌های secrets را در Git commit نکنید

### 3. نکات مهم امنیتی

1. **همیشه دسترسی فایل‌های secrets را محدود کنید:**

   ```bash
   # Linux
   chmod 600 secrets/*.txt
   chown root:root secrets/*.txt

   # Windows
   icacls "secrets\*.txt" /inheritance:r /grant:r "%USERNAME%:F"
   ```

2. **بررسی کنید که فایل‌های secrets در Git نباشند:**

   ```bash
   git ls-files secrets/
   # نباید هیچ فایلی نمایش دهد
   ```

3. **از رمزهای قوی استفاده کنید:**

   - حداقل 16 کاراکتر
   - ترکیبی از حروف بزرگ، کوچک، اعداد و کاراکترهای خاص
   - استفاده از Password Generator

4. **رمزها را به صورت دوره‌ای تغییر دهید:**
   - هر 90 روز یک بار
   - پس از هر حادثه امنیتی

---

## 📝 نمونه اسکریپت‌های امنیتی

### اسکریپت PowerShell برای Windows (ایمن‌سازی خودکار)

```powershell
# secure-secrets.ps1
$secretsPath = "secrets"

# بررسی وجود پوشه
if (Test-Path $secretsPath) {
    Write-Host "🔒 محدود کردن دسترسی به فایل‌های secrets..." -ForegroundColor Yellow

    # حذف دسترسی‌های ارثی
    icacls "$secretsPath\*.txt" /inheritance:r 2>$null

    # فقط دسترسی کاربر جاری
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    icacls "$secretsPath\*.txt" /grant:r "${currentUser}:F" 2>$null

    # حذف دسترسی‌های عمومی
    icacls "$secretsPath\*.txt" /remove "Everyone" 2>$null
    icacls "$secretsPath\*.txt" /remove "Users" 2>$null
    icacls "$secretsPath\*.txt" /remove "Authenticated Users" 2>$null

    Write-Host "✅ دسترسی‌ها محدود شد" -ForegroundColor Green
} else {
    Write-Host "⚠ پوشه secrets پیدا نشد" -ForegroundColor Red
}

# بررسی Git
Write-Host "`n🔍 بررسی Git..." -ForegroundColor Yellow
$trackedSecrets = git ls-files secrets/ 2>$null
if ($trackedSecrets) {
    Write-Host "⚠ هشدار: فایل‌های secrets در Git track شده‌اند:" -ForegroundColor Red
    $trackedSecrets | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nلطفاً آن‌ها را از Git حذف کنید:" -ForegroundColor Yellow
    Write-Host "  git rm --cached secrets/*.txt" -ForegroundColor Cyan
} else {
    Write-Host "✅ هیچ فایل secret در Git track نشده است" -ForegroundColor Green
}
```

### اسکریپت Bash برای Linux (ایمن‌سازی خودکار)

```bash
#!/bin/bash
# secure-secrets.sh

SECRETS_DIR="secrets"

echo "🔒 محدود کردن دسترسی به فایل‌های secrets..."

if [ -d "$SECRETS_DIR" ]; then
    # محدود کردن دسترسی پوشه
    chmod 700 "$SECRETS_DIR"

    # محدود کردن دسترسی فایل‌ها
    find "$SECRETS_DIR" -type f -name "*.txt" -exec chmod 600 {} \;

    # تغییر مالکیت (اگر root هستید)
    if [ "$EUID" -eq 0 ]; then
        chown root:root "$SECRETS_DIR"/*.txt
        chmod 600 "$SECRETS_DIR"/*.txt
    fi

    echo "✅ دسترسی‌ها محدود شد"
else
    echo "⚠ پوشه $SECRETS_DIR پیدا نشد"
fi

# بررسی Git
echo ""
echo "🔍 بررسی Git..."
TRACKED_SECRETS=$(git ls-files secrets/ 2>/dev/null)
if [ -n "$TRACKED_SECRETS" ]; then
    echo "⚠ هشدار: فایل‌های secrets در Git track شده‌اند:"
    echo "$TRACKED_SECRETS"
    echo ""
    echo "لطفاً آن‌ها را از Git حذف کنید:"
    echo "  git rm --cached secrets/*.txt"
else
    echo "✅ هیچ فایل secret در Git track نشده است"
fi
```

---

## 🔄 تبدیل به متغیرهای محیطی سیستم عامل

### در Windows:

اگر می‌خواهید به جای فایل‌ها از متغیرهای محیطی استفاده کنید:

```powershell
# خواندن از فایل‌ها و تنظیم متغیرهای محیطی
$dbPassword = Get-Content "secrets\db_password.txt" -Raw
$redisPassword = Get-Content "secrets\redis_password.txt" -Raw
$secretKey = Get-Content "secrets\django_secret_key.txt" -Raw

# تنظیم متغیرهای محیطی کاربر
[System.Environment]::SetEnvironmentVariable("DB_PASSWORD", $dbPassword.Trim(), "User")
[System.Environment]::SetEnvironmentVariable("REDIS_PASSWORD", $redisPassword.Trim(), "User")
[System.Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", $secretKey.Trim(), "User")

# حذف فایل‌ها (اختیاری)
Remove-Item "secrets\*.txt" -Force

# استفاده در docker-compose.yml
# environment:
#   DB_PASSWORD: ${DB_PASSWORD}
```

### در Linux:

```bash
# خواندن از فایل‌ها و تنظیم متغیرهای محیطی
export DB_PASSWORD=$(cat secrets/db_password.txt | tr -d '\r\n')
export REDIS_PASSWORD=$(cat secrets/redis_password.txt | tr -d '\r\n')
export DJANGO_SECRET_KEY=$(cat secrets/django_secret_key.txt | tr -d '\r\n')

# ذخیره در ~/.bashrc یا ~/.profile
cat >> ~/.bashrc << EOF
export DB_PASSWORD="$DB_PASSWORD"
export REDIS_PASSWORD="$REDIS_PASSWORD"
export DJANGO_SECRET_KEY="$DJANGO_SECRET_KEY"
EOF

source ~/.bashrc
```

---

## ✅ چک‌لیست امنیتی

- [ ] فایل‌های `secrets/*.txt` در `.gitignore` هستند ✅
- [ ] دسترسی فایل‌ها محدود شده (600 در Linux، فقط مالک در Windows)
- [ ] فایل‌های secrets در Git commit نشده‌اند
- [ ] رمزها قوی هستند (حداقل 16 کاراکتر، ترکیبی)
- [ ] رمزها به صورت دوره‌ای تغییر می‌کنند
- [ ] در Production از Docker Secrets یا Vault استفاده می‌شود
- [ ] لاگ‌ها حاوی رمز نیستند
- [ ] دسترسی SSH به سرور امن است

---

## 🆘 در صورت لو رفتن رمز

1. **فوری رمزها را تغییر دهید:**

   ```bash
   # اجرای اسکریپت setup-secrets.ps1 یا setup-secrets.sh
   ```

2. **بررسی لاگ‌ها برای دسترسی غیرمجاز**

3. **تغییر رمز در دیتابیس:**

   ```sql
   ALTER USER 'budgets_user'@'%' IDENTIFIED BY 'new_secure_password';
   FLUSH PRIVILEGES;
   ```

4. **راه‌اندازی مجدد سرویس‌ها:**
   ```bash
   docker compose down
   docker compose up -d
   ```

---

## 📞 پشتیبانی

برای سوالات امنیتی بیشتر، به فایل `docs/DOCKER_DEPLOYMENT_GUIDE.md` مراجعه کنید.
