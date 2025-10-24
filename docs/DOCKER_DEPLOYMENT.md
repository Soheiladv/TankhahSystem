# 🐳 Docker Deployment Guide for Budgets System

## 📋 Prerequisites

### Windows Requirements
- **Docker Desktop for Windows** (latest version)
- **Windows 10/11** with WSL2 enabled
- **Git** for cloning the repository
- **PowerShell** or **Command Prompt**

### System Requirements
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: At least 10GB free space
- **CPU**: 2+ cores recommended

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repository-url>
cd BudgetsSystem

# Copy environment template
copy env.example .env
```

### 2. Configure Environment
Edit `.env` file with your settings:
```bash
# Critical settings - CHANGE THESE!
SECRET_KEY=your-super-secret-key-here
DB_PASSWORD=your-strong-database-password
REDIS_PASSWORD=your-strong-redis-password

# Domain settings
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

### 3. Run Setup Script
```bash
# Make script executable (if needed)
# Run setup
docker/scripts/setup.sh
```

### 4. Access Application
- **HTTP**: http://localhost
- **HTTPS**: https://localhost
- **Admin**: https://localhost/admin (admin/admin123)

## 🔧 Manual Setup

### 1. Build Images
```bash
docker-compose build
```

### 2. Start Services
```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Initialize Database
```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

## 📁 File Structure

```
BudgetsSystem/
├── docker-compose.yml          # Development configuration
├── docker-compose.prod.yml     # Production configuration
├── Dockerfile                  # Main application image
├── .env                        # Environment variables (create from env.example)
├── env.example                 # Environment template
├── requirements.txt            # Python dependencies
├── nginx/                      # Nginx configuration
│   ├── nginx.conf
│   └── conf.d/
│       └── budgets.conf
├── docker/                     # Docker utilities
│   ├── entrypoint.sh
│   ├── healthcheck.sh
│   └── scripts/
│       ├── setup.sh
│       ├── backup.sh
│       └── restore.sh
├── ssl/                        # SSL certificates
│   ├── cert.pem
│   └── key.pem
├── logs/                       # Application logs
├── backups/                    # Database backups
└── DOCKER_SECURITY.md          # Security documentation
```

## 🔐 Security Configuration

### SSL Certificates
For production, replace self-signed certificates:

```bash
# Place your SSL certificates in ssl/ directory
ssl/
├── cert.pem    # Your SSL certificate
└── key.pem     # Your private key
```

### Environment Security
- **Never commit `.env` files**
- **Use strong passwords** (minimum 16 characters)
- **Rotate secrets regularly**
- **Enable HTTPS only** in production

## 📊 Monitoring and Logs

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f nginx
```

### Health Checks
```bash
# Check service status
docker-compose ps

# Check application health
curl https://localhost/health/
```

## 💾 Backup and Restore

### Automated Backup
```bash
# Run backup script
docker/scripts/backup.sh

# Schedule with cron (Linux/Mac)
0 2 * * * /path/to/docker/scripts/backup.sh
```

### Manual Backup
```bash
# Database backup
docker-compose exec db pg_dump -U budgets_user budgets_db > backup.sql

# Restore from backup
docker-compose exec -T db psql -U budgets_user budgets_db < backup.sql
```

## 🔄 Updates and Maintenance

### Update Application
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Update Dependencies
```bash
# Update requirements.txt
# Rebuild image
docker-compose build --no-cache
```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
netstat -ano | findstr :80
netstat -ano | findstr :443

# Kill the process
taskkill /PID <process_id> /F
```

#### Permission Denied
```bash
# Fix file permissions
icacls . /grant Everyone:F /T
```

#### Database Connection Failed
```bash
# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

#### SSL Certificate Issues
```bash
# Regenerate certificates
rm ssl/cert.pem ssl/key.pem
docker/scripts/setup.sh
```

### Reset Everything
```bash
# Stop all services
docker-compose down

# Remove all data (WARNING: This deletes all data!)
docker-compose down -v
docker system prune -a

# Start fresh
docker/scripts/setup.sh
```

## 📈 Performance Optimization

### Resource Limits
Edit `docker-compose.yml` to set resource limits:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Caching
- **Redis** is configured for session and cache storage
- **Static files** are served by Nginx with proper caching headers
- **Database queries** should use Django's ORM optimization

## 🌐 Production Deployment

### 1. Use Production Configuration
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Configure Domain
Update `.env`:
```bash
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### 3. SSL Certificates
Replace self-signed certificates with valid ones:
```bash
# Place your certificates
ssl/
├── cert.pem
└── key.pem
```

### 4. Monitoring
- Set up **Sentry** for error tracking
- Configure **log aggregation**
- Set up **health monitoring**

## 📞 Support

### Getting Help
1. Check the logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Check service status: `docker-compose ps`
4. Review security documentation: `DOCKER_SECURITY.md`

### Useful Commands
```bash
# View running containers
docker ps

# View all containers
docker ps -a

# View container logs
docker logs <container_name>

# Execute command in container
docker-compose exec web python manage.py shell

# View resource usage
docker stats
```

## ✅ Checklist

### Pre-deployment
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database passwords set
- [ ] Domain configured
- [ ] Backup strategy implemented

### Post-deployment
- [ ] Application accessible
- [ ] Admin panel working
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Logs being generated
- [ ] Health checks passing
- [ ] Backups working
- [ ] Monitoring configured

Remember: Always test in a development environment before deploying to production!
