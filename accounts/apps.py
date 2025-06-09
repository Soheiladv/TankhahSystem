# from django.utils.module_loading import autodiscover_modules
from django.apps import AppConfig
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name =  'مدیریت کاربران'

    def ready(self):
        import accounts.signals  # وارد کردن سیگنال‌ها
