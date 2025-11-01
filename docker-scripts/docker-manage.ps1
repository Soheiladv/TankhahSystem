# اسکریپت مدیریت پروژه Docker
# این اسکریپت برای مدیریت روزانه پروژه در Docker استفاده می‌شود

param(
    [string]$Action = "status",
    [string]$Service = "",
    [switch]$Follow = $false,
    [switch]$All = $false
)

Write-Host "=== اسکریپت مدیریت پروژه Docker ===" -ForegroundColor Green

# تابع نمایش وضعیت
function Show-Status {
    Write-Host "📊 وضعیت سیستم:" -ForegroundColor Yellow
    
    # وضعیت کانتینرها
    Write-Host "`nکانتینرها:" -ForegroundColor Cyan
    docker-compose ps
    
    # استفاده از منابع
    Write-Host "`nاستفاده از منابع:" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    
    # حجم image ها
    Write-Host "`nحجم image ها:" -ForegroundColor Cyan
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # حجم volume ها
    Write-Host "`nحجم volume ها:" -ForegroundColor Cyan
    docker volume ls --format "table {{.Name}}\t{{.Driver}}\t{{.Size}}"
}

# تابع نمایش لاگ‌ها
function Show-Logs {
    param([string]$ServiceName, [bool]$FollowLogs)
    
    if ($ServiceName) {
        if ($FollowLogs) {
            Write-Host "📋 نمایش لاگ‌های $ServiceName (فشردن Ctrl+C برای خروج):" -ForegroundColor Yellow
            docker-compose logs -f $ServiceName
        } else {
            Write-Host "📋 آخرین لاگ‌های $ServiceName:" -ForegroundColor Yellow
            docker-compose logs --tail=50 $ServiceName
        }
    } else {
        if ($FollowLogs) {
            Write-Host "📋 نمایش تمام لاگ‌ها (فشردن Ctrl+C برای خروج):" -ForegroundColor Yellow
            docker-compose logs -f
        } else {
            Write-Host "📋 آخرین لاگ‌ها:" -ForegroundColor Yellow
            docker-compose logs --tail=50
        }
    }
}

# تابع اجرای دستور در کانتینر
function Execute-Command {
    param([string]$ServiceName, [string]$Command)
    
    if (!$ServiceName) {
        Write-Host "✗ نام سرویس مشخص نشده است" -ForegroundColor Red
        return
    }
    
    Write-Host "🔧 اجرای دستور در $ServiceName : $Command" -ForegroundColor Yellow
    docker-compose exec $ServiceName $Command
}

# تابع پشتیبان‌گیری
function Backup-Data {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "backups\manual_$timestamp"
    
    if (!(Test-Path "backups")) {
        New-Item -ItemType Directory -Path "backups" | Out-Null
    }
    
    Write-Host "📦 ایجاد پشتیبان در $backupDir ..." -ForegroundColor Yellow
    
    # پشتیبان از دیتابیس
    Write-Host "  - پشتیبان از دیتابیس..." -ForegroundColor Cyan
    docker-compose exec -T db pg_dump -U budgets_user -d budgets_db > "$backupDir\database.sql" 2>$null
    
    # پشتیبان از فایل‌های media
    Write-Host "  - پشتیبان از فایل‌های media..." -ForegroundColor Cyan
    docker-compose exec -T web tar -czf - /app/mediafiles > "$backupDir\media.tar.gz" 2>$null
    
    # پشتیبان از تنظیمات
    Write-Host "  - پشتیبان از تنظیمات..." -ForegroundColor Cyan
    Copy-Item ".env" "$backupDir\env_backup" -ErrorAction SilentlyContinue
    Copy-Item "docker-compose.yml" "$backupDir\docker-compose_backup.yml" -ErrorAction SilentlyContinue
    
    Write-Host "✓ پشتیبان در $backupDir ایجاد شد" -ForegroundColor Green
}

# تابع بازگردانی
function Restore-Data {
    $backupDir = Read-Host "مسیر پوشه پشتیبان"
    
    if (!(Test-Path $backupDir)) {
        Write-Host "✗ پوشه پشتیبان یافت نشد" -ForegroundColor Red
        return
    }
    
    Write-Host "🔄 بازگردانی از $backupDir ..." -ForegroundColor Yellow
    
    # بازگردانی دیتابیس
    if (Test-Path "$backupDir\database.sql") {
        Write-Host "  - بازگردانی دیتابیس..." -ForegroundColor Cyan
        docker-compose exec -T db psql -U budgets_user -d budgets_db < "$backupDir\database.sql" 2>$null
    }
    
    # بازگردانی فایل‌های media
    if (Test-Path "$backupDir\media.tar.gz") {
        Write-Host "  - بازگردانی فایل‌های media..." -ForegroundColor Cyan
        docker-compose exec -T web tar -xzf - < "$backupDir\media.tar.gz" 2>$null
    }
    
    Write-Host "✓ بازگردانی انجام شد" -ForegroundColor Green
}

