@echo off
REM اسکریپت پشتیبان‌گیری برای Windows
echo شروع پشتیبان‌گیری...

REM تغییر به مسیر پروژه
cd /d "%~dp0.."

REM اجرای پشتیبان‌گیری
python scripts/auto_backup.py

if %errorlevel% equ 0 (
    echo پشتیبان‌گیری موفق
) else (
    echo خطا در پشتیبان‌گیری
    pause
)
