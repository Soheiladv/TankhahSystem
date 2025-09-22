@echo off
REM اسکریپت Batch برای نصب Windows Service
echo ========================================
echo    نصب Windows Service برای Django
echo ========================================
echo.

set SERVICE_NAME=DjangoUSBDongle
set SERVICE_DISPLAY_NAME=Django USB Dongle Service
set SERVICE_DESCRIPTION=Django server for USB Dongle management with admin privileges
set BATCH_PATH=D:\Design & Source Code\Source Coding\BudgetsSystem\scripts\django_service.bat

echo بررسی وجود سرویس...
sc query %SERVICE_NAME% >nul 2>&1
if %errorLevel% == 0 (
    echo سرویس %SERVICE_NAME% قبلاً وجود دارد. حذف کردن...
    sc stop %SERVICE_NAME% >nul 2>&1
    sc delete %SERVICE_NAME% >nul 2>&1
    timeout /t 2 >nul
)

echo ایجاد سرویس %SERVICE_NAME%...
sc create %SERVICE_NAME% binPath= "cmd.exe /c %BATCH_PATH%" start= auto DisplayName= "%SERVICE_DISPLAY_NAME%"

echo تنظیم توضیحات...
sc description %SERVICE_NAME% "%SERVICE_DESCRIPTION%"

echo تنظیم دسترسی ادمین...
sc config %SERVICE_NAME% obj= "LocalSystem"

echo.
echo ✅ سرویس %SERVICE_NAME% ایجاد شد
echo.
echo برای شروع سرویس:
echo   sc start %SERVICE_NAME%
echo.
echo برای توقف سرویس:
echo   sc stop %SERVICE_NAME%
echo.
echo برای حذف سرویس:
echo   sc delete %SERVICE_NAME%
echo.
pause
