# PowerShell Script برای نصب MCP Server (Windows)

Write-Host "🚀 نصب MCP Server برای Ollama..." -ForegroundColor Cyan
Write-Host ""

# بررسی Node.js
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js نصب شده: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js یافت نشد. لطفاً ابتدا Node.js را نصب کنید." -ForegroundColor Red
    exit 1
}

# بررسی Ollama
$ollamaInstalled = $false
try {
    $ollamaVersion = ollama --version
    Write-Host "✅ Ollama نصب شده: $ollamaVersion" -ForegroundColor Green
    $ollamaInstalled = $true
} catch {
    Write-Host "⚠️  Ollama یافت نشد." -ForegroundColor Yellow
    Write-Host "لطفاً Ollama را از https://ollama.ai/download نصب کنید." -ForegroundColor Yellow
    $continue = Read-Host "آیا می‌خواهید ادامه دهید؟ (y/n)"
    if ($continue -ne 'y') {
        exit 1
    }
}

# نصب dependencies
Write-Host ""
Write-Host "📦 نصب dependencies..." -ForegroundColor Cyan
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ خطا در نصب dependencies" -ForegroundColor Red
    exit 1
}

# Build
Write-Host ""
Write-Host "🔨 Build پروژه..." -ForegroundColor Cyan
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ خطا در build" -ForegroundColor Red
    exit 1
}

# بررسی مدل‌ها
if ($ollamaInstalled) {
    Write-Host ""
    Write-Host "🔍 بررسی مدل‌های Ollama..." -ForegroundColor Cyan
    
    # بررسی qwen2.5-coder:1.5b
    $models = ollama list 2>$null
    if ($models -match "qwen2.5-coder:1.5b") {
        Write-Host "✅ qwen2.5-coder:1.5b یافت شد" -ForegroundColor Green
    } else {
        Write-Host "⚠️  qwen2.5-coder:1.5b یافت نشد" -ForegroundColor Yellow
        $install = Read-Host "آیا می‌خواهید نصب کنید؟ (y/n)"
        if ($install -eq 'y') {
            Write-Host "📥 نصب qwen2.5-coder:1.5b..." -ForegroundColor Cyan
            ollama pull qwen2.5-coder:1.5b
        }
    }
    
    # بررسی llama3.2:1b
    if ($models -match "llama3.2:1b") {
        Write-Host "✅ llama3.2:1b یافت شد" -ForegroundColor Green
    } else {
        Write-Host "⚠️  llama3.2:1b یافت نشد" -ForegroundColor Yellow
        $install = Read-Host "آیا می‌خواهید نصب کنید؟ (y/n)"
        if ($install -eq 'y') {
            Write-Host "📥 نصب llama3.2:1b..." -ForegroundColor Cyan
            ollama pull llama3.2:1b
        }
    }
}

Write-Host ""
Write-Host "✅ نصب کامل شد!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 مراحل بعدی:" -ForegroundColor Cyan
Write-Host "1. فایل .cursor/mcp.json را ویرایش کنید و مسیر را به پروژه خود تغییر دهید"
Write-Host "2. Cursor را restart کنید"
Write-Host "3. از مدل‌های Ollama استفاده کنید!"
Write-Host ""

