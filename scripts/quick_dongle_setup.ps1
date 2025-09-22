# اسکریپت PowerShell برای ایجاد سریع USB Dongle
# این اسکریپت اطلاعات قفل را ذخیره کرده و dongle ایجاد می‌کند

Write-Host "========================================" -ForegroundColor Green
Write-Host "   اسکریپت سریع USB Dongle" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# تغییر به دایرکتوری پروژه
$projectPath = "D:\Design & Source Code\Source Coding\BudgetsSystem"
Set-Location $projectPath

Write-Host "📁 تغییر به دایرکتوری پروژه..." -ForegroundColor Cyan
Write-Host ""

# ذخیره اطلاعات قفل
Write-Host "💾 ذخیره اطلاعات قفل..." -ForegroundColor Cyan
python scripts/save_lock_config.py

Write-Host ""
Write-Host "🔍 بررسی نتیجه ذخیره..." -ForegroundColor Cyan

if (Test-Path "scripts\lock_config.json") {
    Write-Host "✅ فایل کد شده ایجاد شد" -ForegroundColor Green
} else {
    Write-Host "❌ فایل کد شده ایجاد نشد" -ForegroundColor Red
    Read-Host "برای خروج Enter را فشار دهید"
    exit 1
}

Write-Host ""
Write-Host "🚀 ایجاد dongle روی فلش..." -ForegroundColor Cyan
Write-Host "⚠️  توجه: اطمینان حاصل کنید که فلش USB متصل است" -ForegroundColor Yellow
Write-Host ""

python scripts/auto_write_dongle.py

Write-Host ""
Write-Host "🎉 فرآیند کامل شد!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 برای مدیریت dongle:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8000/usb-key-validator/enhanced/" -ForegroundColor White
Write-Host ""
Write-Host "📊 برای داشبورد:" -ForegroundColor Cyan
Write-Host "   http://127.0.0.1:8000/usb-key-validator/dashboard/" -ForegroundColor White
Write-Host ""

Read-Host "برای خروج Enter را فشار دهید"
