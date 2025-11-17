# ✅ رفع مشکل Extension در VSCODE_QUICK_SETUP.ps1

## 🐛 مشکل

هنگام اجرای `VSCODE_QUICK_SETUP.ps1` خطای زیر رخ می‌داد:

```
Extension 'ms-vscode.vscode-json' not found.
```

## 🔍 علت

Extension ID `ms-vscode.vscode-json` وجود ندارد. JSON support در VSCode به صورت **built-in** است و نیازی به نصب extension جداگانه ندارد.

## ✅ راه‌حل

1. **حذف `ms-vscode.vscode-json` از لیست Extension ها**
2. **بهبود error handling** در اسکریپت
3. **افزودن خروجی تفصیلی** برای هر Extension

## 📝 تغییرات

### VSCODE_QUICK_SETUP.ps1

**قبل:**
```powershell
$extensions = @(
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.flake8",
    "ms-python.pylint",
    "ms-vscode.vscode-json",  # ❌ وجود ندارد
    "redhat.vscode-yaml",
    "ms-vscode.powershell",
    "eamodio.gitlens"
)
```

**بعد:**
```powershell
$extensions = @(
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.flake8",
    "ms-python.pylint",
    "redhat.vscode-yaml",  # ✅ فقط YAML
    "ms-vscode.powershell",
    "eamodio.gitlens"
)

# JSON support در VSCode به صورت built-in است، نیازی به نصب نیست
```

### بهبود Error Handling

**قبل:**
```powershell
code --install-extension $ext --force 2>&1 | Out-Null
```

**بعد:**
```powershell
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
} else {
    Write-Host "      ⚠️  خطا در نصب: $installOutput" -ForegroundColor Yellow
}
```

## 📋 Extension های صحیح

### Extension های نصب شده:
✅ **Python** - `ms-python.python`
✅ **Pylance** - `ms-python.vscode-pylance`
✅ **Flake8** - `ms-python.flake8`
✅ **Pylint** - `ms-python.pylint`
✅ **YAML** - `redhat.vscode-yaml`
✅ **PowerShell** - `ms-vscode.powershell`
✅ **GitLens** - `eamodio.gitlens`

### Extension های Built-in (نیازی به نصب ندارند):
✅ **JSON** - در VSCode built-in است

## 🧪 تست

برای تست Extension های نصب شده:

```powershell
powershell -ExecutionPolicy ByPass -File TEST_EXTENSIONS.ps1
```

یا:

```powershell
code --list-extensions
```

## 📚 فایل‌های به‌روزرسانی شده

1. ✅ `VSCODE_QUICK_SETUP.ps1` - اصلاح شد
2. ✅ `INSTALL_VSCODE_EXTENSIONS.ps1` - اصلاح شد
3. ✅ `.vscode/extensions.json` - اصلاح شد
4. ✅ `TEST_EXTENSIONS.ps1` - ایجاد شد (جدید)

## ✅ نتیجه

حالا اسکریپت بدون خطا کار می‌کند و همه Extension های ضروری به درستی نصب می‌شوند.

---

**تاریخ:** $(Get-Date -Format "yyyy-MM-dd HH:mm")
**وضعیت:** ✅ رفع شده

