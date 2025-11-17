# اسکریپت اضافه کردن Ollama به تنظیمات موجود بدون تغییر تنظیمات قبلی
# این اسکریپت تنظیمات موجود را حفظ می‌کند و فقط Ollama را اضافه می‌کند

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "🔧 اضافه کردن Ollama MCP به تنظیمات موجود..." -ForegroundColor Cyan
Write-Host ""

# تابع برای merge کردن JSON با حفظ تنظیمات موجود
function Merge-McpServers {
    param(
        [string]$FilePath,
        [PSCustomObject]$NewServer
    )
    
    if (Test-Path $FilePath) {
        Write-Host "   📝 خواندن تنظیمات موجود از $FilePath..." -ForegroundColor Yellow
        try {
            $content = Get-Content $FilePath -Raw -Encoding UTF8
            $json = $content | ConvertFrom-Json
            
            # تبدیل به hashtable برای کار راحت‌تر
            $jsonDict = @{}
            $json.PSObject.Properties | ForEach-Object {
                $jsonDict[$_.Name] = $_.Value
            }
            
            # بررسی اینکه آیا mcpServers یا mcp.servers وجود دارد
            $serverKey = $null
            if ($jsonDict.ContainsKey('mcpServers')) {
                $serverKey = 'mcpServers'
            } elseif ($jsonDict.ContainsKey('mcp.servers')) {
                $serverKey = 'mcp.servers'
            }
            
            if ($null -ne $serverKey) {
                # تبدیل به hashtable
                $servers = @{}
                $jsonDict[$serverKey].PSObject.Properties | ForEach-Object {
                    $servers[$_.Name] = $_.Value
                }
                
                # اضافه کردن ollama-local فقط اگر وجود ندارد
                if (-not $servers.ContainsKey('ollama-local')) {
                    Write-Host "   ✅ اضافه کردن ollama-local به $serverKey موجود (حفظ تنظیمات قبلی)" -ForegroundColor Green
                    $servers['ollama-local'] = $NewServer
                    $jsonDict[$serverKey] = $servers
                } else {
                    Write-Host "   ℹ️  ollama-local از قبل وجود دارد، به‌روزرسانی..." -ForegroundColor Yellow
                    $servers['ollama-local'] = $NewServer
                    $jsonDict[$serverKey] = $servers
                }
            } else {
                Write-Host "   📝 اضافه کردن $serverKey جدید (حفظ تمام تنظیمات قبلی)..." -ForegroundColor Yellow
                $jsonDict['mcpServers'] = @{
                    'ollama-local' = $NewServer
                }
            }
            
            # تبدیل دوباره به PSCustomObject با حفظ تمام properties
            $result = New-Object PSCustomObject
            foreach ($key in $jsonDict.Keys) {
                $result | Add-Member -MemberType NoteProperty -Name $key -Value $jsonDict[$key] -Force
            }
            
            return $result
        } catch {
            Write-Host "   ⚠️  خطا در خواندن فایل: $_" -ForegroundColor Yellow
            Write-Host "   📝 ایجاد فایل جدید..." -ForegroundColor Yellow
            return $null
        }
    } else {
        Write-Host "   📝 فایل موجود نیست، ایجاد فایل جدید..." -ForegroundColor Yellow
        return $null
    }
}

# تعریف تنظیمات Ollama
$ollamaServer = @{
    command = "node"
    args = @("${workspaceFolder}/mcp-server-ollama/dist/index.js")
    env = @{
        OLLAMA_URL = "http://localhost:11434"
    }
}

# تبدیل به PSCustomObject برای سازگاری
$ollamaServerObj = New-Object PSCustomObject
$ollamaServerObj | Add-Member -MemberType NoteProperty -Name "command" -Value $ollamaServer.command
$ollamaServerObj | Add-Member -MemberType NoteProperty -Name "args" -Value $ollamaServer.args
$ollamaServerObj | Add-Member -MemberType NoteProperty -Name "env" -Value (@{
    OLLAMA_URL = $ollamaServer.env.OLLAMA_URL
} | ConvertTo-Json | ConvertFrom-Json)

# پردازش .cursor/mcp.json
Write-Host "📁 پردازش .cursor/mcp.json..." -ForegroundColor Yellow
$cursorPath = ".cursor/mcp.json"

if (-not (Test-Path ".cursor")) {
    New-Item -ItemType Directory -Force -Path ".cursor" | Out-Null
    Write-Host "   📁 پوشه .cursor ایجاد شد" -ForegroundColor Green
}

$cursorJson = Merge-McpServers -FilePath $cursorPath -NewServer $ollamaServerObj

if ($null -eq $cursorJson) {
    # ایجاد فایل جدید
    $cursorJson = New-Object PSCustomObject
    $cursorJson | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{
        "ollama-local" = $ollamaServer
    }
}

