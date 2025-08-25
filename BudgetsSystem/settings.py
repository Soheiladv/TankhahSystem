# settings.py
import logging.config
import os
from pathlib import Path

logger = logging.getLogger('SettingError')

# --- Start of your existing settings.py ---

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-*zron+$_y8zn14z7a7r(wgllx%8n0vii^(6uar=_r)94(v!khc'
DEBUG = True  # در محیط توسعه، DEBUG = True باشد
# ALLOWED_HOSTS = ['*']  # برای لوکال هاست، '127.0.0.1', 'localhost' یا '*'
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']
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
    # 'notifications',
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
    'dbbackup',  # افزودن django-db-backup به Installed Apps
    'storages',
    'usb_key_validator.apps.UsbKeyValidatorConfig',
    'notificationApp.apps.NotificationappConfig'  # اگر می‌خواهید بک‌آپ‌ها را در فضای ابری ذخیره کنید (مثلاً S3)
    # 'django_select2',

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

ROOT_URLCONF = 'BudgetsSystem.urls'

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
                # 'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'BudgetsSystem.wsgi.application'

# --- تنظیمات django-db-backup ---

# مسیر پیش‌فرض برای ذخیره بک‌آپ‌های دیتابیس و مدیا (در صورتی که از FileSystemStorage استفاده می‌کنید)
# در محیط پروداکشن، بهتر است این مسیر خارج از public_html باشد.
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': os.path.join(BASE_DIR, 'backups')}
# DBBACKUP_GPG_RECIPIENT = 'DCDD2D7315FF4295A13FD9C5BF0C641B3F0AFD7B'  # نام کلید GPG
DBBACKUP_GPG_RECIPIENT = None
# اگر می‌خواهید بک‌آپ‌ها در S3 یا فضای ابری دیگری ذخیره شوند، این را تغییر دهید:
# DBBACKUP_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# DBBACKUP_STORAGE_OPTIONS = {} # تنظیمات S3 باید در بخش‌های دیگر settings.py تعریف شوند (مثلاً AWS_STORAGE_BUCKET_NAME)

# تنظیمات پاک کردن بک‌آپ‌های قدیمی (در زمان اجرای دستور dbbackup --clean)
DBBACKUP_CLEANUP_KEEP_DAYS = 7  # نگه داشتن بک‌آپ‌های ۷ روز اخیر
DBBACKUP_CLEANUP_KEEP_MEDIA_DAYS = 7  # نگه داشتن بک‌آپ‌های مدیای ۷ روز اخیر

# ایمیل برای ارسال گزارش بک‌آپ‌ها
DBBACKUP_MAIL_ADMINS = True  # ارسال ایمیل به ادمین‌ها در صورت موفقیت/خطا
DBBACKUP_MAIL_SUBJECT = '[Django Backup] '  # پیشوند موضوع ایمیل
# EMAIL_BACKEND و سایر تنظیمات ایمیل باید در settings.py تعریف شده باشند.
# تنظیمات GPG (در صورت استفاده از رمزنگاری)
DBBACKUP_GPG_ALWAYS_TRUST = True  # در صورت نیاز به اعتماد به کلیدهای GPG
# --- تنظیمات برای ویوی دستی بک‌آپ و ریست ---

# لیستی از اپلیکیشن‌هایی که مدل‌هایشان در بخش مدیریت دیتابیس نمایش داده می‌شوند.
# این لیست را بر اساس نیاز خود تنظیم کنید.
DATABASE_MANAGE_APP_LABELS = ['core', 'budgets', 'tankhah', 'BudgetsSystem', 'notificationApp', 'accounts', 'reports']

DATABASE_ROUTERS = ['accounts.routers.LogRouter']

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
        'tankhah_logs_db': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'tankhah_logs_db',
            'USER': 'root',
            'PASSWORD': 'S@123456@1234',
            'HOST': 'localhost',
            'PORT': '3306',
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
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'staticfiles'), ]
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

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
##########################################################################################################
#          Licence
##########################################################################################################
# TIME_LOCK_FILE = os.path.join(BASE_DIR, "core/RCMS_Lock/timelock.dat")
# RCMS_SECRET_KEY = '8nrJNs-teqRyAlyAVIknDQwZCBeN-j-W2EKF7cKGW9A='
# FERNET_KEY = os.getenv("FERNET_KEY", "ATLZREELWdggY12feExDxVYyM8ANnQrWjjDKza3iB1g=")
#
# if len(RCMS_SECRET_KEY) != 44:
#     raise ValueError("🔴 RCMS_SECRET_KEY is invalid! Please provide a valid value.")
#
# MAX_ACTIVE_USERS = 5
############################################## New Licence ###############################################
# مسیر فایل کانفیگ لایسنس
# RCMS_LICENSE_CONFIG_PATH = os.environ.get('RCMS_LICENSE_CONFIG_PATH', '/opt/rcms_config/license_config.json') # Linux
# RCMS_LICENSE_CONFIG_PATH = os.environ.get('RCMS_LICENSE_CONFIG_PATH', 'config/license_config.json') # Linux
RCMS_LICENSE_CONFIG_PATH = os.environ.get('RCMS_LICENSE_CONFIG_PATH',
                                          os.path.join(BASE_DIR, 'config/license_config.json'))

