#!/bin/bash
# اسکریپت امنیت‌سازی فایل‌های Secrets در Linux
# این اسکریپت دسترسی فایل‌های secrets را محدود می‌کند

SECRETS_DIR="${1:-secrets}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT" || exit 1

echo ""
echo "🔒 امنیت‌سازی فایل‌های Secrets"
echo "=================================================="
echo ""

# بررسی وجود پوشه
if [ ! -d "$SECRETS_DIR" ]; then
    echo "❌ پوشه $SECRETS_DIR پیدا نشد"
    echo "لطفاً ابتدا فایل‌های secrets را ایجاد کنید:"
    echo "  bash docker-scripts/setup-secrets.sh"
    exit 1
fi

# بررسی وجود فایل‌های secrets
SECRET_FILES=$(find "$SECRETS_DIR" -type f -name "*.txt" 2>/dev/null)
if [ -z "$SECRET_FILES" ]; then
    echo "⚠ هیچ فایل secret پیدا نشد"
    echo "لطفاً ابتدا فایل‌های secrets را ایجاد کنید:"
    echo "  bash docker-scripts/setup-secrets.sh"
    exit 1
fi

echo "📁 فایل‌های پیدا شده:"
echo "$SECRET_FILES" | while read -r file; do
    echo "  - $(basename "$file")"
done

# محدود کردن دسترسی فایل‌ها
echo ""
echo "🔐 محدود کردن دسترسی‌ها..."

# محدود کردن دسترسی پوشه
chmod 700 "$SECRETS_DIR" 2>/dev/null || {
    echo "⚠ نتوانست دسترسی پوشه را تغییر دهد (ممکن است نیاز به sudo باشد)"
}

# محدود کردن دسترسی هر فایل
echo "$SECRET_FILES" | while read -r file; do
    if [ -f "$file" ]; then
        # تنظیم دسترسی 600 (فقط مالک می‌تواند بخواند و بنویسد)
        chmod 600 "$file" 2>/dev/null || {
            echo "  ⚠ نتوانست دسترسی $file را تغییر دهد"
            continue
        }
        echo "  ✓ $(basename "$file") محافظت شد"
    fi
done

# اگر root هستیم، مالکیت را تغییر می‌دهیم
if [ "$EUID" -eq 0 ]; then
    echo ""
    echo "🔐 تنظیم مالکیت root (با دسترسی sudo)..."
    chown root:root "$SECRETS_DIR"/*.txt 2>/dev/null
    chmod 600 "$SECRETS_DIR"/*.txt 2>/dev/null
    echo "  ✓ مالکیت root تنظیم شد"
else
    echo ""
    echo "💡 برای محافظت بیشتر، می‌توانید با sudo اجرا کنید:"
    echo "  sudo bash docker-scripts/secure-secrets.sh"
fi

# بررسی Git
echo ""
echo "🔍 بررسی Git..."

if [ -d ".git" ]; then
    TRACKED_SECRETS=$(git ls-files "$SECRETS_DIR/" 2>/dev/null)

    if [ -n "$TRACKED_SECRETS" ]; then
        echo "⚠ هشدار امنیتی: فایل‌های secrets در Git track شده‌اند:"
        echo "$TRACKED_SECRETS" | while read -r file; do
            echo "  - $file"
        done
        echo ""
        echo "💡 برای حذف آن‌ها از Git (بدون حذف از دیسک):"
        echo "  git rm --cached $SECRETS_DIR/*.txt"
        echo "  git commit -m 'Remove secrets from git tracking'"
    else
        echo "  ✅ هیچ فایل secret در Git track نشده است"
    fi
else
    echo "  ℹ این پروژه یک مخزن Git نیست"
fi

# بررسی .gitignore
echo ""
echo "📋 بررسی .gitignore..."

if [ -f ".gitignore" ]; then
    if grep -q "secrets.*\.txt" .gitignore || grep -q "secrets/" .gitignore; then
        echo "  ✅ فایل‌های secrets در .gitignore هستند"
    else
        echo "  ⚠ فایل‌های secrets ممکن است در .gitignore نباشند"
        echo "  💡 اضافه کردن به .gitignore:"
        echo "    secrets/*.txt"
    fi
else
    echo "  ⚠ فایل .gitignore پیدا نشد"
fi

# نمایش دسترسی‌های فعلی
echo ""
echo "📊 دسترسی‌های فعلی:"
echo "$SECRET_FILES" | while read -r file; do
    if [ -f "$file" ]; then
        echo ""
        echo "  $(basename "$file"):"
        ls -lh "$file" | awk '{print "    " $1 " " $3 " " $4}'
    fi
done

echo ""
echo "✅ امنیت‌سازی با موفقیت انجام شد!"
echo ""
echo "💡 نکات مهم:"
echo "  - فایل‌های secrets اکنون فقط توسط شما قابل دسترسی هستند"
echo "  - هرگز این فایل‌ها را در Git commit نکنید"
echo "  - در صورت نیاز به به‌اشتراک‌گذاری، از روش‌های امن استفاده کنید"
echo ""

