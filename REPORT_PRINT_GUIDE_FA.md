## راهنمای سریع چاپ گزارش در Django (ReportLab)

این پروژه دو API برای چاپ گزارش دارد:

- GET: `/budgets/api/reportlab/` (خروجی از مدل‌های Django)
- POST: `/budgets/api/reportlab/custom/` (خروجی از داده سفارشی JSON)

تنظیمات پیش‌فرض کاغذ و حاشیه‌ها در `config/report_settings.json` ذخیره شده و قابل تغییر است. پارامترهای URL نسبت به تنظیمات فایل اولویت دارند.

### 1) چاپ مستقیم از مدل

آدرس پایه:
```
/budgets/api/reportlab/?app=<app>&model=<Model>
```

پارامترهای مهم:
- `app`: نام اپ، مثال: `tankhah`
- `model`: نام مدل، مثال: `Tankhah`
- `fields`: لیست ستون‌ها با کاما (اختیاری؛ پیش‌فرض همه فیلدها)
- `filters`: فیلتر به صورت JSON URL-encoded (اختیاری)
- `order_by`: مرتب‌سازی (اختیاری)
- `title`: عنوان گزارش (اختیاری)
- `landscape`: `true|false` (اختیاری)
- `page_size`: `A4` یا اندازه سفارشی مثل `20x28` (سانتی‌متر) (اختیاری)
- `preset`: نام preset از `config/report_settings.json` (اختیاری)
- `font_path`: مسیر فایل فونت TTF سفارشی (اختیاری)

نمونه‌ها:
```
/budgets/api/reportlab/?app=tankhah&model=Tankhah&fields=number,date,amount,description&order_by=-date&landscape=true&page_size=20x28&title=%D9%84%DB%8C%D8%B3%D8%AA%20%D8%AA%D9%86%D8%AE%D9%88%D8%A7%D9%87

/budgets/api/reportlab/?app=tankhah&model=Tankhah&fields=number,date,amount&filters=%7B%22id%22%3A123%7D&preset=custom_20x28
```

نکته: مقدار `filters` باید JSON معتبر و URL-encode شده باشد. مثال ساده برای فیلتر یک رکورد: `{ "id": 123 }` → `%7B%22id%22%3A123%7D`

### 2) چاپ از داده سفارشی (JSON)

آدرس:
```
POST /budgets/api/reportlab/custom/
Content-Type: application/json
```

بدنه نمونه:
```json
{
  "title": "گزارش سفارشی",
  "fields": ["شماره", "تاریخ", "مبلغ"],
  "rows": [
    {"شماره": "HSarein-IPTV_Sarein-001", "تاریخ": "2025-09-22 20:30:00", "مبلغ": "75000000"}
  ],
  "landscape": true,
  "page_size": "20x28",
  "footer": "تاریخ تهیه: 2025-09-24 21:10"
}
```

### 3) تنظیمات کاغذ و حاشیه‌ها

فایل: `config/report_settings.json`

ساختار نمونه:
```json
{
  "default": {
    "page_size": "20x28",
    "landscape": true,
    "margins": { "top_cm": 1.5, "right_cm": 1.5, "bottom_cm": 1.5, "left_cm": 1.5 }
  },
  "presets": {
    "a4_landscape_wide": {
      "page_size": "A4",
      "landscape": true,
      "margins": { "top_cm": 1.0, "right_cm": 1.0, "bottom_cm": 1.0, "left_cm": 1.0 }
    },
    "custom_20x28": {
      "page_size": "20x28",
      "landscape": true,
      "margins": { "top_cm": 1.5, "right_cm": 1.5, "bottom_cm": 1.5, "left_cm": 1.5 }
    }
  }
}
```

می‌توانید preset جدید اضافه کنید و در URL از `preset=<name>` استفاده کنید.

### 4) بهینه‌سازی برای جا شدن در عرض کاغذ

- ستون‌ها را در `fields` به موارد ضروری محدود کنید.
- از `preset` با حاشیه کمتر (مثلاً 1.0cm) استفاده کنید.
- `landscape=true` و `page_size=20x28` را امتحان کنید.
- در کد، فونت جدول کوچک و wrap فعال شده است؛ متن‌های طولانی در چند خط می‌شکنند.

### 5) نمونه لینک چاپ برای لیست تنخواه

در تمپلیت (نمونه کلی):
```
{% url 'reportlab_pdf_api' %}?app=tankhah&model=Tankhah&fields=number,date,amount,description&order_by=-date&preset=custom_20x28
```

چاپ یک ردیف مشخص:
```
{% url 'reportlab_pdf_api' %}?app=tankhah&model=Tankhah&fields=number,date,amount,description&filters=%7B%22id%22%3A{{ tankhah.id }}%7D&preset=custom_20x28
```

### 6) فونت فارسی

اگر فونت فارسی سیستم پیدا نشد، می‌توانید مسیر فونت TTF را در URL بدهید:
```
&font_path=/absolute/path/to/Vazirmatn-Regular.ttf
```

### 7) خطاهای متداول

- عرض محتوا زیاد است → ستون‌ها را کمتر کنید، preset با حاشیه کمتر انتخاب کنید، از landscape استفاده کنید.
- فیلتر اعمال نمی‌شود → مطمئن شوید کلیدهای `filters` با نام فیلدهای مدل دقیقاً یکسان باشند و JSON را URL-encode کرده‌اید.
- فونت فارسی به‌هم‌ریخته → مسیر فونت معتبر بدهید یا فونت را در `static/fonts` قرار دهید.

---
در صورت نیاز، می‌توانیم preset اختصاصی شما را اضافه کنیم یا لینک‌های چاپ در `templates/tankhah/tankhah_list.html` را به‌صورت پیش‌فرض به preset دلخواه متصل کنیم.


