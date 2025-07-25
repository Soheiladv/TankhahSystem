# سامانه یکپارچه بودجه و تنخواه "سامان"

**نسخه: 3.0.0.25**

سامانه "سامان" یک سیستم جامع و هوشمند برای مدیریت فرآیندهای بودجه‌ریزی، تخصیص بودجه، تنخواه‌گردانی، و کنترل هزینه‌ها در سازمان‌ها است. این سامانه با هدف افزایش شفافیت مالی، بهینه‌سازی فرآیندهای مالی، کاهش خطاهای انسانی، و ارائه گزارش‌های دقیق و کاربردی برای مدیران طراحی شده است.

## 🌟 قابلیت‌های کلیدی

### مدیریت جامع بودجه
- **تعریف دوره‌های بودجه‌ای** (سالانه، شش‌ماهه، سه‌ماهه و غیره)
- **سرفصل‌های بودجه‌ای** با ساختار سلسله‌مراتبی
- **تخصیص بودجه** به سازمان‌ها، واحدها، پروژه‌ها، مراکز هزینه
- **مدیریت پروژه‌ها و زیرپروژه‌ها**
- **بازگشت بودجه** با ثبت دلایل و توضیحات خودکار

### سیستم تنخواه‌گردانی یکپارچه
- **درخواست تنخواه** توسط کاربران
- **مدیریت هزینه‌ها** با ثبت فاکتورها و ردیف‌های هزینه
- **محاسبات لحظه‌ای مانده تنخواه**
- **تسویه تنخواه** با بررسی فاکتورها

### گردش‌کار پویا و قدرتمند
- **تعریف مراحل سفارشی گردش‌کار**
- **مدیریت تأییدات بر اساس نقش‌ها**
- **اقدامات پس‌ازتأیید** (مانند ارسال اعلان)
- **تاریخچه کامل در ApprovalLog**

### دستور پرداخت مکانیزه
- **تولید خودکار دستور پرداخت**
- **گردش‌کار الکترونیکی امضا و تأیید**
- **اتصال به سوابق مالی**
- **پیگیری وضعیت پرداخت‌ها**

### ساختار سازمانی انعطاف‌پذیر
- **سلسله‌مراتب سازمانی و واحدها**
- **پست‌های سازمانی و انتساب کاربران**
- **سیستم کنترل دسترسی RBAC**
- **مدیریت کاربران با نقش‌های متنوع**

### داشبوردها و گزارش‌های مدیریتی
- **داشبورد تعاملی KPI**
- **گزارش‌های سلسله‌مراتبی Drill-Down**
- **خروجی PDF و Excel**
- **فیلترهای پیشرفته گزارش‌ها**
- **نمودارهای تحلیلی**

### امنیت و پایداری
- **استفاده از قابلیت‌های امنیتی Django**
- **ثبت لاگ کامل اقدامات کاربران**
- **مدیریت خطاها و پیام‌های کاربرپسند**
- **پشتیبان‌گیری از دیتابیس**
- **بهینه‌سازی کوئری‌ها و استفاده از Redis**

### قابلیت‌های چندزبانه و محلی‌سازی
- **رابط کاملاً فارسی و تاریخ جلالی**
- **پشتیبانی از چند زبان**
- **نمایش اعداد به‌صورت فارسی و حروفی**

## 🛠️ تکنولوژی‌های مورد استفاده

### Backend
- **زبان:** Python 3.11+
- **فریم‌ورک:** Django 5.x
- **ORM:** Django ORM
- **API:** Django REST Framework
- **Celery + Redis** برای پردازش پس‌زمینه
- **امنیت:** Django Auth, Permissions, cors-headers
- **PDF:** WeasyPrint
- **Excel:** openpyxl
- **تاریخ:** jdatetime, jalali_tags

### Database
- **اصلی:** MySQL 8.x (یا PostgreSQL)
- **ویژگی‌ها:** Index, select_related, prefetch_related

### Frontend
- **زبان‌ها:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5
- **کتابخانه‌ها:** jQuery, Chart.js
- **RTL و فونت فارسی:** IRANSans

### ابزارهای دیگر
- **static files:** collectstatic, CDN
- **WebSocket:** Django Channels
- **اطلاع‌رسانی:** ایمیل و پیامک با API ایرانی
- **نسخه‌بندی:** Git + GitHub
- **محیط توسعه:** Docker (اختیاری)

## 🚀 راهنمای نصب و راه‌اندازی

### پیش‌نیازها
- Python 3.11+
- MySQL 8.x
- Git
- Node.js (اختیاری)

### مراحل نصب

```bash
git clone https://github.com/your-repo/saman.git
cd saman
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

### فایل .env نمونه:
```env
SECRET_KEY='your-secure-secret-key'
DEBUG=True
DB_ENGINE=django.db.backends.mysql
DB_NAME=saman_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3306
EMAIL_HOST=smtp.your-email-provider.com
EMAIL_PORT=587
EMAIL_USER=your-email
EMAIL_PASSWORD=your-email-password
REDIS_URL=redis://localhost:6379/0
```

### دستورات اجرایی:
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
python manage.py runserver
```

### اجرای Celery:
```bash
celery -A saman worker --loglevel=info
celery -A saman beat --loglevel=info
```

## 🗺️ نقشه راه آینده
- استفاده از cache و subquery برای سرعت
- یکپارچه‌سازی با سیستم‌های حسابداری
- نوتیفیکیشن پیشرفته با پیامک و ایمیل
- بودجه‌ریزی غلطان و تحلیل سناریو
- ماژول دارایی‌های ثابت
- تست خودکار با پوشش ۸۰٪
- مستندات API با Swagger/Redoc
- پشتیبانی چندشعبه و اپ موبایل (Flutter/React Native)

## 🤝 مشارکت
- فایل `CONTRIBUTING.md` را بخوانید.
- از Git Flow استفاده کنید.
- Issues را ثبت و Pull Request ارسال کنید.

## 📄 لایسنس
MIT License. جزئیات در فایل LICENSE موجود است.

## 📚 مستندات و پشتیبانی
- [Django Docs](https://docs.djangoproject.com)
- [MySQL Docs](https://dev.mysql.com/doc/)
- [WeasyPrint Docs](https://weasyprint.readthedocs.io)
- ایمیل: support@your-domain.com
- شبکه اجتماعی: [your-community-link]

---

ساخته شده با ❤️ و Django توسط [T,arjmand]
