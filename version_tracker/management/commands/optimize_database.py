"""
دستور بهینه‌سازی دیتابیس version_tracker
"""
from django.core.management.base import BaseCommand
from django.db import connection, models
from version_tracker.models import AppVersion, FileHash, CodeChangeLog
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'بهینه‌سازی دیتابیس version_tracker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='تحلیل حجم دیتابیس و ارائه گزارش'
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help='اجرای بهینه‌سازی دیتابیس'
        )

    def handle(self, *args, **options):
        if options['analyze']:
            self.analyze_database()
        
        if options['optimize']:
            self.optimize_database()

    def analyze_database(self):
        """تحلیل حجم دیتابیس"""
        self.stdout.write("تحلیل حجم دیتابیس version_tracker...")
        
        with connection.cursor() as cursor:
            # حجم جداول
            cursor.execute("""
                SELECT 
                    table_name,
                    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
                    table_rows
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name IN ('version_tracker_appversion', 'version_tracker_filehash', 'version_tracker_codechangelog', 'version_tracker_finalversion')
                ORDER BY (data_length + index_length) DESC
            """)
            
            self.stdout.write("\nحجم جداول:")
            self.stdout.write("-" * 60)
            for row in cursor.fetchall():
                self.stdout.write(f"{row[0]:<30} {row[1]:<10} MB {row[2]:<10} رکورد")
        
        # آمار مدل‌ها
        self.stdout.write("\nآمار مدل‌ها:")
        self.stdout.write("-" * 40)
        self.stdout.write(f"AppVersion: {AppVersion.objects.count()}")
        self.stdout.write(f"FileHash: {FileHash.objects.count()}")
        self.stdout.write(f"CodeChangeLog: {CodeChangeLog.objects.count()}")
        
        # بزرگترین فایل‌ها
        largest_files = FileHash.objects.values('file_path').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        self.stdout.write("\nبیشترین فایل‌های تغییر یافته:")
        self.stdout.write("-" * 50)
        for item in largest_files:
            self.stdout.write(f"{item['file_path']}: {item['count']} تغییر")

    def optimize_database(self):
        """بهینه‌سازی دیتابیس"""
        self.stdout.write("شروع بهینه‌سازی دیتابیس...")
        
        with connection.cursor() as cursor:
            # بهینه‌سازی جداول
            tables = [
                'version_tracker_appversion',
                'version_tracker_filehash', 
                'version_tracker_codechangelog',
                'version_tracker_finalversion'
            ]
            
            for table in tables:
                self.stdout.write(f"بهینه‌سازی جدول {table}...")
                cursor.execute(f"OPTIMIZE TABLE {table}")
                self.stdout.write(self.style.SUCCESS(f"جدول {table} بهینه شد"))
            
            # ایجاد ایندکس‌های مفید (MySQL syntax)
            indexes = [
                "CREATE INDEX idx_filehash_timestamp ON version_tracker_filehash(timestamp)",
                "CREATE INDEX idx_codechangelog_date ON version_tracker_codechangelog(change_date)",
                "CREATE INDEX idx_appversion_release ON version_tracker_appversion(release_date)",
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(self.style.SUCCESS("ایندکس ایجاد شد"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"خطا در ایجاد ایندکس: {e}"))
        
        self.stdout.write(self.style.SUCCESS("بهینه‌سازی دیتابیس تکمیل شد!"))
