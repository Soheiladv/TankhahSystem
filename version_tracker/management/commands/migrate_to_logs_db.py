"""
دستور انتقال داده‌های version_tracker به دیتابیس لاگ
"""
from django.core.management.base import BaseCommand
from django.db import connections
from version_tracker.models import AppVersion, FileHash, CodeChangeLog, FinalVersion
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'انتقال داده‌های version_tracker از دیتابیس اصلی به دیتابیس لاگ'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='نمایش داده‌هایی که منتقل خواهند شد بدون انتقال واقعی'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("حالت تست - هیچ داده‌ای منتقل نخواهد شد"))
        
        # اتصال به دیتابیس‌ها
        default_db = connections['default']
        logs_db = connections['tankhah_logs_db']
        
        try:
            # بررسی وجود جداول در دیتابیس لاگ
            with logs_db.cursor() as cursor:
                cursor.execute("SHOW TABLES LIKE 'version_tracker_%'")
                existing_tables = [row[0] for row in cursor.fetchall()]
                
                if not existing_tables:
                    self.stdout.write("جداول version_tracker در دیتابیس لاگ وجود ندارند")
                    self.stdout.write("ابتدا migration را اجرا کنید:")
                    self.stdout.write("python manage.py migrate version_tracker --database=tankhah_logs_db")
                    return
            
            # انتقال AppVersion
            app_versions = AppVersion.objects.using('default').all()
            self.stdout.write(f"تعداد AppVersion برای انتقال: {app_versions.count()}")
            
            if not dry_run and app_versions.exists():
                # حذف داده‌های موجود در دیتابیس لاگ
                AppVersion.objects.using('tankhah_logs_db').all().delete()
                
                # انتقال داده‌ها
                for version in app_versions:
                    version.pk = None  # برای ایجاد رکورد جدید
                    version.save(using='tankhah_logs_db')
                
                self.stdout.write(self.style.SUCCESS(f"{app_versions.count()} AppVersion منتقل شد"))
            
            # انتقال FileHash
            file_hashes = FileHash.objects.using('default').all()
            self.stdout.write(f"تعداد FileHash برای انتقال: {file_hashes.count()}")
            
            if not dry_run and file_hashes.exists():
                FileHash.objects.using('tankhah_logs_db').all().delete()
                
                for file_hash in file_hashes:
                    file_hash.pk = None
                    file_hash.save(using='tankhah_logs_db')
                
                self.stdout.write(self.style.SUCCESS(f"{file_hashes.count()} FileHash منتقل شد"))
            
            # انتقال CodeChangeLog
            code_changes = CodeChangeLog.objects.using('default').all()
            self.stdout.write(f"تعداد CodeChangeLog برای انتقال: {code_changes.count()}")
            
            if not dry_run and code_changes.exists():
                CodeChangeLog.objects.using('tankhah_logs_db').all().delete()
                
                for code_change in code_changes:
                    code_change.pk = None
                    code_change.save(using='tankhah_logs_db')
                
                self.stdout.write(self.style.SUCCESS(f"{code_changes.count()} CodeChangeLog منتقل شد"))
            
            # انتقال FinalVersion
            final_versions = FinalVersion.objects.using('default').all()
            self.stdout.write(f"تعداد FinalVersion برای انتقال: {final_versions.count()}")
            
            if not dry_run and final_versions.exists():
                FinalVersion.objects.using('tankhah_logs_db').all().delete()
                
                for final_version in final_versions:
                    final_version.pk = None
                    final_version.save(using='tankhah_logs_db')
                
                self.stdout.write(self.style.SUCCESS(f"{final_versions.count()} FinalVersion منتقل شد"))
            
            # نمایش آمار نهایی
            if not dry_run:
                self.stdout.write("\n" + "="*50)
                self.stdout.write("آمار نهایی دیتابیس لاگ:")
                self.stdout.write(f"AppVersion: {AppVersion.objects.using('tankhah_logs_db').count()}")
                self.stdout.write(f"FileHash: {FileHash.objects.using('tankhah_logs_db').count()}")
                self.stdout.write(f"CodeChangeLog: {CodeChangeLog.objects.using('tankhah_logs_db').count()}")
                self.stdout.write(f"FinalVersion: {FinalVersion.objects.using('tankhah_logs_db').count()}")
                self.stdout.write("="*50)
                
                self.stdout.write(self.style.SUCCESS("انتقال داده‌ها با موفقیت انجام شد!"))
            else:
                self.stdout.write(self.style.WARNING("برای اجرای واقعی، --dry-run را حذف کنید"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"خطا در انتقال داده‌ها: {str(e)}"))
            logger.error(f"خطا در انتقال داده‌ها: {str(e)}", exc_info=True)
