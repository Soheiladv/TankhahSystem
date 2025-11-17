# اسکریپت تست ایمن - اضافه کردن Ollama با backup و بررسی
# این نسخه ابتدا backup می‌گیرد و سپس تغییرات را اعمال می‌کند

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🧪 اسکریپت تست ایمن - اضافه کردن Ollama" -ForegroundColor Cyan
Write-Host "   این نسخه ابتدا backup می‌گیرد و سپس تغییرات را اعمال می‌کند" -ForegroundColor Yellow
Write-Host ""

# متغیرهای مسیر
$backupDir = ".backup_mcp_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$cursorPath = ".cursor/mcp.json"
$vscodePath = ".vscode/settings.json"

# تابع برای backup گرفتن
function Backup-File {
    param([string]$FilePath, [string]$BackupDir)

    if (Test-Path $FilePath) {
        $fileName = Split-Path $FilePath -Leaf
        $backupPath = Join-Path $BackupDir $fileName
        Copy-Item $FilePath $backupPath -Force
        Write-Host "   ✅ Backup: $FilePath -> $backupPath" -ForegroundColor Green
        return $backupPath
    }
    return $null
}

# تابع برای restore
function Restore-File {
    param([string]$FilePath, [string]$BackupPath)

    if (Test-Path $BackupPath) {
        Copy-Item $BackupPath $FilePath -Force
        Write-Host "   ✅ Restore: $BackupPath -> $FilePath" -ForegroundColor Green
        return $true
    }
    return $false
}

# تابع برای بررسی JSON معتبر
function Test-JsonFile {
    param([string]$FilePath)

    if (-not (Test-Path $FilePath)) {
        return $true  # فایل جدید می‌تواند ایجاد شود
    }

    try {
        $null = Get-Content $FilePath -Raw -Encoding UTF8 | ConvertFrom-Json
        return $true
    }
    catch {
        Write-Host "   ❌ JSON نامعتبر در $FilePath : $_" -ForegroundColor Red
        return $false
    }
}

# تابع برای بررسی اینکه تنظیمات قبلی حفظ شده
function Test-PreservedSettings {
    param(
        [string]$OriginalPath,
        [string]$NewPath
    )

    if (-not (Test-Path $OriginalPath)) {
        return $true  # فایل جدید است، مشکلی نیست
    }

    try {
        $original = Get-Content $OriginalPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $new = Get-Content $NewPath -Raw -Encoding UTF8 | ConvertFrom-Json

        # بررسی تمام properties اصلی (به جز mcp.servers و mcpServers)
        $originalProps = $original.PSObject.Properties | Where-Object {
            $_.Name -ne 'mcp.servers' -and $_.Name -ne 'mcpServers'
        }

        foreach ($prop in $originalProps) {
            $propName = $prop.Name
            if (-not $new.PSObject.Properties[$propName]) {
                Write-Host "   ⚠️  Property '$propName' گم شده!" -ForegroundColor Yellow
                return $false
            }
        }

        # بررسی MCP servers قبلی (به جز ollama-local)
        if ($original.mcpServers) {
            $originalServers = $original.mcpServers.PSObject.Properties | Where-Object {
                $_.Name -ne 'ollama-local'
            }
            foreach ($server in $originalServers) {
                if (-not $new.mcpServers.PSObject.Properties[$server.Name]) {
                    Write-Host "   ⚠️  MCP Server '$($server.Name)' گم شده!" -ForegroundColor Yellow
                    return $false
                }
            }
        }

        if ($original.'mcp.servers') {
            $originalServers = $original.'mcp.servers'.PSObject.Properties | Where-Object {
                $_.Name -ne 'ollama-local'
            }
            foreach ($server in $originalServers) {
                if (-not $new.'mcp.servers'.PSObject.Properties[$server.Name]) {
                    Write-Host "   ⚠️  MCP Server '$($server.Name)' گم شده!" -ForegroundColor Yellow
                    return $false
                }
            }
        }

        return $true
    }
    catch {
        Write-Host "   ❌ خطا در بررسی: $_" -ForegroundColor Red
        return $false
    }
}

# مرحله 1: ایجاد backup directory
Write-Host "📦 مرحله 1: ایجاد backup..." -ForegroundColor Yellow
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Write-Host "   ✅ پوشه backup ایجاد شد: $backupDir" -ForegroundColor Green
}
else {
    Write-Host "   ℹ️  پوشه backup از قبل وجود دارد" -ForegroundColor Yellow
}

# Backup فایل‌ها
$cursorBackup = Backup-File -FilePath $cursorPath -BackupDir $backupDir
$vscodeBackup = Backup-File -FilePath $vscodePath -BackupDir $backupDir

