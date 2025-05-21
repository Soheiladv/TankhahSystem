# settings.py
import logging.config
import os
from pathlib import Path

# --- Start of your existing settings.py ---

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-*zron+$_y8zn14z7a7r(wgllx%8n0vii^(6uar=_r)94(v!khc'
DEBUG = True  # در محیط توسعه، DEBUG = True باشد
ALLOWED_HOSTS = ['*']  # برای لوکال هاست، '127.0.0.1', 'localhost' یا '*'

INSTALLED_APPS = [
    'django.contrib.humanize',
    'rest_framework',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'notifications',
    'core.apps.CoreConfig',
    'reports.apps.ReportsConfig',
    'django_jalali',
    'jalali_date',
    'version_tracker.apps.VersionTrackerConfig',
    'tankhah.apps.TankhahConfig',
    'accounts.apps.AccountsConfig',
    'core.templatetags.file_tags',
    'budgets.apps.BudgetsConfig',
    'formtools',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.AuditLogMiddleware',
    'accounts.middleware.ActiveUserMiddleware',
    'accounts.middleware.RequestMiddleware',
]

ROOT_URLCONF = 'Tanbakhsystem.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.version_info',
                'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'Tanbakhsystem.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tankhasystem',
        'USER': 'root',
        'PASSWORD': 'S@123456@1234',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'use_unicode': True,
            'charset': 'utf8mb4',
        },
        'TEST': {
            'NAME': 'test_tankhasystem',
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        }
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGES = (('fa', 'فارسی'), ('en', 'English'))
LOCALE_PATHS = [BASE_DIR / 'locale']
LANGUAGE_CODE = 'fa'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
SESSION_COOKIE_AGE = 1500
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': 'unique-snowflake',
    }
}

JALALI_SETTINGS = {
    "ADMIN_JS_STATIC_FILES": [
        "admin/jquery.ui.datepicker.jalali/scripts/jquery-1.10.2.min.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.core.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc.js",
        "admin/jquery.ui.datepicker.jalali/scripts/calendar.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc-fa.js",
        "admin/main.js",
    ],
    "ADMIN_CSS_STATIC_FILES": {
        "all": [
            "admin/jquery.ui.datepicker.jalali/themes/base/jquery-ui.min.css",
            "admin/css/main.css",
        ]
    },
}

TIME_LOCK_FILE = os.path.join(BASE_DIR, "core/RCMS_Lock/timelock.dat")
RCMS_SECRET_KEY = '8nrJNs-teqRyAlyAVIknDQwZCBeN-j-W2EKF7cKGW9A='
FERNET_KEY = os.getenv("FERNET_KEY", "ATLZREELWdggY12feExDxVYyM8ANnQrWjjDKza3iB1g=")

if len(RCMS_SECRET_KEY) != 44:
    raise ValueError("🔴 RCMS_SECRET_KEY is invalid! Please provide a valid value.")

MAX_ACTIVE_USERS = 5

DJANGO_NOTIFICATIONS_CONFIG = {
    'USE_JSONFIELD': True,
    'SOFT_DELETE': True,
}
NOTIFICATIONS_USE_JSONFIELD = True
NOTIFICATIONS_SOFT_DELETE = True

# --- End of your existing settings.py ---


# --- Logging Configuration (Optimized for Development) ---

# ایجاد پوشه logs اگر وجود ندارد
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)  # مطمئن می‌شویم که پوشه لاگ حتماً وجود دارد

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # لاگرهای موجود را غیرفعال نکن

    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {funcName} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'app_debug': {  # فرمت دقیق‌تر برای دیباگ اپلیکیشن‌های خاص
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {funcName} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    'handlers': {
        'console': {  # هندلر برای خروجی کنسول (ترمینال)
            'level': 'DEBUG',  # در محیط توسعه، همه پیام‌های دیباگ را در کنسول نمایش بده
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_errors': {  # هندلر برای خطاهای کلی برنامه
            'level': 'ERROR',  # فقط پیام‌های خطا و بحرانی را در این فایل ذخیره کن
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'application_errors.log'),
            'maxBytes': 1024 * 1024 * 10,  # حداکثر حجم فایل 10 مگابایت
            'backupCount': 5,  # 5 فایل پشتیبان نگه دار (در مجموع 6 فایل)
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_budgets_debug': {  # هندلر اختصاصی برای دیباگ اپ 'budgets'
            'level': 'DEBUG',  # همه پیام‌های دیباگ 'budgets' را در این فایل ذخیره کن
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'budgets_debug.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 مگابایت
            'backupCount': 3,
            'formatter': 'app_debug',
            'encoding': 'utf-8',
        },
        'file_django_errors': {  # هندلر برای خطاهای داخلی جنگو (سیستم)
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_all_info': {  # هندلر برای ثبت تمام لاگ‌های INFO و بالاتر در یک فایل کلی
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'all_info.log'),
            'maxBytes': 1024 * 1024 * 20,  # 20 مگابایت
            'backupCount': 2,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        '': {
            # Root logger: لاگر ریشه، هر لاگی که توسط لاگرهای دیگر مدیریت نشود، به اینجا می‌رسد (اگر propagate = True باشد)
            'handlers': ['console', 'file_errors', 'file_all_info'],
            'level': 'DEBUG',  # در محیط توسعه، روت را روی DEBUG بگذارید تا چیزی از دست نرود
            'propagate': False,  # بسیار مهم: از تکرار لاگ‌ها در لاگر پیش‌فرض پایتون جلوگیری می‌کند
        },
        'django': {  # لاگر مربوط به پیام‌های داخلی جنگو
            'handlers': ['file_django_errors', 'console'],  # خطاهای جنگو را در کنسول هم نشان بده
            'level': 'INFO',  # سطح اطلاعاتی جنگو
            'propagate': False,
        },
        # 'django.db.backends': { # لاگر مربوط به کوئری‌های دیتابیس
        #     'handlers': ['console'], # فقط در کنسول نشان داده شود تا فایل‌ها پر نشوند
        #     'level': 'DEBUG', # سطح دیباگ برای دیدن جزئیات کوئری‌ها
        #     'propagate': False, # از انتشار این لاگ‌های پرحجم به سایر هندلرها جلوگیری می‌کند
        # },
        'django.db.backends': {  # این قسمت رو ویرایش کنید
            'handlers': [],  # خالی کردن لیست هندلرها
            'level': 'DEBUG',  # سطحش رو DEBUG نگه می‌داریم برای زمانی که نیاز به دیباگ داریم
            'propagate': False,  # همچنان propagate رو False نگه می‌داریم تا به روت لاگر نرن
        },
        'budgets': {  # لاگر مخصوص اپ 'budgets' شما
            'handlers': ['console', 'file_budgets_debug', 'file_errors'],
            # هم در کنسول، هم در فایل دیباگ خودش، هم خطاهایش در فایل خطاهای کلی
            'level': 'DEBUG',  # همه پیام‌های دیباگ را برای اپ 'budgets' ثبت کن
            'propagate': False,
        },
        # اگر اپلیکیشن‌های دیگری دارید که می‌خواهید لاگ‌هایشان را جداگانه مدیریت کنید، اینجا اضافه کنید:
        # 'accounts': {
        #     'handlers': ['console', 'file_all_info'],
        #     'level': 'INFO',
        #     'propagate': False,
        # },
    },
}

# --- End of Logging Configuration ---
