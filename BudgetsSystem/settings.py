import logging.config
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# لود فایل .env
load_dotenv()

logger = logging.getLogger('SettingError')

# محاسبه مسیر اصلی پروژه
BASE_DIR = Path(__file__).resolve().parent.parent
# اضافه کردن مسیر پروژه به Python path
sys.path.insert(0, str(BASE_DIR))

# تنظیمات تمپلیت و استاتیک
TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'templates'),
]

def read_secret_file(*env_keys: str) -> Optional[str]:
    """
    تلاشی ساده برای خواندن مقادیر حساس از فایل‌هایی که مسیرشان در متغیرهای محیطی قرار دارد.
    اولین فایل موجود خوانده می‌شود و مقدار trim شده برگردانده خواهد شد.
    """
    for key in env_keys:
        if not key:
            continue
        file_path = os.getenv(key)
        if not file_path:
            continue
        path_obj = Path(file_path)
        if path_obj.exists():
            try:
                return path_obj.read_text(encoding="utf-8").strip()
            except Exception:  # pragma: no cover - فقط برای جلوگیری از کرش در زمان اجرا
                logger.warning("Could not read secret file for %s", key)
    return None


# تنظیمات حساس از .env / فایل‌های secret
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = read_secret_file('SECRET_KEY_FILE', 'SECRET_KEY_FILE_PATH')
SECRET_KEY = SECRET_KEY or 'django-insecure-default-key-for-dev-only'  # پیش‌فرض برای توسعه
# DEBUG = True # os.getenv('DEBUG', 'False') == 'True'  # تبدیل به bool
DEBUG = os.getenv("DEBUG", "False") == "True"
# دامنه‌های مجاز برای Django
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,*.trycloudflare.com,*.cfargotunnel.com' ).split(',')  # تبدیل به لیست
# دامنه‌های معتبر برای CSRF (POST requests)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,https://*.trycloudflare.com,https://*.cfargotunnel.com").split(',') if origin.strip()]

# تنظیمات دیتابیس از .env
# پشتیبانی از هر دو فرمت: DB_* (Docker) و DATABASE_DEFAULT_* (محلی)
DB_NAME = os.getenv('DATABASE_DEFAULT_NAME') or os.getenv('DB_NAME', 'tankhasystem')
DB_USER = os.getenv('DATABASE_DEFAULT_USER') or os.getenv('DB_USER', 'root')
DB_PASSWORD = (
    os.getenv('DATABASE_DEFAULT_PASSWORD') or
    os.getenv('DB_PASSWORD') or
    read_secret_file('DATABASE_DEFAULT_PASSWORD_FILE', 'DB_PASSWORD_FILE', 'DB_PASSWORD_FILE_PATH') or
    'S@123456@1234'
)
DB_HOST = os.getenv('DATABASE_DEFAULT_HOST') or os.getenv('DB_HOST', '127.0.0.1')
# اگر DB_HOST=db است (برای Docker) اما در سیستم محلی اجرا می‌شود، به localhost تغییر می‌دهیم
if DB_HOST == 'db' and not os.path.exists('/.dockerenv'):
    DB_HOST = '127.0.0.1'
DB_PORT = os.getenv('DATABASE_DEFAULT_PORT') or os.getenv('DB_PORT', '3306')

# تنظیمات ایمیل از .env
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# تنظیمات Redis از .env
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD') or read_secret_file('REDIS_PASSWORD_FILE', 'REDIS_PASSWORD_FILE_PATH')
REDIS_URL = os.getenv('REDIS_URL')
if not REDIS_URL:
    redis_host = os.getenv('REDIS_HOST', '127.0.0.1')
    redis_port = os.getenv('REDIS_PORT', '6379')
    if REDIS_PASSWORD:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{redis_host}:{redis_port}/0"
    else:
        REDIS_URL = f"redis://{redis_host}:{redis_port}/0"

# تنظیمات امنیتی از .env
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'True') == 'True'
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'True') == 'True'

# تنظیمات اضافی برای Cloudflare tunnel
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# تنظیمات USB Dongle Validation
USB_DONGLE_VALIDATION_ENABLED = os.getenv('USB_DONGLE_VALIDATION_ENABLED', 'False') == 'True'
USB_DONGLE_CACHE_TIMEOUT = int(os.getenv('USB_DONGLE_CACHE_TIMEOUT', '300'))
USB_DONGLE_NOTIFICATIONS_ENABLED = os.getenv('USB_DONGLE_NOTIFICATIONS_ENABLED', 'True') == 'True'
USB_DONGLE_DEBUG_MODE = os.getenv('USB_DONGLE_DEBUG_MODE', 'False') == 'True'

