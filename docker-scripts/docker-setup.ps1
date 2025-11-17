# اسکریپت راه‌اندازی اولیه Docker
# این اسکریپت برای راه‌اندازی اولیه پروژه در Docker استفاده می‌شود

param(
    [string]$Environment = "development",
    [switch]$SkipDockerCheck = $false
)

Write-Host "=== اسکریپت راه‌اندازی اولیه Docker ===" -ForegroundColor Green
Write-Host "محیط: $Environment" -ForegroundColor Yellow

# بررسی Docker
if (!$SkipDockerCheck) {
    Write-Host "🔍 بررسی Docker..." -ForegroundColor Yellow

    # بررسی نصب Docker
    try {
        $dockerVersion = docker --version 2>&1
        Write-Host "✓ Docker نصب شده است: $dockerVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker نصب نشده است" -ForegroundColor Red
        Write-Host "لطفاً ابتدا Docker Desktop را نصب کنید:" -ForegroundColor Yellow
        Write-Host "  https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
        exit 1
    }

    # بررسی نصب Docker Compose
    try {
        $composeVersion = docker-compose --version 2>&1
        Write-Host "✓ Docker Compose نصب شده است: $composeVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Docker Compose نصب نشده است" -ForegroundColor Red
        exit 1
    }

    # بررسی اجرای Docker Desktop
    Write-Host "🔍 بررسی Docker Desktop..." -ForegroundColor Yellow
    try {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker Desktop در حال اجرا است" -ForegroundColor Green
        }
        else {
            throw "Docker Desktop is not running"
        }
    }
    catch {
        Write-Host "✗ Docker Desktop در حال اجرا نیست!" -ForegroundColor Red
        Write-Host "" -ForegroundColor Yellow
        Write-Host "⚠️  لطفاً Docker Desktop را باز کنید و منتظر بمانید تا به طور کامل راه‌اندازی شود." -ForegroundColor Yellow
        Write-Host "" -ForegroundColor Yellow
        Write-Host "راه‌حل:" -ForegroundColor Cyan
        Write-Host "  1. Docker Desktop را از منوی Start باز کنید" -ForegroundColor White
        Write-Host "  2. منتظر بمانید تا آیکون Docker در system tray سبز شود" -ForegroundColor White
        Write-Host "  3. سپس این اسکریپت را دوباره اجرا کنید" -ForegroundColor White
        Write-Host "" -ForegroundColor Yellow
        exit 1
    }
}

# تغییر به دایرکتوری اصلی پروژه
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# بررسی فایل‌های ضروری
Write-Host "🔍 بررسی فایل‌های ضروری..." -ForegroundColor Yellow

