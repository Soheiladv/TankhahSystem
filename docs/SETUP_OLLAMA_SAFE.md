# راهنمای ایمن اضافه کردن Ollama به تنظیمات موجود

این راهنما به شما کمک می‌کند Ollama MCP Server را **بدون تغییر تنظیمات موجود** اضافه کنید.

## 🎯 هدف

- ✅ اضافه کردن Ollama MCP Server
- ✅ حفظ تمام تنظیمات قبلی
- ✅ بدون overwrite کردن تنظیمات موجود

## 🚀 روش سریع

### استفاده از اسکریپت خودکار:

```powershell
.\ADD_OLLAMA_TO_EXISTING.ps1
```

این اسکریپت:
- تنظیمات موجود را می‌خواند
- فقط `ollama-local` را اضافه می‌کند
- تمام تنظیمات دیگر را حفظ می‌کند

## 📝 روش دستی

### 1. برای `.cursor/mcp.json`:

اگر فایل از قبل وجود دارد، فقط `ollama-local` را اضافه کنید:

```json
{
  "mcpServers": {
    // تنظیمات قبلی شما حفظ می‌شود
    "your-existing-server": {
      // ...
    },
    // این را اضافه کنید:
    "ollama-local": {
      "command": "node",
      "args": [
        "${workspaceFolder}/mcp-server-ollama/dist/index.js"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

### 2. برای `.vscode/settings.json`:

تنظیمات قبلی را حفظ کنید و فقط `mcp.servers` را اضافه کنید:

```json
{
  // تمام تنظیمات قبلی شما
  "files.exclude": {
    "**/node_modules": true
  },
  // اضافه کردن این بخش:
  "mcp.servers": {
    "ollama-local": {
      "command": "node",
      "args": [
        "${workspaceFolder}/mcp-server-ollama/dist/index.js"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

## ✅ بررسی

پس از اضافه کردن:

1. **Cursor/VSCode را Restart کنید**
2. **بررسی کنید تنظیمات قبلی شما هنوز کار می‌کند**
3. **بررسی کنید Ollama اضافه شده:**
   - `Ctrl+Shift+P`
   - `MCP: List Servers`
   - باید `ollama-local` را ببینید

## 🔍 مثال

### قبل:
```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["my-script.py"]
    }
  }
}
```

### بعد (با اسکریپت):
```json
{
  "mcpServers": {
    "my-custom-server": {
      "command": "python",
      "args": ["my-script.py"]
    },
    "ollama-local": {
      "command": "node",
      "args": [
        "${workspaceFolder}/mcp-server-ollama/dist/index.js"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

## ⚠️ نکات مهم

1. **Backup بگیرید:** قبل از هر تغییری، از فایل‌های تنظیمات backup بگیرید
2. **JSON Valid:** مطمئن شوید JSON معتبر است (comma های اضافی نداشته باشید)
3. **مسیرها:** مسیر `${workspaceFolder}` خودکار resolve می‌شود

## 🐛 رفع مشکل

### خطای JSON:
```powershell
# بررسی JSON معتبر است
Get-Content .cursor/mcp.json | ConvertFrom-Json
```

### تنظیمات کار نمی‌کند:
1. Cursor/VSCode را Restart کنید
2. بررسی کنید فایل JSON معتبر است
3. بررسی کنید مسیر `dist/index.js` درست است

## 📚 بیشتر بدانید

برای راه‌اندازی کامل Ollama، به `SETUP_MCP_OLLAMA.md` مراجعه کنید.

