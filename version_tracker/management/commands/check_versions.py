"""
دستور مدیریتی برای بررسی دستی نسخه‌ها
"""
from django.core.management.base import BaseCommand
from version_tracker.models import AppVersion

class Command(BaseCommand):
    help = 'بررسی و به‌روزرسانی نسخه تمام اپلیکیشن‌ها'

    def handle(self, *args, **options):
        updates = AppVersion.check_and_update_versions()
        
        if updates:
            self.stdout.write(self.style.SUCCESS('\n🔄 تغییرات نسخه شناسایی شد:'))
            for app_name, new_version in updates.items():
                self.stdout.write(f"  • {app_name}: نسخه {new_version}")
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ هیچ تغییری شناسایی نشد.'))