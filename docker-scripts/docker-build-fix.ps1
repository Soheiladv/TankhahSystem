# اسکریپت build با رفع مشکلات
# این اسکریپت Docker build را با رفع مشکلات اجرا می‌کند

Write-Host "=== Build Docker با رفع مشکلات ===" -ForegroundColor Green

# تغییر به دایرکتوری اصلی پروژه
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# بررسی Docker Desktop
Write-Host "🔍 بررسی Docker Desktop..." -ForegroundColor Yellow
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running"
    }
    Write-Host "✓ Docker Desktop در حال اجرا است" -ForegroundColor Green
}
catch {
    Write-Host "✗ Docker Desktop در حال اجرا نیست" -ForegroundColor Red
    Write-Host "   لطفاً Docker Desktop را باز کنید" -ForegroundColor Yellow
    exit 1
}

# پاک‌سازی اولیه
Write-Host "🧹 پاک‌سازی cache..." -ForegroundColor Yellow
docker builder prune -f | Out-Null

# Build با retry
Write-Host "🔨 شروع build..." -ForegroundColor Yellow
Write-Host "⏳ این فرآیند ممکن است چند دقیقه طول بکشد..." -ForegroundColor Cyan

$maxRetries = 3
$retryCount = 0
$buildSuccess = $false

while ($retryCount -lt $maxRetries -and -not $buildSuccess) {
    $retryCount++
    Write-Host "" -ForegroundColor White
    Write-Host "🔄 تلاش $retryCount از $maxRetries..." -ForegroundColor Yellow

    try {
        # Build با no-cache برای اولین تلاش
        if ($retryCount -eq 1) {
            docker-compose build --no-cache --progress=plain 2>&1 | Tee-Object -Variable buildOutput
        }
        else {
            docker-compose build --progress=plain 2>&1 | Tee-Object -Variable buildOutput
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Build موفق بود!" -ForegroundColor Green
            $buildSuccess = $true
        }
        else {
            Write-Host "❌ Build ناموفق بود" -ForegroundColor Red

            # بررسی نوع خطا
            if ($buildOutput -match "short read|unexpected EOF") {
                Write-Host "⚠️ مشکل در دانلود image از Docker Hub" -ForegroundColor Yellow
                Write-Host "   لطفاً اتصال اینترنت خود را بررسی کنید" -ForegroundColor Yellow

                if ($retryCount -lt $maxRetries) {
                    Write-Host "   منتظر 10 ثانیه قبل از تلاش مجدد..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 10
                }
            }
            elseif ($buildOutput -match "Cannot connect to the Docker daemon") {
                Write-Host "⚠️ مشکل در اتصال به Docker daemon" -ForegroundColor Yellow
                Write-Host "   لطفاً Docker Desktop را Restart کنید" -ForegroundColor Yellow
                exit 1
            }
            else {
                Write-Host "⚠️ خطای نامشخص در build" -ForegroundColor Yellow
                if ($retryCount -lt $maxRetries) {
                    Write-Host "   منتظر 5 ثانیه قبل از تلاش مجدد..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 5
                }
            }
        }
    }
    catch {
        Write-Host "❌ خطا: $_" -ForegroundColor Red
        if ($retryCount -lt $maxRetries) {
            Write-Host "   منتظر 5 ثانیه قبل از تلاش مجدد..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
}

if (-not $buildSuccess) {
    Write-Host "" -ForegroundColor White
    Write-Host "❌ Build بعد از $maxRetries تلاش ناموفق بود" -ForegroundColor Red
    Write-Host "" -ForegroundColor White
    Write-Host "💡 راه‌حل‌های پیشنهادی:" -ForegroundColor Yellow
    Write-Host "  1. اتصال اینترنت خود را بررسی کنید" -ForegroundColor White
    Write-Host "  2. Docker Desktop را Restart کنید" -ForegroundColor White
    Write-Host "  3. از VPN استفاده نکنید" -ForegroundColor White
    Write-Host "  4. تنظیمات پروکسی Docker را بررسی کنید" -ForegroundColor White
    Write-Host "  5. دستور زیر را مستقیماً اجرا کنید:" -ForegroundColor White
    Write-Host "     docker pull python:3.12-slim" -ForegroundColor Cyan
    Write-Host "" -ForegroundColor White
    exit 1
}

Write-Host "" -ForegroundColor White
Write-Host "🎉 Build با موفقیت انجام شد!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "📋 مراحل بعدی:" -ForegroundColor Yellow
Write-Host "  docker-compose up -d" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White