if ($cursorBackup -or $vscodeBackup) {
    Write-Host "   ✅ Backup کامل شد" -ForegroundColor Green
}
else {
    Write-Host "   ℹ️  هیچ فایلی برای backup وجود نداشت" -ForegroundColor Yellow
}

# مرحله 2: بررسی فایل‌های موجود
Write-Host ""
Write-Host "🔍 مرحله 2: بررسی فایل‌های موجود..." -ForegroundColor Yellow

$filesValid = $true

if (Test-Path $cursorPath) {
    if (-not (Test-JsonFile -FilePath $cursorPath)) {
        $filesValid = $false
    }
    else {
        Write-Host "   ✅ .cursor/mcp.json معتبر است" -ForegroundColor Green
        $cursorContent = Get-Content $cursorPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cursorContent.mcpServers -or $cursorContent.'mcp.servers') {
            $servers = if ($cursorContent.mcpServers) { $cursorContent.mcpServers } else { $cursorContent.'mcp.servers' }
            $serverNames = $servers.PSObject.Properties.Name
            Write-Host "   📋 MCP Servers موجود: $($serverNames -join ', ')" -ForegroundColor Cyan
        }
    }
}

if (Test-Path $vscodePath) {
    if (-not (Test-JsonFile -FilePath $vscodePath)) {
        $filesValid = $false
    }
    else {
        Write-Host "   ✅ .vscode/settings.json معتبر است" -ForegroundColor Green
        $vscodeContent = Get-Content $vscodePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $otherSettings = $vscodeContent.PSObject.Properties | Where-Object { $_.Name -ne 'mcp.servers' } | Select-Object -ExpandProperty Name
        if ($otherSettings) {
            Write-Host "   📋 تنظیمات دیگر موجود: $($otherSettings -join ', ')" -ForegroundColor Cyan
        }
    }
}

if (-not $filesValid) {
    Write-Host ""
    Write-Host "❌ فایل‌های JSON نامعتبر هستند. لطفاً ابتدا آن‌ها را اصلاح کنید." -ForegroundColor Red
    exit 1
}

# مرحله 3: اجرای اسکریپت اصلی
Write-Host ""
Write-Host "🔧 مرحله 3: اجرای اسکریپت اضافه کردن Ollama..." -ForegroundColor Yellow

try {
    # به جای فراخوانی مستقیم، منطق را اینجا پیاده می‌کنیم
    # تا کنترل کامل داشته باشیم

    Write-Host "   📝 در حال اعمال تغییرات..." -ForegroundColor Cyan

    # تعریف تنظیمات Ollama
    $ollamaServer = @{
        command = "node"
        args    = @("${workspaceFolder}/mcp-server-ollama/dist/index.js")
        env     = @{
            OLLAMA_URL = "http://localhost:11434"
        }
    }

    # پردازش .cursor/mcp.json
    if (Test-Path $cursorPath) {
        $cursorContent = Get-Content $cursorPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $cursorDict = @{}
        $cursorContent.PSObject.Properties | ForEach-Object {
            $cursorDict[$_.Name] = $_.Value
        }

        if (-not $cursorDict.ContainsKey('mcpServers')) {
            $cursorDict['mcpServers'] = @{}
        }

        $servers = @{}
        if ($cursorDict['mcpServers'] -ne $null) {
            $cursorDict['mcpServers'].PSObject.Properties | ForEach-Object {
                $servers[$_.Name] = $_.Value
            }
        }

        $servers['ollama-local'] = $ollamaServer
        $cursorDict['mcpServers'] = $servers

        $result = New-Object PSCustomObject
        foreach ($key in $cursorDict.Keys) {
            $result | Add-Member -MemberType NoteProperty -Name $key -Value $cursorDict[$key] -Force
        }

        $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $cursorPath -Encoding UTF8 -Force
    }
    else {
        # ایجاد فایل جدید
        $newJson = @{
            mcpServers = @{
                "ollama-local" = $ollamaServer
            }
        }
        $newJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $cursorPath -Encoding UTF8 -Force
    }

    # پردازش .vscode/settings.json
    if (Test-Path $vscodePath) {
        $vscodeContent = Get-Content $vscodePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $vscodeDict = @{}
        $vscodeContent.PSObject.Properties | ForEach-Object {
            $vscodeDict[$_.Name] = $_.Value
        }

        if (-not $vscodeDict.ContainsKey('mcp.servers')) {
            $vscodeDict['mcp.servers'] = @{}
        }

        $servers = @{}
        if ($vscodeDict['mcp.servers'] -ne $null) {
            $vscodeDict['mcp.servers'].PSObject.Properties | ForEach-Object {
                $servers[$_.Name] = $_.Value
            }
        }

        $servers['ollama-local'] = $ollamaServer
        $vscodeDict['mcp.servers'] = $servers

        $result = New-Object PSCustomObject
        foreach ($key in $vscodeDict.Keys) {
            $result | Add-Member -MemberType NoteProperty -Name $key -Value $vscodeDict[$key] -Force
        }

        $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $vscodePath -Encoding UTF8 -Force
    }
    else {
        # ایجاد فایل جدید
        $newJson = @{
            "mcp.servers" = @{
                "ollama-local" = $ollamaServer
            }
        }
        $newJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $vscodePath -Encoding UTF8 -Force
    }

    Write-Host "   ✅ تغییرات اعمال شد" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ خطا در اعمال تغییرات: $_" -ForegroundColor Red
    Write-Host "   🔄 در حال restore کردن backup..." -ForegroundColor Yellow

    if ($cursorBackup) { Restore-File -FilePath $cursorPath -BackupPath $cursorBackup }
    if ($vscodeBackup) { Restore-File -FilePath $vscodePath -BackupPath $vscodeBackup }

    exit 1
}

