# اسکریپت نصب خودکار Extension های VSCode
# اجرا در PowerShell

Write-Host ""
Write-Host "🚀 نصب Extension های VSCode برای MCP و Ollama" -ForegroundColor Cyan
Write-Host ""

# بررسی VSCode CLI
Write-Host "🔍 بررسی VSCode CLI..." -ForegroundColor Yellow
try {
    $codeVersion = code --version 2>&1 | Select-Object -First 1
    Write-Host "   ✅ VSCode CLI در دسترس است: $codeVersion" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ VSCode CLI یافت نشد" -ForegroundColor Red
    Write-Host "   📝 راهنما:" -ForegroundColor Yellow
    Write-Host "      1. VSCode را باز کنید" -ForegroundColor White
    Write-Host "      2. Ctrl+Shift+P -> 'Shell Command: Install code command'" -ForegroundColor White
    Write-Host "      3. یا به صورت دستی نصب کنید" -ForegroundColor White
    exit 1
}

# Extension های ضروری
$extensions = @(
    # Python
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.flake8",
    "ms-python.pylint",
    "ms-python.black-formatter",

    # YAML (JSON support در VSCode built-in است)
    "redhat.vscode-yaml",

    # PowerShell
    "ms-vscode.powershell",

    # Git
    "eamodio.gitlens",

    # Editor Enhancements
    "esbenp.prettier-vscode",
    "oderwat.indent-rainbow",
    "usernamehw.errorlens",
    "gruntfuggly.todo-tree",

    # Utilities
    "christian-kohler.path-intellisense",
    "formulahendry.code-runner",
    "streetsidesoftware.code-spell-checker"
)

Write-Host "📦 نصب Extension ها..." -ForegroundColor Yellow
Write-Host ""

$installed = 0
$failed = 0
$alreadyInstalled = 0

foreach ($ext in $extensions) {
    Write-Host "   📥 در حال نصب: $ext" -ForegroundColor Cyan

    # بررسی اینکه از قبل نصب است
    $installedList = code --list-extensions 2>&1
    if ($installedList -match $ext) {
        Write-Host "      ✅ از قبل نصب است" -ForegroundColor Green
        $alreadyInstalled++
        continue
    }

    # نصب extension
    $result = code --install-extension $ext --force 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✅ نصب موفق بود" -ForegroundColor Green
        $installed++
    }
    else {
        Write-Host "      ❌ خطا در نصب: $result" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📊 خلاصه:" -ForegroundColor Yellow
Write-Host "   ✅ نصب شد: $installed" -ForegroundColor Green
Write-Host "   ℹ️  از قبل نصب بود: $alreadyInstalled" -ForegroundColor Yellow
Write-Host "   ❌ خطا: $failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✅ همه Extension ها با موفقیت نصب شدند!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
    Write-Host "   1. VSCode را Restart کنید" -ForegroundColor White
    Write-Host "   2. مطمئن شوید Ollama در حال اجرا است: ollama serve" -ForegroundColor White
    Write-Host "   3. بررسی کنید MCP Server کار می‌کند" -ForegroundColor White
}
else {
    Write-Host "⚠️  برخی Extension ها نصب نشدند" -ForegroundColor Yellow
    Write-Host "   لطفاً به صورت دستی نصب کنید:" -ForegroundColor White
    Write-Host "   code --install-extension <extension-id>" -ForegroundColor Cyan
}

Write-Host ""

