# 🔍 بررسی MCP Server در VSCode

## 📋 نام MCP Server

در VSCode، وقتی `Ctrl+Shift+P` → `MCP: List Servers` را اجرا می‌کنید، باید این عنوان را ببینید:

### ✅ **`ollama-local`**

این نام در فایل `.vscode/settings.json` تنظیم شده است:

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

## 🔍 جزئیات MCP Server

### نام: `ollama-local`
- **نام شناسایی:** `ollama-local`
- **توضیحات:** MCP Server برای مدل‌های محلی Ollama
- **نسخه:** 1.0.0
- **مدل‌های پشتیبانی شده:**
  - `qwen2.5-coder:1.5b`
  - `llama3.2:1b`

### Tool های موجود:

1. **`ollama_complete`**
   - تکمیل متن با استفاده از مدل Ollama
   - پشتیبانی از code completion و text generation

2. **`ollama_list_models`**
   - لیست همه مدل‌های Ollama نصب شده

3. **`ollama_code_assistant`**
   - کمک در کدنویسی (complete, explain, refactor, debug, optimize)

4. **`ollama_chat`**
   - گفتگو با مدل Ollama

### Resource های موجود:

- `ollama://model/qwen2.5-coder:1.5b`
- `ollama://model/llama3.2:1b`

## ✅ بررسی

### 1. بررسی در VSCode:

1. `Ctrl+Shift+P`
2. تایپ کنید: `MCP`
3. باید گزینه‌های زیر را ببینید:
   - `MCP: List Servers` - لیست تمام MCP Servers
   - `MCP: List Tools` - لیست Tool های موجود
   - `MCP: List Resources` - لیست Resource های موجود

### 2. بررسی MCP Servers:

وقتی `MCP: List Servers` را اجرا می‌کنید، باید در لیست ببینید:

```
ollama-local
  └─ Status: Running (یا Connected)
  └─ Tools: 4
  └─ Resources: 2
```

### 3. بررسی Tools:

وقتی `MCP: List Tools` را اجرا می‌کنید، باید این Tool ها را ببینید:

- ✅ `ollama_complete`
- ✅ `ollama_list_models`
- ✅ `ollama_code_assistant`
- ✅ `ollama_chat`

### 4. بررسی Resources:

وقتی `MCP: List Resources` را اجرا می‌کنید، باید این Resource ها را ببینید:

- ✅ `ollama://model/qwen2.5-coder:1.5b`
- ✅ `ollama://model/llama3.2:1b`

## 🐛 Troubleshooting

### اگر `ollama-local` را نمی‌بینید:

1. **بررسی تنظیمات:**
   ```powershell
   Get-Content .vscode/settings.json | ConvertFrom-Json | Select-Object 'mcp.servers'
   ```

2. **بررسی فایل build شده:**
   ```powershell
   Test-Path mcp-server-ollama/dist/index.js
   ```

3. **بررسی Ollama:**
   ```powershell
   ollama list
   curl http://localhost:11434/api/tags
   ```

4. **Restart VSCode:**
   - برای اعمال تنظیمات جدید

### اگر Status: Error نشان می‌دهد:

1. **بررسی Ollama:**
   - مطمئن شوید Ollama در حال اجرا است: `ollama serve`

2. **بررسی Node.js:**
   ```powershell
   node --version
   ```

3. **Rebuild MCP Server:**
   ```powershell
   cd mcp-server-ollama
   node node_modules/typescript/lib/tsc.js
   ```

## 📝 استفاده

### استفاده از Tool ها:

1. `Ctrl+Shift+P`
2. `MCP: Call Tool`
3. انتخاب Tool مورد نظر (مثلاً `ollama_complete`)
4. وارد کردن پارامترها

### استفاده از Resource ها:

1. `Ctrl+Shift+P`
2. `MCP: Read Resource`
3. انتخاب Resource مورد نظر

## ✅ خلاصه

**نام MCP Server:** `ollama-local`

**وضعیت:** باید در لیست `MCP: List Servers` به صورت `ollama-local` نمایش داده شود.

---

**تاریخ:** $(Get-Date -Format "yyyy-MM-dd HH:mm")

