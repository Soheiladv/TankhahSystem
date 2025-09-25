# اسکریپت پیشرفته ارسال خودکار به گیت‌هاب با تحلیل هوشمند تغییرات
# Advanced Git Push with Smart Change Analysis

param(
    [string]$Message = "",
    [switch]$Auto,
    [switch]$DryRun,
    [switch]$Help
)

# نمایش راهنما
if ($Help) {
    Write-Host @"
🚀 اسکریپت پیشرفته ارسال خودکار به گیت‌هاب

استفاده:
  .\scripts\advanced_push.ps1 -Message "توضیح دلخواه"
  .\scripts\advanced_push.ps1 -Auto
  .\scripts\advanced_push.ps1 -DryRun
  .\scripts\advanced_push.ps1 -Help

گزینه‌ها:
  -Message    پیام دلخواه برای کمیت
  -Auto       ارسال خودکار بدون پیام
  -DryRun     فقط نمایش پیام کمیت بدون ارسال
  -Help       نمایش این راهنما

مثال‌ها:
  .\scripts\advanced_push.ps1 -Message "اضافه کردن سیستم تنظیمات"
  .\scripts\advanced_push.ps1 -Auto
  .\scripts\advanced_push.ps1 -DryRun
"@ -ForegroundColor Cyan
    exit 0
}

# بررسی وجود Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "❌ Python نصب نیست یا در PATH نیست."
    Write-Host "لطفاً Python را نصب کنید: https://python.org" -ForegroundColor Yellow
    exit 1
}

# بررسی وجود اسکریپت Python
$scriptPath = Join-Path $PSScriptRoot "smart_git_push.py"
if (-not (Test-Path $scriptPath)) {
    Write-Error "❌ اسکریپت Python پیدا نشد: $scriptPath"
    exit 1
}

# ساخت آرگومان‌ها
$args = @()
if ($Message) { $args += "--message", "`"$Message`"" }
if ($Auto) { $args += "--auto" }
if ($DryRun) { $args += "--dry-run" }

# اجرای اسکریپت Python
Write-Host "🐍 اجرای اسکریپت Python..." -ForegroundColor Green
try {
    & python $scriptPath @args
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "✅ عملیات با موفقیت انجام شد!" -ForegroundColor Green
    } else {
        Write-Host "❌ خطا در اجرای اسکریپت" -ForegroundColor Red
    }
    
    exit $exitCode
} catch {
    Write-Error "❌ خطا در اجرای اسکریپت: $_"
    exit 1
}
