# settings.py
import logging.config
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-*zron+$_y8zn14z7a7r(wgllx%8n0vii^(6uar=_r)94(v!khc'
DEBUG = True
ALLOWED_HOSTS = ['*']#'127.0.0.1', 'localhost'  # اضافه کردم برای لوکال

# INSTALLED_APPS = [
#     'Tanbakhsystem.apps_overrides.AdminInterfaceConfig',  # رابط مدیریت
#     'django.contrib.humanize',
#     'colorfield',
#     'django.contrib.admin',  # 'Tanbakhsystem.apps_overrides.AdminConfig',  # به جای 'django.contrib.admin'
#     # 'Tanbakhsystem.apps_overrides.AuthConfig',  # به جای 'django.contrib.auth'
#     'django.contrib.auth',  # به جای Tanbakhsystem.apps_overrides.AuthConfig
#     # 'Tanbakhsystem.apps_overrides.ContentTypesConfig',  #
#     'django.contrib.contenttypes'
#     # 'Tanbakhsystem.apps_overrides.SessionsConfig',
#     'django.contrib.sessions'
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'core.apps.CoreConfig',
#     'reports.apps.ReportsConfig',
#     'django_jalali',
#     'jalali_date',
#     'version_tracker.apps.VersionTrackerConfig',
#     'tankhah.apps.TankhahConfig',
#     'Tanbakhsystem.apps_overrides.NotificationsConfig',  # اعلانات
#     'accounts.apps.AccountsConfig',
# ]
# clean
INSTALLED_APPS = [
    'django.contrib.humanize',
    # 'admin_interface',
    # 'colorfield',
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
    'core.templatetags.file_tags', # تمپلیت برای تگ تصاویر
    'budgets.apps.BudgetsConfig',
    'formtools',

]

# INSTALLED_APPS = [
#     # 'Tanbakhsystem.apps_overrides.AdminInterfaceConfig',  # اگه از notifications استفاده می‌کنی
#     'django.contrib.humanize',
#     'admin_interface',
#     'colorfield',
#     # 'Tanbakhsystem.apps_overrides.AdminConfig',  # به جای 'django.contrib.admin'
#     # 'Tanbakhsystem.apps_overrides.AuthConfig',  # به جای 'django.contrib.auth'
#     # 'Tanbakhsystem.apps_overrides.ContentTypesConfig',  # به جای 'django.contrib.contenttypes'
#     # 'Tanbakhsystem.apps_overrides.SessionsConfig',  # به جای 'django.contrib.sessions'
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.staticfiles',
#     'core.apps.CoreConfig',
#     'reports.apps.ReportsConfig',
#     'django_jalali',
#     'jalali_date',
#     'version_tracker.apps.VersionTrackerConfig',
#     'tankhah.apps.TankhahConfig',
#     'accounts.apps.AccountsConfig',
#     'Tanbakhsystem.apps_overrides.NotificationsConfig',  # اگه از notifications استفاده می‌کنی
#
# ]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # میدلورهای سفارشی
    'accounts.middleware.AuditLogMiddleware',
    'accounts.middleware.ActiveUserMiddleware',
    'accounts.middleware.RequestMiddleware',  # اضافه کردم
]
# Template
# X_FRAME_OPTIONS = "SAMEORIGIN"
# SILENCED_SYSTEM_CHECKS = ["security.W019"]

ROOT_URLCONF = 'Tanbakhsystem.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'Tanbakhsystem/templates')],
        # 'DIRS': [BASE_DIR / 'templates', ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.version_info',  # باید تعریف بشه
                'core.context_processors.notifications',  # Note User

            ],
        },
    },
]

WSGI_APPLICATION = 'Tanbakhsystem.wsgi.application'

DATABASES = {'default': {
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
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'Tanbakhsystem/static')]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# تنظیمات احراز هویت و سشن
AUTH_USER_MODEL = 'accounts.CustomUser'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
SESSION_COOKIE_AGE = 1500  # 25 دقیقه (برای 7 دقیقه بذار 420)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = False  # برای لوکال
CSRF_COOKIE_SECURE = False  # برای لوکال
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# بقیه تنظیمات
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': 'unique-snowflake',
    }
}

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

# MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
# AUTH_GROUP_MODEL = 'accounts.CustomGroup'
# # Time Lock Configuration
TIME_LOCK_FILE = os.path.join(BASE_DIR, "core/RCMS_Lock/core/RCMS_Lock/timelock.dat")
#
# # Encryption Keys
RCMS_SECRET_KEY = '8nrJNs-teqRyAlyAVIknDQwZCBeN-j-W2EKF7cKGW9A='
FERNET_KEY = os.getenv("FERNET_KEY", "ATLZREELWdggY12feExDxVYyM8ANnQrWjjDKza3iB1g=")
#
# Validate Encryption Key
if len(RCMS_SECRET_KEY) != 44:
    raise ValueError("🔴 RCMS_SECRET_KEY is invalid! Please provide a valid value.")
#
# Active User Limit
MAX_ACTIVE_USERS = 5


# لاگینگ
LOG_DIR = os.path.join(BASE_DIR, 'Tanbakhsystem/logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# settings.py
import os

# Assuming BASE_DIR is defined elsewhere in your settings.py
# BASE_DIR = Path(__file__).resolve().parent.parent # Example

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False, # Keep existing loggers enabled unless explicitly disabled

    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {funcName} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S', # Consistent date format
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
            'level': 'INFO', # Show INFO, WARNING, ERROR, CRITICAL messages in console
            'class': 'logging.StreamHandler',
            'formatter': 'simple', # Simpler format for console output
        },
        'file_errors': { # Handler for application-wide errors
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'Tanbakhsystem/logs', 'application_errors.log'),
            'maxBytes': 1024 * 1024 * 10, # 10 MB per file
            'backupCount': 5, # Keep 5 backup files (total 6 files, 60MB max)
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'file_budgets_debug': { # Specific handler for 'budgets' app debug logs
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'Tanbakhsystem/logs', 'budgets_debug.log'),
            'maxBytes': 1024 * 1024 * 5, # 5 MB per file
            'backupCount': 3, # Keep 3 backup files (total 4 files, 20MB max)
            'formatter': 'app_debug',
            'encoding': 'utf-8',
        },
        'file_django_errors': { # Handler for Django's internal errors (e.g., system)
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'Tanbakhsystem/logs', 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 5, # 5 MB per file
            'backupCount': 3,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        '': { # Root logger: Catches everything that propagates
            'handlers': ['console', 'file_errors'], # Console for info, file for errors
            'level': 'WARNING', # Default level for unhandled logs
            'propagate': False, # Crucial: Prevent propagation to default Python logger
        },
        'django': { # Django's internal messages
            'handlers': ['file_django_errors'],
            'level': 'INFO', # Log INFO and above for Django system messages to a file
            'propagate': False,
        },
        'django.db.backends': { # Database queries
            'handlers': [], # No handlers here means these logs are discarded by default.
                            # Set 'console' or 'file_budgets_debug' if you need to debug DB for 'budgets'.
            'level': 'DEBUG', # Keep this DEBUG, but make sure it doesn't propagate unwantedly.
            'propagate': False, # Prevent these verbose logs from hitting other handlers
        },
        'budgets': { # Your 'budgets' application's specific logger
            'handlers': ['console', 'file_budgets_debug'], # Log to console and specific file for debugging
            'level': 'DEBUG', # Log all debug messages for this app
            'propagate': False, # Do not propagate to root logger
        },
        # Add other app loggers here if needed, e.g.:
        # 'your_other_app': {
        #     'handlers': ['file_errors'], # Send errors to the general error file
        #     'level': 'INFO',
        #     'propagate': False,
        # },
    },
}

# import logging.config
# import os
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # یا هر روش دیگری برای تعریف BASE_DIR
# logging.config.dictConfig(LOGGINGA)
# logger = logging.getLogger(__name__)

DJANGO_NOTIFICATIONS_CONFIG = {
    'USE_JSONFIELD': True,  # برای استفاده از JSONField
    'SOFT_DELETE': True,    # برای فعال کردن حذف نرم
}
# تنظیمات اختیاری notifications
NOTIFICATIONS_USE_JSONFIELD = True
NOTIFICATIONS_SOFT_DELETE = True
