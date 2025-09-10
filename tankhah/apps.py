# tankhah/apps.py
from django.apps import AppConfig

class TankhahConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tankhah'  # یا 'Tankhah' بسته به چیزی که در INSTALLED_APPS استفاده کردید
    label = 'tankhah'  # باید با app_label در دیتابیس تطابق داشته باشد

    verbose_name = 'مدیریت قسمت تنخواه و فاکتور'