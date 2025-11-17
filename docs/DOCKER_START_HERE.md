# 🎯 شروع از اینجا - راهنمای سریع Docker

## ⚡ شروع سریع (4 مرحله)

### مرحله 1: ایجاد فایل .env

```powershell
# در دایرکتوری اصلی پروژه
Copy-Item env.example .env

# ویرایش فایل .env و تنظیم:
# - SECRET_KEY
# - DB_PASSWORD
# - REDIS_PASSWORD
```

### مرحله 2: تولید Secrets ایمن (بر اساس توصیه Docker Secrets)

```powershell
# اجرای اسکریپت امنیتی جدید
cd docker-scripts
.\setup-secrets.ps1
cd ..
```

> این مرحله مطابق توصیه‌های [Docker Secrets](https://www.linkedin.com/posts/erfanramezani_docker-devops-secretsmanagement-activity-7391793147577761792-7gle) است و باعث می‌شود رمز دیتابیس، REDIS و SECRET_KEY داخل container بدون قرار گرفتن در فایل‌های متنی ساده مدیریت شوند.

### مرحله 3: اجرای اسکریپت راه‌اندازی

```powershell
# روش 1: استفاده از منوی تعاملی (پیشنهادی)
cd docker-scripts
.\docker-menu.ps1
# سپس گزینه 1 را انتخاب کنید

# روش 2: اجرای مستقیم اسکریپت
cd docker-scripts
.\docker-setup.ps1
```

### مرحله 4: بررسی وضعیت

```powershell
# بررسی کانتینرها
docker-compose ps

# بررسی دسترسی به وب‌سایت
# باز کردن مرورگر: http://localhost:8080
```

---

## 📋 اسکریپت‌های موجود

| اسکریپت             | توضیحات                               |
| ------------------- | ------------------------------------- |
| `docker-menu.ps1`   | منوی تعاملی اصلی (پیشنهادی برای شروع) |
| `docker-setup.ps1`  | راه‌اندازی اولیه پروژه                |
| `docker-deploy.ps1` | استقرار پروژه                         |
| `docker-manage.ps1` | مدیریت روزانه پروژه                   |
| `docker-update.ps1` | به‌روزرسانی پروژه                     |

---

## 🚀 دستور سریع

```powershell
# 1. ایجاد .env
Copy-Item env.example .env
# (سپس فایل .env را ویرایش کنید)

# 2. تولید secrets امن
cd docker-scripts
.\setup-secrets.ps1
cd ..

# 3. راه‌اندازی
cd docker-scripts
.\docker-menu.ps1
# گزینه 1 را انتخاب کنید

# 4. بررسی
docker-compose ps
```

---

## 📚 راهنماهای کامل

- **DOCKER_QUICK_START.md** - راهنمای سریع شروع
- **DOCKER_GUIDE.md** - راهنمای کامل Docker
- **DOCKER_REVIEW_REPORT.md** - گزارش مشکلات

---

## ⚠️ نکات مهم

1. **فایل .env**: حتماً قبل از راه‌اندازی ایجاد و تنظیم کنید
2. **اسکریپت Secrets**: با `setup-secrets.ps1` مقادیر حساس در Docker Secrets ذخیره می‌شوند
3. **رمزهای عبور**: از رمزهای عبور قوی استفاده کنید (هیچ رمزی در .env نگذارید)
4. **Docker Desktop**: مطمئن شوید Docker Desktop در حال اجرا است
5. **پورت‌ها**: پورت‌های 8080 و 8000 باید آزاد باشند

---

## 🆘 کمک

اگر مشکلی پیش آمد:

1. لاگ‌ها را بررسی کنید: `docker-compose logs`
2. به `DOCKER_QUICK_START.md` مراجعه کنید
3. بخش عیب‌یابی در `DOCKER_GUIDE.md` را مطالعه کنید

---

**🎉 آماده شروع هستید!**
