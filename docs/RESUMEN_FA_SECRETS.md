# 🔐 راهنمای سریع: مخفی کردن رمزها در Windows

## 📍 کجا رمزها مخفی شده‌اند؟

رمزها و پسوردهای سیستم **در پوشه `secrets/`** در ریشه پروژه ذخیره شده‌اند:

```
BudgetsSystem/
└── secrets/
    ├── db_password.txt          # رمز دیتابیس MySQL
    ├── redis_password.txt       # رمز Redis
    └── django_secret_key.txt    # کلید مخفی Django (SECRET_KEY)
```

✅ **خبر خوب:** این فایل‌ها در `.gitignore` هستند و در Git commit نمی‌شوند.

---

## 🖥️ مخفی کردن رمزها در Windows (محلی - Development)

### ⚡ روش سریع: استفاده از اسکریپت آماده

اسکریپت `secure-secrets.ps1` آماده است و فقط باید اجرا شود:

```powershell
cd docker-scripts
.\secure-secrets.ps1
```

این اسکریپت به صورت خودکار:

- ✅ دسترسی فایل‌ها را فقط به شما محدود می‌کند
- ✅ دسترسی عمومی را حذف می‌کند
- ✅ بررسی می‌کند که فایل‌ها در Git track نشده‌اند

---

### 🔧 روش دستی: محدود کردن دسترسی فایل‌ها

اگر می‌خواهید دستی انجام دهید:

```powershell
# رفتن به پوشه پروژه
cd "D:\Design & Source Code\Source Coding\BudgetsSystem"

# محدود کردن دسترسی فقط به کاربر جاری
icacls "secrets\*.txt" /inheritance:r
icacls "secrets\*.txt" /grant:r "$env:USERNAME:F"

# حذف دسترسی از گروه‌های عمومی
icacls "secrets\*.txt" /remove "Everyone"
icacls "secrets\*.txt" /remove "Users"
icacls "secrets\*.txt" /remove "Authenticated Users"
icacls "secrets\*.txt" /remove "BUILTIN\Users"

# محدود کردن دسترسی پوشه secrets هم
icacls "secrets" /inheritance:r
icacls "secrets" /grant:r "$env:USERNAME:F"
```

---

### 🔐 روش پیشرفته: استفاده از متغیرهای محیطی Windows

اگر می‌خواهید فایل‌ها را از روی دیسک حذف کنید و در متغیرهای محیطی نگه دارید:

#### گام 1: خواندن رمزها از فایل‌ها و ذخیره در متغیرهای محیطی

```powershell
# خواندن رمزها از فایل‌ها
$dbPassword = (Get-Content "secrets\db_password.txt" -Raw).Trim()
$redisPassword = (Get-Content "secrets\redis_password.txt" -Raw).Trim()
$secretKey = (Get-Content "secrets\django_secret_key.txt" -Raw).Trim()

# ذخیره در متغیرهای محیطی کاربر (فقط برای کاربر جاری)
[System.Environment]::SetEnvironmentVariable("DB_PASSWORD", $dbPassword, [System.EnvironmentVariableTarget]::User)
[System.Environment]::SetEnvironmentVariable("REDIS_PASSWORD", $redisPassword, [System.EnvironmentVariableTarget]::User)
[System.Environment]::SetEnvironmentVariable("DJANGO_SECRET_KEY", $secretKey, [System.EnvironmentVariableTarget]::User)

# تایید
Write-Host "✅ رمزها در متغیرهای محیطی ذخیره شدند"
```

#### گام 2: حذف فایل‌های secrets (اختیاری)

```powershell
# پشتیبان‌گیری قبل از حذف
Copy-Item -Path "secrets" -Destination "secrets_backup" -Recurse

# حذف فایل‌های secrets (اگر مطمئن هستید)
Remove-Item "secrets\*.txt" -Force
```

#### گام 3: تغییر docker-compose.yml برای استفاده از متغیرهای محیطی

```yaml
secrets:
  db_password:
    file: ${DB_PASSWORD_SECRET_FILE:-./secrets/db_password.txt}
  # یا اگر از متغیر محیطی استفاده می‌کنید:
  # environment:
  #   DB_PASSWORD: ${DB_PASSWORD}
```

---

