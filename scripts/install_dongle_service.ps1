
# اسکریپت PowerShell برای ایجاد Windows Service
$serviceName = "DjangoUSBDongle"
$serviceDisplayName = "Django USB Dongle Service"
$serviceDescription = "Django server for USB Dongle management with admin privileges"
$batchPath = "D:\Design & Source Code\Source Coding\BudgetsSystem\scripts\django_service.bat"

# بررسی وجود سرویس
if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
    Write-Host "سرویس $serviceName قبلاً وجود دارد. حذف کردن..."
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

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