# مقادیر پیش‌فرض
RCMS_SECRET_KEY = None
MAX_ACTIVE_USERS = 5
ORGANIZATION_NAME = "پیش‌فرض"

# لود کردن اطلاعات لایسنس از فایل JSON
import os
import json
from datetime import date
from cryptography.fernet import Fernet
import logging

# بارگذاری لایسنس
try:
    if os.path.exists(RCMS_LICENSE_CONFIG_PATH):
        with open(RCMS_LICENSE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            license_data = json.load(f)
        RCMS_SECRET_KEY = license_data.get('fernet_key')
        MAX_ACTIVE_USERS = license_data.get('max_active_users', MAX_ACTIVE_USERS)
        ORGANIZATION_NAME = license_data.get('organization_name', ORGANIZATION_NAME)

        if not RCMS_SECRET_KEY or len(RCMS_SECRET_KEY) != 44:
            raise ValueError("کلید Fernet نامعتبر است.")

        logger.info(
            f"لایسنس از {RCMS_LICENSE_CONFIG_PATH} بارگذاری شد: کاربران={MAX_ACTIVE_USERS}, شرکت={ORGANIZATION_NAME}")
    else:
        raise FileNotFoundError(f"فایل لایسنس در {RCMS_LICENSE_CONFIG_PATH} یافت نشد.")
except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
    logger.error(f"خطا در بارگذاری لایسنس: {e}. استفاده از مقادیر پیش‌فرض.")
    RCMS_SECRET_KEY = Fernet.generate_key().decode()  # کلید موقت
except Exception as e:
    logger.critical(f"خطای غیرمنتظره در بارگذاری لایسنس: {e}")
    raise
# مقداردهی اولیه Fernet cipher (برای استفاده توسط TimeLockModel)
if RCMS_SECRET_KEY:
    RCMS_SECRET_KEY_CIPHER = Fernet(RCMS_SECRET_KEY.encode())
else:
    RCMS_SECRET_KEY_CIPHER = Fernet(Fernet.generate_key())
    logger.critical(
        "RCMS_SECRET_KEY_CIPHER is initialized with a dummy key. Decryption will likely fail for TimeLockModel.")

##########################################################################################################
# DJANGO_NOTIFICATIONS_CONFIG = {
#     'USE_JSONFIELD': True,
#     'SOFT_DELETE': True,
# }
# NOTIFICATIONS_USE_JSONFIELD = True
# NOTIFICATIONS_SOFT_DELETE = True

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
# -----------------------------------------------------------------
#  تنظیمات WebSocket در settings.py:
ASGI_APPLICATION = 'tankhah.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
# -----------------------------------------------------------------
