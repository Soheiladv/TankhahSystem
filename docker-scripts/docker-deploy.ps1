# اسکریپت استقرار پروژه در Docker
# این اسکریپت برای استقرار اولیه و مدیریت پروژه در Docker استفاده می‌شود

param(
    [string]$Environment = "development",
    [string]$Action = "deploy",
    [switch]$SkipBackup = $false,
    [switch]$Force = $false
)

Write-Host "=== اسکریپت استقرار پروژه Docker ===" -ForegroundColor Green
Write-Host "محیط: $Environment" -ForegroundColor Yellow
Write-Host "عملیات: $Action" -ForegroundColor Yellow

# بررسی وجود فایل‌های ضروری
$requiredFiles = @("docker-compose.yml", "Dockerfile", ".env")
foreach ($file in $requiredFiles) {
    if (!(Test-Path $file)) {
        Write-Host "✗ فایل $file یافت نشد" -ForegroundColor Red
        exit 1
    }
}

# تابع بررسی محیط
function Test-Environment {
    Write-Host "🔍 بررسی محیط..." -ForegroundColor Yellow
    
    # بررسی Docker
    try {
        docker --version | Out-Null
        Write-Host "✓ Docker نصب شده است" -ForegroundColor Green
    } catch {
        Write-Host "✗ Docker نصب نشده است" -ForegroundColor Red
        return $false
    }
    
    # بررسی Docker Compose
    try {
        docker-compose --version | Out-Null
        Write-Host "✓ Docker Compose نصب شده است" -ForegroundColor Green
    } catch {
        Write-Host "✗ Docker Compose نصب نشده است" -ForegroundColor Red
        return $false
    }
    
    # بررسی فایل .env
    if (!(Test-Path ".env")) {
        Write-Host "⚠ فایل .env یافت نشد. از env.example کپی می‌کنم..." -ForegroundColor Yellow
        if (Test-Path "env.example") {
            Copy-Item "env.example" ".env"
            Write-Host "✓ فایل .env ایجاد شد" -ForegroundColor Green
        } else {
            Write-Host "✗ فایل env.example یافت نشد" -ForegroundColor Red
            return $false
        }
    }
    
    return $true
}

# تابع استقرار اولیه
function Deploy-Initial {
    Write-Host "🚀 شروع استقرار اولیه..." -ForegroundColor Yellow
    
    # ایجاد دایرکتوری‌های مورد نیاز
    $directories = @("logs", "backups", "media", "static")
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir | Out-Null
            Write-Host "✓ دایرکتوری $dir ایجاد شد" -ForegroundColor Green
        }
    }
    
    # ساخت image ها
    Write-Host "  - ساخت Docker image ها..." -ForegroundColor Cyan
    docker-compose build
    
    # اجرای کانتینرها
    Write-Host "  - اجرای کانتینرها..." -ForegroundColor Cyan
    docker-compose up -d
    
    # انتظار برای راه‌اندازی
    Write-Host "  - انتظار برای راه‌اندازی سرویس‌ها..." -ForegroundColor Cyan
    Start-Sleep -Seconds 30
    
    # اجرای migrations
    Write-Host "  - اجرای migrations..." -ForegroundColor Cyan
    docker-compose exec -T web python manage.py migrate
    
    # ایجاد superuser
    Write-Host "  - ایجاد superuser..." -ForegroundColor Cyan
    docker-compose exec -T web python manage.py createsuperuser --noinput --username admin --email admin@example.com 2>$null
    
    # جمع‌آوری فایل‌های static
    Write-Host "  - جمع‌آوری فایل‌های static..." -ForegroundColor Cyan
    docker-compose exec -T web python manage.py collectstatic --noinput
    
    Write-Host "✓ استقرار اولیه با موفقیت انجام شد" -ForegroundColor Green
}

# تابع استقرار production
function Deploy-Production {
    Write-Host "🏭 شروع استقرار production..." -ForegroundColor Yellow
    
    # بررسی فایل docker-compose.prod.yml
    if (!(Test-Path "docker-compose.prod.yml")) {
        Write-Host "✗ فایل docker-compose.prod.yml یافت نشد" -ForegroundColor Red
        return
    }
    
    # توقف کانتینرهای development
    docker-compose down
    
    # اجرای production
    docker-compose -f docker-compose.prod.yml up -d --build
    
    Write-Host "✓ استقرار production با موفقیت انجام شد" -ForegroundColor Green
}

