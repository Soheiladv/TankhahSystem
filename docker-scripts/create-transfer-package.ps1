# اسکریپت ایجاد پکیج برای انتقال به سیستم دیگر
# این اسکریپت یک فایل ZIP شامل تمام فایل‌های لازم ایجاد می‌کند

Write-Host "`n📦 ایجاد پکیج انتقال Docker..." -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outputFile = Join-Path $projectRoot "BudgetsSystem-Docker-Transfer-$timestamp.zip"

# الگوی فایل/پوشه‌هایی که نباید منتقل شوند
$excludePatterns = @(
    "venv",
    "old__venv",
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.zip",
    "*.7z",
    "*.rar",
    "*.bak",
    "*.tmp",
    "BudgetsSystem-Docker-Transfer-*.zip"
)

Write-Host "`n📋 جمع‌آوری خودکار همه پوشه‌ها و اپلیکیشن‌ها (به‌جز موارد غیرضروری)..." -ForegroundColor Yellow

$itemsToInclude = Get-ChildItem -Force | Where-Object {
    $itemName = $_.Name

    # نادیده گرفتن دات‌فایل‌های سیستمی
    if ($itemName -eq "." -or $itemName -eq "..") { return $false }

    foreach ($pattern in $excludePatterns) {
        if ($itemName -like $pattern) {
            Write-Host "  🚫 حذف $itemName (مطابق الگوی $pattern)" -ForegroundColor DarkGray
            return $false
        }
    }
    Write-Host "  ✅ اضافه شد: $itemName" -ForegroundColor Green
    return $true
} | Select-Object -ExpandProperty Name

if ($itemsToInclude.Count -eq 0) {
    Write-Host "❌ هیچ فایلی برای فشرده‌سازی پیدا نشد (ممکن است الگوهای حذف بیش از حد restrictive باشند)" -ForegroundColor Red
    exit 1
}

# افزودن فایل .env اگر وجود دارد (اختیاری - معمولاً نباید منتقل شود)
$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) {
    Write-Host "`n⚠ فایل .env پیدا شد. آیا می‌خواهید آن را نیز شامل کنید؟" -ForegroundColor Yellow
    Write-Host "  (توصیه: خیر، چون باید در سیستم مقصد تنظیم شود)" -ForegroundColor Gray
    $includeEnv = Read-Host "شامل شود؟ (y/n)"
    if ($includeEnv -eq "y" -or $includeEnv -eq "Y") {
        $itemsToInclude += ".env"
    }
}

# بررسی فایل‌های secrets
Write-Host "`n🔐 بررسی فایل‌های Secrets..." -ForegroundColor Yellow
$secretsDir = Join-Path $projectRoot "secrets"
if (Test-Path $secretsDir) {
    $secretFiles = Get-ChildItem $secretsDir -Filter "*.txt"
    if ($secretFiles.Count -gt 0) {
        Write-Host "  ⚠ فایل‌های secrets پیدا شدند:" -ForegroundColor Yellow
        $secretFiles | ForEach-Object {
            Write-Host "    - $($_.Name)" -ForegroundColor Gray
        }
        Write-Host "  💡 این فایل‌ها در پکیج شامل می‌شوند." -ForegroundColor Cyan
        Write-Host "     حتماً پس از انتقال، دسترسی آن‌ها را محدود کنید!" -ForegroundColor Yellow
    }
}

# ایجاد فایل ZIP
Write-Host "`n📦 در حال ایجاد فایل ZIP..." -ForegroundColor Yellow

try {
    # حذف فایل قبلی اگر وجود دارد
    if (Test-Path $outputFile) {
        Remove-Item $outputFile -Force
    }

    # ایجاد ZIP
    Compress-Archive -Path $itemsToInclude -DestinationPath $outputFile -CompressionLevel Optimal -Force

    $fileSize = (Get-Item $outputFile).Length / 1MB
    Write-Host "  ✅ فایل ZIP ایجاد شد: $outputFile" -ForegroundColor Green
    Write-Host "  📊 حجم فایل: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
}
catch {
    Write-Host "  ❌ خطا در ایجاد فایل ZIP: $_" -ForegroundColor Red
    exit 1
}

# خلاصه
Write-Host "`n" + ("=" * 50) -ForegroundColor Cyan
Write-Host "✅ پکیج انتقال آماده است!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Cyan

Write-Host "`n📦 فایل ایجاد شده:" -ForegroundColor Yellow
Write-Host "  $outputFile" -ForegroundColor Cyan

Write-Host "`n📋 مراحل بعدی:" -ForegroundColor Yellow
Write-Host "  1. انتقال فایل ZIP به سیستم مقصد" -ForegroundColor Gray
Write-Host "  2. Extract کردن در سیستم مقصد" -ForegroundColor Gray
Write-Host "  3. اجرای: .\docker-scripts\check-docker-setup.ps1 -Fix" -ForegroundColor Gray
Write-Host "  4. اجرای: .\docker-scripts\run-docker.ps1" -ForegroundColor Gray

Write-Host "`n⚠ نکات مهم:" -ForegroundColor Yellow
Write-Host "  - فایل‌های secrets در پکیج هستند. امنیت آن‌ها را حفظ کنید!" -ForegroundColor Red
Write-Host "  - در سیستم مقصد حتماً دسترسی secrets را محدود کنید" -ForegroundColor Yellow
Write-Host "  - فایل .env باید در سیستم مقصد تنظیم شود" -ForegroundColor Yellow

Write-Host "`n"

