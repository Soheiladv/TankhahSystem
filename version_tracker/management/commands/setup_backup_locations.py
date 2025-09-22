from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from version_tracker.models_backup_locations import BackupLocation
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'ایجاد مسیرهای پیش‌فرض پشتیبان‌گیری'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='نام کاربری برای ایجاد مسیرها'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجبار ایجاد مجدد مسیرهای موجود'
        )

    def handle(self, *args, **options):
        username = options['username']
        force = options['force']
        
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"کاربر '{username}' یافت نشد")
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"ایجاد مسیرهای پیش‌فرض برای کاربر: {user.username}")
        )
        
        # ایجاد مسیرهای پیش‌فرض
        BackupLocation.create_default_locations(user)
        
        # نمایش مسیرهای ایجاد شده
        locations = BackupLocation.objects.all()
        
        self.stdout.write(
            self.style.SUCCESS(f"تعداد مسیرهای ایجاد شده: {locations.count()}")
        )
        
        for location in locations:
            # تست اتصال
            success, message = location.test_connection()
            status = "✅" if success else "❌"
            
            self.stdout.write(
                f"{status} {location.name} - {location.path} ({location.get_location_type_display()})"
            )
            if not success:
                self.stdout.write(
                    self.style.WARNING(f"   خطا: {message}")
                )
        
        self.stdout.write(
            self.style.SUCCESS("عملیات ایجاد مسیرهای پیش‌فرض تکمیل شد")
        )
