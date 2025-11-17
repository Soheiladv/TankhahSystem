# اسکریپت تنظیم فایل .env
# این اسکریپت فایل .env را ایجاد و تنظیم می‌کند

Write-Host "=== تنظیم فایل .env ===" -ForegroundColor Green

# تغییر به دایرکتوری اصلی پروژه
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# بررسی وجود env.example
if (!(Test-Path "env.example")) {
    Write-Host "✗ فایل env.example یافت نشد" -ForegroundColor Red
    exit 1
}

# ایجاد SECRET_KEY
Write-Host "🔑 ایجاد SECRET_KEY..." -ForegroundColor Yellow
try {
    $secretKey = python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠ خطا در ایجاد SECRET_KEY، استفاده از مقدار پیش‌فرض" -ForegroundColor Yellow
        $secretKey = "django-insecure-change-this-in-production-" + (New-Guid).ToString()
    }
    $secretKey = $secretKey.Trim()
    Write-Host "✓ SECRET_KEY ایجاد شد" -ForegroundColor Green
}
catch {
    Write-Host "⚠ خطا در ایجاد SECRET_KEY، استفاده از مقدار پیش‌فرض" -ForegroundColor Yellow
    $secretKey = "django-insecure-change-this-in-production-" + (New-Guid).ToString()
}

# ایجاد رمزهای عبور
$dbPassword = "BudgetsDB2024!SecurePass#$(Get-Random -Minimum 1000 -Maximum 9999)"
$redisPassword = "BudgetsRedis2024!SecurePass#$(Get-Random -Minimum 1000 -Maximum 9999)"

# کپی از env.example
if (Test-Path ".env") {
    Write-Host "⚠ فایل .env از قبل وجود دارد" -ForegroundColor Yellow
    $backup = Read-Host "آیا می‌خواهید از فایل موجود backup بگیرید؟ (y/N)"
    if ($backup -eq "y" -or $backup -eq "Y") {
        $backupFile = ".env.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item ".env" $backupFile
        Write-Host "✓ Backup در $backupFile ایجاد شد" -ForegroundColor Green
    }
}

# خواندن فایل env.example
$envContent = Get-Content "env.example" -Raw

# جایگزینی مقادیر
Write-Host "📝 تنظیم مقادیر..." -ForegroundColor Yellow

# SECRET_KEY
$envContent = $envContent -replace "SECRET_KEY=your-super-secret-key-here-change-this-immediately", "SECRET_KEY=$secretKey"

# DB_PASSWORD
$envContent = $envContent -replace "DB_PASSWORD=your-strong-database-password-here", "DB_PASSWORD=$dbPassword"

# REDIS_PASSWORD
$envContent = $envContent -replace "REDIS_PASSWORD=your-strong-redis-password-here", "REDIS_PASSWORD=$redisPassword"

# DEBUG برای development
$envContent = $envContent -replace "DEBUG=False", "DEBUG=True"

# ALLOWED_HOSTS برای development
$envContent = $envContent -replace "ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com", "ALLOWED_HOSTS=localhost,127.0.0.1"

# CORS برای development
$envContent = $envContent -replace "CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com", "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080"

# SSL برای development (غیرفعال)
$envContent = $envContent -replace "SSL_ENABLED=True", "SSL_ENABLED=False"

# SESSION_COOKIE_SECURE برای development (غیرفعال)
$envContent = $envContent -replace "SESSION_COOKIE_SECURE=True", "SESSION_COOKIE_SECURE=False"
$envContent = $envContent -replace "SESSION_COOKIE_SAMESITE=Strict", "SESSION_COOKIE_SAMESITE=Lax"

# CSRF_COOKIE_SECURE برای development (غیرفعال)
$envContent = $envContent -replace "CSRF_COOKIE_SECURE=True", "CSRF_COOKIE_SECURE=False"
$envContent = $envContent -replace "CSRF_COOKIE_SAMESITE=Strict", "CSRF_COOKIE_SAMESITE=Lax"

# نوشتن فایل .env
$envContent | Set-Content ".env" -Encoding UTF8
Write-Host "✓ فایل .env ایجاد شد" -ForegroundColor Green

Write-Host "" -ForegroundColor White
Write-Host "✅ تنظیمات انجام شد:" -ForegroundColor Green
Write-Host "  • SECRET_KEY: تنظیم شد" -ForegroundColor White
Write-Host "  • DB_PASSWORD: $dbPassword" -ForegroundColor White
Write-Host "  • REDIS_PASSWORD: $redisPassword" -ForegroundColor White
Write-Host "  • DEBUG: True (برای development)" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "⚠️  نکته: این رمزهای عبور برای development هستند." -ForegroundColor Yellow
Write-Host "   برای production، حتماً رمزهای عبور قوی‌تر و منحصر به فرد تنظیم کنید." -ForegroundColor Yellow
Write-Host "" -ForegroundColor White

