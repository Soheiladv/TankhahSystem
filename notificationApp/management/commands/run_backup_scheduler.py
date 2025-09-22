from django.core.management.base import BaseCommand
from notificationApp.utils import check_and_execute_scheduled_backups
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'اجرای پشتیبان‌گیری‌های زمان‌بندی شده'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schedule-id',
            type=int,
            help='اجرای پشتیبان‌گیری برای اسکچول خاص',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='اجرای تستی بدون انجام عملیات',
        )

    def handle(self, *args, **options):
        schedule_id = options.get('schedule_id')
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write('اجرای تستی - هیچ عملیاتی انجام نخواهد شد')
            return
        
        if schedule_id:
            # اجرای اسکچول خاص
            from notificationApp.utils import execute_scheduled_backup
            self.stdout.write(f'اجرای پشتیبان‌گیری برای اسکچول {schedule_id}...')
            
            success = execute_scheduled_backup(schedule_id)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'پشتیبان‌گیری اسکچول {schedule_id} با موفقیت تکمیل شد')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'پشتیبان‌گیری اسکچول {schedule_id} ناموفق بود')
                )
        else:
            # بررسی و اجرای همه اسکچول‌ها
            self.stdout.write('بررسی پشتیبان‌گیری‌های زمان‌بندی شده...')
            
            try:
                check_and_execute_scheduled_backups()
                self.stdout.write(
                    self.style.SUCCESS('بررسی و اجرای پشتیبان‌گیری‌ها تکمیل شد')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'خطا در اجرای پشتیبان‌گیری‌ها: {str(e)}')
                )
                logger.error(f'خطا در اجرای پشتیبان‌گیری‌ها: {str(e)}')
