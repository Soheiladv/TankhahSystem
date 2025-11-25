# اسکریپت امنیت‌سازی فایل‌های Secrets در Windows
# این اسکریپت دسترسی فایل‌های secrets را محدود می‌کند

param(
    [string]$SecretsPath = "secrets"
)

Write-Host "`n🔒 امنیت‌سازی فایل‌های Secrets" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

$fullSecretsPath = Join-Path $projectRoot $SecretsPath

# بررسی وجود پوشه
if (-not (Test-Path $fullSecretsPath)) {
    Write-Host "❌ پوشه $fullSecretsPath پیدا نشد" -ForegroundColor Red
    Write-Host "لطفاً ابتدا فایل‌های secrets را ایجاد کنید:" -ForegroundColor Yellow
    Write-Host "  .\docker-scripts\setup-secrets.ps1" -ForegroundColor Cyan
    exit 1
}

# بررسی وجود فایل‌های secrets
$secretFiles = Get-ChildItem -Path $fullSecretsPath -Filter "*.txt" -ErrorAction SilentlyContinue
if (-not $secretFiles) {
    Write-Host "⚠ هیچ فایل secret پیدا نشد" -ForegroundColor Yellow
    Write-Host "لطفاً ابتدا فایل‌های secrets را ایجاد کنید:" -ForegroundColor Yellow
    Write-Host "  .\docker-scripts\setup-secrets.ps1" -ForegroundColor Cyan
    exit 1
}

Write-Host "`n📁 فایل‌های پیدا شده:" -ForegroundColor Yellow
$secretFiles | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

# محدود کردن دسترسی فایل‌ها
Write-Host "`n🔐 محدود کردن دسترسی‌ها..." -ForegroundColor Yellow

try {
    # دریافت کاربر جاری
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

    foreach ($file in $secretFiles) {
        $filePath = $file.FullName

        # حذف دسترسی‌های ارثی
        icacls $filePath /inheritance:r 2>&1 | Out-Null

        # فقط دسترسی کاربر جاری (Full Control)
        icacls $filePath /grant:r "${currentUser}:F" 2>&1 | Out-Null

        # حذف دسترسی‌های عمومی
        icacls $filePath /remove "Everyone" 2>&1 | Out-Null
        icacls $filePath /remove "Users" 2>&1 | Out-Null
        icacls $filePath /remove "Authenticated Users" 2>&1 | Out-Null
        icacls $filePath /remove "BUILTIN\Users" 2>&1 | Out-Null

        Write-Host "  ✓ $($file.Name) محافظت شد" -ForegroundColor Green
    }

    # محدود کردن دسترسی به خود پوشه
    icacls $fullSecretsPath /inheritance:r 2>&1 | Out-Null
    icacls $fullSecretsPath /grant:r "${currentUser}:F" 2>&1 | Out-Null
    icacls $fullSecretsPath /remove "Everyone" 2>&1 | Out-Null
    icacls $fullSecretsPath /remove "Users" 2>&1 | Out-Null

    Write-Host "  ✓ پوشه $SecretsPath محافظت شد" -ForegroundColor Green

}
catch {
    Write-Host "❌ خطا در محدود کردن دسترسی‌ها: $_" -ForegroundColor Red
    exit 1
}

# بررسی Git
Write-Host "`n🔍 بررسی Git..." -ForegroundColor Yellow

if (Test-Path ".git") {
    try {
        $trackedSecrets = git ls-files "$SecretsPath/" 2>$null

        if ($trackedSecrets) {
            Write-Host "⚠ هشدار امنیتی: فایل‌های secrets در Git track شده‌اند:" -ForegroundColor Red
            $trackedSecrets | ForEach-Object {
                Write-Host "  - $_" -ForegroundColor Red
            }
            Write-Host "`n💡 برای حذف آن‌ها از Git (بدون حذف از دیسک):" -ForegroundColor Yellow
            Write-Host "  git rm --cached $SecretsPath/*.txt" -ForegroundColor Cyan
            Write-Host "  git commit -m 'Remove secrets from git tracking'" -ForegroundColor Cyan
        }
        else {
            Write-Host "  ✅ هیچ فایل secret در Git track نشده است" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  ⚠ نتوانست Git را بررسی کند (ممکن است Git نصب نباشد)" -ForegroundColor Yellow
    }
}
else {
    Write-Host "  ℹ این پروژه یک مخزن Git نیست" -ForegroundColor Gray
}

# بررسی .gitignore
Write-Host "`n📋 بررسی .gitignore..." -ForegroundColor Yellow

if (Test-Path ".gitignore") {
    $gitignoreContent = Get-Content ".gitignore" -Raw

    if ($gitignoreContent -match "secrets.*\.txt") {
        Write-Host "  ✅ فایل‌های secrets در .gitignore هستند" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠ فایل‌های secrets ممکن است در .gitignore نباشند" -ForegroundColor Yellow
        Write-Host "  💡 اضافه کردن به .gitignore:" -ForegroundColor Yellow
        Write-Host "    secrets/*.txt" -ForegroundColor Cyan
    }
}
else {
    Write-Host "  ⚠ فایل .gitignore پیدا نشد" -ForegroundColor Yellow
}

# نمایش دسترسی‌های فعلی
Write-Host "`n📊 دسترسی‌های فعلی:" -ForegroundColor Yellow
foreach ($file in $secretFiles) {
    Write-Host "`n  $($file.Name):" -ForegroundColor Gray
    icacls $file.FullName 2>&1 | Select-String -Pattern "BUILTIN|Users|Everyone" | ForEach-Object {
        Write-Host "    $_" -ForegroundColor DarkGray
    }
}

Write-Host "`n✅ امنیت‌سازی با موفقیت انجام شد!" -ForegroundColor Green
Write-Host "`n💡 نکات مهم:" -ForegroundColor Yellow
Write-Host "  - فایل‌های secrets اکنون فقط توسط شما قابل دسترسی هستند" -ForegroundColor Gray
Write-Host "  - هرگز این فایل‌ها را در Git commit نکنید" -ForegroundColor Gray
Write-Host "  - در صورت نیاز به به‌اشتراک‌گذاری، از روش‌های امن استفاده کنید" -ForegroundColor Gray
Write-Host "`n"

