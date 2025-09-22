@echo off
REM اسکریپت سریع برای ایجاد USB Dongle
REM این اسکریپت اطلاعات قفل را ذخیره کرده و dongle ایجاد می‌کند

echo ========================================
echo    اسکریپت سریع USB Dongle
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
pause
