# تست و لیست Extension های موجود

Write-Host ""
Write-Host "🔍 بررسی Extension های VSCode..." -ForegroundColor Cyan
Write-Host ""

# Extension های مورد نیاز
$requiredExtensions = @(
    @{ Name = "Python"; Id = "ms-python.python" },
    @{ Name = "Pylance"; Id = "ms-python.vscode-pylance" },
    @{ Name = "Flake8"; Id = "ms-python.flake8" },
    @{ Name = "Pylint"; Id = "ms-python.pylint" },
    @{ Name = "YAML"; Id = "redhat.vscode-yaml" },
    @{ Name = "PowerShell"; Id = "ms-vscode.powershell" },
    @{ Name = "GitLens"; Id = "eamodio.gitlens" }
)

Write-Host "📋 Extension های نصب شده:" -ForegroundColor Yellow
$installedList = code --list-extensions 2>&1

$foundCount = 0
$missingCount = 0

foreach ($ext in $requiredExtensions) {
    if ($installedList -match [regex]::Escape($ext.Id)) {
        Write-Host "   ✅ $($ext.Name) ($($ext.Id))" -ForegroundColor Green
        $foundCount++
    }
    else {
        Write-Host "   ❌ $($ext.Name) ($($ext.Id))" -ForegroundColor Red
        $missingCount++
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "📊 خلاصه:" -ForegroundColor Yellow
Write-Host "   ✅ نصب شده: $foundCount" -ForegroundColor Green
Write-Host "   ❌ نصب نشده: $missingCount" -ForegroundColor $(if ($missingCount -eq 0) { "Green" } else { "Red" })
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($missingCount -gt 0) {
    Write-Host ""
    Write-Host "💡 برای نصب Extension های نصب نشده:" -ForegroundColor Cyan
    Write-Host "   .\INSTALL_VSCODE_EXTENSIONS.ps1" -ForegroundColor Yellow
    Write-Host "   یا در VSCode: Ctrl+Shift+X" -ForegroundColor Yellow
}

Write-Host ""