# تابع پشتیبان‌گیری
function Backup-System {
    if (!$SkipBackup) {
        Write-Host "📦 ایجاد پشتیبان از سیستم..." -ForegroundColor Yellow
        
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backupDir = "backups\system_$timestamp"
        
        if (!(Test-Path "backups")) {
            New-Item -ItemType Directory -Path "backups" | Out-Null
        }
        
        # پشتیبان از دیتابیس
        Write-Host "  - پشتیبان از دیتابیس..." -ForegroundColor Cyan
        docker-compose exec -T db pg_dump -U budgets_user -d budgets_db > "$backupDir\database.sql" 2>$null
        
        # پشتیبان از فایل‌های media
        Write-Host "  - پشتیبان از فایل‌های media..." -ForegroundColor Cyan
        docker-compose exec -T web tar -czf - /app/mediafiles > "$backupDir\media.tar.gz" 2>$null
        
        # پشتیبان از تنظیمات
        Write-Host "  - پشتیبان از تنظیمات..." -ForegroundColor Cyan
        Copy-Item ".env" "$backupDir\env_backup"
        Copy-Item "docker-compose.yml" "$backupDir\docker-compose_backup.yml"
        
        Write-Host "✓ پشتیبان در $backupDir ایجاد شد" -ForegroundColor Green
    }
}

# تابع بررسی سلامت سیستم
function Test-Health {
    Write-Host "🏥 بررسی سلامت سیستم..." -ForegroundColor Yellow
    
    # بررسی وضعیت کانتینرها
    $containers = docker-compose ps --services
    foreach ($container in $containers) {
        $status = docker-compose ps $container --format "table {{.State}}"
        if ($status -match "Up") {
            Write-Host "✓ $container در حال اجرا است" -ForegroundColor Green
        } else {
            Write-Host "✗ $container متوقف است" -ForegroundColor Red
        }
    }
    
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
    
    # بررسی لاگ‌ها
    Write-Host "  - بررسی لاگ‌های خطا..." -ForegroundColor Cyan
    $errorLogs = docker-compose logs --tail=100 | Select-String "ERROR"
    if ($errorLogs) {
        Write-Host "⚠ خطاهای زیر یافت شد:" -ForegroundColor Yellow
        $errorLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    } else {
        Write-Host "✓ خطایی یافت نشد" -ForegroundColor Green
    }
}

# تابع نمایش اطلاعات سیستم
function Show-SystemInfo {
    Write-Host "📊 اطلاعات سیستم:" -ForegroundColor Yellow
    
    Write-Host "  - وضعیت کانتینرها:" -ForegroundColor Cyan
    docker-compose ps
    
    Write-Host "  - استفاده از منابع:" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    
    Write-Host "  - حجم image ها:" -ForegroundColor Cyan
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
}

# اجرای عملیات
if (!(Test-Environment)) {
    Write-Host "✗ محیط آماده نیست" -ForegroundColor Red
    exit 1
}

switch ($Action.ToLower()) {
    "deploy" {
        if ($Environment -eq "production") {
            Deploy-Production
        } else {
            Deploy-Initial
        }
        Test-Health
    }
    "backup" {
        Backup-System
    }
    "health" {
        Test-Health
    }
    "info" {
        Show-SystemInfo
    }
    "logs" {
        Write-Host "📋 نمایش لاگ‌های سیستم:" -ForegroundColor Yellow
        docker-compose logs --tail=50
    }
    "restart" {
        Write-Host "🔄 راه‌اندازی مجدد سیستم..." -ForegroundColor Yellow
        docker-compose restart
        Test-Health
    }
    "stop" {
        Write-Host "⏹ توقف سیستم..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "✓ سیستم متوقف شد" -ForegroundColor Green
    }
    "start" {
        Write-Host "▶ راه‌اندازی سیستم..." -ForegroundColor Yellow
        docker-compose up -d
        Test-Health
    }
    default {
        Write-Host "استفاده:" -ForegroundColor Yellow
        Write-Host "  .\docker-deploy.ps1 -Action deploy -Environment development" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action deploy -Environment production" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action backup" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action health" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action info" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action logs" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action restart" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action stop" -ForegroundColor Cyan
        Write-Host "  .\docker-deploy.ps1 -Action start" -ForegroundColor Cyan
    }
}

Write-Host "`n=== عملیات تکمیل شد ===" -ForegroundColor Green