# تنظیمات اعلان‌ها
NOTIFICATION_ENABLED = os.getenv('NOTIFICATION_ENABLED', 'True') == 'True'
NOTIFICATION_CHANNELS = os.getenv('NOTIFICATION_CHANNELS', 'in_app,email').split(',')
NOTIFICATION_RETENTION_DAYS = int(os.getenv('NOTIFICATION_RETENTION_DAYS', '30'))

# تنظیمات workflow
WORKFLOW_ENABLED = os.getenv('WORKFLOW_ENABLED', 'True') == 'True'
WORKFLOW_AUTO_APPROVE = os.getenv('WORKFLOW_AUTO_APPROVE', 'False') == 'True'
WORKFLOW_NOTIFICATION_ENABLED = os.getenv('WORKFLOW_NOTIFICATION_ENABLED', 'True') == 'True'

# تنظیمات گزارش‌گیری
REPORT_ENABLED = os.getenv('REPORT_ENABLED', 'True') == 'True'
REPORT_CACHE_TIMEOUT = int(os.getenv('REPORT_CACHE_TIMEOUT', '600'))
REPORT_MAX_RECORDS = int(os.getenv('REPORT_MAX_RECORDS', '10000'))

# تنظیمات اتصال به نرم‌افزارهای خارجی (API Integrations)
EXTERNAL_INTEGRATIONS = {
    # نمونه:
    # 'wms': {
    #     'BASE_URL': os.getenv('WMS_BASE_URL', ''),
    #     'API_KEY': os.getenv('WMS_API_KEY', ''),
    #     'TIMEOUT': int(os.getenv('WMS_TIMEOUT', '15')),
    # }
}

# تنظیمات version tracking
VERSION_TRACKING_ENABLED = os.getenv('VERSION_TRACKING_ENABLED', 'True') == 'True'
VERSION_AUTO_BACKUP = os.getenv('VERSION_AUTO_BACKUP', 'True') == 'True'
VERSION_RETENTION_COUNT = int(os.getenv('VERSION_RETENTION_COUNT', '10'))

INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.humanize',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'channels',
    'django_jalali',
    'jalali_date',
    'formtools',
    'dbbackup',
    'storages',

    # Your project apps (ترتیب مهم ↓)
    'core.apps.CoreConfig',                   # ✅ باید قبل از اپ‌های وابسته بیاید
    'accounts.apps.AccountsConfig',
    'reports.apps.ReportsConfig',
    'version_tracker.apps.VersionTrackerConfig',
    'usb_key_validator.apps.UsbKeyValidatorConfig',
    'notificationApp.apps.NotificationappConfig',
    'purchase_requests.apps.PurchaseRequestsConfig',
    'tankhah.apps.TankhahConfig',
    'budgets.apps.BudgetsConfig',             # ✅ بعد از core و tankhah و غیره
    'guide',                                  # ✅ اپلیکیشن راهنما
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
    'usb_key_validator.middleware.USBDongleValidationMiddleware',
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
                'budgets.context_processors.payment_order_stats',
                'accounts.context_processors.user_theme',
            ],
        },
    },
]

WSGI_APPLICATION = 'BudgetsSystem.wsgi.application'

# تنظیمات django-db-backup
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'

# مسیرهای پشتیبان‌گیری (محلی و شبکه)
BACKUP_LOCATIONS = {
    'local': os.path.join(BASE_DIR, 'backups'),
    'network': os.getenv('BACKUP_NETWORK_PATH', '\\\\server\\backups\\budgets'),  # مسیر دیسک شبکه
    'secondary': os.getenv('BACKUP_SECONDARY_PATH', 'D:\\Backups\\BudgetsSystem'),  # مسیر ثانویه
}

# مسیر پیش‌فرض
DBBACKUP_STORAGE_OPTIONS = {'location': BACKUP_LOCATIONS['local']}

DBBACKUP_GPG_RECIPIENT = None
DBBACKUP_CLEANUP_KEEP_DAYS = 7
DBBACKUP_CLEANUP_KEEP_MEDIA_DAYS = 7
DBBACKUP_MAIL_ADMINS = True
DBBACKUP_MAIL_SUBJECT = '[Django Backup] '
DBBACKUP_GPG_ALWAYS_TRUST = True

# نرمال‌سازی مقادیر دیتابیس برای استفاده در چند بخش
DATABASE_DEFAULT_NAME = os.getenv('DATABASE_DEFAULT_NAME', DB_NAME)
DATABASE_DEFAULT_USER = os.getenv('DATABASE_DEFAULT_USER', DB_USER)
DATABASE_DEFAULT_PASSWORD = os.getenv('DATABASE_DEFAULT_PASSWORD', DB_PASSWORD)
DATABASE_DEFAULT_HOST = os.getenv('DATABASE_DEFAULT_HOST', DB_HOST)
DATABASE_DEFAULT_PORT = os.getenv('DATABASE_DEFAULT_PORT', DB_PORT)

