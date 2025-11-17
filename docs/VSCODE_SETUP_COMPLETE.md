# راهنمای کامل آماده‌سازی VSCode برای MCP و Ollama

این راهنما به شما کمک می‌کند VSCode را کاملاً برای استفاده از MCP Server و مدل‌های Ollama آماده کنید.

## 📋 مرحله 1: نصب Extension های لازم

### روش 1: نصب خودکار (توصیه می‌شود)

فایل `.vscode/extensions.json` در پروژه شما لیست extension های توصیه شده را دارد.

**در VSCode:**
1. `Ctrl+Shift+P` (یا `Cmd+Shift+P` در Mac)
2. تایپ کنید: `Extensions: Show Recommended Extensions`
3. روی `Install All` کلیک کنید

### روش 2: نصب دستی

Extension های ضروری:

#### برای Python/Django:
```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.flake8
code --install-extension ms-python.pylint
code --install-extension ms-python.black-formatter
```

#### برای MCP و JSON:
```bash
code --install-extension ms-vscode.vscode-json
code --install-extension redhat.vscode-yaml
```

#### برای PowerShell (Windows):
```bash
code --install-extension ms-vscode.powershell
```

#### برای Git:
```bash
code --install-extension eamodio.gitlens
```

## 📋 مرحله 2: نصب Extension MCP (اگر موجود است)

### بررسی Extension های MCP موجود:

1. در VSCode: `Ctrl+Shift+X`
2. جستجو کنید: `MCP` یا `Model Context Protocol`
3. Extension های مرتبط را نصب کنید

### Extension های احتمالی:
- `MCP Client` (اگر موجود باشد)
- `Claude Dev` (اگر موجود باشد)
- `Cursor/Claude Extension` (اگر موجود باشد)

## ⚙️ مرحله 3: تنظیمات VSCode

### فایل `.vscode/settings.json` شما شامل:

✅ **MCP Servers:**
```json
{
  "mcp.servers": {
    "ollama-local": {
      "command": "node",
      "args": ["${workspaceFolder}/mcp-server-ollama/dist/index.js"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

✅ **Claude-code (AgentRouter):**
```json
{
  "claude-code.useTerminal": true,
  "claude-code.environmentVariables": [
    {
      "claude.apiBase": "https://agentrouter.org/",
      "claude.apiKey": "sk-TYv5IehnCWDMz66j2TKSOUXXekib2x08THAYUGmD0tjhOO5m"
    }
  ]
}
```

✅ **تنظیمات پیش‌فرض:**
- Python interpreter
- Editor formatting
- File encoding
- Auto-save
- Linting

## 🔧 مرحله 4: راه‌اندازی Ollama

### 4.1: نصب Ollama

```powershell
# Windows
winget install Ollama.Ollama

# یا دانلود از: https://ollama.ai/download
```

### 4.2: نصب مدل‌ها

```bash
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b
ollama list
```

### 4.3: راه‌اندازی سرویس

```bash
ollama serve
```

بررسی:
```bash
curl http://localhost:11434/api/tags
```

## 🚀 مرحله 5: Build MCP Server

```powershell
cd mcp-server-ollama
npm install
npm run build
```

بررسی:
```powershell
Test-Path dist/index.js  # باید True باشد
```

## ✅ مرحله 6: بررسی در VSCode

### 6.1: بررسی MCP Server

1. VSCode را Restart کنید
2. `Ctrl+Shift+P`
3. تایپ کنید: `MCP` یا `Model Context`
4. باید `ollama-local` را ببینید

### 6.2: بررسی Python Extension

1. یک فایل `.py` باز کنید
2. باید autocomplete و linting کار کند

### 6.3: بررسی Claude-code

1. `Ctrl+Shift+P`
2. تایپ کنید: `Claude` یا `Agent`
3. باید دستورات Claude را ببینید

## 🎯 استفاده در VSCode

### استفاده از MCP Tools:

#### از طریق Command Palette:
1. `Ctrl+Shift+P`
2. `MCP: Call Tool`
3. انتخاب `ollama_complete` یا `ollama_chat`

#### از طریق Code Actions:
- Right-click روی کد
- انتخاب `MCP: Complete with Ollama`

### استفاده از Claude-code:

1. `Ctrl+Shift+P`
2. `Claude: Chat` یا `Claude: Complete`
3. استفاده از AgentRouter API

## 🔍 Troubleshooting

### مشکل 1: MCP Server کار نمی‌کند

**بررسی:**
```powershell
# بررسی Ollama
curl http://localhost:11434/api/tags

# بررسی فایل build شده
Test-Path mcp-server-ollama/dist/index.js

# بررسی Node.js
node --version
```

**راه حل:**
1. مطمئن شوید Ollama در حال اجرا است
2. MCP Server را build کنید: `npm run build`
3. VSCode را Restart کنید

### مشکل 2: Extension ها کار نمی‌کنند

**بررسی:**
1. `Ctrl+Shift+X` -> بررسی extension های نصب شده
2. Extension ها را disable/enable کنید
3. VSCode را Restart کنید

### مشکل 3: Python Extension کار نمی‌کند

**بررسی:**
```powershell
# بررسی Python
python --version

# بررسی venv
Test-Path venv/Scripts/python.exe
```

**راه حل:**
1. Python را انتخاب کنید: `Ctrl+Shift+P` -> `Python: Select Interpreter`
2. مسیر: `venv/Scripts/python.exe`

## 📝 تنظیمات اضافی (اختیاری)

### افزودن به `.vscode/settings.json`:

```json
{
  // Git
  "git.enabled": true,
  "git.autofetch": true,
  "git.confirmSync": false,

  // Terminal
  "terminal.integrated.defaultProfile.windows": "PowerShell",
  "terminal.integrated.fontSize": 14,

  // Editor Advanced
  "editor.minimap.enabled": true,
  "editor.wordWrap": "on",
  "editor.suggestSelection": "first",
  "editor.quickSuggestions": {
    "other": true,
    "comments": false,
    "strings": true
  },

  // Python Advanced
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.completeFunctionParens": true,
  "python.formatting.provider": "black",

  // Files
  "files.watcherExclude": {
    "**/node_modules/**": true,
    "**/venv/**": true,
    "**/.git/**": true
  },

  // Search
  "search.exclude": {
    "**/node_modules": true,
    "**/venv": true,
    "**/dist": true,
    "**/__pycache__": true
  }
}
```

## 🎉 خلاصه

پس از انجام این مراحل:

✅ Extension های لازم نصب شده
✅ MCP Server تنظیم شده
✅ Ollama آماده است
✅ Claude-code تنظیم شده
✅ Python Extension آماده است
✅ همه تنظیمات پیش‌فرض اضافه شده

**حالا VSCode شما کاملاً آماده استفاده از MCP و Ollama است!** 🚀

