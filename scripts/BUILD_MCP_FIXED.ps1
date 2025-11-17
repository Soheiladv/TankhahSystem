# اسکریپت Build MCP Server (با رفع مشکل TypeScript)
# این اسکریپت مشکل PATH و TypeScript را حل می‌کند

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🔨 Build MCP Server..." -ForegroundColor Cyan
Write-Host ""

Set-Location mcp-server-ollama

# بررسی node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "📦 نصب dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ خطا در نصب dependencies" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
}

# بررسی TypeScript
if (-not (Test-Path "node_modules/typescript/lib/tsc.js")) {
    Write-Host "❌ TypeScript نصب نیست!" -ForegroundColor Red
    Write-Host "📥 در حال نصب TypeScript..." -ForegroundColor Yellow
    npm install typescript --save-dev
}

# Build با استفاده از node مستقیم
Write-Host "🔨 در حال compile..." -ForegroundColor Cyan
node node_modules/typescript/lib/tsc.js

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ خطا در build!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# بررسی فایل build شده
if (-not (Test-Path "dist/index.js")) {
    Write-Host ""
    Write-Host "❌ فایل dist/index.js ساخته نشد!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

$fileInfo = Get-Item "dist/index.js"
Write-Host ""
Write-Host "✅ Build موفق بود!" -ForegroundColor Green
Write-Host "   📄 فایل: dist/index.js" -ForegroundColor White
Write-Host "   📊 حجم: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor White
Write-Host "   📅 تاریخ: $($fileInfo.LastWriteTime)" -ForegroundColor White

Set-Location ..

Write-Host ""
Write-Host "🎉 آماده استفاده است!" -ForegroundColor Green
Write-Host ""