# ذخیره فایل .cursor/mcp.json با حفظ فرمت
$jsonString = $cursorJson | ConvertTo-Json -Depth 10
# اصلاح فرمت برای حفظ فاصله‌ها
$jsonString = ($jsonString -replace '"args":\s*\[', '"args": [' -replace '"env":\s*{', '"env": {')
$jsonString | Out-File -FilePath $cursorPath -Encoding UTF8 -Force
Write-Host "   ✅ .cursor/mcp.json به‌روزرسانی شد (تنظیمات قبلی حفظ شد)" -ForegroundColor Green

# پردازش .vscode/settings.json
Write-Host ""
Write-Host "📁 پردازش .vscode/settings.json..." -ForegroundColor Yellow
$vscodePath = ".vscode/settings.json"

if (-not (Test-Path ".vscode")) {
    New-Item -ItemType Directory -Force -Path ".vscode" | Out-Null
    Write-Host "   📁 پوشه .vscode ایجاد شد" -ForegroundColor Green
}

if (Test-Path $vscodePath) {
    Write-Host "   📝 خواندن تنظیمات موجود..." -ForegroundColor Yellow
    try {
        $content = Get-Content $vscodePath -Raw -Encoding UTF8
        $vscodeJson = $content | ConvertFrom-Json
        
        # تبدیل به hashtable برای حفظ همه تنظیمات
        $vscodeDict = @{}
        $vscodeJson.PSObject.Properties | ForEach-Object {
            $vscodeDict[$_.Name] = $_.Value
        }
        
        # اضافه کردن mcp.servers اگر وجود ندارد
        if (-not $vscodeDict.ContainsKey('mcp.servers')) {
            Write-Host "   ✅ اضافه کردن mcp.servers..." -ForegroundColor Green
            $vscodeDict['mcp.servers'] = @{}
        }
        
        # تبدیل mcp.servers به hashtable
        $servers = @{}
        if ($vscodeDict['mcp.servers'] -ne $null) {
            $vscodeDict['mcp.servers'].PSObject.Properties | ForEach-Object {
                $servers[$_.Name] = $_.Value
            }
        }
        
        # اضافه کردن ollama-local اگر وجود ندارد (حفظ سایر سرورها)
        if (-not $servers.ContainsKey('ollama-local')) {
            Write-Host "   ✅ اضافه کردن ollama-local (حفظ سایر MCP servers)..." -ForegroundColor Green
            $servers['ollama-local'] = $ollamaServer
        } else {
            Write-Host "   ℹ️  ollama-local از قبل وجود دارد، به‌روزرسانی..." -ForegroundColor Yellow
            $servers['ollama-local'] = $ollamaServer
        }
        
        $vscodeDict['mcp.servers'] = $servers
        
        # تبدیل دوباره به PSCustomObject با حفظ تمام تنظیمات
        $result = New-Object PSCustomObject
        foreach ($key in $vscodeDict.Keys) {
            $result | Add-Member -MemberType NoteProperty -Name $key -Value $vscodeDict[$key] -Force
        }
        
        # ذخیره با حفظ تمام تنظیمات
        $result | ConvertTo-Json -Depth 10 | Out-File -FilePath $vscodePath -Encoding UTF8 -Force
        Write-Host "   ✅ .vscode/settings.json به‌روزرسانی شد (تمام تنظیمات قبلی حفظ شد)" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  خطا در پردازش .vscode/settings.json: $_" -ForegroundColor Yellow
        Write-Host "   📝 ایجاد فایل جدید..." -ForegroundColor Yellow
        $newJson = New-Object PSCustomObject
        $newJson | Add-Member -MemberType NoteProperty -Name "mcp.servers" -Value @{
            "ollama-local" = $ollamaServer
        }
        $newJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $vscodePath -Encoding UTF8 -Force
        Write-Host "   ✅ فایل جدید ایجاد شد" -ForegroundColor Green
    }
} else {
    Write-Host "   📝 ایجاد فایل جدید..." -ForegroundColor Yellow
    $newJson = New-Object PSCustomObject
    $newJson | Add-Member -MemberType NoteProperty -Name "mcp.servers" -Value @{
        "ollama-local" = $ollamaServer
    }
    $newJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $vscodePath -Encoding UTF8 -Force
    Write-Host "   ✅ فایل جدید ایجاد شد" -ForegroundColor Green
}

Write-Host ""
Write-Host "✅ Ollama MCP به تنظیمات اضافه شد بدون تغییر تنظیمات قبلی!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
Write-Host "   1. Cursor/VSCode را Restart کنید" -ForegroundColor White
Write-Host "   2. مطمئن شوید Ollama در حال اجرا است: ollama serve" -ForegroundColor White
Write-Host "   3. بررسی کنید: Ctrl+Shift+P -> MCP: List Servers" -ForegroundColor White
Write-Host ""

