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
    
    try {
        docker --version | Out-Null
        Write-Host "✓ Docker نصب شده است" -ForegroundColor Green
    } catch {
        Write-Host "✗ Docker نصب نشده است" -ForegroundColor Red
        Write-Host "لطفاً ابتدا Docker Desktop را نصب کنید:" -ForegroundColor Yellow
        Write-Host "  https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
        exit 1
    }
    
    try {
        docker-compose --version | Out-Null
        Write-Host "✓ Docker Compose نصب شده است" -ForegroundColor Green
    } catch {
        Write-Host "✗ Docker Compose نصب نشده است" -ForegroundColor Red
        exit 1
    }
}

# بررسی فایل‌های ضروری
Write-Host "🔍 بررسی فایل‌های ضروری..." -ForegroundColor Yellow

$requiredFiles = @("docker-compose.yml", "Dockerfile")
foreach ($file in $requiredFiles) {
    if (!(Test-Path "..\$file")) {
        Write-Host "✗ فایل $file یافت نشد" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ $file موجود است" -ForegroundColor Green
}

# بررسی فایل .env
if (!(Test-Path "..\.env")) {
    Write-Host "⚠ فایل .env یافت نشد" -ForegroundColor Yellow
    if (Test-Path "..\env.example") {
        Write-Host "📋 کپی کردن از env.example..." -ForegroundColor Cyan
        Copy-Item "..\env.example" "..\.env"
        Write-Host "✓ فایل .env ایجاد شد" -ForegroundColor Green
        Write-Host "⚠ لطفاً تنظیمات فایل .env را بررسی کنید" -ForegroundColor Yellow
    } else {
        Write-Host "✗ فایل env.example یافت نشد" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ فایل .env موجود است" -ForegroundColor Green
}

# ایجاد دایرکتوری‌های مورد نیاز
Write-Host "📁 ایجاد دایرکتوری‌های مورد نیاز..." -ForegroundColor Yellow

$directories = @("logs", "backups", "media", "static")
foreach ($dir in $directories) {
    $fullPath = "..\$dir"
    if (!(Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath | Out-Null
        Write-Host "✓ دایرکتوری $dir ایجاد شد" -ForegroundColor Green
    } else {
        Write-Host "✓ دایرکتوری $dir موجود است" -ForegroundColor Green
    }
}

# ساخت Docker image ها
Write-Host "🔨 ساخت Docker image ها..." -ForegroundColor Yellow
Set-Location ..
docker-compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ خطا در ساخت image ها" -ForegroundColor Red
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
    } else {
        Write-Host "⚠ وب‌سایت در دسترس نیست (کد: $($response.StatusCode))" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ وب‌سایت در دسترس نیست" -ForegroundColor Yellow
}

Write-Host "`n🎉 راه‌اندازی اولیه با موفقیت انجام شد!" -ForegroundColor Green
Write-Host "`n📋 دستورات مفید:" -ForegroundColor Yellow
Write-Host "  .\docker-manage.ps1 -Action status    # بررسی وضعیت" -ForegroundColor Cyan
Write-Host "  .\docker-manage.ps1 -Action logs      # نمایش لاگ‌ها" -ForegroundColor Cyan
Write-Host "  .\docker-update.ps1 -Action status    # به‌روزرسانی" -ForegroundColor Cyan

Set-Location docker-scripts
