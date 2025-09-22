@echo off
REM اسکریپت Windows برای اجرای پشتیبان‌گیری‌های زمان‌بندی شده
REM این اسکریپت به صورت خودکار مسیر پروژه را پیدا می‌کند

REM پیدا کردن مسیر پروژه (پوشه والدین اسکریپت)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM تغییر به مسیر پروژه
cd /d "%PROJECT_DIR%"

REM بررسی وجود فایل manage.py
if not exist "manage.py" (
    echo خطا: فایل manage.py یافت نشد. مسیر پروژه صحیح نیست.
    echo مسیر فعلی: %CD%
    pause
    exit /b 1
)

REM اجرای اسکریپت Python با پارامترهای ارسالی
python scripts/backup_scheduler.py %*

REM بررسی نتیجه اجرا
if %errorlevel% neq 0 (
    REM ایجاد پوشه logs در صورت عدم وجود
    if not exist "logs" mkdir logs
    
    REM لاگ کردن خطا
    echo %date% %time% - خطا در اجرای پشتیبان‌گیری (کد خطا: %errorlevel%) >> logs\backup_scheduler_error.log
    
    REM نمایش پیام خطا
    echo خطا در اجرای پشتیبان‌گیری. کد خطا: %errorlevel%
    echo برای جزئیات بیشتر، فایل logs\backup_scheduler_error.log را بررسی کنید.
) else (
    echo پشتیبان‌گیری با موفقیت اجرا شد.
)
