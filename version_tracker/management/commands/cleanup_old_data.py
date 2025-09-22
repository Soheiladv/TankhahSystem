"""
دستور پاکسازی داده‌های قدیمی version_tracker
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from version_tracker.models import AppVersion, FileHash, CodeChangeLog, FinalVersion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'پاکسازی داده‌های قدیمی version_tracker برای کاهش حجم دیتابیس'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='حذف داده‌های قدیمی‌تر از این تعداد روز (پیش‌فرض: 30)'
        )
        parser.add_argument(
            '--keep-versions',
            type=int,
            default=10,
            help='تعداد نسخه‌های اخیر که باید نگه داشته شوند (پیش‌فرض: 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='نمایش داده‌هایی که حذف خواهند شد بدون حذف واقعی'
        )

    def handle(self, *args, **options):
        days = options['days']
        keep_versions = options['keep_versions']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"شروع پاکسازی داده‌های قدیمی‌تر از {days} روز...")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("حالت تست - هیچ داده‌ای حذف نخواهد شد"))
        
        # پاکسازی FileHash های قدیمی
        old_file_hashes = FileHash.objects.filter(timestamp__lt=cutoff_date)
        file_hash_count = old_file_hashes.count()
        
        if file_hash_count > 0:
            self.stdout.write(f"تعداد FileHash های قدیمی: {file_hash_count}")
            if not dry_run:
                old_file_hashes.delete()
                self.stdout.write(self.style.SUCCESS(f"{file_hash_count} FileHash حذف شد"))
        
        # پاکسازی CodeChangeLog های قدیمی
        old_code_changes = CodeChangeLog.objects.filter(change_date__lt=cutoff_date)
        code_change_count = old_code_changes.count()
        
        if code_change_count > 0:
            self.stdout.write(f"تعداد CodeChangeLog های قدیمی: {code_change_count}")
            if not dry_run:
                old_code_changes.delete()
                self.stdout.write(self.style.SUCCESS(f"{code_change_count} CodeChangeLog حذف شد"))
        
        # نگه داشتن فقط آخرین نسخه‌ها
        for app_name in ['core', 'accounts', 'version_tracker']:
            versions = AppVersion.objects.filter(app_name=app_name).order_by('-release_date')
            old_versions_ids = list(versions[keep_versions:].values_list('id', flat=True))
            
            if old_versions_ids:
                old_count = len(old_versions_ids)
                self.stdout.write(f"نسخه‌های قدیمی {app_name}: {old_count}")
                if not dry_run:
                    # حذف FileHash و CodeChangeLog مربوط به نسخه‌های قدیمی
                    FileHash.objects.filter(app_version_id__in=old_versions_ids).delete()
                    CodeChangeLog.objects.filter(version_id__in=old_versions_ids).delete()
                    
                    # حذف نسخه‌های قدیمی
                    AppVersion.objects.filter(id__in=old_versions_ids).delete()
                    self.stdout.write(self.style.SUCCESS(f"{old_count} نسخه قدیمی {app_name} حذف شد"))
        
        # پاکسازی FinalVersion های قدیمی
        old_final_versions = FinalVersion.objects.filter(release_date__lt=cutoff_date)
        final_version_count = old_final_versions.count()
        
        if final_version_count > 0:
            self.stdout.write(f"تعداد FinalVersion های قدیمی: {final_version_count}")
            if not dry_run:
                old_final_versions.delete()
                self.stdout.write(self.style.SUCCESS(f"{final_version_count} FinalVersion حذف شد"))
        
        # نمایش آمار نهایی
        total_file_hashes = FileHash.objects.count()
        total_code_changes = CodeChangeLog.objects.count()
        total_versions = AppVersion.objects.count()
        total_final_versions = FinalVersion.objects.count()
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("آمار نهایی:")
        self.stdout.write(f"FileHash: {total_file_hashes}")
        self.stdout.write(f"CodeChangeLog: {total_code_changes}")
        self.stdout.write(f"AppVersion: {total_versions}")
        self.stdout.write(f"FinalVersion: {total_final_versions}")
        self.stdout.write("="*50)
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS("پاکسازی با موفقیت انجام شد!"))
        else:
            self.stdout.write(self.style.WARNING("برای اجرای واقعی، --dry-run را حذف کنید"))
