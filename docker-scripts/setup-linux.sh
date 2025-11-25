#!/bin/bash
# اسکریپت راه‌اندازی Budgets System در Linux
# این اسکریپت تمام پیش‌نیازها را بررسی و تنظیم می‌کند

set -e

echo ""
echo "🔧 راه‌اندازی Budgets System در Linux"
echo "=================================================="
echo ""

# رنگ‌ها
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# بررسی Docker
echo "[1] بررسی Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker نصب نشده است!${NC}"
    echo "لطفاً Docker را نصب کنید:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y docker.io docker-compose"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker در حال اجرا نیست!${NC}"
    echo "لطفاً Docker را اجرا کنید:"
    echo "  sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker نصب و در حال اجرا است${NC}"

# بررسی Docker Compose
echo ""
echo "[2] بررسی Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker Compose پیدا نشد${NC}"
    echo "نصب Docker Compose..."
    sudo apt-get install -y docker-compose
fi
echo -e "${GREEN}✅ Docker Compose موجود است${NC}"

# بررسی پوشه secrets
echo ""
echo "[3] بررسی فایل‌های Secrets..."
if [ ! -d "secrets" ]; then
    echo "📁 ایجاد پوشه secrets..."
    mkdir -p secrets
fi

# بررسی فایل‌های secrets مورد نیاز
REQUIRED_SECRETS=("db_password.txt" "redis_password.txt" "django_secret_key.txt")
MISSING_SECRETS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
    if [ ! -f "secrets/$secret" ]; then
        MISSING_SECRETS+=("$secret")
        echo -e "${RED}❌ secrets/$secret پیدا نشد${NC}"
    else
        # بررسی اینکه فایل خالی نباشد
        if [ ! -s "secrets/$secret" ]; then
            echo -e "${YELLOW}⚠ secrets/$secret خالی است${NC}"
            MISSING_SECRETS+=("$secret")
        else
            echo -e "${GREEN}✅ secrets/$secret موجود است${NC}"
        fi
    fi
done

if [ ${#MISSING_SECRETS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ فایل‌های secrets زیر پیدا نشدند:${NC}"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - secrets/$secret"
    done
    echo ""
    echo "لطفاً این فایل‌ها را ایجاد کنید:"
    echo "  echo 'your_password' > secrets/db_password.txt"
    echo "  echo 'your_redis_password' > secrets/redis_password.txt"
    echo "  echo 'your_django_secret_key' > secrets/django_secret_key.txt"
    echo ""
    echo "یا از اسکریپت setup-secrets.sh استفاده کنید (اگر موجود است)"
    exit 1
fi

# محدود کردن دسترسی فایل‌های secrets
echo ""
echo "[4] محدود کردن دسترسی فایل‌های Secrets..."
chmod 600 secrets/*.txt 2>/dev/null || {
    echo -e "${YELLOW}⚠ نتوانست دسترسی فایل‌ها را تغییر دهد (ممکن است نیاز به sudo باشد)${NC}"
    echo "در حال تلاش با sudo..."
    sudo chmod 600 secrets/*.txt
    sudo chmod 700 secrets
    sudo chown $USER:$USER secrets/*.txt
}

chmod 700 secrets 2>/dev/null || sudo chmod 700 secrets
echo -e "${GREEN}✅ دسترسی فایل‌های secrets محدود شد${NC}"

# بررسی فایل .env
echo ""
echo "[5] بررسی فایل .env..."
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📄 ایجاد فایل .env از env.example..."
        cp env.example .env
        echo -e "${YELLOW}⚠ لطفاً فایل .env را ویرایش کنید${NC}"
        echo "  nano .env"
    else
        echo -e "${YELLOW}⚠ فایل env.example پیدا نشد${NC}"
    fi
else
    echo -e "${GREEN}✅ فایل .env موجود است${NC}"
fi

# بررسی فایل‌های Docker
echo ""
echo "[6] بررسی فایل‌های Docker..."
DOCKER_FILES=("Dockerfile" "docker-compose.yml" "docker/entrypoint.sh" "docker/healthcheck.sh")
ALL_FILES_EXIST=true

for file in "${DOCKER_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ $file پیدا نشد${NC}"
        ALL_FILES_EXIST=false
    else
        echo -e "${GREEN}✅ $file موجود است${NC}"
    fi
done

if [ "$ALL_FILES_EXIST" = false ]; then
    echo -e "${RED}❌ برخی فایل‌های Docker پیدا نشدند${NC}"
    exit 1
fi

# بررسی requirements.txt
echo ""
echo "[7] بررسی requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt پیدا نشد${NC}"
    exit 1
fi
echo -e "${GREEN}✅ requirements.txt موجود است${NC}"

# بررسی پورت‌ها
echo ""
echo "[8] بررسی پورت‌های استفاده شده..."
PORTS=(3307 6379 8000 8080 443)
USED_PORTS=()

for port in "${PORTS[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        USED_PORTS+=("$port")
        echo -e "${YELLOW}⚠ پورت $port در حال استفاده است${NC}"
    else
        echo -e "${GREEN}✅ پورت $port آزاد است${NC}"
    fi
done

if [ ${#USED_PORTS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ برخی پورت‌ها در حال استفاده هستند: ${USED_PORTS[*]}${NC}"
    echo "ممکن است نیاز به تغییر در docker-compose.yml باشد"
fi

# خلاصه
echo ""
echo "=================================================="
echo -e "${GREEN}✅ همه چیز آماده است!${NC}"
echo "=================================================="
echo ""
echo "🚀 برای اجرای Docker:"
echo "  docker compose up -d --build"
echo ""
echo "📋 دستورات مفید:"
echo "  - مشاهده وضعیت: docker compose ps"
echo "  - مشاهده لاگ‌ها: docker compose logs -f"
echo "  - توقف: docker compose down"
echo ""

