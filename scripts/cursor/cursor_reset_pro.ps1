# cursor_reset_pro.ps1 - Reset Cursor AI Trial to Pro Free (Windows 2025)
# اجرا با Administrator - پشتیبان می‌گیره و Machine ID رو ریست می‌کنه
# هشدار: مسئولیت با خودت!

# چک ادمین
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "خطا: با Administrator اجرا کن!" -ForegroundColor Red
    exit 1
}

# مسیرها
$cursorAppData = "$env:APPDATA\Cursor"
$cursorLocal = "$env:LOCALAPPDATA\Cursor"
$cursorUpdater = "$env:LOCALAPPDATA\cursor-updater"
$storageJson = "$cursorAppData\User\globalStorage\storage.json"
$backupDir = "$env:TEMP\CursorBackup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "شروع ریست Cursor AI..." -ForegroundColor Green

# ایجاد پشتیبان
if (Test-Path $backupDir) { Remove-Item $backupDir -Recurse -Force }
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
if (Test-Path $cursorAppData) { Copy-Item $cursorAppData $backupDir -Recurse }
if (Test-Path $cursorLocal) { Copy-Item $cursorLocal $backupDir -Recurse }
if (Test-Path $cursorUpdater) { Copy-Item $cursorUpdater $backupDir -Recurse }
Write-Host "پشتیبان در $backupDir گرفته شد." -ForegroundColor Yellow

# پاک کردن پوشه‌ها
if (Test-Path $cursorAppData) { Remove-Item $cursorAppData -Recurse -Force }
if (Test-Path $cursorLocal) { Remove-Item $cursorLocal -Recurse -Force }
if (Test-Path $cursorUpdater) { Remove-Item $cursorUpdater -Recurse -Force }
Write-Host "پوشه‌های Cursor پاک شد." -ForegroundColor Cyan

# تغییر MachineGuid در رجیستری (با پشتیبان)
$regPath = "HKLM:\SOFTWARE\Microsoft\Cryptography"
$oldGuid = Get-ItemProperty -Path $regPath -Name "MachineGuid" -ErrorAction SilentlyContinue
if ($oldGuid) {
    $oldGuidValue = $oldGuid.MachineGuid
    Copy-Item "HKLM:\SOFTWARE\Microsoft\Cryptography" "HKLM:\SOFTWARE\Microsoft\Cryptography_Backup_$(Get-Date -Format 'yyyyMMdd')" -ErrorAction SilentlyContinue
}
$newGuid = [guid]::NewGuid().ToString()
Set-ItemProperty -Path $regPath -Name "MachineGuid" -Value $newGuid -Type String -Force
Write-Host "MachineGuid جدید: $newGuid (قدیمی: $oldGuidValue)" -ForegroundColor Green

# نصب مجدد Cursor (فرض: دانلود دستی از cursor.sh/download)
# اگر Cursor نصب نیست، دستی دانلود و نصب کن
Write-Host "Cursor رو از https://cursor.sh/download دانلود و نصب کن." -ForegroundColor Yellow

# ویرایش storage.json (اگر وجود داشت، اما بعد از پاک کردن جدید می‌شه)
# بعد از نصب، یک بار Cursor رو باز و ببند، بعد این بخش رو دستی یا با اسکریپت پایتون قبلی اجرا کن
Write-Host "حالا Cursor رو باز کن، بدون login ببند، و storage.json رو ویرایش کن (از اسکریپت پایتون قبلی استفاده کن)." -ForegroundColor Cyan

# پایان
Write-Host "ریست کامل شد! با ایمیل موقت login کن تا Pro فعال بشه." -ForegroundColor Green
Write-Host "برای برگردوندن: از پشتیبان $backupDir استفاده کن." -ForegroundColor Red