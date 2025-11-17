# راهنمای کامل نصب و راه‌اندازی Ollama MCP Server

این راهنما شما را گام به گام برای استفاده از مدل‌های LLM محلی (Ollama) در Cursor و VS Code راهنمایی می‌کند.

## 📋 پیش‌نیازها

### 1. نصب Node.js
- دانلود از: https://nodejs.org/
- نسخه مورد نیاز: v18 یا بالاتر
- بررسی نصب:
```bash
node --version
npm --version
```

### 2. نصب Ollama

#### Windows:
```powershell
# روش 1: دانلود از سایت
# https://ollama.ai/download/windows

# روش 2: با winget
winget install Ollama.Ollama

# شروع Ollama (در PowerShell جدید):
ollama serve
```

#### Linux:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

#### Mac:
```bash
brew install ollama
ollama serve
```

### 3. نصب مدل‌های مورد نیاز

در terminal جدید (بعد از `ollama serve`):

```bash
# نصب مدل کدنویسی
ollama pull qwen2.5-coder:1.5b

# نصب مدل عمومی
ollama pull llama3.2:1b

# بررسی مدل‌های نصب شده
ollama list
```

## 🔧 نصب MCP Server

### روش 1: استفاده از اسکریپت (توصیه می‌شود)

#### Windows (PowerShell):
```powershell
cd mcp-server-ollama
.\install.ps1
```

#### Linux/Mac:
```bash
cd mcp-server-ollama
chmod +x install.sh
./install.sh
```

### روش 2: دستی

```bash
cd mcp-server-ollama
npm install
npm run build
```

## ⚙️ پیکربندی Cursor

### 1. ویرایش فایل `.cursor/mcp.json`

مسیر کامل به فایل build شده را وارد کنید:

**Windows:**
```json
{
  "mcpServers": {
    "ollama-local": {
      "command": "node",
      "args": ["D:\\Design & Source Code\\Source Coding\\BudgetsSystem\\mcp-server-ollama\\dist\\index.js"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**Linux/Mac:**
```json
{
  "mcpServers": {
    "ollama-local": {
      "command": "node",
      "args": ["/path/to/your/project/mcp-server-ollama/dist/index.js"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

### 2. Restart Cursor

بعد از ویرایش فایل، Cursor را کاملاً بسته و دوباره باز کنید.

## 🧪 تست و بررسی

### 1. بررسی Ollama
```bash
# بررسی اینکه Ollama در حال اجرا است
curl http://localhost:11434/api/tags

# تست مستقیم یک مدل
ollama run qwen2.5-coder:1.5b "Hello, write a simple Python function"
```

### 2. بررسی MCP Server

در Cursor:
- Cmd/Ctrl + Shift + P
- تایپ کنید: "MCP"
- باید "ollama-local" را ببینید

### 3. تست در Cursor

می‌توانید از مدل‌های Ollama در چت Cursor استفاده کنید:
- در چت Cursor، می‌توانید به مدل‌های Ollama دسترسی داشته باشید
- برای کدنویسی، مدل `qwen2.5-coder:1.5b` توصیه می‌شود

## 💡 استفاده عملی

### در Cursor:

1. **تکمیل کد**: مدل می‌تواند به شما در نوشتن کد کمک کند
2. **توضیح کد**: کد موجود را توضیح می‌دهد
3. **بازنویسی**: کد را بهبود می‌بخشد
4. **دیباگ**: خطاهای کد را پیدا می‌کند

### مثال‌ها:

```
کاربر: این کد Python را بررسی کن و بهینه‌سازی کن
[کد را پیست می‌کند]

Ollama: [پاسخ با پیشنهادات بهبود]
```

## 🐛 رفع مشکل

### مشکل 1: "Connection refused"
**راه حل**: مطمئن شوید Ollama در حال اجرا است:
```bash
ollama serve
```

### مشکل 2: "Model not found"
**راه حل**: مدل را نصب کنید:
```bash
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b
```

### مشکل 3: MCP Server کار نمی‌کند
**راه حل**:
1. مسیر در `mcp.json` را بررسی کنید
2. فایل `dist/index.js` وجود دارد؟
3. Cursor را restart کنید
4. لاگ‌ها را بررسی کنید (Developer Tools)

### مشکل 4: مدل خیلی کند است
**راه حل**:
- مدل‌های کوچکتر (1b) سریع‌تر هستند
- برای کدنویسی از `qwen2.5-coder` استفاده کنید
- می‌توانید مدل‌های بزرگ‌تر نصب کنید اما کندتر هستند

## 📊 مقایسه مدل‌ها

| مدل | حجم | سرعت | استفاده |
|-----|-----|-------|---------|
| qwen2.5-coder:1.5b | ~1GB | ⚡⚡⚡ | کدنویسی، تکمیل کد |
| llama3.2:1b | ~700MB | ⚡⚡⚡ | چت عمومی، متن |

## 🔄 به‌روزرسانی

```bash
cd mcp-server-ollama
git pull  # اگر از git استفاده می‌کنید
npm install
npm run build
```

## 📝 نکات مهم

1. **آفلاین کار می‌کند**: همه چیز محلی است، نیاز به اینترنت نیست
2. **بدون محدودیت**: می‌توانید هر چقدر می‌خواهید استفاده کنید
3. **خصوصی**: داده‌های شما از سیستم شما خارج نمی‌شود
4. **سریع**: مدل‌های کوچک (1b) بسیار سریع هستند

## 🎯 مراحل خلاصه

1. ✅ نصب Node.js
2. ✅ نصب Ollama
3. ✅ نصب مدل‌ها (`qwen2.5-coder:1.5b`, `llama3.2:1b`)
4. ✅ نصب MCP Server (`npm install && npm run build`)
5. ✅ پیکربندی Cursor (`.cursor/mcp.json`)
6. ✅ Restart Cursor
7. ✅ استفاده! 🎉

## 💬 کمک

اگر مشکلی داشتید:
1. بررسی کنید Ollama در حال اجرا است
2. مدل‌ها را بررسی کنید (`ollama list`)
3. مسیرها در `mcp.json` را بررسی کنید
4. Cursor را restart کنید

