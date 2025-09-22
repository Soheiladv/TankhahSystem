@echo off
REM اسکریپت نهایی برای ایجاد USB Dongle
echo ========================================
echo    اسکریپت نهایی USB Dongle
echo ========================================
echo.

echo 📁 تغییر به دایرکتوری پروژه...
cd /d "D:\Design & Source Code\Source Coding\BudgetsSystem"

echo.
echo 💾 ذخیره اطلاعات قفل...
python scripts/save_lock_config.py

echo.
echo 🔍 بررسی نتیجه ذخیره...
if exist "scripts\lock_config.json" (
    echo ✅ فایل کد شده ایجاد شد
) else (
    echo ❌ فایل کد شده ایجاد نشد
    pause
    exit /b 1
)

echo.
echo 🚀 ایجاد dongle روی فلش...
echo ⚠️  توجه: اطمینان حاصل کنید که فلش USB متصل است
echo.

REM اجرای اسکریپت dongle
python scripts/auto_write_dongle.py

echo.
echo 🎉 فرآیند کامل شد!
echo.
echo 📋 برای مدیریت dongle:
echo    http://127.0.0.1:8000/usb-key-validator/enhanced/
echo.
echo 📊 برای داشبورد:
echo    http://127.0.0.1:8000/usb-key-validator/dashboard/
echo.
echo 🔧 اگر خطای Access Denied دریافت کردید:
echo    1. Django را به عنوان Administrator اجرا کنید
echo    2. یا از اسکریپت run_django_admin_auto.vbs استفاده کنید
echo.
pause
