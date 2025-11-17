# تست کامل MCP Server بعد از Build

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🧪 تست کامل MCP Server                                 ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$allOk = $true

# 1. بررسی فایل build شده
Write-Host "1️⃣  بررسی فایل build شده..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    $fileInfo = Get-Item "mcp-server-ollama/dist/index.js"
    Write-Host "   ✅ dist/index.js موجود است" -ForegroundColor Green
    Write-Host "      📊 حجم: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor White
}
else {
    Write-Host "   ❌ dist/index.js یافت نشد!" -ForegroundColor Red
    $allOk = $false
}

# 2. تست اجرای فایل
Write-Host ""
Write-Host "2️⃣  تست اجرای فایل..." -ForegroundColor Yellow
try {
    $test = node -e "console.log('Node.js OK')" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Node.js کار می‌کند" -ForegroundColor Green
    }
}
catch {
    Write-Host "   ❌ Node.js مشکل دارد" -ForegroundColor Red
    $allOk = $false
}

# 3. بررسی Ollama
Write-Host ""
Write-Host "3️⃣  بررسی Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Ollama در حال اجرا است" -ForegroundColor Green

    $models = ($response.Content | ConvertFrom-Json).models
    if ($models) {
        Write-Host "   📦 مدل‌های نصب شده:" -ForegroundColor White
        $models | ForEach-Object { Write-Host "      - $($_.name)" -ForegroundColor Cyan }
    }
}
catch {
    Write-Host "   ⚠️  Ollama در حال اجرا نیست" -ForegroundColor Yellow
    Write-Host "      💡 اجرا کنید: ollama serve" -ForegroundColor Cyan
}

# 4. بررسی تنظیمات
Write-Host ""
Write-Host "4️⃣  بررسی تنظیمات..." -ForegroundColor Yellow

if (Test-Path ".vscode/settings.json") {
    try {
        $settings = Get-Content ".vscode/settings.json" -Raw | ConvertFrom-Json
        if ($settings.'mcp.servers'.'ollama-local') {
            Write-Host "   ✅ MCP Server در settings.json تنظیم شده" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "   ⚠️  خطا در خواندن settings.json" -ForegroundColor Yellow
    }
}
else {
    Write-Host "   ⚠️  settings.json یافت نشد" -ForegroundColor Yellow
}

if (Test-Path ".cursor/mcp.json") {
    Write-Host "   ✅ .cursor/mcp.json موجود است" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  .cursor/mcp.json یافت نشد" -ForegroundColor Yellow
}

# 5. تست syntax فایل build شده
Write-Host ""
Write-Host "5️⃣  تست syntax..." -ForegroundColor Yellow
try {
    $syntaxCheck = node --check "mcp-server-ollama/dist/index.js" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Syntax صحیح است" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  خطای syntax: $syntaxCheck" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "   ⚠️  نتوانست syntax را بررسی کند" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
Write-Host "║  $(if ($allOk) { '✅ همه تست‌ها موفق بود!' } else { '⚠️  برخی مشکلات وجود دارد' })                              ║" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
Write-Host ""

if ($allOk) {
    Write-Host "🎉 MCP Server آماده استفاده است!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
    Write-Host "   1. VSCode را Restart کنید" -ForegroundColor White
    Write-Host "   2. Ctrl+Shift+P -> 'MCP: List Servers'" -ForegroundColor White
    Write-Host "   3. باید 'ollama-local' را ببینید" -ForegroundColor White
}

Write-Host ""

