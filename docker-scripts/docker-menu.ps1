# منوی اصلی مدیریت Docker
# این اسکریپت منوی اصلی برای مدیریت پروژه Docker است

function Show-Menu {
    Clear-Host
    Write-Host "=== منوی مدیریت پروژه Docker ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "1️⃣  راه‌اندازی اولیه" -ForegroundColor Yellow
    Write-Host "2️⃣  بررسی وضعیت سیستم" -ForegroundColor Yellow
    Write-Host "3️⃣  نمایش لاگ‌ها" -ForegroundColor Yellow
    Write-Host "4️⃣  به‌روزرسانی پروژه" -ForegroundColor Yellow
    Write-Host "5️⃣  پشتیبان‌گیری" -ForegroundColor Yellow
    Write-Host "6️⃣  بازگردانی" -ForegroundColor Yellow
    Write-Host "7️⃣  راه‌اندازی مجدد" -ForegroundColor Yellow
    Write-Host "8️⃣  توقف سیستم" -ForegroundColor Yellow
    Write-Host "9️⃣  پاک‌سازی سیستم" -ForegroundColor Yellow
    Write-Host "🔟  نمایش اطلاعات سیستم" -ForegroundColor Yellow
    Write-Host "1️⃣1️⃣  اجرای دستور در کانتینر" -ForegroundColor Yellow
    Write-Host "1️⃣2️⃣  ورود به shell کانتینر" -ForegroundColor Yellow
    Write-Host "1️⃣3️⃣  نمایش دستورات مفید" -ForegroundColor Yellow
    Write-Host "0️⃣  خروج" -ForegroundColor Red
    Write-Host ""
}

function Get-UserChoice {
    do {
        $choice = Read-Host "لطفاً گزینه مورد نظر را انتخاب کنید (0-13)"
        if ($choice -match '^[0-9]+$' -and [int]$choice -ge 0 -and [int]$choice -le 13) {
            return [int]$choice
        } else {
            Write-Host "⚠ لطفاً عدد معتبر وارد کنید" -ForegroundColor Red
        }
    } while ($true)
}

function Execute-Choice {
    param([int]$Choice)
    
    switch ($Choice) {
        1 {
            Write-Host "🚀 راه‌اندازی اولیه..." -ForegroundColor Yellow
            .\docker-setup.ps1
        }
        2 {
            Write-Host "📊 بررسی وضعیت سیستم..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action status
        }
        3 {
            Write-Host "📋 نمایش لاگ‌ها..." -ForegroundColor Yellow
            $service = Read-Host "نام سرویس (Enter برای همه): "
            if ($service) {
                .\docker-manage.ps1 -Action logs -Service $service
            } else {
                .\docker-manage.ps1 -Action logs
            }
        }
        4 {
            Write-Host "🔄 به‌روزرسانی پروژه..." -ForegroundColor Yellow
            $force = Read-Host "حذف image های قدیمی؟ (y/N): "
            if ($force -eq "y" -or $force -eq "Y") {
                .\docker-update.ps1 -Action update -Force
            } else {
                .\docker-update.ps1 -Action update
            }
        }
        5 {
            Write-Host "📦 پشتیبان‌گیری..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action backup
        }
        6 {
            Write-Host "🔄 بازگردانی..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action restore
        }
        7 {
            Write-Host "🔄 راه‌اندازی مجدد..." -ForegroundColor Yellow
            $service = Read-Host "نام سرویس (Enter برای همه): "
            if ($service) {
                .\docker-manage.ps1 -Action restart -Service $service
            } else {
                .\docker-manage.ps1 -Action restart
            }
        }
        8 {
            Write-Host "⏹ توقف سیستم..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action stop
        }
        9 {
            Write-Host "🧹 پاک‌سازی سیستم..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action clean
        }
        10 {
            Write-Host "📊 نمایش اطلاعات سیستم..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action info
        }
        11 {
            Write-Host "🔧 اجرای دستور در کانتینر..." -ForegroundColor Yellow
            $service = Read-Host "نام سرویس (web/db/redis/nginx): "
            $command = Read-Host "دستور: "
            .\docker-manage.ps1 -Action exec -Service $service -Command $command
        }
        12 {
            Write-Host "🐚 ورود به shell کانتینر..." -ForegroundColor Yellow
            $service = Read-Host "نام سرویس (پیش‌فرض: web): "
            if (!$service) { $service = "web" }
            .\docker-manage.ps1 -Action shell -Service $service
        }
        13 {
            Write-Host "📚 نمایش دستورات مفید..." -ForegroundColor Yellow
            .\docker-manage.ps1 -Action commands
        }
        0 {
            Write-Host "👋 خروج از برنامه" -ForegroundColor Green
            return $false
        }
        default {
            Write-Host "⚠ گزینه نامعتبر" -ForegroundColor Red
        }
    }
    
    return $true
}

# اجرای منو
do {
    Show-Menu
    $choice = Get-UserChoice
    $continue = Execute-Choice -Choice $choice
    
    if ($continue) {
        Write-Host "`n⏸ فشردن Enter برای ادامه..." -ForegroundColor Yellow
        Read-Host
    }
} while ($continue)

Write-Host "`n🎉 با تشکر از استفاده!" -ForegroundColor Green
