# اسکریپت به‌روزرسانی پروژه در Docker
# این اسکریپت برای به‌روزرسانی پروژه در محیط Docker استفاده می‌شود

param(
    [string]$Action = "update",
    [switch]$Force = $false,
    [switch]$Backup = $true
)

Write-Host "=== اسکریپت به‌روزرسانی پروژه Docker ===" -ForegroundColor Green
Write-Host "عملیات: $Action" -ForegroundColor Yellow

# بررسی وجود Docker
try {
    docker --version | Out-Null
    Write-Host "✓ Docker نصب شده است" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker نصب نشده است. لطفاً ابتدا Docker را نصب کنید." -ForegroundColor Red
    exit 1
}

# بررسی وجود docker-compose
try {
    docker-compose --version | Out-Null
    Write-Host "✓ Docker Compose نصب شده است" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose نصب نشده است. لطفاً ابتدا Docker Compose را نصب کنید." -ForegroundColor Red
    exit 1
}

# تابع پشتیبان‌گیری
function Backup-Data {
    if ($Backup) {
        Write-Host "📦 ایجاد پشتیبان از داده‌ها..." -ForegroundColor Yellow
        
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupDir = "backups\docker_$timestamp"
        
        if (!(Test-Path "backups")) {
            New-Item -ItemType Directory -Path "backups" | Out-Null
        }
        
        # پشتیبان از دیتابیس
        Write-Host "  - پشتیبان از دیتابیس..." -ForegroundColor Cyan
        docker-compose exec -T db pg_dump -U budgets_user -d budgets_db > "$backupDir\database.sql" 2>$null
        
        # پشتیبان از فایل‌های media
        Write-Host "  - پشتیبان از فایل‌های media..." -ForegroundColor Cyan
        docker-compose exec -T web tar -czf - /app/mediafiles > "$backupDir\media.tar.gz" 2>$null
        
        Write-Host "✓ پشتیبان در $backupDir ایجاد شد" -ForegroundColor Green
    }
}

# تابع به‌روزرسانی
function Update-Project {
    Write-Host "🔄 شروع به‌روزرسانی پروژه..." -ForegroundColor Yellow
    
    # توقف کانتینرها
    Write-Host "  - توقف کانتینرها..." -ForegroundColor Cyan
    docker-compose down
    
    # حذف image های قدیمی
    if ($Force) {
        Write-Host "  - حذف image های قدیمی..." -ForegroundColor Cyan
        docker image prune -f
        docker rmi budgetssystem-web budgetssystem-celery budgetssystem-celery-beat -f 2>$null
    }
    
    # ساخت image های جدید
    Write-Host "  - ساخت image های جدید..." -ForegroundColor Cyan
    docker-compose build --no-cache
    
    # اجرای migrations
    Write-Host "  - اجرای migrations..." -ForegroundColor Cyan
    docker-compose up -d db redis
    Start-Sleep -Seconds 10
    docker-compose exec -T web python manage.py migrate
    
    # جمع‌آوری فایل‌های static
    Write-Host "  - جمع‌آوری فایل‌های static..." -ForegroundColor Cyan
    docker-compose exec -T web python manage.py collectstatic --noinput
    
    # اجرای کانتینرها
    Write-Host "  - اجرای کانتینرها..." -ForegroundColor Cyan
    docker-compose up -d
    
    Write-Host "✓ به‌روزرسانی با موفقیت انجام شد" -ForegroundColor Green
}

# تابع بررسی وضعیت
function Check-Status {
    Write-Host "🔍 بررسی وضعیت کانتینرها..." -ForegroundColor Yellow
    
    docker-compose ps
    
    # بررسی دسترسی به وب‌سایت
    Write-Host "  - بررسی دسترسی به وب‌سایت..." -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ وب‌سایت در دسترس است" -ForegroundColor Green
        } else {
            Write-Host "⚠ وب‌سایت در دسترس نیست (کد: $($response.StatusCode))" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "✗ وب‌سایت در دسترس نیست" -ForegroundColor Red
    }
}

# تابع نمایش لاگ‌ها
function Show-Logs {
    Write-Host "📋 نمایش لاگ‌های سیستم..." -ForegroundColor Yellow
    
    $service = Read-Host "نام سرویس (web/db/redis/nginx) یا Enter برای همه"
    
    if ($service) {
        docker-compose logs --tail=50 $service
    } else {
        docker-compose logs --tail=20
    }
}

# تابع پاک‌سازی
function Clean-System {
    Write-Host "🧹 پاک‌سازی سیستم..." -ForegroundColor Yellow
    
    # توقف کانتینرها
    docker-compose down
    
    # حذف کانتینرهای متوقف
    docker container prune -f
    
    # حذف image های استفاده نشده
    docker image prune -f
    
    # حذف volume های استفاده نشده
    docker volume prune -f
    
    Write-Host "✓ پاک‌سازی انجام شد" -ForegroundColor Green
}

# اجرای عملیات بر اساس پارامتر
switch ($Action.ToLower()) {
    "update" {
        Backup-Data
        Update-Project
        Check-Status
    }
    "status" {
        Check-Status
    }
    "logs" {
        Show-Logs
    }
    "clean" {
        Clean-System
    }
    "backup" {
        Backup-Data
    }
    "restart" {
        Write-Host "🔄 راه‌اندازی مجدد کانتینرها..." -ForegroundColor Yellow
        docker-compose restart
        Check-Status
    }
    "stop" {
        Write-Host "⏹ توقف کانتینرها..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "✓ کانتینرها متوقف شدند" -ForegroundColor Green
    }
    "start" {
        Write-Host "▶ راه‌اندازی کانتینرها..." -ForegroundColor Yellow
        docker-compose up -d
        Check-Status
    }
    default {
        Write-Host "استفاده:" -ForegroundColor Yellow
        Write-Host "  .\docker-update.ps1 -Action update    # به‌روزرسانی پروژه" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action status    # بررسی وضعیت" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action logs      # نمایش لاگ‌ها" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action clean     # پاک‌سازی سیستم" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action backup    # پشتیبان‌گیری" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action restart   # راه‌اندازی مجدد" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action stop      # توقف" -ForegroundColor Cyan
        Write-Host "  .\docker-update.ps1 -Action start     # راه‌اندازی" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "پارامترهای اختیاری:" -ForegroundColor Yellow
        Write-Host "  -Force    # حذف image های قدیمی" -ForegroundColor Cyan
        Write-Host "  -Backup   # ایجاد پشتیبان (پیش‌فرض: true)" -ForegroundColor Cyan
    }
}

Write-Host "`n=== عملیات تکمیل شد ===" -ForegroundColor Green
