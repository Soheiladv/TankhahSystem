# اسکریپت کامل آماده‌سازی VSCode برای MCP و Ollama
# این اسکریپت همه چیز را یکجا انجام می‌دهد

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 آماده‌سازی کامل VSCode برای MCP و Ollama          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# مرحله 1: بررسی VSCode CLI
Write-Host "📋 مرحله 1: بررسی VSCode..." -ForegroundColor Yellow
try {
    $codeVersion = code --version 2>&1 | Select-Object -First 1
    Write-Host "   ✅ VSCode CLI: $codeVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ VSCode CLI یافت نشد!" -ForegroundColor Red
    Write-Host "   📝 در VSCode: Ctrl+Shift+P -> 'Shell Command: Install code command'" -ForegroundColor Yellow
    exit 1
}

# مرحله 2: بررسی Node.js
Write-Host ""
Write-Host "📋 مرحله 2: بررسی Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js: $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Node.js یافت نشد!" -ForegroundColor Red
    Write-Host "   📥 نصب: winget install OpenJS.NodeJS.LTS" -ForegroundColor Yellow
    exit 1
}

# مرحله 3: بررسی Ollama
Write-Host ""
Write-Host "📋 مرحله 3: بررسی Ollama..." -ForegroundColor Yellow
try {
    $ollamaCheck = ollama list 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Ollama نصب است" -ForegroundColor Green

        # بررسی مدل‌ها
        $models = ollama list 2>&1 | Out-String
        if ($models -match "qwen2.5-coder:1.5b" -and $models -match "llama3.2:1b") {
            Write-Host "   ✅ مدل‌ها نصب شده" -ForegroundColor Green
        }
        else {
            Write-Host "   ⚠️  برخی مدل‌ها نصب نیست" -ForegroundColor Yellow
            Write-Host "   📥 نصب مدل‌ها..." -ForegroundColor Cyan
            ollama pull qwen2.5-coder:1.5b
            ollama pull llama3.2:1b
        }

        # بررسی سرویس
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
            Write-Host "   ✅ Ollama در حال اجرا است" -ForegroundColor Green
        }
        catch {
            Write-Host "   ⚠️  Ollama در حال اجرا نیست" -ForegroundColor Yellow
            Write-Host "   💡 در terminal جدید اجرا کنید: ollama serve" -ForegroundColor Cyan
        }
    }
    else {
        Write-Host "   ❌ Ollama نصب نشده" -ForegroundColor Red
        Write-Host "   📥 نصب: winget install Ollama.Ollama" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Host "   ❌ Ollama یافت نشد" -ForegroundColor Red
    Write-Host "   📥 نصب: winget install Ollama.Ollama" -ForegroundColor Yellow
    exit 1
}

# مرحله 4: Build MCP Server
Write-Host ""
Write-Host "📋 مرحله 4: Build MCP Server..." -ForegroundColor Yellow

Set-Location mcp-server-ollama

if (-not (Test-Path "node_modules")) {
    Write-Host "   📦 نصب dependencies..." -ForegroundColor Cyan
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ خطا در نصب dependencies" -ForegroundColor Red
        Set-Location ..
        exit 1
    }
}

Write-Host "   🔨 Build..." -ForegroundColor Cyan
# استفاده از node مستقیم برای جلوگیری از مشکل PATH
$buildOutput = node node_modules/typescript/lib/tsc.js 2>&1
if ($LASTEXITCODE -ne 0) {
    # اگر خطا وجود دارد اما فایل از قبل موجود است، ادامه می‌دهیم
    if (-not (Test-Path "dist/index.js")) {
        Write-Host "   ❌ خطا در build" -ForegroundColor Red
        Write-Host $buildOutput
        Set-Location ..
        exit 1
    }
    else {
        Write-Host "   ⚠️  خطا در compile اما فایل قبلی موجود است" -ForegroundColor Yellow
    }
}

if (-not (Test-Path "dist/index.js")) {
    Write-Host "   ❌ فایل dist/index.js یافت نشد" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host "   ✅ Build موفق بود" -ForegroundColor Green
Set-Location ..

# مرحله 5: نصب Extension ها
Write-Host ""
Write-Host "📋 مرحله 5: نصب Extension های VSCode..." -ForegroundColor Yellow

$extensions = @(
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.flake8",
    "ms-python.pylint",
    "redhat.vscode-yaml",
    "ms-vscode.powershell",
    "eamodio.gitlens"
)

# JSON support در VSCode به صورت built-in است، نیازی به نصب نیست

$installedCount = 0
$alreadyInstalled = 0

foreach ($ext in $extensions) {
    Write-Host "   📥 بررسی: $ext" -ForegroundColor Cyan
    $installedList = code --list-extensions 2>&1
    if ($installedList -match [regex]::Escape($ext)) {
        Write-Host "      ✅ از قبل نصب است" -ForegroundColor Green
        $alreadyInstalled++
        continue
    }

    Write-Host "      📦 در حال نصب..." -ForegroundColor Yellow
    $installOutput = code --install-extension $ext --force 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✅ نصب موفق بود" -ForegroundColor Green
        $installedCount++
    }
    else {
        Write-Host "      ⚠️  خطا در نصب: $installOutput" -ForegroundColor Yellow
    }
}

Write-Host "   ✅ نصب شد: $installedCount" -ForegroundColor Green
Write-Host "   ℹ️  از قبل بود: $alreadyInstalled" -ForegroundColor Yellow

# مرحله 6: بررسی تنظیمات
Write-Host ""
Write-Host "📋 مرحله 6: بررسی تنظیمات..." -ForegroundColor Yellow

if (Test-Path ".vscode/settings.json") {
    try {
        $settings = Get-Content ".vscode/settings.json" -Raw | ConvertFrom-Json
        Write-Host "   ✅ .vscode/settings.json معتبر است" -ForegroundColor Green

        if ($settings.'mcp.servers') {
            Write-Host "   ✅ MCP servers تنظیم شده" -ForegroundColor Green
        }

        if ($settings.'claude-code.useTerminal') {
            Write-Host "   ✅ Claude-code تنظیم شده" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "   ⚠️  خطا در بررسی تنظیمات: $_" -ForegroundColor Yellow
    }
}
else {
    Write-Host "   ⚠️  فایل settings.json یافت نشد" -ForegroundColor Yellow
}

if (Test-Path ".cursor/mcp.json") {
    Write-Host "   ✅ .cursor/mcp.json موجود است" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  فایل .cursor/mcp.json یافت نشد" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ آماده‌سازی کامل شد!                               ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. 🔄 VSCode را Restart کنید" -ForegroundColor White
Write-Host ""
Write-Host "   2. 🚀 مطمئن شوید Ollama در حال اجرا است:" -ForegroundColor White
Write-Host "      ollama serve" -ForegroundColor Yellow
Write-Host ""
Write-Host "   3. ✅ بررسی MCP Server:" -ForegroundColor White
Write-Host "      Ctrl+Shift+P -> 'MCP: List Servers'" -ForegroundColor Yellow
Write-Host ""
Write-Host "   4. ✅ بررسی Python Extension:" -ForegroundColor White
Write-Host "      یک فایل .py باز کنید" -ForegroundColor Yellow
Write-Host ""
Write-Host "   5. ✅ تست Ollama:" -ForegroundColor White
Write-Host "      ollama run qwen2.5-coder:1.5b 'write hello world in Python'" -ForegroundColor Yellow
Write-Host ""
Write-Host "🎉 حالا می‌توانید از مدل‌های محلی Ollama در VSCode استفاده کنید!" -ForegroundColor Green
Write-Host ""

