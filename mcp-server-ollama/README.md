# MCP Server برای Ollama (مدل‌های LLM آفلاین)

این MCP Server به شما امکان استفاده از مدل‌های Ollama محلی را در VS Code و Cursor می‌دهد.

## 📋 نیازمندی‌ها

1. **Node.js** (v18 یا بالاتر)
2. **Ollama** نصب شده و در حال اجرا
3. **مدل‌های Ollama**:
   - `qwen2.5-coder:1.5b`
   - `llama3.2:1b`

## 🚀 نصب Ollama

### Windows:
```powershell
# دانلود از https://ollama.ai/download
# یا با winget:
winget install Ollama.Ollama

# شروع سرویس Ollama
ollama serve
```

### Linux/Mac:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

## 📥 نصب مدل‌ها

```bash
# نصب مدل‌های مورد نیاز
ollama pull qwen2.5-coder:1.5b
ollama pull llama3.2:1b

# بررسی مدل‌های نصب شده
ollama list
```

## 🔧 نصب MCP Server

```bash
cd mcp-server-ollama
npm install
npm run build
```

## ⚙️ پیکربندی

### برای Cursor:

فایل `.cursor/mcp.json` را ویرایش کنید و مسیر را به پروژه خود تغییر دهید:

```json
{
  "mcpServers": {
    "ollama-local": {
      "command": "node",
      "args": ["<مسیر-کامل-به-پروژه>/mcp-server-ollama/dist/index.js"],
      "env": {
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

### برای VS Code:

فایل `.vscode/settings.json` را ویرایش کنید.

## 🎯 استفاده

پس از راه‌اندازی، می‌توانید:

1. **در Cursor**: از مدل‌های Ollama برای کمک در کدنویسی استفاده کنید
2. **در VS Code**: از extension MCP استفاده کنید
3. **مستقیماً**: از طریق tool calls

## 🛠️ Tool های موجود

### `ollama_complete`
تکمیل متن با استفاده از مدل Ollama

### `ollama_code_assistant`
کمک در کدنویسی (تکمیل، توضیح، بازنویسی)

### `ollama_chat`
چت با مدل Ollama

### `ollama_list_models`
لیست مدل‌های موجود

## 🔍 بررسی کارکرد

```bash
# بررسی اتصال Ollama
curl http://localhost:11434/api/tags

# تست مستقیم مدل
ollama run qwen2.5-coder:1.5b "Hello, write a Python function"
```

## 🐛 رفع مشکل

1. **خطای اتصال**: مطمئن شوید Ollama در حال اجرا است (`ollama serve`)
2. **مدل یافت نشد**: مدل را نصب کنید (`ollama pull <model-name>`)
3. **MCP کار نمی‌کند**: Cursor/VS Code را restart کنید

## 📝 مثال استفاده در کد

```python
# می‌توانید از مدل‌های Ollama برای:
# - تکمیل کد
# - توضیح کد موجود
# - بازنویسی و بهینه‌سازی
# - دیباگ
# - تولید کد جدید
```

