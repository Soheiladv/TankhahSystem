@echo off
REM اسکریپت اعتبارسنجی روزانه USB Dongle
REM این اسکریپت باید در Windows Task Scheduler اجرا شود

echo شروع اعتبارسنجی روزانه USB Dongle...
echo تاریخ: %date% %time%

REM تغییر به دایرکتوری پروژه
cd /d "D:\Design & Source Code\Source Coding\BudgetsSystem"

REM اجرای دستور اعتبارسنجی
python manage.py daily_usb_validation --stats

REM بررسی نتیجه
if %errorlevel% equ 0 (
    echo اعتبارسنجی روزانه با موفقیت انجام شد
) else (
    echo خطا در اعتبارسنجی روزانه
    REM ارسال ایمیل یا لاگ خطا
)

echo پایان اعتبارسنجی روزانه
pause
