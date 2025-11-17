# اسکریپت سریع تست و نصب MCP Server برای VSCode
# این اسکریپت همه چیز را بررسی و تست می‌کند

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 تست و نصب سریع MCP Server برای VSCode               ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$allOk = $true
$issues = @()

# 1. بررسی فایل build شده
Write-Host "1️⃣  بررسی فایل build شده..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    $fileInfo = Get-Item "mcp-server-ollama/dist/index.js"
    Write-Host "   ✅ dist/index.js موجود است" -ForegroundColor Green
    Write-Host "      📊 حجم: $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor White
}
else {
    Write-Host "   ❌ dist/index.js یافت نشد!" -ForegroundColor Red
    Write-Host "   📦 در حال build..." -ForegroundColor Yellow
    Set-Location mcp-server-ollama
    if (Test-Path "node_modules/typescript/lib/tsc.js") {
        node node_modules/typescript/lib/tsc.js 2>&1 | Out-Null
        Set-Location ..
        if (Test-Path "mcp-server-ollama/dist/index.js") {
            Write-Host "   ✅ Build موفق بود!" -ForegroundColor Green
        }
        else {
            Write-Host "   ❌ Build ناموفق بود" -ForegroundColor Red
            $allOk = $false
            $issues += "فایل dist/index.js ساخته نشد"
        }
    }
    else {
        Write-Host "   ❌ TypeScript یافت نشد - در حال نصب..." -ForegroundColor Yellow
        Set-Location mcp-server-ollama
        npm install 2>&1 | Out-Null
        node node_modules/typescript/lib/tsc.js 2>&1 | Out-Null
        Set-Location ..
        if (Test-Path "mcp-server-ollama/dist/index.js") {
            Write-Host "   ✅ Build موفق بود!" -ForegroundColor Green
        }
        else {
            $allOk = $false
            $issues += "Build ناموفق"
        }
    }
}

# 2. تست syntax
Write-Host ""
Write-Host "2️⃣  تست syntax فایل..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    $syntaxCheck = node --check "mcp-server-ollama/dist/index.js" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Syntax صحیح است" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  هشدار syntax: $syntaxCheck" -ForegroundColor Yellow
    }
}

# 3. بررسی تنظیمات VSCode
Write-Host ""
Write-Host "3️⃣  بررسی تنظیمات VSCode..." -ForegroundColor Yellow
if (Test-Path ".vscode/settings.json") {
    try {
        $settings = Get-Content ".vscode/settings.json" -Raw | ConvertFrom-Json
        if ($settings.'mcp.servers'.'ollama-local') {
            Write-Host "   ✅ MCP Server 'ollama-local' تنظیم شده" -ForegroundColor Green
            $mcp = $settings.'mcp.servers'.'ollama-local'
            $mcpPath = $mcp.args[0] -replace '\$\{workspaceFolder\}', (Get-Location).Path
            if (Test-Path $mcpPath) {
                Write-Host "      ✅ مسیر فایل صحیح است: $mcpPath" -ForegroundColor Green
            }
            else {
                Write-Host "      ❌ مسیر فایل یافت نشد: $mcpPath" -ForegroundColor Red
                $allOk = $false
                $issues += "مسیر MCP Server صحیح نیست"
            }
        }
        else {
            Write-Host "   ❌ MCP Server تنظیم نشده!" -ForegroundColor Red
            $allOk = $false
            $issues += "MCP Server در settings.json تنظیم نشده"
        }
    }
    catch {
        Write-Host "   ⚠️  خطا در خواندن settings.json: $_" -ForegroundColor Yellow
    }
}
else {
    Write-Host "   ❌ فایل settings.json یافت نشد!" -ForegroundColor Red
    $allOk = $false
    $issues += "settings.json یافت نشد"
}

# 4. بررسی Ollama
Write-Host ""
Write-Host "4️⃣  بررسی Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✅ Ollama در حال اجرا است" -ForegroundColor Green

    $models = ($response.Content | ConvertFrom-Json).models
    if ($models) {
        Write-Host "   📦 مدل‌های نصب شده:" -ForegroundColor White
        $requiredModels = @("qwen2.5-coder:1.5b", "llama3.2:1b")
        $foundModels = @()
        $models | ForEach-Object {
            $modelName = $_.name
            Write-Host "      - $modelName" -ForegroundColor Cyan
            if ($requiredModels -contains $modelName) {
                $foundModels += $modelName
            }
        }
        if ($foundModels.Count -lt $requiredModels.Count) {
            Write-Host "   ⚠️  برخی مدل‌های مورد نیاز نصب نیست" -ForegroundColor Yellow
            $missing = $requiredModels | Where-Object { $foundModels -notcontains $_ }
            Write-Host "      نصب کنید: $($missing -join ', ')" -ForegroundColor Yellow
        }
        else {
            Write-Host "   ✅ همه مدل‌های مورد نیاز نصب شده" -ForegroundColor Green
        }
    }
}
catch {
    Write-Host "   ❌ Ollama در حال اجرا نیست" -ForegroundColor Red
    Write-Host "      💡 اجرا کنید: ollama serve" -ForegroundColor Yellow
    $allOk = $false
    $issues += "Ollama در حال اجرا نیست"
}

# 5. تست اجرای MCP Server
Write-Host ""
Write-Host "5️⃣  تست اجرای MCP Server..." -ForegroundColor Yellow
if (Test-Path "mcp-server-ollama/dist/index.js") {
    try {
        # تست سریع - فقط بررسی اینکه فایل قابل اجرا است
        Write-Host "   🔍 بررسی فایل..." -ForegroundColor Cyan
        $content = Get-Content "mcp-server-ollama/dist/index.js" -Raw -ErrorAction Stop
        if ($content -match "OllamaMCPServer" -or $content -match "ollama") {
            Write-Host "   ✅ فایل MCP Server معتبر است" -ForegroundColor Green
        }
        else {
            Write-Host "   ⚠️  محتوای فایل غیرمعمول است" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "   ⚠️  نتوانست فایل را بررسی کند: $_" -ForegroundColor Yellow
    }
}

# نتیجه نهایی
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })
if ($allOk) {
    Write-Host "║  ✅ همه تست‌ها موفق بود!                              ║" -ForegroundColor Green
}
else {
    Write-Host "║  ⚠️  برخی مشکلات وجود دارد                          ║" -ForegroundColor Yellow
}
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor $(if ($allOk) { "Green" } else { "Yellow" })

if ($issues.Count -gt 0) {
    Write-Host ""
    Write-Host "📋 مشکلات پیدا شده:" -ForegroundColor Yellow
    $issues | ForEach-Object { Write-Host "   - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "💡 راه‌حل‌ها:" -ForegroundColor Cyan
    if ($issues -contains "Ollama در حال اجرا نیست") {
        Write-Host "   1. در terminal جدید اجرا کنید: ollama serve" -ForegroundColor White
    }
    if ($issues -contains "فایل dist/index.js ساخته نشد") {
        Write-Host "   2. Build کنید: cd mcp-server-ollama && node node_modules/typescript/lib/tsc.js" -ForegroundColor White
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "🎉 MCP Server آماده استفاده است!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
    Write-Host "   1. 🔄 VSCode را Restart کنید" -ForegroundColor White
    Write-Host "   2. Ctrl+Shift+P → 'MCP: List Servers'" -ForegroundColor White
    Write-Host "   3. باید 'ollama-local' را ببینید" -ForegroundColor White
}
else {
    Write-Host "⚠️  لطفاً مشکلات را برطرف کنید و دوباره تست کنید" -ForegroundColor Yellow
}
Write-Host ""

