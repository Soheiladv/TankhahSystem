# اسکریپت تستی - فقط نمایش تغییرات بدون اعمال آنها
# این اسکریپت چیزی را تغییر نمی‌دهد، فقط نشان می‌دهد چه می‌شد

$ErrorActionPreference = "Continue"  # Stop نمی‌کنیم تا همه چیز را ببینیم

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🧪 MODE: TEST/DRY-RUN - هیچ تغییری اعمال نمی‌شود      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# تعریف تنظیمات Ollama (فقط برای نمایش)
$ollamaServer = @{
    command = "node"
    args = @("${workspaceFolder}/mcp-server-ollama/dist/index.js")
    env = @{
        OLLAMA_URL = "http://localhost:11434"
    }
}

Write-Host "📋 تنظیمات Ollama که اضافه خواهد شد:" -ForegroundColor Yellow
$ollamaServer | ConvertTo-Json -Depth 3 | Write-Host -ForegroundColor Cyan
Write-Host ""

# بررسی .cursor/mcp.json
Write-Host "📁 بررسی .cursor/mcp.json..." -ForegroundColor Yellow
$cursorPath = ".cursor/mcp.json"

if (Test-Path $cursorPath) {
    Write-Host "   ✅ فایل موجود است" -ForegroundColor Green
    Write-Host "   📝 محتوای فعلی:" -ForegroundColor Cyan
    try {
        $current = Get-Content $cursorPath -Raw -Encoding UTF8
        $json = $current | ConvertFrom-Json
        
        Write-Host $current -ForegroundColor Gray
        Write-Host ""
        
        # بررسی تنظیمات موجود
        if ($json.mcpServers) {
            Write-Host "   📊 MCP Servers موجود:" -ForegroundColor Yellow
            $json.mcpServers.PSObject.Properties | ForEach-Object {
                Write-Host "      - $($_.Name)" -ForegroundColor White
            }
            
            if ($json.mcpServers.'ollama-local') {
                Write-Host "   ⚠️  ollama-local از قبل وجود دارد!" -ForegroundColor Yellow
                Write-Host "   🔄 به‌روزرسانی خواهد شد" -ForegroundColor Cyan
            } else {
                Write-Host "   ✅ ollama-local اضافه خواهد شد" -ForegroundColor Green
            }
        } else {
            Write-Host "   📝 mcpServers وجود ندارد، ایجاد خواهد شد" -ForegroundColor Cyan
        }
        
        Write-Host ""
        Write-Host "   🔮 حالت بعد از اعمال تغییرات:" -ForegroundColor Magenta
        Write-Host "   ──────────────────────────────────────" -ForegroundColor DarkGray
        
        # شبیه‌سازی تغییرات
        $simulated = @{}
        $json.PSObject.Properties | ForEach-Object {
            $simulated[$_.Name] = $_.Value
        }
        
        if (-not $simulated.ContainsKey('mcpServers')) {
            $simulated['mcpServers'] = @{}
        }
        
        $servers = @{}
        if ($simulated['mcpServers'] -ne $null) {
            $simulated['mcpServers'].PSObject.Properties | ForEach-Object {
                $servers[$_.Name] = $_.Value
            }
        }
        $servers['ollama-local'] = $ollamaServer
        $simulated['mcpServers'] = $servers
        
        $simulatedJson = New-Object PSCustomObject
        foreach ($key in $simulated.Keys) {
            $simulatedJson | Add-Member -MemberType NoteProperty -Name $key -Value $simulated[$key] -Force
        }
        
        $simulatedJson | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Green
        
    } catch {
        Write-Host "   ❌ خطا در خواندن فایل: $_" -ForegroundColor Red
        Write-Host "   ⚠️  ممکن است JSON معتبر نباشد" -ForegroundColor Yellow
    }
} else {
    Write-Host "   📝 فایل موجود نیست" -ForegroundColor Yellow
    Write-Host "   🔮 فایل جدید ایجاد خواهد شد با محتویات:" -ForegroundColor Magenta
    $newConfig = @{
        mcpServers = @{
            "ollama-local" = $ollamaServer
        }
    }
    $newConfig | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Green
}

