# راهنمای تست ایمن اضافه کردن Ollama

این راهنما توضیح می‌دهد چگونه اسکریپت اضافه کردن Ollama را **به صورت ایمن و تستی** اجرا کنید.

## 🧪 دو روش تست

### روش 1: تست نمایشی (بدون تغییر)
اسکریپت `TEST_ADD_OLLAMA.ps1` را اجرا کنید:

```powershell
.\TEST_ADD_OLLAMA.ps1
```

این اسکریپت:
- ✅ **هیچ فایلی را تغییر نمی‌دهد**
- ✅ فقط نشان می‌دهد چه تغییراتی اعمال می‌شد
- ✅ تنظیمات فعلی را نمایش می‌دهد
- ✅ پیش‌نمایش تغییرات را نشان می‌دهد

### روش 2: تست با Backup (توصیه می‌شود)
اسکریپت `TEST_ADD_OLLAMA_SAFE.ps1` را اجرا کنید:

```powershell
.\TEST_ADD_OLLAMA_SAFE.ps1
```

این اسکریپت:
- ✅ ابتدا **backup کامل** می‌گیرد
- ✅ سپس تغییرات را اعمال می‌کند
- ✅ بررسی می‌کند تنظیمات حفظ شده
- ✅ اگر مشکلی بود، **خودکار restore** می‌کند
- ✅ Backup را نگه می‌دارد برای restore دستی

## 📋 مراحل تست

### مرحله 1: تست نمایشی

```powershell
.\TEST_ADD_OLLAMA.ps1
```

خروجی نشان می‌دهد:
- تنظیمات فعلی چیست
- چه تغییراتی اعمال می‌شود
- تنظیمات قبلی حفظ می‌شود یا نه

### مرحله 2: تست واقعی با Backup

```powershell
.\TEST_ADD_OLLAMA_SAFE.ps1
```

این اسکریپت:
1. Backup می‌گیرد در `.backup_mcp_YYYYMMDD_HHMMSS/`
2. تغییرات را اعمال می‌کند
3. بررسی می‌کند تنظیمات حفظ شده
4. اگر مشکلی بود، restore می‌کند

## ✅ بررسی نتایج

پس از اجرای `TEST_ADD_OLLAMA_SAFE.ps1`:

### اگر موفق بود:
```
✅ تست موفق بود!
   ✅ Backup گرفته شد: .backup_mcp_20241220_143022
   ✅ تنظیمات قبلی حفظ شد
   ✅ ollama-local اضافه شد
```

### اگر ناموفق بود:
```
❌ تست ناموفق بود!
   🔄 در حال restore کردن backup...
   ✅ Backup restore شد
```

## 🔄 Restore دستی

اگر می‌خواهید دستی restore کنید:

```powershell
# پیدا کردن backup
Get-ChildItem -Directory -Filter ".backup_mcp_*"

# Restore
Copy-Item .backup_mcp_YYYYMMDD_HHMMSS/mcp.json .cursor/mcp.json -Force
Copy-Item .backup_mcp_YYYYMMDD_HHMMSS/settings.json .vscode/settings.json -Force
```

## 📊 چه بررسی می‌شود؟

اسکریپت تست این موارد را بررسی می‌کند:

1. ✅ JSON معتبر است
2. ✅ تمام properties قبلی حفظ شده
3. ✅ تمام MCP servers قبلی حفظ شده
4. ✅ ollama-local اضافه شده
5. ✅ ollama-local تنظیمات درست دارد

## 🎯 استفاده

### فقط نمایش (بدون تغییر):
```powershell
.\TEST_ADD_OLLAMA.ps1
```

### تست واقعی با backup:
```powershell
.\TEST_ADD_OLLAMA_SAFE.ps1
```

### اعمال تغییرات (اگر تست موفق بود):
```powershell
.\ADD_OLLAMA_TO_EXISTING.ps1
```

## ⚠️ نکات مهم

1. **همیشه ابتدا تست نمایشی را اجرا کنید**
2. **اگر مطمئن نیستید، از نسخه با backup استفاده کنید**
3. **Backup ها را نگه دارید تا مطمئن شوید همه چیز کار می‌کند**

## 🐛 رفع مشکل

### اگر JSON نامعتبر است:
```powershell
# بررسی
Get-Content .cursor/mcp.json | ConvertFrom-Json
Get-Content .vscode/settings.json | ConvertFrom-Json
```

### اگر restore نیاز است:
```powershell
# استفاده از backup که اسکریپت ایجاد کرده
.\TEST_ADD_OLLAMA_SAFE.ps1
# اگر ناموفق بود، خودکار restore می‌کند
```

---

**💡 توصیه:** همیشه ابتدا `TEST_ADD_OLLAMA.ps1` را اجرا کنید تا ببینید چه می‌شود!

