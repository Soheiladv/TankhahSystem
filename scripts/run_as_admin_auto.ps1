# اسکریپت PowerShell برای اجرای خودکار Django به عنوان Administrator
# این اسکریپت خودش دسترسی ادمین را درخواست می‌کند

# بررسی اینکه آیا اسکریپت به عنوان Administrator اجرا می‌شود
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# اگر به عنوان Administrator اجرا نمی‌شود، خودش را دوباره اجرا کند
if (-NOT (Test-Administrator)) {
    Write-Host "🔄 درخواست دسترسی ادمین..." -ForegroundColor Yellow
    Write-Host "لطفاً در پنجره UAC که باز می‌شود 'Yes' را کلیک کنید" -ForegroundColor Cyan
    
    # اجرای مجدد با دسترسی ادمین
    Start-Process PowerShell -Verb RunAs -ArgumentList "-File `"$PSCommandPath`""
    exit
}

# اگر به عنوان Administrator اجرا می‌شود، ادامه دهید
Write-Host "========================================" -ForegroundColor Green
Write-Host "   اجرای Django به عنوان Administrator" -ForegroundColor Green
Write-Host "   برای دسترسی به USB Dongle" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "✅ دسترسی ادمین تایید شد" -ForegroundColor Green
Write-Host ""

Write-Host "📁 تغییر به دایرکتوری پروژه..." -ForegroundColor Cyan
Set-Location "D:\Design & Source Code\Source Coding\BudgetsSystem"

Write-Host ""
Write-Host "🚀 اجرای Django Server..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  توجه: برای دسترسی کامل به USB Dongle، Django باید به عنوان Administrator اجرا شود" -ForegroundColor Yellow
Write-Host ""
Write-Host "🌐 سرور در آدرس زیر در دسترس خواهد بود:" -ForegroundColor Cyan
Write-Host "    http://127.0.0.1:8000/" -ForegroundColor White
Write-Host ""
Write-Host "🔐 برای مدیریت USB Dongle:" -ForegroundColor Cyan
Write-Host "    http://127.0.0.1:8000/usb-key-validator/enhanced/" -ForegroundColor White
Write-Host ""
Write-Host "📊 برای داشبورد:" -ForegroundColor Cyan
Write-Host "    http://127.0.0.1:8000/usb-key-validator/dashboard/" -ForegroundColor White
Write-Host ""

# اجرای Django
Write-Host "🔄 شروع سرور Django..." -ForegroundColor Green
python manage.py runserver

Write-Host ""
Write-Host "🛑 سرور متوقف شد" -ForegroundColor Red
Write-Host "برای بستن این پنجره، هر کلیدی را فشار دهید..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