Write-Host ""
Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# بررسی .vscode/settings.json
Write-Host "📁 بررسی .vscode/settings.json..." -ForegroundColor Yellow
$vscodePath = ".vscode/settings.json"

if (Test-Path $vscodePath) {
    Write-Host "   ✅ فایل موجود است" -ForegroundColor Green
    Write-Host "   📝 محتوای فعلی:" -ForegroundColor Cyan
    
    try {
        $current = Get-Content $vscodePath -Raw -Encoding UTF8
        $json = $current | ConvertFrom-Json
        
        Write-Host $current -ForegroundColor Gray
        Write-Host ""
        
        # شمارش تنظیمات موجود
        $settingsCount = ($json.PSObject.Properties | Measure-Object).Count
        Write-Host "   📊 تعداد تنظیمات موجود: $settingsCount" -ForegroundColor Yellow
        
        if ($json.'mcp.servers') {
            Write-Host "   📊 MCP Servers موجود:" -ForegroundColor Yellow
            $json.'mcp.servers'.PSObject.Properties | ForEach-Object {
                Write-Host "      - $($_.Name)" -ForegroundColor White
            }
            
            if ($json.'mcp.servers'.'ollama-local') {
                Write-Host "   ⚠️  ollama-local از قبل وجود دارد!" -ForegroundColor Yellow
                Write-Host "   🔄 به‌روزرسانی خواهد شد" -ForegroundColor Cyan
            } else {
                Write-Host "   ✅ ollama-local اضافه خواهد شد" -ForegroundColor Green
            }
        } else {
            Write-Host "   📝 mcp.servers وجود ندارد، اضافه خواهد شد" -ForegroundColor Cyan
        }
        
        Write-Host ""
        Write-Host "   🔮 حالت بعد از اعمال تغییرات:" -ForegroundColor Magenta
        Write-Host "   ──────────────────────────────────────" -ForegroundColor DarkGray
        
        # شبیه‌سازی تغییرات
        $simulated = @{}
        $json.PSObject.Properties | ForEach-Object {
            $simulated[$_.Name] = $_.Value
        }
        
        if (-not $simulated.ContainsKey('mcp.servers')) {
            $simulated['mcp.servers'] = @{}
        }
        
        $servers = @{}
        if ($simulated['mcp.servers'] -ne $null) {
            $simulated['mcp.servers'].PSObject.Properties | ForEach-Object {
                $servers[$_.Name] = $_.Value
            }
        }
        $servers['ollama-local'] = $ollamaServer
        $simulated['mcp.servers'] = $servers
        
        $simulatedJson = New-Object PSCustomObject
        foreach ($key in $simulated.Keys) {
            $simulatedJson | Add-Member -MemberType NoteProperty -Name $key -Value $simulated[$key] -Force
        }
        
        $simulatedJson | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Green
        
    } catch {
        Write-Host "   ❌ خطا در خواندن فایل: $_" -ForegroundColor Red
        Write-Host "   ⚠️  ممکن است JSON معتبر نباشد" -ForegroundColor Yellow
    }
} else {
    Write-Host "   📝 فایل موجود نیست" -ForegroundColor Yellow
    Write-Host "   🔮 فایل جدید ایجاد خواهد شد با محتویات:" -ForegroundColor Magenta
    $newConfig = @{
        "mcp.servers" = @{
            "ollama-local" = $ollamaServer
        }
    }
    $newConfig | ConvertTo-Json -Depth 10 | Write-Host -ForegroundColor Green
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  ✅ تست کامل شد - هیچ تغییری اعمال نشد                ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
Write-Host ""
Write-Host "📝 خلاصه:" -ForegroundColor Cyan
Write-Host "   - فایل‌های موجود بررسی شدند" -ForegroundColor White
Write-Host "   - تغییرات پیشنهادی نمایش داده شد" -ForegroundColor White
Write-Host "   - هیچ فایلی تغییر نکرد" -ForegroundColor White
Write-Host ""
Write-Host "🔧 برای اعمال واقعی تغییرات، اجرا کنید:" -ForegroundColor Green
Write-Host "   .\ADD_OLLAMA_TO_EXISTING.ps1" -ForegroundColor Yellow
Write-Host ""