# تابع پاک‌سازی
function Clean-System {
    Write-Host "🧹 پاک‌سازی سیستم..." -ForegroundColor Yellow
    
    $confirm = Read-Host "آیا مطمئن هستید؟ (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "عملیات لغو شد" -ForegroundColor Yellow
        return
    }
    
    # توقف کانتینرها
    docker-compose down
    
    # حذف کانتینرهای متوقف
    docker container prune -f
    
    # حذف image های استفاده نشده
    docker image prune -f
    
    # حذف volume های استفاده نشده
    docker volume prune -f
    
    # حذف network های استفاده نشده
    docker network prune -f
    
    Write-Host "✓ پاک‌سازی انجام شد" -ForegroundColor Green
}

# تابع نمایش اطلاعات سرویس
function Show-ServiceInfo {
    param([string]$ServiceName)
    
    if (!$ServiceName) {
        Write-Host "✗ نام سرویس مشخص نشده است" -ForegroundColor Red
        return
    }
    
    Write-Host "ℹ️ اطلاعات سرویس $ServiceName :" -ForegroundColor Yellow
    
    # اطلاعات کانتینر
    docker-compose ps $ServiceName
    
    # لاگ‌های اخیر
    Write-Host "`nآخرین لاگ‌ها:" -ForegroundColor Cyan
    docker-compose logs --tail=20 $ServiceName
    
    # استفاده از منابع
    Write-Host "`nاستفاده از منابع:" -ForegroundColor Cyan
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | Select-String $ServiceName
}

# تابع راه‌اندازی مجدد سرویس
function Restart-Service {
    param([string]$ServiceName)
    
    if (!$ServiceName) {
        Write-Host "✗ نام سرویس مشخص نشده است" -ForegroundColor Red
        return
    }
    
    Write-Host "🔄 راه‌اندازی مجدد $ServiceName ..." -ForegroundColor Yellow
    docker-compose restart $ServiceName
    Write-Host "✓ $ServiceName راه‌اندازی مجدد شد" -ForegroundColor Green
}

# تابع نمایش دستورات مفید
function Show-Commands {
    Write-Host "🔧 دستورات مفید:" -ForegroundColor Yellow
    
    Write-Host "`nمدیریت کانتینرها:" -ForegroundColor Cyan
    Write-Host "  docker-compose up -d                    # راه‌اندازی" -ForegroundColor White
    Write-Host "  docker-compose down                     # توقف" -ForegroundColor White
    Write-Host "  docker-compose restart [service]        # راه‌اندازی مجدد" -ForegroundColor White
    Write-Host "  docker-compose ps                       # وضعیت" -ForegroundColor White
    
    Write-Host "`nمدیریت لاگ‌ها:" -ForegroundColor Cyan
    Write-Host "  docker-compose logs [service]           # لاگ‌ها" -ForegroundColor White
    Write-Host "  docker-compose logs -f [service]        # لاگ‌های زنده" -ForegroundColor White
    Write-Host "  docker-compose logs --tail=50 [service] # آخرین 50 خط" -ForegroundColor White
    
    Write-Host "`nاجرای دستورات:" -ForegroundColor Cyan
    Write-Host "  docker-compose exec web python manage.py migrate" -ForegroundColor White
    Write-Host "  docker-compose exec web python manage.py collectstatic" -ForegroundColor White
    Write-Host "  docker-compose exec web python manage.py shell" -ForegroundColor White
    
    Write-Host "`nمدیریت دیتابیس:" -ForegroundColor Cyan
    Write-Host "  docker-compose exec db psql -U budgets_user -d budgets_db" -ForegroundColor White
    Write-Host "  docker-compose exec -T db pg_dump -U budgets_user -d budgets_db > backup.sql" -ForegroundColor White
}

# اجرای عملیات
switch ($Action.ToLower()) {
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs -ServiceName $Service -FollowLogs $Follow
    }
    "exec" {
        $command = Read-Host "دستور را وارد کنید"
        Execute-Command -ServiceName $Service -Command $command
    }
    "backup" {
        Backup-Data
    }
    "restore" {
        Restore-Data
    }
    "clean" {
        Clean-System
    }
    "info" {
        if ($Service) {
            Show-ServiceInfo -ServiceName $Service
        } else {
            Show-Status
        }
    }
    "restart" {
        if ($Service) {
            Restart-Service -ServiceName $Service
        } else {
            Write-Host "🔄 راه‌اندازی مجدد تمام سرویس‌ها..." -ForegroundColor Yellow
            docker-compose restart
        }
    }
    "shell" {
        if (!$Service) {
            $Service = "web"
        }
        Write-Host "🐚 ورود به shell کانتینر $Service ..." -ForegroundColor Yellow
        docker-compose exec $Service /bin/bash
    }
    "commands" {
        Show-Commands
    }
    default {
        Write-Host "استفاده:" -ForegroundColor Yellow
        Write-Host "  .\docker-manage.ps1 -Action status                     # وضعیت سیستم" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action logs -Service web          # لاگ‌های وب" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action logs -Follow               # لاگ‌های زنده" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action exec -Service web          # اجرای دستور" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action backup                     # پشتیبان‌گیری" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action restore                    # بازگردانی" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action clean                      # پاک‌سازی" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action info -Service web          # اطلاعات سرویس" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action restart -Service web       # راه‌اندازی مجدد" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action shell -Service web         # ورود به shell" -ForegroundColor Cyan
        Write-Host "  .\docker-manage.ps1 -Action commands                   # دستورات مفید" -ForegroundColor Cyan
    }
}

Write-Host "`n=== عملیات تکمیل شد ===" -ForegroundColor Green
