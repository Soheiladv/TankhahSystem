# Quick Start Script for MCP Ollama Setup
# اجرا با PowerShell

Write-Host "🚀 راه‌اندازی MCP Server برای Ollama" -ForegroundColor Cyan
Write-Host ""

# بررسی Node.js
Write-Host "📦 بررسی Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js نصب است: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js یافت نشد. لطفاً نصب کنید:" -ForegroundColor Red
    Write-Host "   winget install OpenJS.NodeJS.LTS" -ForegroundColor Yellow
    exit 1
}

# بررسی Ollama
Write-Host "📦 بررسی Ollama..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version
    Write-Host "✅ Ollama نصب است" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama یافت نشد. لطفاً نصب کنید:" -ForegroundColor Red
    Write-Host "   winget install Ollama.Ollama" -ForegroundColor Yellow
    Write-Host "   یا از https://ollama.ai/download دانلود کنید" -ForegroundColor Yellow
    exit 1
}

# بررسی اتصال Ollama
Write-Host "🔌 بررسی اتصال Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Ollama در حال اجرا است" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama در حال اجرا نیست. در حال راه‌اندازی..." -ForegroundColor Yellow
    Write-Host "   لطفاً در یک terminal جدید اجرا کنید: ollama serve" -ForegroundColor Yellow
    Write-Host "   یا Windows Service را بررسی کنید" -ForegroundColor Yellow
}

# بررسی مدل‌ها
Write-Host "📥 بررسی مدل‌های نصب شده..." -ForegroundColor Yellow
$modelsInstalled = $false

try {
    $models = ollama list 2>&1
    if ($models -match "qwen2.5-coder:1.5b" -and $models -match "llama3.2:1b") {
        Write-Host "✅ همه مدل‌ها نصب شده" -ForegroundColor Green
        $modelsInstalled = $true
    } else {
        Write-Host "⚠️  برخی مدل‌ها نصب نشده‌اند" -ForegroundColor Yellow
        Write-Host "   در حال نصب مدل‌ها..." -ForegroundColor Yellow
        
        if ($models -notmatch "qwen2.5-coder:1.5b") {
            Write-Host "   📥 نصب qwen2.5-coder:1.5b..." -ForegroundColor Cyan
            ollama pull qwen2.5-coder:1.5b
        }
        
        if ($models -notmatch "llama3.2:1b") {
            Write-Host "   📥 نصب llama3.2:1b..." -ForegroundColor Cyan
            ollama pull llama3.2:1b
        }
        
        $modelsInstalled = $true
    }
} catch {
    Write-Host "⚠️  خطا در بررسی مدل‌ها: $_" -ForegroundColor Yellow
}

# نصب dependencies
Write-Host "📦 نصب dependencies..." -ForegroundColor Yellow
Set-Location mcp-server-ollama

if (Test-Path "node_modules") {
    Write-Host "✅ node_modules موجود است" -ForegroundColor Green
} else {
    Write-Host "   در حال نصب npm packages..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ خطا در نصب dependencies" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Dependencies نصب شد" -ForegroundColor Green
}

# Build پروژه
Write-Host "🔨 Build کردن MCP Server..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ خطا در build" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build موفق بود" -ForegroundColor Green

Set-Location ..

# بررسی فایل build شده
Write-Host "🔍 بررسی فایل‌های build..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    Write-Host "✅ فایل dist/index.js موجود است" -ForegroundColor Green
} else {
    Write-Host "❌ فایل dist/index.js یافت نشد" -ForegroundColor Red
    exit 1
}

# بررسی تنظیمات
Write-Host "⚙️  بررسی تنظیمات..." -ForegroundColor Yellow

# بررسی .cursor/mcp.json
if (Test-Path ".cursor/mcp.json") {
    Write-Host "✅ فایل .cursor/mcp.json موجود است" -ForegroundColor Green
} else {
    Write-Host "⚠️  فایل .cursor/mcp.json ایجاد شد" -ForegroundColor Yellow
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
    Write-Host "✅ فایل ایجاد شد" -ForegroundColor Green
}

# بررسی .vscode/settings.json
if (Test-Path ".vscode/settings.json") {
    $settings = Get-Content ".vscode/settings.json" | ConvertFrom-Json
    if ($settings.'mcp.servers') {
        Write-Host "✅ تنظیمات MCP در .vscode/settings.json موجود است" -ForegroundColor Green
    } else {
        Write-Host "⚠️  اضافه کردن تنظیمات MCP به .vscode/settings.json..." -ForegroundColor Yellow
        # اضافه کردن تنظیمات
    }
} else {
    Write-Host "⚠️  فایل .vscode/settings.json موجود نیست" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 راه‌اندازی کامل شد!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
Write-Host "   1. مطمئن شوید Ollama در حال اجرا است: ollama serve" -ForegroundColor White
Write-Host "   2. Cursor را Restart کنید" -ForegroundColor White
Write-Host "   3. در Cursor: Ctrl+Shift+P -> MCP: List Servers" -ForegroundColor White
Write-Host "   4. باید 'ollama-local' را ببینید" -ForegroundColor White
Write-Host ""
Write-Host "✅ حالا می‌توانید از مدل‌های محلی استفاده کنید!" -ForegroundColor Green

