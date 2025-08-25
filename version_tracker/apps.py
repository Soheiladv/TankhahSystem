"""
پیکربندی اپلیکیشن version_tracker
"""
from django.apps import AppConfig

class VersionTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'version_tracker'
    verbose_name = 'مدیریت نسخه'

    def ready(self):
        from django.db.models.signals import post_migrate
        from .signals import update_versions
<<<<<<< HEAD
        post_migrate.connect(update_versions, sender=self)
=======
        post_migrate.connect(update_versions, sender=self)



>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
