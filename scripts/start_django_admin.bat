@echo off
REM اسکریپت ساده برای اجرای Django با دسترسی ادمین

echo ========================================
echo    اجرای Django برای USB Dongle
echo ========================================
echo.

echo 📁 تغییر به دایرکتوری پروژه...
cd /d "D:\Design & Source Code\Source Coding\BudgetsSystem"

echo.
echo 🚀 اجرای Django Server...
echo.
echo ⚠️  توجه: اگر خطای Access Denied دریافت کردید،
echo    این فایل را به عنوان Administrator اجرا کنید
echo.
echo 🌐 سرور در آدرس زیر در دسترس خواهد بود:
echo    http://127.0.0.1:8000/
echo.
echo 🔐 برای مدیریت USB Dongle:
echo    http://127.0.0.1:8000/usb-key-validator/enhanced/
echo.
echo 📊 برای داشبورد:
echo    http://127.0.0.1:8000/usb-key-validator/dashboard/
echo.

REM اجرای Django
python manage.py runserver

echo.
echo 🛑 سرور متوقف شد
pause
