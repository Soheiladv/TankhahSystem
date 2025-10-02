### راهنمای استفاده از تاریخ جلالی (Jalali Date) در پروژه

- **هدف**
  - ورود تاریخ به‌صورت جلالی (مثال: 1404/01/17) و تبدیل به میلادی در سمت سرور.
  - بدون نیاز به اسکریپت اختصاصی در هر صفحه؛ همه چیز از `base.html` مقداردهی می‌شود.

### افزودن ورودی تاریخ جلالی

- روش 1: استفاده مستقیم از data-jdp
```html
<input type="text" name="date" class="form-control" placeholder="1404/01/17" data-jdp autocomplete="off">
```

- روش 2: افزودن کلاس jalali-datepicker
```html
<input type="text" name="date" class="form-control jalali-datepicker" placeholder="1404/01/17" autocomplete="off">
```
- نکته: در `templates/base.html` به‌صورت خودکار روی `.jalali-datepicker` ویژگی `data-jdp` ست شده و Persian Datepicker با فرمت `YYYY/MM/DD` فعال می‌شود.

### تبدیل تاریخ جلالی به میلادی در فرم جنگو

- نمونه فرم
```python
from django import forms
from core.forms import parse_jalali_date  # تبدیل جلالی → میلادی (date)

class ReportFilterForm(forms.Form):
    start_date = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control jalali-datepicker', 'placeholder': '1404/01/01', 'autocomplete': 'off'})
    )
    end_date = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control jalali-datepicker', 'placeholder': '1404/12/29', 'autocomplete': 'off'})
    )

    def clean_start_date(self):
        return parse_jalali_date(self.cleaned_data['start_date'])

    def clean_end_date(self):
        return parse_jalali_date(self.cleaned_data['end_date'])
```

### نمایش تاریخ جلالی در قالب‌ها

- استفاده از فیلتر `to_jalali`
```django
{% load jalali_filters %}
{{ obj.date|to_jalali:'%Y/%m/%d' }}
```

### فیلتر بازه تاریخ (GET)

- فرم/قالب
```html
<input type="text" name="date_from" class="form-control jalali-datepicker" placeholder="1404/01/01" value="{{ request.GET.date_from }}" autocomplete="off">
<input type="text" name="date_to"   class="form-control jalali-datepicker" placeholder="1404/12/29" value="{{ request.GET.date_to }}" autocomplete="off">
```

- ویو (تبدیل و فیلتر)
```python
import jdatetime
qs = AuditLog.objects.all()
date_from = request.GET.get('date_from')
date_to = request.GET.get('date_to')

if date_from:
    g_from = jdatetime.date.fromisoformat(date_from).togregorian()
    qs = qs.filter(timestamp__date__gte=g_from)
if date_to:
    g_to = jdatetime.date.fromisoformat(date_to).togregorian()
    qs = qs.filter(timestamp__date__lte=g_to)
```

### بهترین‌عمل‌ها

- همیشه `autocomplete="off"` روی ورودی تاریخ قرار دهید.
- `placeholder` را با نمونه جلالی مثل `1404/01/17` تنظیم کنید.
- فیلدهای مدل را میلادی نگه دارید؛ تبدیل در فرم/ویو انجام شود.

### عیب‌یابی سریع

- دیتاپیکر فعال نشد؟
  - صفحه باید از `base.html` ارث‌بری کند.
  - روی input یکی از این‌ها باشد: `data-jdp` یا `class="jalali-datepicker"`.
  - فایل‌های استاتیک `jalalidatepicker.min.js` و اسکریپت‌های init سراسری لود شده باشند.
- خطا در تبدیل تاریخ؟
  - فرمت ورودی باید `YYYY/MM/DD` باشد.
  - از `parse_jalali_date` استفاده کنید تا اعداد فارسی نیز پشتیبانی شود.

### رفرنس‌های داخل پروژه

- سراسری‌سازی دیتاپیکر: `templates/base.html` (راه‌اندازی `[data-jdp]` و افزودن خودکار به `.jalali-datepicker`)
- فرم نمونه: `tankhah/Factor/NF/form_Nfactor.py`
- تبدیل تاریخ جلالی: `core/forms.py` تابع `parse_jalali_date`
- فیلتر نمایش جلالی: `accounts/templatetags/jalali_filters.py`


