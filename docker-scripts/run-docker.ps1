# اسکریپت اجرای Docker با بررسی‌های کامل
# این اسکریپت Docker را بدون خطا اجرا می‌کند

param(
    [switch]$Build = $true,
    [switch]$Force = $false,
    [switch]$SkipCheck = $false
)

Write-Host "`n🚀 اجرای Docker برای Budgets System" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# بررسی اولیه (اگر -SkipCheck نباشد)
if (-not $SkipCheck) {
    Write-Host "`n🔍 در حال بررسی پیش‌نیازها..." -ForegroundColor Yellow
    & "$scriptPath\check-docker-setup.ps1" -Fix:$Force

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ بررسی اولیه ناموفق بود. لطفاً خطاها را برطرف کنید." -ForegroundColor Red
        exit 1
    }
}

# توقف کانتینرهای قبلی (اگر وجود دارند)
Write-Host "`n🛑 توقف کانتینرهای قبلی..." -ForegroundColor Yellow
docker compose down 2>&1 | Out-Null

# ساخت image و اجرای کانتینرها
Write-Host "`n🔨 ساخت و راه‌اندازی کانتینرها..." -ForegroundColor Yellow

if ($Build) {
    Write-Host "  در حال ساخت image..." -ForegroundColor Gray
    docker compose build --no-cache

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n❌ ساخت image ناموفق بود!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n🚀 راه‌اندازی سرویس‌ها..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ راه‌اندازی سرویس‌ها ناموفق بود!" -ForegroundColor Red
    Write-Host "`n📋 مشاهده لاگ‌ها برای بررسی خطا:" -ForegroundColor Yellow
    Write-Host "  docker compose logs" -ForegroundColor Cyan
    exit 1
}

# صبر برای آماده شدن سرویس‌ها
Write-Host "`n⏳ منتظر آماده شدن سرویس‌ها..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# بررسی وضعیت سرویس‌ها
Write-Host "`n📊 وضعیت سرویس‌ها:" -ForegroundColor Yellow
docker compose ps

# بررسی سلامت سرویس‌ها
Write-Host "`n🏥 بررسی سلامت سرویس‌ها..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$services = @("db", "redis", "web", "nginx")
$allHealthy = $true

foreach ($service in $services) {
    $status = docker compose ps --format json | ConvertFrom-Json | Where-Object { $_.Name -like "*$service*" } | Select-Object -First 1

    if ($status) {
        if ($status.State -eq "running") {
            Write-Host "  ✅ $service در حال اجرا است" -ForegroundColor Green
        }
        else {
            Write-Host "  ❌ $service در حال اجرا نیست (وضعیت: $($status.State))" -ForegroundColor Red
            $allHealthy = $false
        }
    }
    else {
        Write-Host "  ⚠ $service پیدا نشد" -ForegroundColor Yellow
    }
}

# نمایش اطلاعات دسترسی
Write-Host "`n" + ("=" * 50) -ForegroundColor Cyan
Write-Host "✅ Docker با موفقیت اجرا شد!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Cyan

Write-Host "`n🌐 دسترسی به اپلیکیشن:" -ForegroundColor Yellow
Write-Host "  - Django (مستقیم): http://localhost:8000" -ForegroundColor Cyan
Write-Host "  - Nginx (Reverse Proxy): http://localhost:8080" -ForegroundColor Cyan
Write-Host "  - MySQL: localhost:3307" -ForegroundColor Cyan
Write-Host "  - Redis: localhost:6379" -ForegroundColor Cyan

Write-Host "`n📋 دستورات مفید:" -ForegroundColor Yellow
Write-Host "  - مشاهده لاگ‌ها: docker compose logs -f" -ForegroundColor Gray
Write-Host "  - مشاهده لاگ web: docker compose logs -f web" -ForegroundColor Gray
Write-Host "  - توقف: docker compose down" -ForegroundColor Gray
Write-Host "  - اجرای migration: docker compose exec web python manage.py migrate" -ForegroundColor Gray
Write-Host "  - ایجاد superuser: docker compose exec web python manage.py createsuperuser" -ForegroundColor Gray

Write-Host "`n"

if (-not $allHealthy) {
    Write-Host "⚠ برخی سرویس‌ها ممکن است هنوز آماده نباشند. لطفاً لاگ‌ها را بررسی کنید:" -ForegroundColor Yellow
    Write-Host "  docker compose logs" -ForegroundColor Cyan
}

