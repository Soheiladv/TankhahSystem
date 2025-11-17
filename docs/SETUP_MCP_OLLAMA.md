# راهنمای کامل راه‌اندازی MCP با Ollama برای مدل‌های محلی

این راهنما به شما کمک می‌کند مدل‌های LLM محلی (`qwen2.5-coder:1.5b` و `llama3.2:1b`) را در VSCode و Cursor راه‌اندازی کنید.

## 📋 مرحله 1: نصب Ollama

### Windows (PowerShell):

```powershell
# روش 1: با winget (پیشنهادی)
winget install Ollama.Ollama

# روش 2: دانلود دستی
# از https://ollama.ai/download دانلود کنید و نصب کنید

# بررسی نصب
ollama --version
```

### Linux/Mac:

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

## 📥 مرحله 2: نصب مدل‌ها

پس از نصب Ollama، مدل‌های مورد نیاز را نصب کنید:

```bash
# نصب مدل‌های مورد نیاز
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b

# بررسی مدل‌های نصب شده
ollama list
```

**نکته:** اولین بار نصب ممکن است چند دقیقه طول بکشد.

## 🚀 مرحله 3: راه‌اندازی Ollama Service

Ollama باید به عنوان سرویس در حال اجرا باشد:

```bash
# Windows (PowerShell)
ollama serve

# یا به عنوان Windows Service (پس از نصب خودکار راه‌اندازی می‌شود)
```

بررسی کنید که Ollama در حال اجرا است:

```bash
# بررسی اتصال
curl http://localhost:11434/api/tags

# یا در مرورگر باز کنید:
# http://localhost:11434/api/tags
```

## 🔧 مرحله 4: نصب و Build MCP Server

```powershell
# در PowerShell از ریشه پروژه:
cd mcp-server-ollama

# نصب dependencies
npm install

# Build پروژه
npm run build
```

## ⚙️ مرحله 5: پیکربندی Cursor

### 5.1: پیدا کردن مسیر MCP Config در Cursor

در Windows، فایل تنظیمات Cursor معمولاً در این مسیر است:

