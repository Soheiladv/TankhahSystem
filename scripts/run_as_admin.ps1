# اسکریپت PowerShell برای اجرای Django به عنوان Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   اجرای Django به عنوان Administrator" -ForegroundColor Cyan
Write-Host "   برای دسترسی به USB Dongle" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# بررسی دسترسی ادمین
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ نیاز به دسترسی ادمین" -ForegroundColor Red
    Write-Host "لطفاً PowerShell را به عنوان Administrator اجرا کنید" -ForegroundColor Yellow
    Read-Host "برای خروج Enter را فشار دهید"
    exit 1
}

Write-Host "✅ دسترسی ادمین تایید شد" -ForegroundColor Green
Write-Host ""

Write-Host "📁 تغییر به دایرکتوری پروژه..." -ForegroundColor Blue
Set-Location "D:\Design & Source Code\Source Coding\BudgetsSystem"

Write-Host ""
Write-Host "🚀 اجرای Django Server..." -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  توجه: برای دسترسی کامل به USB Dongle، Django باید به عنوان Administrator اجرا شود" -ForegroundColor Yellow
Write-Host ""
Write-Host "🌐 سرور در آدرس زیر در دسترس خواهد بود:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8000/" -ForegroundColor White
Write-Host ""
Write-Host "🔐 برای مدیریت USB Dongle:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8000/usb-key-validator/enhanced/" -ForegroundColor White
Write-Host ""
Write-Host "📊 برای داشبورد:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8000/usb-key-validator/dashboard/" -ForegroundColor White
Write-Host ""

# اجرای Django
try {
    python manage.py runserver
} catch {
    Write-Host "❌ خطا در اجرای Django: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "🛑 سرور متوقف شد" -ForegroundColor Yellow
Read-Host "برای خروج Enter را فشار دهید"
