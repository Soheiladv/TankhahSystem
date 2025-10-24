#!/bin/bash
# Setup script for Budgets System Docker deployment

set -e

echo "🚀 Setting up Budgets System Docker environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p ssl
mkdir -p logs
mkdir -p backups
mkdir -p nginx/conf.d

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f env.example ]; then
        cp env.example .env
        echo "✅ .env file created from template. Please update the values."
    else
        echo "❌ env.example file not found. Please create .env file manually."
        exit 1
    fi
fi

# Generate SSL certificates for development
echo "🔐 Generating SSL certificates for development..."
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=IR/ST=Tehran/L=Tehran/O=BudgetsSystem/CN=localhost"
    echo "✅ SSL certificates generated for development"
else
    echo "✅ SSL certificates already exist"
fi

# Set proper permissions
echo "🔒 Setting proper permissions..."
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Build Docker images
echo "🏗️  Building Docker images..."
docker-compose build

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose exec web python manage.py migrate

# Create superuser
echo "👤 Creating superuser..."
docker-compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# Collect static files
echo "📦 Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

echo "✅ Setup completed successfully!"
echo ""
echo "🌐 Application is available at:"
echo "   - HTTP:  http://localhost"
echo "   - HTTPS: https://localhost"
echo ""
echo "👤 Default admin credentials:"
echo "   - Username: admin"
echo "   - Password: admin123"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose down"
