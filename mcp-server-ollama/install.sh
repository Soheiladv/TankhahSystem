#!/bin/bash

echo "🚀 نصب MCP Server برای Ollama..."
echo ""

# بررسی Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js یافت نشد. لطفاً ابتدا Node.js را نصب کنید."
    exit 1
fi

echo "✅ Node.js نصب شده: $(node --version)"

# بررسی Ollama
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama یافت نشد."
    echo "لطفاً Ollama را از https://ollama.ai/download نصب کنید."
    read -p "آیا می‌خواهید ادامه دهید؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Ollama نصب شده: $(ollama --version)"
fi

# نصب dependencies
echo ""
echo "📦 نصب dependencies..."
npm install

# Build
echo ""
echo "🔨 Build پروژه..."
npm run build

# بررسی مدل‌ها
echo ""
echo "🔍 بررسی مدل‌های Ollama..."
if command -v ollama &> /dev/null; then
    echo "مدل‌های موجود:"
    ollama list
    
    echo ""
    echo "در حال بررسی مدل‌های مورد نیاز..."
    
    if ollama list | grep -q "qwen2.5-coder:1.5b"; then
        echo "✅ qwen2.5-coder:1.5b یافت شد"
    else
        echo "⚠️  qwen2.5-coder:1.5b یافت نشد"
        read -p "آیا می‌خواهید نصب کنید؟ (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📥 نصب qwen2.5-coder:1.5b..."
            ollama pull qwen2.5-coder:1.5b
        fi
    fi
    
    if ollama list | grep -q "llama3.2:1b"; then
        echo "✅ llama3.2:1b یافت شد"
    else
        echo "⚠️  llama3.2:1b یافت نشد"
        read -p "آیا می‌خواهید نصب کنید؟ (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📥 نصب llama3.2:1b..."
            ollama pull llama3.2:1b
        fi
    fi
fi

echo ""
echo "✅ نصب کامل شد!"
echo ""
echo "📝 مراحل بعدی:"
echo "1. فایل .cursor/mcp.json را ویرایش کنید و مسیر را به پروژه خود تغییر دهید"
echo "2. Cursor را restart کنید"
echo "3. از مدل‌های Ollama استفاده کنید!"
echo ""

