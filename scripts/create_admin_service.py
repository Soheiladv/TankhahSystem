#!/usr/bin/env python
"""
ایجاد Windows Service برای اجرای Django با دسترسی ادمین
این اسکریپت یک سرویس Windows ایجاد می‌کند که Django را با دسترسی ادمین اجرا می‌کند
"""

import os
import sys
import subprocess
import winreg
import time

def create_admin_service():
    """ایجاد Windows Service برای Django"""
    print("🔧 ایجاد Windows Service برای Django...")
    print("=" * 60)
    
    # مسیر پروژه
    project_path = r"D:\Design & Source Code\Source Coding\BudgetsSystem"
    python_path = sys.executable
    manage_path = os.path.join(project_path, "manage.py")
    
    print(f"📁 مسیر پروژه: {project_path}")
    print(f"🐍 مسیر Python: {python_path}")
    print(f"📄 فایل manage.py: {manage_path}")
    
    # بررسی وجود فایل‌ها
    if not os.path.exists(manage_path):
        print("❌ فایل manage.py یافت نشد!")
        return False
    
    if not os.path.exists(python_path):
        print("❌ Python یافت نشد!")
        return False
    
    # ایجاد اسکریپت batch برای سرویس
    batch_content = f'''@echo off
REM اسکریپت اجرای Django برای Windows Service
cd /d "{project_path}"
"{python_path}" manage.py runserver 0.0.0.0:8000
'''
    
    batch_path = os.path.join(project_path, "scripts", "django_service.bat")
    
    try:
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        print(f"✅ اسکریپت batch ایجاد شد: {batch_path}")
    except Exception as e:
        print(f"❌ خطا در ایجاد اسکریپت batch: {e}")
        return False
    
    # ایجاد اسکریپت PowerShell برای نصب سرویس
    ps_content = f'''
# اسکریپت PowerShell برای ایجاد Windows Service
$serviceName = "DjangoUSBDongle"
$serviceDisplayName = "Django USB Dongle Service"
$serviceDescription = "Django server for USB Dongle management with admin privileges"
$batchPath = "{batch_path}"

# بررسی وجود سرویس
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {{
    Write-Host "سرویس $serviceName قبلاً وجود دارد. حذف کردن..."
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}}

# ایجاد سرویس
Write-Host "ایجاد سرویس $serviceName..."
sc.exe create $serviceName binPath= "cmd.exe /c $batchPath" start= auto DisplayName= "$serviceDisplayName"

# تنظیم توضیحات
sc.exe description $serviceName "$serviceDescription"

# تنظیم دسترسی ادمین
sc.exe config $serviceName obj= "LocalSystem"

Write-Host "✅ سرویس $serviceName ایجاد شد"
Write-Host "برای شروع سرویس: Start-Service -Name $serviceName"
Write-Host "برای توقف سرویس: Stop-Service -Name $serviceName"
Write-Host "برای حذف سرویس: sc.exe delete $serviceName"
'''
    
    ps_path = os.path.join(project_path, "scripts", "install_django_service.ps1")
    
    try:
        with open(ps_path, 'w', encoding='utf-8') as f:
            f.write(ps_content)
        print(f"✅ اسکریپت PowerShell ایجاد شد: {ps_path}")
    except Exception as e:
        print(f"❌ خطا در ایجاد اسکریپت PowerShell: {e}")
        return False
    
    # ایجاد اسکریپت VBS برای اجرای خودکار
    vbs_content = f'''
' اسکریپت VBS برای اجرای خودکار Django با دسترسی ادمین
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' مسیر پروژه
strProjectPath = "{project_path}"
strPythonPath = "{python_path}"
strManagePath = strProjectPath & "\\manage.py"

' بررسی وجود فایل‌ها
If Not objFSO.FileExists(strManagePath) Then
    MsgBox "فایل manage.py یافت نشد: " & strManagePath, vbCritical, "خطا"
    WScript.Quit
End If

If Not objFSO.FileExists(strPythonPath) Then
    MsgBox "Python یافت نشد: " & strPythonPath, vbCritical, "خطا"
    WScript.Quit
End If

' نمایش پیام شروع
MsgBox "🚀 در حال اجرای Django با دسترسی ادمین..." & vbCrLf & vbCrLf & _
       "⚠️ توجه: این اسکریپت Django را با دسترسی ادمین اجرا می‌کند" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس خواهد بود:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/", _
       vbInformation, "Django USB Dongle Server"

' دستور اجرای Django
strCommand = "cmd /c cd /d """ & strProjectPath & """ && """ & strPythonPath & """ manage.py runserver 0.0.0.0:8000"

' اجرای دستور با دسترسی ادمین
On Error Resume Next
Set objExec = objShell.Exec("runas /user:Administrator """ & strCommand & """")
If Err.Number <> 0 Then
    ' اگر runas کار نکرد، از PowerShell استفاده کن
    strPowerShellCommand = "Start-Process powershell -Verb RunAs -ArgumentList '-Command cd """ & strProjectPath & """; """ & strPythonPath & """ manage.py runserver 0.0.0.0:8000'"
    objShell.Run strPowerShellCommand, 1, False
End If
On Error GoTo 0

' نمایش پیام پایان
MsgBox "✅ Django Server شروع شد!" & vbCrLf & vbCrLf & _
       "🌐 سرور در آدرس زیر در دسترس است:" & vbCrLf & _
       "    http://127.0.0.1:8000/" & vbCrLf & vbCrLf & _
       "🔐 برای مدیریت USB Dongle:" & vbCrLf & _
       "    http://127.0.0.1:8000/usb-key-validator/enhanced/", _
       vbInformation, "Django USB Dongle Server - Ready"
'''
    
    vbs_path = os.path.join(project_path, "scripts", "run_django_admin_auto.vbs")
    
    try:
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        print(f"✅ اسکریپت VBS ایجاد شد: {vbs_path}")
    except Exception as e:
        print(f"❌ خطا در ایجاد اسکریپت VBS: {e}")
        return False
    
    print(f"\n🎯 راهنمای استفاده:")
    print(f"=" * 60)
    print(f"1. برای اجرای فوری:")
    print(f"   - دوبار کلیک روی: scripts/run_django_admin_auto.vbs")
    print(f"   - در پنجره UAC که باز می‌شود 'Yes' را کلیک کنید")
    print(f"")
    print(f"2. برای ایجاد Windows Service:")
    print(f"   - راست کلیک روی: scripts/install_django_service.ps1")
    print(f"   - 'Run with PowerShell' را انتخاب کنید")
    print(f"   - در پنجره UAC که باز می‌شود 'Yes' را کلیک کنید")
    print(f"")
    print(f"3. برای مدیریت سرویس:")
    print(f"   - Start-Service -Name DjangoUSBDongle")
    print(f"   - Stop-Service -Name DjangoUSBDongle")
    print(f"   - sc.exe delete DjangoUSBDongle")
    
    return True

if __name__ == "__main__":
    try:
        print("🔐 ایجاد سیستم اجرای Django با دسترسی ادمین")
        print("=" * 60)
        
        if create_admin_service():
            print(f"\n✅ همه اسکریپت‌ها با موفقیت ایجاد شدند!")
        else:
            print(f"\n❌ خطا در ایجاد اسکریپت‌ها!")
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    
    input("\nبرای خروج Enter را فشار دهید...")
