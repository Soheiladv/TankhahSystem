# راهنمای سریع: اضافه کردن Ollama به تنظیمات موجود

این راهنما نشان می‌دهد چگونه **فقط Ollama** را به تنظیمات موجود اضافه کنید **بدون تغییر تنظیمات دیگر**.

## ✅ استفاده از اسکریپت خودکار (پیشنهادی)

```powershell
.\ADD_OLLAMA_TO_EXISTING.ps1
```

این اسکریپت:
- ✅ تنظیمات موجود را می‌خواند
- ✅ فقط `ollama-local` را اضافه می‌کند  
- ✅ تمام تنظیمات دیگر را حفظ می‌کند
- ✅ سایر MCP servers را حفظ می‌کند

## 📋 چه اتفاقی می‌افتد؟

### قبل از اجرا:
```json
{
  "mcpServers": {
    "my-existing-server": {
      "command": "python",
      "args": ["script.py"]
    }
  },
  "otherSettings": {
    "key": "value"
  }
}
```

### بعد از اجرا:
```json
{
  "mcpServers": {
    "my-existing-server": {
      "command": "python",
      "args": ["script.py"]
    },
    "ollama-local": {
      "command": "node",
      "args": ["${workspaceFolder}/mcp-server-ollama/dist/index.js"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  },
  "otherSettings": {
    "key": "value"
  }
}
```

**همانطور که می‌بینید:**
- ✅ `my-existing-server` حفظ شد
- ✅ `otherSettings` حفظ شد  
- ✅ فقط `ollama-local` اضافه شد

## 🔍 بررسی

پس از اجرای اسکریپت:

1. **Cursor/VSCode را Restart کنید**
2. **بررسی کنید تنظیمات قبلی کار می‌کند**
3. **بررسی کنید Ollama اضافه شده:**
   - `Ctrl+Shift+P`
   - `MCP: List Servers`
   - باید `ollama-local` را ببینید

## 📁 فایل‌های تغییر یافته

اسکریپت فقط این فایل‌ها را تغییر می‌دهد:

- `.cursor/mcp.json` - اضافه کردن `ollama-local` به `mcpServers`
- `.vscode/settings.json` - اضافه کردن `ollama-local` به `mcp.servers`

**همه تنظیمات دیگر حفظ می‌شوند!**

## ⚠️ نکات

1. **Backup:** اسکریپت خودکار backup نمی‌گیرد، اگر می‌خواهید:
   ```powershell
   Copy-Item .cursor/mcp.json .cursor/mcp.json.backup
   Copy-Item .vscode/settings.json .vscode/settings.json.backup
   ```

2. **JSON معتبر:** مطمئن شوید فایل‌های JSON شما معتبر هستند

3. **مسیرها:** مسیر `${workspaceFolder}` خودکار resolve می‌شود

## 🐛 اگر مشکلی پیش آمد

```powershell
# بررسی JSON معتبر است
Get-Content .cursor/mcp.json | ConvertFrom-Json
Get-Content .vscode/settings.json | ConvertFrom-Json
```

اگر خطا داد، JSON شما معتبر نیست و باید دستی اصلاح کنید.

