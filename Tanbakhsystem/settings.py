import locale
import logging
import logging.config
import os
# Warnings
import warnings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

SECRET_KEY = 'django-insecure-*zron+$_y8zn14z7a7r(wgllx%8n0vii^(6uar=_r)94(v!khc'
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
# ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'admin_interface',
    'django.contrib.humanize',
    "colorfield",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'reports',
    'django_jalali',
    'jalali_date',
    'version_tracker',

    'accounts',
    'tanbakh',
    'Tanbakhsystem',
    'notifications',
]
# APPEND_SLASH = True
# #حد بازگشیتی تست
# import sys
# sys.setrecursionlimit(2000)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # برای مدیریت زبان‌ها
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'Tanbakhsystem.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
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
            'charset': 'utf8mb4',  # Unicode support
        },
        'TEST': {
            'NAME': 'testtankhasystem',
            'CHARSET': 'utf8mb4',
            'COLLATION': 'utf8mb4_unicode_ci',
        }
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'tanbakh_db',
#         'USER': 'root',
#         'PASSWORD': 'Tankh@h',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators


# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Locale Configuration

LANGUAGES = (
    ('fa', 'فارسی'),
    ('en', 'English'),
)
LOCALE_PATHS = [BASE_DIR / 'locale']  # پوشه‌ای برای فایل‌های ترجمه
try:
    locale.setlocale(locale.LC_ALL, "fa_IR.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, "fa_IR")
    except locale.Error:
        pass
# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/
LANGUAGE_CODE = 'fa'  # زبان پیش‌فرض
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True  # فعال کردن بین‌المللی‌سازی
USE_L10N = True  # فعال کردن محلی‌سازی
USE_TZ = True

NUMBER_SEPARATOR = '-'  # می‌تونید به '/' یا '_' یا هر چیز دیگه تغییر بدید

USE_THOUSAND_SEPARATOR = True
#

SECRET_KEY = 'django-insecure-k=jhx8cj8&0z!!#8o291(=dc%$#g)rhr+63#!0-d0op8m&wrnr'

# CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'
# CSRF_TRUSTED_ORIGINS = [
#     'http://127.0.0.1:8000',
#     'http://127.0.0.1',  # بدون پورت
#     'http://localhost:8000',
#     'http://localhost',  # بدون پورت
# ]

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer",
#     },
# }

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

JALALI_SETTINGS = {
    # JavaScript static files for the admin Jalali date widget
    "ADMIN_JS_STATIC_FILES": [
        "admin/jquery.ui.datepicker.jalali/scripts/jquery-1.10.2.min.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.core.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc.js",
        "admin/jquery.ui.datepicker.jalali/scripts/calendar.js",
        "admin/jquery.ui.datepicker.jalali/scripts/jquery.ui.datepicker-cc-fa.js",
        "admin/main.js",
    ],
    # CSS static files for the admin Jalali date widget
    "ADMIN_CSS_STATIC_FILES": {
        "all": [
            "admin/jquery.ui.datepicker.jalali/themes/base/jquery-ui.min.css",
            "admin/css/main.css",
        ]
    },
}

# Static and Media Files
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Authentication Settings
AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = '/accounts/login/'  # Corrected path
LOGIN_URL = '/accounts/login/'  # Corrected path

# Logging Configuration
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOGGING_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
os.makedirs(LOGGING_DIR, exist_ok=True)  # اطمینان از وجود پوشه `logs`

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'MyLog.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

logging.config.dictConfig(LOGGING)
# ایجاد پوشه logs در صورت عدم وجود
# ایجاد یک هَندلر (handler) که لاگ‌ها را به یک فایل می‌نویسد
file_handler = logging.FileHandler('logfile.log', 'w', 'utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
# ایجاد یک لاگر (logger) و افزودن هَندلر به آن
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)
logger.setLevel(logging.INFO)

warnings.filterwarnings('always', category=RuntimeWarning)

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
AUTH_GROUP_MODEL = 'accounts.CustomGroup'
# Time Lock Configuration
TIME_LOCK_FILE = os.path.join(BASE_DIR, "core/RCMS_Lock/timelock.dat")

# Encryption Keys
RCMS_SECRET_KEY = '8nrJNs-teqRyAlyAVIknDQwZCBeN-j-W2EKF7cKGW9A='
FERNET_KEY = os.getenv("FERNET_KEY", "ATLZREELWdggY12feExDxVYyM8ANnQrWjjDKza3iB1g=")

# Validate Encryption Key
if len(RCMS_SECRET_KEY) != 44:
    raise ValueError("🔴 RCMS_SECRET_KEY is invalid! Please provide a valid value.")

# Active User Limit
MAX_ACTIVE_USERS = 3

# Add TimeLockMiddleware
# MIDDLEWARE.append('core.middleware.TimeLockMiddleware')
###############
# تنظیمات پیشرفته سشن
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # اطمینان از استفاده از دیتابیس
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # جدید
SESSION_COOKIE_AGE = 420  # 7 دقیقه
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True  # هر درخواست سشن را تازه‌سازی می‌کند
SESSION_COOKIE_SAMESITE = 'Lax'  # برای اطمینان از ارسال کوکی در درخواست‌های AJAX

"""
SESSION_COOKIE_AGE: مدت زمان (به ثانیه) که سشن کاربر در مرورگر ذخیره می‌شود. پس از این مدت، کوکی سشن منقضی شده و مرورگر آن را حذف می‌کند.
SESSION_SAVE_EVERY_REQUEST: تعیین می‌کند که آیا سشن در هر درخواست ذخیره شود یا خیر. با تنظیم این گزینه به True، زمان انقضای سشن در هر درخواست کاربر به‌روزرسانی می‌شود.
"""
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
