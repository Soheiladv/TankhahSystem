# 🚀 راهنمای سریع آماده‌سازی VSCode

## ⚡ روش سریع (توصیه می‌شود)

فقط این دستور را اجرا کنید:

```powershell
.\VSCODE_QUICK_SETUP.ps1
```

این اسکریپت به صورت خودکار:
- ✅ VSCode CLI را بررسی می‌کند
- ✅ Node.js را بررسی می‌کند
- ✅ Ollama و مدل‌ها را بررسی و نصب می‌کند
- ✅ MCP Server را build می‌کند
- ✅ Extension های لازم را نصب می‌کند
- ✅ تنظیمات را بررسی می‌کند

## 📦 روش دستی

### 1. نصب Extension ها

```powershell
.\INSTALL_VSCODE_EXTENSIONS.ps1
```

یا در VSCode:
- `Ctrl+Shift+P` -> `Extensions: Show Recommended Extensions`
- روی `Install All` کلیک کنید

### 2. راه‌اندازی Ollama

```powershell
# بررسی Ollama
ollama list

# نصب مدل‌ها (اگر نصب نیستند)
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b

# شروع سرویس
ollama serve
```

### 3. Build MCP Server

```powershell
cd mcp-server-ollama
npm install
npm run build
cd ..
```

### 4. Restart VSCode

تمام! 🎉

## ✅ بررسی

### بررسی MCP Server:
```powershell
# در VSCode: Ctrl+Shift+P
# تایپ کنید: MCP
# باید ollama-local را ببینید
```

### بررسی Extension ها:
```powershell
code --list-extensions
```

### بررسی Ollama:
```powershell
ollama list
curl http://localhost:11434/api/tags
```

## 📚 فایل‌های راهنما

- **`VSCODE_SETUP_COMPLETE.md`** - راهنمای کامل و تفصیلی
- **`VSCODE_QUICK_SETUP.ps1`** - اسکریپت خودکار کامل
- **`INSTALL_VSCODE_EXTENSIONS.ps1`** - فقط نصب extension ها
- **`.vscode/extensions.json`** - لیست extension های توصیه شده
- **`.vscode/settings.json`** - تنظیمات کامل VSCode

## 🎯 تنظیمات موجود

✅ **MCP Server** (`ollama-local`)
✅ **Claude-code** (AgentRouter)
✅ **Python** (Django, Black, Pylint, Flake8)
✅ **Editor** (Formatting, Linting, Auto-save)
✅ **Git** (Auto-fetch)
✅ **Terminal** (PowerShell)
✅ **File Watching** (Exclusions)
✅ **Search** (Exclusions)

## 💡 استفاده

### استفاده از MCP Tools:
1. `Ctrl+Shift+P`
2. `MCP: Call Tool`
3. انتخاب `ollama_complete` یا `ollama_chat`

### استفاده از Claude-code:
1. `Ctrl+Shift+P`
2. `Claude: Chat` یا `Claude: Complete`

### استفاده از Ollama مستقیم:
```powershell
ollama run qwen2.5-coder:1.5b "write a Python function to sort a list"
```

## 🆘 Troubleshooting

### MCP Server کار نمی‌کند:
1. مطمئن شوید Ollama در حال اجرا است: `ollama serve`
2. MCP Server را rebuild کنید: `cd mcp-server-ollama && npm run build`
3. VSCode را Restart کنید

### Extension ها کار نمی‌کنند:
1. Extension ها را disable/enable کنید
2. VSCode را Restart کنید
3. به صورت دستی نصب کنید: `code --install-extension <id>`

### Python Extension کار نمی‌کند:
1. `Ctrl+Shift+P` -> `Python: Select Interpreter`
2. مسیر را انتخاب کنید: `venv/Scripts/python.exe`

## 📞 پشتیبانی

برای اطلاعات بیشتر، فایل **`VSCODE_SETUP_COMPLETE.md`** را مطالعه کنید.

