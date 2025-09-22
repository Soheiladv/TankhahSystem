@echo off
REM اسکریپت اجرای Django به عنوان Administrator برای USB Dongle

echo ========================================
echo    اجرای Django به عنوان Administrator
echo    برای دسترسی به USB Dongle
echo ========================================
echo.

REM بررسی دسترسی ادمین
net session >nul 2>&1
if %errorLevel% == 0 (
    echo  'دسترسی ادمین تایید شد'
) else (
    echo '❌ نیاز به دسترسی ادمین'
    echo لطفاً این فایل را به عنوان Administrator اجرا کنید
    pause
    exit /b 1
)

echo.
echo '📁 تغییر به دایرکتوری پروژه...'
cd /d "D:\Design & Source Code\Source Coding\BudgetsSystem"

echo.
echo '🚀 اجرای Django Server...'
echo.
echo '⚠️  توجه: برای دسترسی کامل به USB Dongle، Django باید به عنوان Administrator اجرا شود'
echo.
echo '🌐 سرور در آدرس زیر در دسترس خواهد بود:'
echo '    http://127.0.0.1:8000/'
echo.
echo '🔐 برای مدیریت USB Dongle:'
echo    http://127.0.0.1:8000/usb-key-validator/enhanced/
echo.
echo '📊 برای داشبورد:'
echo    http://127.0.0.1:8000/usb-key-validator/dashboard/
echo.

REM اجرای Django
python manage.py runserver

echo.
echo '🛑 سرور متوقف شد'
pause
