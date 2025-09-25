from .settings import *  # noqa

# Use SQLite for tests to avoid MySQL-specific features like ArrayField issues
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test.sqlite3',
    }
}

# Trim problematic middlewares for tests (USB dongle)
MIDDLEWARE = [m for m in MIDDLEWARE if 'usb_key_validator.middleware.USBDongleValidationMiddleware' not in m]

# Speed up hashing in tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Disable migrations for core so tests use model state (avoids ArrayField migration SQL)
MIGRATION_MODULES = {
    'core': None,
    'tankhah': None,
    'accounts': None,
    'budgets': None,
    'reports': None,
    'notificationApp': None,
    'version_tracker': None,
}