# تنظیمات پشتیبان‌گیری برای دیتابیس لاگ
DBBACKUP_CONNECTORS = {
    'default': {
        'CONNECTOR': 'dbbackup.db.mysql.MysqlDumpConnector',
        'NAME': DATABASE_DEFAULT_NAME,
        'USER': DATABASE_DEFAULT_USER,
        'PASSWORD': DATABASE_DEFAULT_PASSWORD,
        'HOST': DATABASE_DEFAULT_HOST,
        'PORT': DATABASE_DEFAULT_PORT,
    },
    'logs': {
        'CONNECTOR': 'dbbackup.db.mysql.MysqlDumpConnector',
        'NAME': os.getenv('DATABASE_LOGS_NAME', 'tankhah_logs_db'),
        'USER': os.getenv('DATABASE_LOGS_USER', 'root'),
        'PASSWORD': os.getenv('DATABASE_LOGS_PASSWORD', ''),
        'HOST': os.getenv('DATABASE_LOGS_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_LOGS_PORT', '3306'),
    }
}

# تنظیمات برای ویوی دستی بک‌آپ و ریست
DATABASE_MANAGE_APP_LABELS = ['core', 'budgets', 'tankhah', 'BudgetsSystem', 'notificationApp', 'accounts', 'reports']

DATABASE_ROUTERS = ['accounts.routers.LogRouter']

# تنظیمات دیتابیس از .env
# استفاده از pymysql در Docker (Linux) - باید قبل از import کردن Django database backends باشد
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except (ImportError, ModuleNotFoundError):
    # اگر pymysql نصب نشده، از mysqlclient استفاده می‌شود
    pass

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DATABASE_DEFAULT_NAME,
        'USER': DATABASE_DEFAULT_USER,
        'PASSWORD': DATABASE_DEFAULT_PASSWORD,
        'HOST': DATABASE_DEFAULT_HOST,
        'PORT': DATABASE_DEFAULT_PORT,
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
    },
    'tankhah_logs_db': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DATABASE_LOGS_NAME', 'tankhah_logs_db'),
        'USER': os.getenv('DATABASE_LOGS_USER', 'root'),
        'PASSWORD': os.getenv('DATABASE_LOGS_PASSWORD', ''),
        'HOST': os.getenv('DATABASE_LOGS_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_LOGS_PORT', '3306'),
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

# تنظیمات فایل‌های استاتیک - یکپارچه‌سازی شده
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),  # پوشه اصلی فایل‌های استاتیک توسعه
]
STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static')  # پوشه جمع‌آوری شده برای production

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
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'  # برای HTTPS در production
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'  # برای HTTPS در production
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = True
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

# تنظیمات لایسنس
RCMS_LICENSE_CONFIG_PATH = os.getenv('RCMS_LICENSE_CONFIG_PATH', os.path.join(BASE_DIR, 'config/license_config.json'))
RCMS_SECRET_KEY = None
MAX_ACTIVE_USERS = 5
ORGANIZATION_NAME = "پیش‌فرض"

# لود کردن اطلاعات لایسنس از فایل JSON
import json
from datetime import date

from cryptography.fernet import Fernet

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
    RCMS_SECRET_KEY = Fernet.generate_key().decode()
except Exception as e:
    logger.critical(f"خطای غیرمنتظره در بارگذاری لایسنس: {e}")
    raise

if RCMS_SECRET_KEY:
    RCMS_SECRET_KEY_CIPHER = Fernet(RCMS_SECRET_KEY.encode())
else:
    RCMS_SECRET_KEY_CIPHER = Fernet(Fernet.generate_key())
    logger.critical(
        "RCMS_SECRET_KEY_CIPHER is initialized with a dummy key. Decryption will likely fail for TimeLockModel.")

# تنظیمات لاگینگ
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
        'app_debug': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {funcName} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'application_errors.log'),
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_budgets_debug': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'budgets_debug.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 3,
            'formatter': 'app_debug',
            'encoding': 'utf-8',
        },
        'file_django_errors': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_all_info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'all_info.log'),
            'maxBytes': 1024 * 1024 * 20,
            'backupCount': 2,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file_errors', 'file_all_info'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['file_django_errors', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': [],
            'level': 'DEBUG',
            'propagate': False,
        },
        'budgets': {
            'handlers': ['console', 'file_budgets_debug', 'file_errors'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# تنظیمات WebSocket
ASGI_APPLICATION = 'BudgetsSystem.asgi.application'
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Configurable initial status for PaymentOrder
#  برای پیش فرض اشافه شده است
PAYMENT_ORDER_INITIAL_STATUS_CODE = os.getenv('PAYMENT_ORDER_INITIAL_STATUS_CODE', 'PO_DRAFT')
PAYMENT_ORDER_INITIAL_STATUS_NAME = os.getenv('PAYMENT_ORDER_INITIAL_STATUS_NAME', 'پیش‌نویس دستور پرداخت')
