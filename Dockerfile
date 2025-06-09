# از یک ایمیج پایه پایتون رسمی استفاده می‌کنیم.
# نسخه slim-buster سبک‌تر هست و بر پایه دبیان ساخته شده.
FROM python:3.10-slim-buster

# متغیرهای محیطی برای جنگو (اختیاری اما توصیه میشه)
# میتونید اینها رو بعدا موقع اجرای docker run از طریق متغیرهای محیطی بدید
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE Tanbakhsystem.settings # مطمئن بشید که به فایل settings اصلی شما اشاره میکنه

# مسیر کاری رو داخل کانتینر تنظیم می‌کنیم.
# همه دستورات بعدی از این مسیر اجرا میشن.
WORKDIR /app

# فایل requirements.txt رو اول کپی می‌کنیم. این به داکر اجازه میده تا
# لایه نصب pip رو کش (cache) کنه. پس اگر requirements.txt تغییر نکنه،
# این مرحله در ساخت‌های بعدی نادیده گرفته میشه و سریعتر اجرا میشه.
COPY requirements.txt /app/

# وابستگی‌های پایتون رو نصب می‌کنیم.
# --no-cache-dir حجم Image رو کاهش میده.
RUN pip install --no-cache-dir -r requirements.txt

# بقیه کدهای پروژه جنگو رو داخل کانتینر کپی می‌کنیم.
# این شامل همه فایل‌های پایتون، تمپلیت‌ها، فایل‌های استاتیک هست (قبل از collectstatic).
COPY . /app/

# دستور collectstatic جنگو رو برای جمع‌آوری همه فایل‌های استاتیک در STATIC_ROOT اجرا می‌کنیم.
# --noinput برای جلوگیری از سوال پرسیدن‌های تعاملی هست.
# مطمئن بشید که STATIC_ROOT در settings.py شما تنظیم شده باشه (مثلاً: STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected'))
RUN python manage.py collectstatic --noinput
#RUN pip install -r requirements.txt:
# این دستور تمام کتابخانه‌های پایتون که در requirements.txt لیست کردید (مثل جنگو، Gunicorn، Pillow و...) رو دانلود و نصب می‌کنه. این کتابخانه‌ها هم داخل Image قرار می‌گیرند.
RUN pip install -r requirements.txt
# پورتی که اپلیکیشن جنگو روی اون اجرا میشه رو مشخص می‌کنیم.
# این فقط یک اعلام هست که کانتینر روی این پورت گوش میده.
EXPOSE 8000

# دستوری که موقع شروع کانتینر، اپلیکیشن جنگو رو با Gunicorn اجرا می‌کنه.
# Gunicorn یک سرور WSGI محبوب برای محیط Production هست.
# 'Tanbakhsystem' رو با نام واقعی پوشه پروژه جنگوتون جایگزین کنید
# (پوشه‌ای که فایل‌های settings.py و wsgi.py در اون قرار دارن).
# مثلاً اگر پوشه پروژه شما 'mywebsite' هست، باید باشه 'mywebsite.wsgi:application'
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "Tanbakhsystem.wsgi:application"]