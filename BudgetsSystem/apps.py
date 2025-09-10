from django.apps import AppConfig

class BudgetsSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'BudgetsSystem'
    verbose_name = 'مرکز اصلی یا هسته مدیریت ساختار نرم افزار تنخواه گردان'
    label = 'BudgetsSystem'  # باید با app_label در دیتابیس تطابق داشته باشد

    def ready(self):
        import BudgetsSystem.signals  # وارد کردن سیگنال‌ها