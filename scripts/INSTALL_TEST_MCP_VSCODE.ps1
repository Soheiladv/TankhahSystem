# اسکریپت کامل نصب و تست MCP Server برای VSCode
# این بهترین فایل برای نصب و تست است

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 نصب و تست کامل MCP Server برای VSCode                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$originalLocation = Get-Location
$allOk = $true
$warnings = @()

# ============================================================================
# مرحله 1: بررسی و Build MCP Server
# ============================================================================
Write-Host "📋 مرحله 1: بررسی و Build MCP Server..." -ForegroundColor Yellow
Write-Host ""

Set-Location mcp-server-ollama

# بررسی node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "   📦 نصب dependencies..." -ForegroundColor Cyan
    npm install 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   ❌ خطا در نصب dependencies" -ForegroundColor Red
        $allOk = $false
        Set-Location $originalLocation
        exit 1
    }
}

# Build
if (-not (Test-Path "dist/index.js")) {
    Write-Host "   🔨 Build در حال انجام..." -ForegroundColor Cyan
    if (Test-Path "node_modules/typescript/lib/tsc.js") {
        node node_modules/typescript/lib/tsc.js 2>&1 | Out-Null
    }
    else {
        Write-Host "   📥 نصب TypeScript..." -ForegroundColor Cyan
        npm install typescript --save-dev 2>&1 | Out-Null
        node node_modules/typescript/lib/tsc.js 2>&1 | Out-Null
    }
}

if (Test-Path "dist/index.js") {
    $fileInfo = Get-Item "dist/index.js"
    Write-Host "   ✅ Build موفق بود" -ForegroundColor Green
    Write-Host "      📄 فایل: dist/index.js" -ForegroundColor White
    Write-Host "      📊 حجم: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor White
}
else {
    Write-Host "   ❌ Build ناموفق بود" -ForegroundColor Red
    $allOk = $false
}

Set-Location $originalLocation

# ============================================================================
# مرحله 2: تست Syntax
# ============================================================================
Write-Host ""
Write-Host "📋 مرحله 2: تست Syntax..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    $syntaxCheck = node --check "mcp-server-ollama/dist/index.js" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Syntax صحیح است" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  هشدار syntax: $syntaxCheck" -ForegroundColor Yellow
        $warnings += "خطای syntax احتمالی"
    }
}

# ============================================================================
# مرحله 3: بررسی تنظیمات VSCode
# ============================================================================
Write-Host ""
Write-Host "📋 مرحله 3: بررسی تنظیمات VSCode..." -ForegroundColor Yellow

if (Test-Path ".vscode/settings.json") {
    try {
        $settings = Get-Content ".vscode/settings.json" -Raw | ConvertFrom-Json
        if ($settings.'mcp.servers'.'ollama-local') {
            Write-Host "   ✅ MCP Server 'ollama-local' تنظیم شده" -ForegroundColor Green
            $mcp = $settings.'mcp.servers'.'ollama-local'
            Write-Host "      Command: $($mcp.command)" -ForegroundColor White
            Write-Host "      Args: $($mcp.args -join ' ')" -ForegroundColor White
            Write-Host "      OLLAMA_URL: $($mcp.env.OLLAMA_URL)" -ForegroundColor White
        }
        else {
            Write-Host "   ❌ MCP Server تنظیم نشده!" -ForegroundColor Red
            $allOk = $false
        }
    }
    catch {
        Write-Host "   ⚠️  خطا در خواندن settings.json: $_" -ForegroundColor Yellow
        $warnings += "مشکل در خواندن settings.json"
    }
}
else {
    Write-Host "   ❌ فایل settings.json یافت نشد!" -ForegroundColor Red
    $allOk = $false
}

if (Test-Path ".cursor/mcp.json") {
    Write-Host "   ✅ .cursor/mcp.json موجود است" -ForegroundColor Green
}
else {
    Write-Host "   ⚠️  .cursor/mcp.json یافت نشد (اختیاری)" -ForegroundColor Yellow
}