## 🐳 اطمینان از امنیت Docker

### ✅ بررسی کنید که Docker به فایل‌های secrets دسترسی دارد

Docker از Docker Secrets استفاده می‌کند که امن است:

```yaml
# در docker-compose.yml
secrets:
  db_password:
    file: ./secrets/db_password.txt
```

این به این معنی است:

- ✅ رمزها در داخل کانتینر در `/run/secrets/` قرار می‌گیرند
- ✅ رمزها در environment variables نمایش داده نمی‌شوند
- ✅ رمزها در لاگ‌ها نمایش داده نمی‌شوند

### ⚠️ نکات مهم برای Docker:

1. **هرگز رمزها را در docker-compose.yml به صورت plain text ننویسید**

   ```yaml
   # ❌ اشتباه
   environment:
     DB_PASSWORD: "my_password_123"

   # ✅ درست
   environment:
     DB_PASSWORD_FILE: /run/secrets/db_password
   ```

2. **فایل‌های secrets را فقط برای مالک قابل خواندن کنید:**

   ```powershell
   icacls "secrets\*.txt" /inheritance:r /grant:r "$env:USERNAME:R"
   ```

3. **بررسی کنید که فایل‌های secrets در Git track نشده‌اند:**
   ```powershell
   git ls-files secrets/
   # نباید چیزی نمایش دهد
   ```

---

## 🏠 تنظیمات لوکال (Development)

### برای محیط Development (لوکال)

**توصیه می‌شود:**

- ✅ استفاده از فایل‌های `secrets/*.txt` با دسترسی محدود
- ✅ اجرای اسکریپت `secure-secrets.ps1` برای محدود کردن دسترسی
- ✅ استفاده از `.env` برای تنظیمات غیر حساس

### ساختار پیشنهادی برای Development:

```
BudgetsSystem/
├── secrets/                    # فایل‌های حساس (در .gitignore)
│   ├── db_password.txt        # فقط مالک قابل خواندن
│   ├── redis_password.txt     # فقط مالک قابل خواندن
│   └── django_secret_key.txt  # فقط مالک قابل خواندن
├── .env                       # تنظیمات غیر حساس (در .gitignore)
├── docker-compose.yml         # استفاده از Docker Secrets
└── .gitignore                 # شامل secrets/*.txt
```

---

## 🔒 چک‌لیست امنیتی

قبل از ادامه کار، این موارد را بررسی کنید:

- [ ] فایل‌های `secrets/*.txt` وجود دارند
- [ ] دسترسی فایل‌ها محدود شده (فقط شما)
- [ ] فایل‌های secrets در `.gitignore` هستند
- [ ] فایل‌های secrets در Git track نشده‌اند (`git ls-files secrets/`)
- [ ] Docker Secrets در `docker-compose.yml` تنظیم شده
- [ ] رمزها قوی هستند (حداقل 16 کاراکتر)

---

## 🚀 دستورات سریع

### محدود کردن دسترسی (Windows):

```powershell
.\docker-scripts\secure-secrets.ps1
```

### بررسی دسترسی‌های فعلی:

```powershell
icacls "secrets\*.txt"
```

### بررسی Git tracking:

```powershell
git ls-files secrets/
```

### خواندن رمز از متغیر محیطی:

```powershell
$env:DB_PASSWORD
```

---

## 📞 کمک بیشتر

- راهنمای کامل: `docs/SECURITY_SECRETS_GUIDE.md`
- راهنمای Docker: `docs/DOCKER_DEPLOYMENT_GUIDE.md`
- اسکریپت امنیت‌سازی: `docker-scripts/secure-secrets.ps1`

---

## ⚠️ هشدار امنیتی

**هرگز:**

- ❌ فایل‌های secrets را در Git commit نکنید
- ❌ رمزها را در کد hardcode نکنید
- ❌ رمزها را در لاگ‌ها نمایش ندهید
- ❌ رمزها را از طریق ایمیل یا پیام ارسال نکنید

**همیشه:**

- ✅ از Docker Secrets استفاده کنید
- ✅ دسترسی فایل‌ها را محدود کنید
- ✅ رمزهای قوی استفاده کنید
- ✅ رمزها را به صورت دوره‌ای تغییر دهید
