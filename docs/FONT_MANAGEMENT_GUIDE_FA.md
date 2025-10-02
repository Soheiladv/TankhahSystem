# راهنمای کامل مدیریت فونت‌ها

## 📋 فهرست مطالب

1. [مقدمه](#مقدمه)
2. [ویژگی‌های سیستم فونت](#ویژگیهای-سیستم-فونت)
3. [مراحل افزودن فونت جدید](#مراحل-افزودن-فونت-جدید)
4. [فرمت‌های پشتیبانی شده](#فرمتهای-پشتیبانی-شده)
5. [مدیریت فونت‌های موجود](#مدیریت-فونتهای-موجود)
6. [تنظیمات پیشرفته](#تنظیمات-پیشرفته)
7. [نکات مهم و بهترین روش‌ها](#نکات-مهم-و-بهترین-روشها)
8. [عیب‌یابی مشکلات رایج](#عیبیابی-مشکلات-رایج)
9. [API و توسعه](#api-و-توسعه)

---

## 🎯 مقدمه

سیستم مدیریت فونت‌ها یکی از ویژگی‌های پیشرفته سیستم بودجه‌بندی است که به مدیران سیستم امکان کنترل کامل بر روی ظاهر و خوانایی متن‌ها را می‌دهد.

### مزایای کلیدی:
- ✅ **یکپارچگی ظاهری** در تمام بخش‌های سیستم
- ✅ **پشتیبانی کامل از فارسی** و زبان‌های راست به چپ
- ✅ **بهبود تجربه کاربری** و خوانایی
- ✅ **مدیریت آسان** بدون نیاز به برنامه‌نویسی
- ✅ **پیش‌نمایش زنده** قبل از اعمال تغییرات

---

## 🚀 ویژگی‌های سیستم فونت

### 1. مدیریت فایل‌های فونت
- پشتیبانی از فرمت‌های TTF, WOFF, WOFF2, EOT, OTF
- آپلود فایل‌های تا 10 مگابایت
- اعتبارسنجی خودکار فایل‌ها
- ذخیره‌سازی ایمن در سرور

### 2. سیستم وزن فونت
| وزن | نام | کاربرد |
|-----|-----|--------|
| 100 | Thin | متن‌های بسیار سبک |
| 200 | Extra Light | متن‌های سبک |
| 300 | Light | متن‌های معمولی سبک |
| 400 | Regular | متن‌های عادی (پیش‌فرض) |
| 500 | Medium | تأکید متوسط |
| 600 | Semi Bold | عناوین فرعی |
| 700 | Bold | عناوین اصلی |
| 800 | Extra Bold | تأکید قوی |
| 900 | Black | حداکثر تأکید |

### 3. مدیریت فونت پیش‌فرض
- تنظیم یک فونت به عنوان پیش‌فرض سیستم
- اعمال خودکار در تمام صفحات
- امکان تغییر آسان فونت اصلی

---

## 📝 مراحل افزودن فونت جدید

### مرحله 1: ورود به بخش مدیریت
1. وارد پنل مدیریت شوید
2. از منوی کناری، روی **"تنظیمات سیستم"** کلیک کنید
3. تب **"فونت‌ها"** را انتخاب کنید
4. روی **"مدیریت فونت‌ها"** کلیک کنید

### مرحله 2: شروع فرآیند افزودن
1. در صفحه لیست فونت‌ها، روی **"افزودن فونت جدید"** کلیک کنید
2. فرم افزودن فونت باز می‌شود

### مرحله 3: تکمیل اطلاعات اصلی

#### اطلاعات ضروری:
```
نام فونت: وزیرمتن بولد
نام خانواده فونت: Vazirmatn
فرمت فونت: woff2
وزن فونت: 700 (Bold)
```

#### فایل فونت:
- فایل مورد نظر را از کامپیوتر انتخاب کنید
- مطمئن شوید فرمت انتخاب شده با فایل مطابقت دارد
- حجم فایل کمتر از 10 مگابایت باشد

### مرحله 4: تنظیمات اضافی

#### گزینه‌های قابل تنظیم:
- ☑️ **فعال**: فونت در سیستم قابل استفاده باشد
- ☑️ **فونت پیش‌فرض**: به عنوان فونت اصلی سیستم
- ☑️ **پشتیبانی RTL**: برای زبان‌های راست به چپ
- 📝 **توضیحات**: توضیح اختیاری درباره فونت

### مرحله 5: پیش‌نمایش و تأیید
1. روی **"نمایش پیش‌نمایش"** کلیک کنید
2. فونت با متن نمونه نمایش داده می‌شود
3. در صورت رضایت، روی **"ذخیره فونت"** کلیک کنید

---

## 📁 فرمت‌های پشتیبانی شده

### 1. TTF (TrueType Font)
```css
@font-face {
    font-family: 'FontName';
    src: url('font.ttf') format('truetype');
}
```
- **مزایا**: پشتیبانی گسترده، کیفیت بالا
- **معایب**: حجم بیشتر نسبت به WOFF
- **کاربرد**: فونت‌های دسکتاپ و وب

### 2. WOFF/WOFF2 (Web Open Font Format)
```css
@font-face {
    font-family: 'FontName';
    src: url('font.woff2') format('woff2'),
         url('font.woff') format('woff');
}
```
- **مزایا**: فشرده‌سازی بهتر، سرعت بارگذاری بالا
- **معایب**: پشتیبانی محدود در مرورگرهای قدیمی
- **کاربرد**: بهینه برای وب

### 3. EOT (Embedded OpenType)
```css
@font-face {
    font-family: 'FontName';
    src: url('font.eot');
}
```
- **مزایا**: پشتیبانی از Internet Explorer
- **معایب**: فقط در IE کار می‌کند
- **کاربرد**: سازگاری با مرورگرهای قدیمی

### 4. OTF (OpenType Font)
```css
@font-face {
    font-family: 'FontName';
    src: url('font.otf') format('opentype');
}
```
- **مزایا**: ویژگی‌های تایپوگرافی پیشرفته
- **معایب**: حجم بیشتر
- **کاربرد**: فونت‌های حرفه‌ای

---

## ⚙️ مدیریت فونت‌های موجود

### عملیات قابل انجام:

#### 1. ویرایش فونت
- تغییر نام نمایشی
- به‌روزرسانی توضیحات
- تغییر تنظیمات فعال/غیرفعال
- تغییر وضعیت پیش‌فرض

#### 2. فعال/غیرفعال کردن
```javascript
// کد نمونه برای تغییر وضعیت
fetch('/system-settings/fonts/1/toggle/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
})
```

#### 3. تنظیم به عنوان پیش‌فرض
- فقط یک فونت می‌تواند پیش‌فرض باشد
- فونت باید فعال باشد
- تغییر فوری در کل سیستم

#### 4. حذف فونت
⚠️ **هشدار**: حذف فونت غیرقابل بازگشت است
- فونت پیش‌فرض قابل حذف نیست
- فایل فونت از سرور حذف می‌شود
- تأیید کاربر الزامی است

---

## 🔧 تنظیمات پیشرفته

### 1. CSS سفارشی
فونت‌های سیستم به صورت خودکار در CSS زیر اعمال می‌شوند:

```css
body, 
.system-font,
.navbar,
.sidebar,
.card,
.btn,
.form-control,
.form-select,
.form-label,
.breadcrumb,
.alert,
.table,
.modal,
.dropdown-menu {
    font-family: 'FontName', 'Tahoma', 'Arial', sans-serif !important;
}
```

### 2. Template Tags
برای استفاده در template ها:

```django
{% load core_extras %}

<!-- دریافت فونت پیش‌فرض -->
{% get_default_font as default_font %}

<!-- دریافت تمام فونت‌های فعال -->
{% get_active_fonts as fonts %}

<!-- دریافت آمار فونت‌ها -->
{% get_font_stats as stats %}

<!-- شامل کردن CSS فونت‌ها -->
{% include_system_fonts %}
```

### 3. API دسترسی
```python
from core.models import FontSettings

# دریافت فونت پیش‌فرض
default_font = FontSettings.get_default_font()

# دریافت فونت‌های فعال
active_fonts = FontSettings.get_active_fonts()

# تولید CSS
css_code = font.get_css_font_face()
```

---

## 💡 نکات مهم و بهترین روش‌ها

### ✅ انجام دهید:

#### 1. تست قبل از آپلود
```bash
# بررسی فایل فونت در محیط محلی
fc-list | grep "FontName"
```

#### 2. نام‌گذاری صحیح
- نام‌های واضح و قابل فهم
- عدم استفاده از کاراکترهای خاص
- نام خانواده منحصر به فرد

#### 3. مدیریت حجم
- استفاده از فرمت WOFF2 برای کاهش حجم
- حذف فونت‌های غیرضروری
- بهینه‌سازی فایل‌ها قبل از آپلود

#### 4. پشتیبان‌گیری
- ذخیره فایل‌های اصلی فونت
- یادداشت تنظیمات مهم
- تست در مرورگرهای مختلف

### ❌ انجام ندهید:

#### 1. مسائل حقوقی
- آپلود فونت‌های بدون مجوز
- نقض حقوق مالکیت معنوی
- استفاده تجاری غیرمجاز

#### 2. مسائل فنی
- آپلود فایل‌های خراب
- استفاده از نام‌های تکراری
- حذف فونت پیش‌فرض بدون جایگزین

#### 3. مسائل عملکردی
- نگه‌داری فونت‌های غیرفعال زیاد
- آپلود فونت‌های سنگین بدون ضرورت
- تغییر مکرر فونت پیش‌فرض

---

## 🛠️ عیب‌یابی مشکلات رایج

### مشکل 1: فونت نمایش داده نمی‌شود

#### علل احتمالی:
- فونت غیرفعال است
- مشکل در کش مرورگر
- خطا در فایل فونت
- مشکل در مسیر فایل

#### راه‌حل‌ها:
```javascript
// پاک کردن کش فونت‌ها
document.fonts.clear();

// بارگذاری مجدد فونت
const font = new FontFace('FontName', 'url(/path/to/font.woff2)');
font.load().then(() => {
    document.fonts.add(font);
});
```

### مشکل 2: خطا در آپلود فایل

#### بررسی‌های لازم:
```python
# بررسی حجم فایل
if file.size > 10 * 1024 * 1024:
    raise ValidationError("حجم فایل بیش از حد مجاز")

# بررسی فرمت
allowed_formats = ['.ttf', '.woff', '.woff2', '.eot', '.otf']
if not any(file.name.lower().endswith(fmt) for fmt in allowed_formats):
    raise ValidationError("فرمت فایل پشتیبانی نمی‌شود")
```

### مشکل 3: فونت فارسی نامناسب

#### تنظیمات CSS:
```css
/* تنظیمات مخصوص فارسی */
.persian-text {
    font-family: 'PersianFont', 'Tahoma', sans-serif;
    direction: rtl;
    text-align: right;
    unicode-bidi: embed;
}
```

### مشکل 4: کندی بارگذاری

#### بهینه‌سازی:
```css
/* استفاده از font-display */
@font-face {
    font-family: 'FontName';
    src: url('font.woff2') format('woff2');
    font-display: swap; /* بهبود عملکرد */
}
```

---

## 🔌 API و توسعه

### 1. مدل FontSettings

```python
class FontSettings(models.Model):
    name = models.CharField(max_length=100)
    family_name = models.CharField(max_length=100)
    font_file = models.FileField(upload_to='fonts/')
    font_format = models.CharField(max_length=10, choices=FONT_FORMATS)
    font_weight = models.IntegerField(choices=FONT_WEIGHTS, default=400)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_rtl_support = models.BooleanField(default=True)
    
    @classmethod
    def get_default_font(cls):
        return cls.objects.filter(is_default=True, is_active=True).first()
    
    def get_css_font_face(self):
        # تولید CSS @font-face
        pass
```

### 2. ViewSet API

```python
from rest_framework import viewsets
from .models import FontSettings
from .serializers import FontSettingsSerializer

class FontSettingsViewSet(viewsets.ModelViewSet):
    queryset = FontSettings.objects.all()
    serializer_class = FontSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        font = self.get_object()
        FontSettings.objects.update(is_default=False)
        font.is_default = True
        font.save()
        return Response({'status': 'success'})
```

### 3. JavaScript API

```javascript
class FontManager {
    static async loadFont(fontFamily, fontUrl) {
        const font = new FontFace(fontFamily, `url(${fontUrl})`);
        await font.load();
        document.fonts.add(font);
        return font;
    }
    
    static async setDefaultFont(fontId) {
        const response = await fetch(`/api/fonts/${fontId}/set_default/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        return response.json();
    }
}
```

---

## 📊 آمار و گزارش‌گیری

### داشبورد فونت‌ها
- تعداد کل فونت‌ها
- فونت‌های فعال/غیرفعال
- حجم کل فایل‌های فونت
- آخرین فونت‌های اضافه شده

### گزارش استفاده
```sql
-- کوئری نمونه برای آمار
SELECT 
    COUNT(*) as total_fonts,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_fonts,
    SUM(file_size) as total_size
FROM core_fontsettings;
```

---

## 🔗 پیوندهای مفید

### مستندات مرتبط:
- [راهنمای تنظیمات سیستم](./SYSTEM_SETTINGS_GUIDE_FA.md)
- [راهنمای مدیریت کاربران](./USER_MANAGEMENT_GUIDE_FA.md)
- [راهنمای توسعه‌دهندگان](./DEVELOPER_GUIDE_FA.md)

### منابع خارجی:
- [Google Fonts](https://fonts.google.com/)
- [Font Squirrel](https://www.fontsquirrel.com/)
- [وب‌فونت](https://webfont.ir/)

---

## 📞 پشتیبانی

در صورت بروز مشکل یا نیاز به راهنمایی بیشتر:

- 📧 **ایمیل پشتیبانی**: support@budgetsystem.ir
- 📱 **تلفن**: 021-12345678
- 💬 **چت آنلاین**: از طریق پنل مدیریت
- 📖 **مستندات کامل**: [docs.budgetsystem.ir](https://docs.budgetsystem.ir)

---

**نسخه مستند**: 1.0.0  
**تاریخ به‌روزرسانی**: 1403/07/11  
**نویسنده**: تیم توسعه سیستم بودجه‌بندی
