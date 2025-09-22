from django.core.management.base import BaseCommand
from django.utils import timezone
from usb_key_validator.enhanced_utils import dongle_manager
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'اعتبارسنجی روزانه USB Dongle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='اجبار اعتبارسنجی بدون توجه به cache',
        )
        parser.add_argument(
            '--repair',
            action='store_true',
            help='تعمیر سکتورهای خراب در صورت یافت شدن',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='نمایش آمار dongle',
        )

    def handle(self, *args, **options):
        force = options['force']
        repair = options['repair']
        stats = options['stats']
        
        self.stdout.write(
            self.style.SUCCESS(f"شروع اعتبارسنجی روزانه USB Dongle - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        )
        
        # اگر force باشد، cache را پاک کن
        if force:
            from django.core.cache import cache
            cache.delete('usb_dongle_validation')
            self.stdout.write("Cache پاک شد")
        
        # اعتبارسنجی روزانه
        result = dongle_manager.daily_validation_check()
        
        # نمایش نتیجه
        if result['valid']:
            self.stdout.write(
                self.style.SUCCESS(f"✅ اعتبارسنجی موفق: {result['message']}")
            )
            self.stdout.write(f"📱 دستگاه: {result.get('device', 'نامشخص')}")
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ اعتبارسنجی ناموفق: {result['message']}")
            )
        
        self.stdout.write(f"🕐 زمان: {result['timestamp']}")
        
        # نمایش آمار
        if stats:
            usb_drives = dongle_manager.find_usb_drives()
            if usb_drives:
                device = usb_drives[0]['device_id']
                stats_data = dongle_manager.get_dongle_statistics(device)
                if stats_data:
                    self.stdout.write("\n📊 آمار Dongle:")
                    self.stdout.write(f"   کل سکتورها: {stats_data['total_sectors']}")
                    self.stdout.write(f"   سکتورهای معتبر: {stats_data['valid_sectors']}")
                    self.stdout.write(f"   سکتور اصلی: {stats_data['master_sector']}")
                    self.stdout.write(f"   سکتورهای پشتیبان: {stats_data['backup_sectors']}")
                    
                    self.stdout.write("\n🔍 وضعیت سکتورها:")
                    for sector, status in stats_data['sector_status'].items():
                        status_icon = "✅" if status['status'] == 'valid' else "❌"
                        self.stdout.write(f"   سکتور {sector}: {status_icon} {status['status']} ({status['size']} بایت)")
        
        # تعمیر در صورت نیاز
        if repair and not result['valid']:
            self.stdout.write("\n🔧 تلاش برای تعمیر...")
            usb_drives = dongle_manager.find_usb_drives()
            if usb_drives:
                device = usb_drives[0]['device_id']
                repair_success, repair_message = dongle_manager.repair_dongle_sectors(device)
                if repair_success:
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ تعمیر موفق: {repair_message}")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ تعمیر ناموفق: {repair_message}")
                    )
            else:
                self.stdout.write(
                    self.style.ERROR("❌ هیچ USB برای تعمیر یافت نشد")
                )
        
        # لاگ نتیجه
        if result['valid']:
            logger.info(f"اعتبارسنجی روزانه موفق: {result['message']}")
        else:
            logger.warning(f"اعتبارسنجی روزانه ناموفق: {result['message']}")
        
        self.stdout.write(
            self.style.SUCCESS("اعتبارسنجی روزانه تکمیل شد")
        )
