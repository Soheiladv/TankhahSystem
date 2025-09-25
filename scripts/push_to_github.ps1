# ارسال خودکار تغییرات پروژه به گیت‌هاب با پیام کمیت فارسی
# استفاده:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\push_to_github.ps1 -Message "توضیح دلخواه"

param(
    [string]$Message = ""
)

# شروع ارسال
Write-Host "ارسال به گیت‌هاب شروع شد..." -ForegroundColor Cyan

# رفتن به ریشه پروژه (یکی بالاتر از مسیر اسکریپت)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptDir "..")
Set-Location $repoRoot

# بررسی وجود Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git نصب نیست یا در PATH نیست."
    exit 1
}

# دریافت نام شاخه جاری
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) { $branch = "main" }

# مرحله‌بندی همه تغییرات
& git add -A | Out-Null

# خلاصه تغییرات بر اساس وضعیت porcelain
$status = git status --porcelain
$lines = $status -split "`n" | Where-Object { $_ -ne "" }
$added = ($lines | Where-Object { $_ -match '^[\?\?]|^A ' }).Count
$modified = ($lines | Where-Object { $_ -match '^ M |^M ' }).Count
$deleted = ($lines | Where-Object { $_ -match '^ D |^D ' }).Count
$renamed = ($lines | Where-Object { $_ -match '^R ' }).Count
$untracked = ($lines | Where-Object { $_ -match '^[\?\?]' }).Count

# تاریخ و ساعت
$now = Get-Date -Format "yyyy-MM-dd HH:mm"

# ساخت پیام کمیت فارسی
$summaryLines = @()
$summaryLines += "تاریخ: $now"
$summaryLines += "شاخه: $branch"
$summaryLines += "تغییرات: +$added ~ $modified -$deleted ⟲$renamed | فایل‌های جدید: $untracked"
if ($Message -and $Message.Trim().Length -gt 0) {
    $summaryLines += "توضیحات: $Message"
}

$commitTitle = "به‌روزرسانی خودکار پروژه - $now"
$commitBody = ($summaryLines -join "`n")
$commitMsg = "$commitTitle`n`n$commitBody"

# اگر چیزی برای کمیت نیست، خروج با پیام مناسب
if (-not $status) {
    Write-Host "تغییری برای ارسال وجود ندارد." -ForegroundColor Yellow
    exit 0
}

# انجام کمیت
$commitResult = & git commit -m $commitMsg 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "خطا در commit: $commitResult"
    exit 1
}

# پوش به ریموت
$pushResult = & git push origin $branch 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "خطا در push: $pushResult"
    exit 1
}

Write-Host "ارسال با موفقیت انجام شد ✅" -ForegroundColor Green


