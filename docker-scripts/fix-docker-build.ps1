# اسکریپت رفع مشکل build Docker
# این اسکریپت مشکلات build را برطرف می‌کند

Write-Host "=== رفع مشکل Build Docker ===" -ForegroundColor Green

# تغییر به دایرکتوری اصلی پروژه
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "🔍 بررسی مشکلات..." -ForegroundColor Yellow

# 1. پاک‌سازی cache Docker
Write-Host "🧹 پاک‌سازی cache Docker..." -ForegroundColor Yellow
docker system prune -f
docker builder prune -f

# 2. حذف image های ناقص
Write-Host "🗑️ حذف image های ناقص..." -ForegroundColor Yellow
docker images --filter "dangling=true" -q | ForEach-Object {
    docker rmi $_ -f
}

# 3. پاک‌سازی build cache
Write-Host "🧹 پاک‌سازی build cache..." -ForegroundColor Yellow
docker-compose down
docker volume prune -f

# 4. بررسی فایل .env
Write-Host "🔍 بررسی فایل .env..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw

    # بررسی کاراکترهای مشکل‌ساز
    if ($envContent -match '@|#|\$|\*|\!') {
        Write-Host "⚠️ فایل .env دارای کاراکترهای خاص است که ممکن است مشکل ایجاد کند" -ForegroundColor Yellow
        Write-Host "   این کاراکترها در Docker Compose باید escape شوند" -ForegroundColor Yellow
    }

    Write-Host "✓ فایل .env موجود است" -ForegroundColor Green
}
else {
    Write-Host "✗ فایل .env یافت نشد" -ForegroundColor Red
    Write-Host "   لطفاً ابتدا فایل .env را ایجاد کنید:" -ForegroundColor Yellow
    Write-Host "   .\docker-scripts\setup-env.ps1" -ForegroundColor Cyan
    exit 1
}

# 5. بررسی اتصال اینترنت
Write-Host "🌐 بررسی اتصال اینترنت..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://hub.docker.com" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✓ اتصال اینترنت برقرار است" -ForegroundColor Green
}
catch {
    Write-Host "⚠️ مشکل در اتصال به اینترنت" -ForegroundColor Yellow
    Write-Host "   لطفاً اتصال اینترنت خود را بررسی کنید" -ForegroundColor Yellow
}

# 6. پیشنهاد راه‌حل
Write-Host "" -ForegroundColor White
Write-Host "✅ پاک‌سازی انجام شد" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "📋 مراحل بعدی:" -ForegroundColor Yellow
Write-Host "  1. اطمینان حاصل کنید که Docker Desktop در حال اجرا است" -ForegroundColor White
Write-Host "  2. اطمینان حاصل کنید که اتصال اینترنت برقرار است" -ForegroundColor White
Write-Host "  3. دوباره build کنید:" -ForegroundColor White
Write-Host "     docker-compose build --no-cache" -ForegroundColor Cyan
Write-Host "  4. یا از اسکریپت setup استفاده کنید:" -ForegroundColor White
Write-Host "     .\docker-scripts\docker-setup.ps1" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White

# 7. اگر مشکل ادامه داشت، پیشنهاد استفاده از image محلی
Write-Host "💡 اگر مشکل ادامه داشت:" -ForegroundColor Yellow
Write-Host "  - از VPN استفاده نکنید" -ForegroundColor White
Write-Host "  - تنظیمات پروکسی Docker را بررسی کنید" -ForegroundColor White
Write-Host "  - Docker Desktop را Restart کنید" -ForegroundColor White
Write-Host "  - WSL2 را Restart کنید (اگر از WSL2 استفاده می‌کنید)" -ForegroundColor White
Write-Host "" -ForegroundColor White

