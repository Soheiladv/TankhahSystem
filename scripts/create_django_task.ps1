
# اسکریپت PowerShell برای ایجاد Task Scheduler
$taskName = "DjangoUSBDongle"
$taskDescription = "Django server for USB Dongle management with admin privileges"
$batchPath = "D:\Design & Source Code\Source Coding\BudgetsSystem\scripts\django_task.bat"

# بررسی وجود task
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Host "Task $taskName قبلاً وجود دارد. حذف کردن..."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Start-Sleep -Seconds 2
}

# ایجاد task action
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $batchPath"

# ایجاد task trigger (در زمان logon)
$trigger = New-ScheduledTaskTrigger -AtLogOn

# ایجاد task settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# ایجاد task principal (با دسترسی ادمین)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# ایجاد task
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $taskDescription

# ثبت task
Register-ScheduledTask -TaskName $taskName -InputObject $task

Write-Host "✅ Task $taskName ایجاد شد"
Write-Host "برای شروع task: Start-ScheduledTask -TaskName $taskName"
Write-Host "برای توقف task: Stop-ScheduledTask -TaskName $taskName"
Write-Host "برای حذف task: Unregister-ScheduledTask -TaskName $taskName"
Write-Host "برای مشاهده task: Get-ScheduledTask -TaskName $taskName"
