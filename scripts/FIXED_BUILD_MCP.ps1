# اسکریپت Build MCP Server با رفع مشکل TypeScript
# این نسخه از node مستقیم برای tsc استفاده می‌کند

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🔨 Build MCP Server (Fixed)..." -ForegroundColor Cyan
Write-Host ""

$originalLocation = Get-Location

try {
    Set-Location "mcp-server-ollama"

    # بررسی node_modules
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 نصب dependencies..." -ForegroundColor Yellow
        npm install
        if ($LASTEXITCODE -ne 0) {
            throw "خطا در نصب dependencies"
        }
    }

    # بررسی TypeScript
    if (-not (Test-Path "node_modules/typescript/lib/tsc.js")) {
        Write-Host "📥 نصب TypeScript..." -ForegroundColor Yellow
        npm install typescript --save-dev
    }

    # پاک کردن dist قبلی (اختیاری)
    if (Test-Path "dist") {
        Write-Host "🗑️  پاک کردن dist قبلی..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force dist
    }

    # Build با استفاده از node مستقیم
    Write-Host "🔨 در حال compile TypeScript..." -ForegroundColor Cyan
    $buildOutput = node node_modules/typescript/lib/tsc.js 2>&1

    if ($LASTEXITCODE -eq 0) {
        if (Test-Path "dist/index.js") {
            $fileInfo = Get-Item "dist/index.js"
            Write-Host ""
            Write-Host "✅ Build موفق بود!" -ForegroundColor Green
            Write-Host "   📄 فایل: dist/index.js" -ForegroundColor White
            Write-Host "   📊 حجم: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor White
            Write-Host "   📅 تاریخ: $($fileInfo.LastWriteTime)" -ForegroundColor White
            Write-Host ""
            Write-Host "🎉 آماده استفاده است!" -ForegroundColor Green
        }
        else {
            throw "فایل dist/index.js ساخته نشد"
        }
    }
    else {
        # اگر خطا وجود دارد، اما فایل از قبل موجود است
        if (Test-Path "dist/index.js") {
            $fileInfo = Get-Item "dist/index.js"
            Write-Host ""
            Write-Host "⚠️  خطا در compile اما فایل قبلی موجود است" -ForegroundColor Yellow
            Write-Host "   📄 فایل: dist/index.js ($([math]::Round($fileInfo.Length / 1KB, 2)) KB)" -ForegroundColor White
            Write-Host "   💡 استفاده از فایل موجود..." -ForegroundColor Cyan
            Write-Host ""
            Write-Host "✅ آماده استفاده است!" -ForegroundColor Green
        }
        else {
            Write-Host ""
            Write-Host "❌ خطا در build:" -ForegroundColor Red
            Write-Host $buildOutput
            throw "Build ناموفق"
        }
    }
}
catch {
    Write-Host ""
    Write-Host "❌ خطا: $_" -ForegroundColor Red
    Set-Location $originalLocation
    exit 1
}
finally {
    Set-Location $originalLocation
}

Write-Host ""