```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

یا اگر از تنظیمات workspace استفاده می‌کنید:

```
<workspace>/.cursor/mcp.json
```

### 5.2: ایجاد/ویرایش فایل تنظیمات

#### روش 1: از طریق Cursor Settings UI

1. در Cursor: `Ctrl+Shift+P` (یا `Cmd+Shift+P` در Mac)
2. تایپ کنید: `Preferences: Open User Settings (JSON)`
3. اضافه کنید:

```json
{
  "mcp.servers": {
    "ollama-local": {
      "command": "node",
      "args": [
        "D:\\Design & Source Code\\Source Coding\\BudgetsSystem\\mcp-server-ollama\\dist\\index.js"
      ],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**⚠️ مهم:** مسیر `D:\\Design & Source Code\\Source Coding\\BudgetsSystem\\mcp-server-ollama\\dist\\index.js` را به مسیر واقعی پروژه خود تغییر دهید.

#### روش 2: ایجاد فایل `.cursor/mcp.json` در پروژه

در ریشه پروژه، پوشه `.cursor` ایجاد کنید و فایل `mcp.json` بسازید:

```json
{
  "mcpServers": {
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

### 5.3: تنظیمات برای Auto (من)

برای اینکه من (Auto) بتوانم از مدل‌های Ollama استفاده کنم، باید در تنظیمات Cursor MCP servers را فعال کنید.

## ⚙️ مرحله 6: پیکربندی VSCode (اختیاری)

اگر از VSCode استفاده می‌کنید، فایل `.vscode/settings.json` را ویرایش کنید:

```json
{
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

## ✅ مرحله 7: بررسی کارکرد

### 7.1: بررسی Ollama

```bash
# تست اتصال
curl http://localhost:11434/api/tags

# تست مدل
ollama run qwen2.5-coder:1.5b "write a hello world function in Python"
```

### 7.2: بررسی MCP Server

```powershell
# از پوشه mcp-server-ollama
npm start

# باید خروجی MCP server را ببینید
```

### 7.3: بررسی در Cursor

1. Cursor را Restart کنید
2. `Ctrl+Shift+P` بزنید
3. تایپ کنید: `MCP: List Servers`
4. باید `ollama-local` را ببینید

## 🎯 استفاده

### در Cursor:

1. **استفاده از Command Palette:**
   - `Ctrl+Shift+P`
   - `MCP: Call Tool`
   - انتخاب `ollama_complete` یا `ollama_chat`

2. **استفاده مستقیم:**
   - وقتی از من (Auto) سوال می‌پرسید، من می‌توانم از MCP tools استفاده کنم

### Tool های موجود:

#### 1. `ollama_complete`
تکمیل متن یا کد:

```json
{
  "prompt": "write a function to calculate budget",
  "model": "qwen2.5-coder:1.5b",
  "max_tokens": 500
}
```

#### 2. `ollama_chat`
چت با مدل:

```json
{
  "message": "explain this code",
  "model": "llama3.2:1b",
  "context": "your code here"
}
```

#### 3. `ollama_code_assistant`
کمک در کدنویسی:

```json
{
  "task": "refactor",
  "code": "your code",
  "model": "qwen2.5-coder:1.5b"
}
```

#### 4. `ollama_list_models`
لیست مدل‌های موجود

## 🔍 تست سریع

یک فایل تست بسازید:

```bash
# test-mcp.ps1
node mcp-server-ollama/dist/index.js
```

اگر خروجی MCP protocol را دیدید، یعنی کار می‌کند.

## 🐛 رفع مشکلات

### مشکل 1: Ollama اجرا نمی‌شود

```powershell
# بررسی سرویس
Get-Service | Where-Object {$_.Name -like "*ollama*"}

# راه‌اندازی دستی
ollama serve
```

### مشکل 2: مدل یافت نشد

```bash
# بررسی مدل‌های نصب شده
ollama list

# اگر مدل نیست، دوباره نصب کنید
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b
```

### مشکل 3: MCP Server کار نمی‌کند

1. مطمئن شوید `npm run build` اجرا شده
2. بررسی کنید `dist/index.js` وجود دارد
3. مسیر در `settings.json` را بررسی کنید
4. Cursor را Restart کنید

### مشکل 4: خطای اتصال

```bash
# بررسی اینکه Ollama در حال اجرا است
curl http://localhost:11434/api/tags

# اگر خطا داد، Ollama را restart کنید
```

### مشکل 5: Node.js یافت نشد

```powershell
# بررسی Node.js
node --version

# اگر نیست، نصب کنید:
winget install OpenJS.NodeJS.LTS
```

## 📝 نکات مهم

1. **مسیرها:** همه مسیرها باید absolute باشند یا از `${workspaceFolder}` استفاده کنید
2. **Node.js:** باید Node.js v18+ نصب باشد
3. **Ollama:** باید همیشه در حال اجرا باشد
4. **Restart:** بعد از هر تغییر تنظیمات، Cursor را restart کنید

## 🚀 بهینه‌سازی

برای عملکرد بهتر:

1. **مدل کوچک‌تر استفاده کنید:** `llama3.2:1b` سریع‌تر است
2. **Batch size را تنظیم کنید:** در فایل `.vscode/settings.json`
3. **Cache را فعال کنید:** Ollama به صورت خودکار cache می‌کند

## 📚 منابع بیشتر

- [Ollama Documentation](https://ollama.ai/docs)
- [MCP Protocol](https://modelcontextprotocol.io)
- [Cursor MCP Setup](https://cursor.sh/docs/mcp)

## ✅ چک‌لیست نهایی

- [ ] Ollama نصب و اجرا شده
- [ ] مدل‌های `qwen2.5-coder:1.5b` و `llama3.2:1b` نصب شده
- [ ] MCP server build شده (`npm run build`)
- [ ] فایل تنظیمات Cursor درست است
- [ ] Cursor restart شده
- [ ] MCP server در Cursor دیده می‌شود
- [ ] تست اولیه موفق بوده

---

**پس از راه‌اندازی، من (Auto) می‌توانم از این مدل‌های محلی برای کمک به شما استفاده کنم! 🎉**