# مرحله 4: بررسی اینکه تنظیمات حفظ شده
Write-Host ""
Write-Host "✅ مرحله 4: بررسی حفظ تنظیمات..." -ForegroundColor Yellow

$preserved = $true

if ((Test-Path $cursorPath) -and $cursorBackup) {
    if (Test-PreservedSettings -OriginalPath $cursorBackup -NewPath $cursorPath) {
        Write-Host "   ✅ تنظیمات .cursor/mcp.json حفظ شده" -ForegroundColor Green
    }
    else {
        Write-Host "   ❌ برخی تنظیمات .cursor/mcp.json حفظ نشده!" -ForegroundColor Red
        $preserved = $false
    }
}

if ((Test-Path $vscodePath) -and $vscodeBackup) {
    if (Test-PreservedSettings -OriginalPath $vscodeBackup -NewPath $vscodePath) {
        Write-Host "   ✅ تنظیمات .vscode/settings.json حفظ شده" -ForegroundColor Green
    }
    else {
        Write-Host "   ❌ برخی تنظیمات .vscode/settings.json حفظ نشده!" -ForegroundColor Red
        $preserved = $false
    }
}

# مرحله 5: بررسی اضافه شدن ollama-local
Write-Host ""
Write-Host "🔍 مرحله 5: بررسی اضافه شدن ollama-local..." -ForegroundColor Yellow

$ollamaAdded = $true

if (Test-Path $cursorPath) {
    $cursorContent = Get-Content $cursorPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $servers = if ($cursorContent.mcpServers) { $cursorContent.mcpServers } else { $cursorContent.'mcp.servers' }
    if ($servers -and $servers.PSObject.Properties['ollama-local']) {
        Write-Host "   ✅ ollama-local در .cursor/mcp.json اضافه شده" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  ollama-local در .cursor/mcp.json یافت نشد" -ForegroundColor Yellow
        $ollamaAdded = $false
    }
}

if (Test-Path $vscodePath) {
    $vscodeContent = Get-Content $vscodePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($vscodeContent.'mcp.servers' -and $vscodeContent.'mcp.servers'.PSObject.Properties['ollama-local']) {
        Write-Host "   ✅ ollama-local در .vscode/settings.json اضافه شده" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  ollama-local در .vscode/settings.json یافت نشد" -ForegroundColor Yellow
        $ollamaAdded = $false
    }
}

# نتیجه نهایی
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan

if ($preserved -and $ollamaAdded) {
    Write-Host "✅ تست موفق بود!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 خلاصه:" -ForegroundColor Cyan
    Write-Host "   ✅ Backup گرفته شد: $backupDir" -ForegroundColor White
    Write-Host "   ✅ تنظیمات قبلی حفظ شد" -ForegroundColor White
    Write-Host "   ✅ ollama-local اضافه شد" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 اگر می‌خواهید backup را نگه دارید، پوشه '$backupDir' را نگه دارید" -ForegroundColor Yellow
    Write-Host "💡 اگر می‌خواهید backup را حذف کنید: Remove-Item -Recurse -Force '$backupDir'" -ForegroundColor Yellow
}
else {
    Write-Host "❌ تست ناموفق بود!" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔄 در حال restore کردن backup..." -ForegroundColor Yellow

    if ($cursorBackup) { Restore-File -FilePath $cursorPath -BackupPath $cursorBackup }
    if ($vscodeBackup) { Restore-File -FilePath $vscodePath -BackupPath $vscodeBackup }

    Write-Host ""
    Write-Host "✅ Backup restore شد. فایل‌ها به حالت قبل بازگشتند." -ForegroundColor Green
    Write-Host "📁 Backup در پوشه '$backupDir' نگه داشته شد" -ForegroundColor Yellow
}

Write-Host "═══════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

