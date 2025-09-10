from django.apps import AppConfig

class NotificationappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notificationApp'        # مسیر پوشه
    label = 'notificationApp'       # همون اسم، تغییر نده
    verbose_name = "سیستم اعلان‌ها"
