# اسکریپت راه‌اندازی سریع Ollama و MCP Server
# اجرا در PowerShell از ریشه پروژه

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  راه‌اندازی Ollama MCP Server برای مدل‌های محلی       ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# مرحله 1: بررسی Ollama
Write-Host "🔍 مرحله 1: بررسی Ollama..." -ForegroundColor Yellow
try {
    $ollamaCheck = ollama list 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Ollama نصب و در حال اجرا است" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Ollama یافت نشد" -ForegroundColor Red
        Write-Host "   📥 نصب Ollama..." -ForegroundColor Yellow
        Write-Host "   لطفاً از https://ollama.ai/download دانلود کنید یا:" -ForegroundColor White
        Write-Host "   winget install Ollama.Ollama" -ForegroundColor Cyan
        exit 1
    }
} catch {
    Write-Host "   ❌ Ollama نصب نشده است" -ForegroundColor Red
    Write-Host "   لطفاً ابتدا Ollama را نصب کنید" -ForegroundColor Yellow
    exit 1
}

# بررسی اتصال
Write-Host "   🔌 بررسی اتصال به Ollama API..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Ollama API در دسترس است" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Ollama در حال اجرا نیست. در حال راه‌اندازی..." -ForegroundColor Yellow
    Write-Host "   💡 راهنما: در یک terminal جدید اجرا کنید:" -ForegroundColor Cyan
    Write-Host "      ollama serve" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "   آیا می‌خواهید ادامه دهید؟ (y/n)"
    if ($continue -ne 'y') {
        exit 0
    }
}

# مرحله 2: بررسی و نصب مدل‌ها
Write-Host ""
Write-Host "📥 مرحله 2: بررسی مدل‌ها..." -ForegroundColor Yellow

$models = ollama list 2>&1 | Out-String
$modelsToInstall = @()

if ($models -notmatch "qwen2.5-coder:1.5b") {
    Write-Host "   ⚠️  qwen2.5-coder:1.5b نصب نیست" -ForegroundColor Yellow
    $modelsToInstall += "qwen2.5-coder:1.5b"
} else {
    Write-Host "   ✅ qwen2.5-coder:1.5b نصب است" -ForegroundColor Green
}

if ($models -notmatch "llama3.2:1b") {
    Write-Host "   ⚠️  llama3.2:1b نصب نیست" -ForegroundColor Yellow
    $modelsToInstall += "llama3.2:1b"
} else {
    Write-Host "   ✅ llama3.2:1b نصب است" -ForegroundColor Green
}

if ($modelsToInstall.Count -gt 0) {
    Write-Host ""
    Write-Host "   📥 نصب مدل‌های مورد نیاز..." -ForegroundColor Cyan
    foreach ($model in $modelsToInstall) {
        Write-Host "   📦 در حال نصب $model (این ممکن است چند دقیقه طول بکشد)..." -ForegroundColor Yellow
        ollama pull $model
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ $model با موفقیت نصب شد" -ForegroundColor Green
        } else {
            Write-Host "   ❌ خطا در نصب $model" -ForegroundColor Red
            exit 1
        }
    }
}

# مرحله 3: بررسی Node.js
Write-Host ""
Write-Host "📦 مرحله 3: بررسی Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js نصب است: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Node.js یافت نشد" -ForegroundColor Red
    Write-Host "   📥 نصب Node.js..." -ForegroundColor Yellow
    Write-Host "   winget install OpenJS.NodeJS.LTS" -ForegroundColor Cyan
    exit 1
}

# مرحله 4: نصب و Build MCP Server
Write-Host ""
Write-Host "🔨 مرحله 4: نصب و Build MCP Server..." -ForegroundColor Yellow

Set-Location mcp-server-ollama

# نصب dependencies
if (-not (Test-Path "node_modules")) {
    Write-Host "   📦 نصب npm packages..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ خطا در نصب dependencies" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
    Write-Host "   ✅ Dependencies نصب شد" -ForegroundColor Green
} else {
    Write-Host "   ✅ node_modules موجود است" -ForegroundColor Green
}

# Build
Write-Host "   🔨 Build کردن TypeScript..." -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ❌ خطا در build" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# بررسی فایل build شده
if (-not (Test-Path "dist/index.js")) {
    Write-Host "   ❌ فایل dist/index.js یافت نشد" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host "   ✅ Build موفق بود" -ForegroundColor Green
Set-Location ..

# مرحله 5: بررسی تنظیمات
Write-Host ""
Write-Host "⚙️  مرحله 5: بررسی تنظیمات..." -ForegroundColor Yellow

# بررسی .cursor/mcp.json
if (Test-Path ".cursor/mcp.json") {
    Write-Host "   ✅ فایل .cursor/mcp.json موجود است" -ForegroundColor Green
} else {
    Write-Host "   📝 ایجاد فایل .cursor/mcp.json..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path ".cursor" | Out-Null
    @"
{
  "mcpServers": {
    "ollama-local": {
      "command": "node",
      "args": [
        "`${workspaceFolder}/mcp-server-ollama/dist/index.js"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
"@ | Out-File -FilePath ".cursor/mcp.json" -Encoding UTF8
    Write-Host "   ✅ فایل ایجاد شد" -ForegroundColor Green
}

# بررسی .vscode/settings.json
if (Test-Path ".vscode/settings.json") {
    $settings = Get-Content ".vscode/settings.json" -Raw | ConvertFrom-Json
    if ($settings.'mcp.servers') {
        Write-Host "   ✅ تنظیمات MCP در .vscode/settings.json موجود است" -ForegroundColor Green
    }
}

# مرحله 6: تست
Write-Host ""
Write-Host "🧪 مرحله 6: تست اتصال..." -ForegroundColor Yellow

# تست Ollama
try {
    $testResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get
    Write-Host "   ✅ اتصال به Ollama موفق بود" -ForegroundColor Green
    Write-Host "   📋 مدل‌های موجود:" -ForegroundColor Cyan
    foreach ($model in $testResponse.models) {
        Write-Host "      - $($model.name)" -ForegroundColor White
    }
} catch {
    Write-Host "   ⚠️  خطا در اتصال به Ollama: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ راه‌اندازی کامل شد!                                ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. مطمئن شوید Ollama در حال اجرا است:" -ForegroundColor White
Write-Host "      ollama serve" -ForegroundColor Yellow
Write-Host ""
Write-Host "   2. Cursor یا VSCode را Restart کنید" -ForegroundColor White
Write-Host ""
Write-Host "   3. در Cursor: Ctrl+Shift+P -> 'MCP: List Servers'" -ForegroundColor White
Write-Host "      باید 'ollama-local' را ببینید" -ForegroundColor White
Write-Host ""
Write-Host "   4. حالا من (Auto) می‌توانم از مدل‌های محلی کمک بگیرم! 🎉" -ForegroundColor Green
Write-Host ""
Write-Host "💡 تست سریع:" -ForegroundColor Cyan
Write-Host "   ollama run qwen2.5-coder:1.5b 'write hello world in Python'" -ForegroundColor Yellow
Write-Host ""

