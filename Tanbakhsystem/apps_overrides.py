# core/apps_overrides.py
from django.apps import AppConfig
# نیازی به وارد کردن AdminSite نیست، چون فقط مسیر رشته‌ای را استفاده می‌کنیم

class AdminConfig(AppConfig):
    name = 'django.contrib.admin'
    verbose_name = 'مدیریت'
    default_site = 'django.contrib.admin.sites.AdminSite'  # به صورت رشته
    default_auto_field = 'django.db.models.BigAutoField'

class AuthConfig(AppConfig):
    name = 'django.contrib.auth'
    verbose_name = 'احراز هویت و مجوزها'
    default_auto_field = 'django.db.models.BigAutoField'
    def ready(self):
        from accounts.models import CustomUser  # اگه این باشه، CustomUser لود نمی‌شه

class ContentTypesConfig(AppConfig):
    name = 'django.contrib.contenttypes'
    verbose_name = 'انواع محتوا'
    default_auto_field = 'django.db.models.BigAutoField'


class SessionsConfig(AppConfig):
    name = 'django.contrib.sessions'
    verbose_name = 'جلسات'
    default_auto_field = 'django.db.models.BigAutoField'

class AdminInterfaceConfig(AppConfig):
    name = 'admin_interface'
    verbose_name = 'رابط مدیریت'
    default_auto_field = 'django.db.models.BigAutoField'
#
class NotificationsConfig(AppConfig):
    name = 'notifications'
    verbose_name = 'اعلانات'
    default_auto_field = 'django.db.models.BigAutoField'