# ============================================================================
# مرحله 4: بررسی Ollama
# ============================================================================
Write-Host ""
Write-Host "📋 مرحله 4: بررسی Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Ollama در حال اجرا است" -ForegroundColor Green

    $models = ($response.Content | ConvertFrom-Json).models
    if ($models) {
        Write-Host "   📦 مدل‌های نصب شده: $($models.Count)" -ForegroundColor White
        $requiredModels = @("qwen2.5-coder:1.5b", "llama3.2:1b")
        $foundModels = @()

        $models | Select-Object -First 5 | ForEach-Object {
            $modelName = $_.name
            $isRequired = $requiredModels | Where-Object { $modelName -like "*$_*" }
            if ($isRequired) {
                Write-Host "      ✅ $modelName" -ForegroundColor Green
                $foundModels += $modelName
            }
            else {
                Write-Host "      - $modelName" -ForegroundColor Cyan
            }
        }

        if ($foundModels.Count -lt $requiredModels.Count) {
            Write-Host "   ⚠️  برخی مدل‌های مورد نیاز ممکن است نصب نباشند" -ForegroundColor Yellow
        }
        else {
            Write-Host "   ✅ مدل‌های مورد نیاز موجود هستند" -ForegroundColor Green
        }
    }
}
catch {
    Write-Host "   ❌ Ollama در حال اجرا نیست" -ForegroundColor Red
    Write-Host "      💡 در terminal جدید اجرا کنید: ollama serve" -ForegroundColor Yellow
    $allOk = $false
}

# ============================================================================
# مرحله 5: تست نهایی
# ============================================================================
Write-Host ""
Write-Host "📋 مرحله 5: تست نهایی..." -ForegroundColor Yellow

# بررسی Node.js
try {
    $nodeVersion = node --version
    Write-Host "   ✅ Node.js: $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Node.js یافت نشد" -ForegroundColor Red
    $allOk = $false
}

# بررسی VSCode CLI
try {
    $codeVersion = code --version 2>&1 | Select-Object -First 1
    Write-Host "   ✅ VSCode CLI: $codeVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ⚠️  VSCode CLI یافت نشد (برای نصب Extension نیاز است)" -ForegroundColor Yellow
    $warnings += "VSCode CLI یافت نشد"
}

# ============================================================================
# نتیجه نهایی
# ============================================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
if ($allOk) {
    Write-Host "║  ✅ همه چیز آماده است!                                 ║" -ForegroundColor Green
}
else {
    Write-Host "║  ⚠️  برخی مشکلات وجود دارد                          ║" -ForegroundColor Yellow
}
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "⚠️  هشدارها:" -ForegroundColor Yellow
    $warnings | ForEach-Object { Write-Host "   - $_" -ForegroundColor Yellow }
}

if ($allOk) {
    Write-Host ""
    Write-Host "🎉 MCP Server آماده استفاده است!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   1. 🔄 VSCode را Restart کنید (مهم!)" -ForegroundColor White
    Write-Host ""
    Write-Host "   2. 🔍 بررسی MCP Server:" -ForegroundColor White
    Write-Host "      • Ctrl+Shift+P" -ForegroundColor Yellow
    Write-Host "      • تایپ کنید: MCP" -ForegroundColor Yellow
    Write-Host "      • انتخاب کنید: 'MCP: List Servers'" -ForegroundColor Yellow
    Write-Host "      • باید 'ollama-local' را ببینید ✅" -ForegroundColor Green
    Write-Host ""
    Write-Host "   3. 🛠️  استفاده از Tools:" -ForegroundColor White
    Write-Host "      • Ctrl+Shift+P → 'MCP: List Tools'" -ForegroundColor Yellow
    Write-Host "      • باید 4 Tool ببینید:" -ForegroundColor White
    Write-Host "        - ollama_complete" -ForegroundColor Cyan
    Write-Host "        - ollama_list_models" -ForegroundColor Cyan
    Write-Host "        - ollama_code_assistant" -ForegroundColor Cyan
    Write-Host "        - ollama_chat" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   4. 🧪 تست با Ollama:" -ForegroundColor White
    Write-Host "      ollama run qwen2.5-coder:1.5b 'write hello world in Python'" -ForegroundColor Yellow
    Write-Host ""
}
else {
    Write-Host ""
    Write-Host "❌ لطفاً مشکلات را برطرف کنید:" -ForegroundColor Red
    if (-not (Test-Path "mcp-server-ollama/dist/index.js")) {
        Write-Host "   • Build MCP Server: cd mcp-server-ollama && node node_modules/typescript/lib/tsc.js" -ForegroundColor White
    }
    Write-Host ""
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📄 فایل تست: INSTALL_TEST_MCP_VSCODE.ps1" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