$requiredFiles = @("docker-compose.yml", "Dockerfile")
foreach ($file in $requiredFiles) {
    if (!(Test-Path $file)) {
        Write-Host "✗ فایل $file یافت نشد" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ $file موجود است" -ForegroundColor Green
}

# بررسی فایل .env
if (!(Test-Path ".env")) {
    Write-Host "⚠ فایل .env یافت نشد" -ForegroundColor Yellow
    if (Test-Path "env.example") {
        Write-Host "📋 کپی کردن از env.example..." -ForegroundColor Cyan
        Copy-Item "env.example" ".env"
        Write-Host "✓ فایل .env ایجاد شد" -ForegroundColor Green
        Write-Host "⚠ لطفاً تنظیمات فایل .env را بررسی کنید" -ForegroundColor Yellow
    }
    else {
        Write-Host "✗ فایل env.example یافت نشد" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "✓ فایل .env موجود است" -ForegroundColor Green

    # بررسی تنظیمات ضروری در .env
    Write-Host "🔍 بررسی تنظیمات فایل .env..." -ForegroundColor Yellow
    $envContent = Get-Content ".env" -Raw
    $issues = @()

    if ($envContent -match "SECRET_KEY=your-super-secret-key-here" -or $envContent -match "SECRET_KEY=$") {
        $issues += "SECRET_KEY تنظیم نشده است"
    }

    if ($envContent -match "DB_PASSWORD=your-strong-database-password-here" -or $envContent -match "DB_PASSWORD=$") {
        $issues += "DB_PASSWORD تنظیم نشده است"
    }

    if ($envContent -match "REDIS_PASSWORD=your-strong-redis-password-here" -or $envContent -match "REDIS_PASSWORD=$") {
        $issues += "REDIS_PASSWORD تنظیم نشده است"
    }

    if ($issues.Count -gt 0) {
        Write-Host "⚠️  مشکلات در فایل .env:" -ForegroundColor Yellow
        foreach ($issue in $issues) {
            Write-Host "  • $issue" -ForegroundColor Red
        }
        Write-Host "" -ForegroundColor Yellow
        Write-Host "لطفاً فایل .env را ویرایش کنید و مقادیر زیر را تنظیم کنید:" -ForegroundColor Yellow
        Write-Host "  - SECRET_KEY (یک کلید منحصر به فرد)" -ForegroundColor White
        Write-Host "  - DB_PASSWORD (رمز عبور دیتابیس)" -ForegroundColor White
        Write-Host "  - REDIS_PASSWORD (رمز عبور Redis)" -ForegroundColor White
        Write-Host "" -ForegroundColor Yellow
        Write-Host "برای ایجاد SECRET_KEY:" -ForegroundColor Cyan
        Write-Host "  python -c `"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`"" -ForegroundColor White
        Write-Host "" -ForegroundColor Yellow
        $continue = Read-Host "آیا می‌خواهید ادامه دهید؟ (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "عملیات لغو شد. لطفاً فایل .env را تنظیم کنید و دوباره تلاش کنید." -ForegroundColor Yellow
            exit 1
        }
    }
    else {
        Write-Host "✓ تنظیمات ضروری .env بررسی شد" -ForegroundColor Green
    }
}

# بررسی فایل‌های Secrets
Write-Host "🔐 بررسی فایل‌های secrets..." -ForegroundColor Yellow
$secretFiles = @(
    @{ Path = "secrets/db_password.txt"; Description = "رمز دیتابیس" },
    @{ Path = "secrets/redis_password.txt"; Description = "رمز Redis" },
    @{ Path = "secrets/django_secret_key.txt"; Description = "SECRET_KEY جنگو" }
)

$missingSecrets = @()
foreach ($secret in $secretFiles) {
    if (!(Test-Path $secret.Path)) {
        $missingSecrets += $secret
    }
}

if ($missingSecrets.Count -eq 0) {
    Write-Host "✓ تمامی secrets موجود هستند" -ForegroundColor Green
}
else {
    Write-Host "⚠ فایل‌های secrets زیر پیدا نشدند:" -ForegroundColor Yellow
    foreach ($item in $missingSecrets) {
        Write-Host "  • $($item.Path) ($($item.Description))" -ForegroundColor Red
    }

    $runSetup = Read-Host "آیا می‌خواهید اسکریپت setup-secrets.ps1 اجرا شود؟ (Y/n)"
    if ($runSetup -eq "" -or $runSetup -eq "y" -or $runSetup -eq "Y") {
        $setupScript = Join-Path $scriptPath "setup-secrets.ps1"
        if (Test-Path $setupScript) {
            & $setupScript
        }
        else {
            Write-Host "✗ اسکریپت setup-secrets.ps1 پیدا نشد!" -ForegroundColor Red
            exit 1
        }
    }
    else {
        Write-Host "✗ بدون secrets ادامه نمی‌توان داد. لطفاً فایل‌ها را ایجاد کنید." -ForegroundColor Red
        exit 1
    }
}

# ایجاد دایرکتوری‌های مورد نیاز
Write-Host "📁 ایجاد دایرکتوری‌های مورد نیاز..." -ForegroundColor Yellow

$directories = @("logs", "backups", "media", "static")
foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "✓ دایرکتوری $dir ایجاد شد" -ForegroundColor Green
    }
    else {
        Write-Host "✓ دایرکتوری $dir موجود است" -ForegroundColor Green
    }
}

# ساخت Docker image ها
Write-Host "🔨 ساخت Docker image ها..." -ForegroundColor Yellow
Write-Host "⏳ این فرآیند ممکن است چند دقیقه طول بکشد..." -ForegroundColor Cyan

try {
    docker-compose build 2>&1 | Tee-Object -Variable buildOutput
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ خطا در ساخت image ها" -ForegroundColor Red
        Write-Host "" -ForegroundColor Yellow
        Write-Host "خطاهای احتمالی:" -ForegroundColor Yellow
        if ($buildOutput -match "Cannot connect to the Docker daemon" -or $buildOutput -match "dockerDesktopLinuxEngine") {
            Write-Host "  • Docker Desktop در حال اجرا نیست" -ForegroundColor Red
            Write-Host "  • لطفاً Docker Desktop را باز کنید و منتظر بمانید تا راه‌اندازی شود" -ForegroundColor Yellow
        }
        elseif ($buildOutput -match "DB_PASSWORD.*not set" -or $buildOutput -match "REDIS_PASSWORD.*not set") {
            Write-Host "  • متغیرهای محیطی در فایل .env تنظیم نشده‌اند" -ForegroundColor Red
            Write-Host "  • لطفاً فایل .env را بررسی و تنظیم کنید" -ForegroundColor Yellow
        }
        exit 1
    }
}
catch {
    Write-Host "✗ خطا در ساخت image ها: $_" -ForegroundColor Red
    Write-Host "لطفاً Docker Desktop را بررسی کنید" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Docker image ها ساخته شدند" -ForegroundColor Green

# اجرای کانتینرها
Write-Host "🚀 اجرای کانتینرها..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ خطا در اجرای کانتینرها" -ForegroundColor Red
    exit 1
}

# انتظار برای راه‌اندازی
Write-Host "⏳ انتظار برای راه‌اندازی سرویس‌ها..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# بررسی وضعیت
Write-Host "🔍 بررسی وضعیت کانتینرها..." -ForegroundColor Yellow
docker-compose ps

# اجرای migrations
Write-Host "🗄️ اجرای migrations..." -ForegroundColor Yellow
docker-compose exec -T web python manage.py migrate

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ خطا در اجرای migrations" -ForegroundColor Yellow
}

# جمع‌آوری فایل‌های static
Write-Host "📦 جمع‌آوری فایل‌های static..." -ForegroundColor Yellow
docker-compose exec -T web python manage.py collectstatic --noinput

if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠ خطا در جمع‌آوری فایل‌های static" -ForegroundColor Yellow
}

# بررسی دسترسی به وب‌سایت
Write-Host "🌐 بررسی دسترسی به وب‌سایت..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ وب‌سایت در دسترس است: http://localhost:8080" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ وب‌سایت در دسترس نیست (کد: $($response.StatusCode))" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "⚠ وب‌سایت در دسترس نیست" -ForegroundColor Yellow
}

Write-Host "`n🎉 راه‌اندازی اولیه با موفقیت انجام شد!" -ForegroundColor Green
Write-Host "`n📋 دستورات مفید:" -ForegroundColor Yellow
Write-Host "  cd docker-scripts" -ForegroundColor Cyan
Write-Host "  .\docker-manage.ps1 -Action status    # بررسی وضعیت" -ForegroundColor Cyan
Write-Host "  .\docker-manage.ps1 -Action logs      # نمایش لاگ‌ها" -ForegroundColor Cyan
Write-Host "  .\docker-update.ps1 -Action status    # به‌روزرسانی" -ForegroundColor Cyan
