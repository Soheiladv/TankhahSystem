# تنظیمات پویای گردش کار

## 📋 توضیحات

این سیستم به شما امکان می‌دهد تا بدون تغییر کد، تنظیمات رنگ‌بندی و آیکون‌های گردش کار را تغییر دهید.

## 🔧 نحوه استفاده

### 1. تغییر تنظیمات از طریق فایل JSON

فایل `workflow-config.json` را ویرایش کنید:

```json
{
  "actions": {
    "SUBMIT": {
      "rowClass": "table-primary",
      "icon": "fas fa-paper-plane",
      "color": "text-primary",
      "label": "ارسال"
    }
  }
}
```

### 2. تغییر تنظیمات از طریق JavaScript

```javascript
// اضافه کردن اقدام جدید
addActionConfig('NEW_ACTION', {
    rowClass: 'table-info',
    icon: 'fas fa-star',
    color: 'text-info',
    label: 'اقدام جدید'
});

// اضافه کردن نوع موجودیت جدید
addEntityConfig('NEW_ENTITY', {
    badge: 'bg-purple',
    icon: 'fas fa-diamond',
    label: 'موجودیت جدید'
});

// به‌روزرسانی تنظیمات
updateConfig();
```

### 3. دریافت تنظیمات

```javascript
// دریافت تنظیمات یک اقدام
const submitConfig = getActionConfig('SUBMIT');

// دریافت تنظیمات یک نوع موجودیت
const factorConfig = getEntityConfig('FACTOR');
```

## 🎨 کلاس‌های Bootstrap موجود

### رنگ‌های ردیف:
- `table-primary` - آبی
- `table-success` - سبز
- `table-danger` - قرمز
- `table-warning` - زرد
- `table-info` - آبی روشن
- `table-secondary` - خاکستری
- `table-light` - سفید
- `table-dark` - تیره

### رنگ‌های متن:
- `text-primary` - آبی
- `text-success` - سبز
- `text-danger` - قرمز
- `text-warning` - زرد
- `text-info` - آبی روشن
- `text-secondary` - خاکستری
- `text-muted` - کم‌رنگ

### رنگ‌های Badge:
- `bg-primary` - آبی
- `bg-success` - سبز
- `bg-danger` - قرمز
- `bg-warning` - زرد
- `bg-info` - آبی روشن
- `bg-secondary` - خاکستری
- `bg-light` - سفید
- `bg-dark` - تیره

## 🔄 به‌روزرسانی خودکار

پس از تغییر فایل JSON، صفحه را رفرش کنید تا تغییرات اعمال شوند.

## ⚠️ نکات مهم

1. **نام‌گذاری**: کدهای اقدام و نوع موجودیت باید دقیقاً مطابق با داده‌های دیتابیس باشند
2. **آیکون‌ها**: از Font Awesome استفاده کنید (مثال: `fas fa-check`)
3. **کلاس‌ها**: از کلاس‌های Bootstrap استفاده کنید
4. **پشتیبان‌گیری**: قبل از تغییرات، از فایل JSON پشتیبان تهیه کنید

## 🚀 مثال کامل

```json
{
  "actions": {
    "CUSTOM_ACTION": {
      "rowClass": "table-info",
      "icon": "fas fa-magic",
      "color": "text-info",
      "label": "اقدام سفارشی"
    }
  },
  "entities": {
    "CUSTOM_ENTITY": {
      "badge": "bg-gradient",
      "icon": "fas fa-rocket",
      "label": "موجودیت سفارشی"
    }
  }
}
```
