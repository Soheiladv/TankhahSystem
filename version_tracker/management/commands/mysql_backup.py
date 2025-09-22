from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'ایجاد پشتیبان‌گیری MySQL استاندارد'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            type=str,
            default='both',
            choices=['default', 'logs', 'both'],
            help='دیتابیس مورد نظر برای پشتیبان‌گیری'
        )

    def handle(self, *args, **options):
        database = options['database']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # تنظیمات دیتابیس
        db_configs = {
            'default': {
                'name': settings.DATABASES['default']['NAME'],
                'user': settings.DATABASES['default']['USER'],
                'password': settings.DATABASES['default']['PASSWORD'],
                'host': settings.DATABASES['default']['HOST'],
                'port': settings.DATABASES['default']['PORT'],
            }
        }
        
        # اگر دیتابیس logs موجود است، اضافه کن
        if 'logs' in settings.DATABASES:
            db_configs['logs'] = {
                'name': settings.DATABASES['logs']['NAME'],
                'user': settings.DATABASES['logs']['USER'],
                'password': settings.DATABASES['logs']['PASSWORD'],
                'host': settings.DATABASES['logs']['HOST'],
                'port': settings.DATABASES['logs']['PORT'],
            }
        
        # مسیر backup
        backup_dir = getattr(settings, 'DBBACKUP_STORAGE_OPTIONS', {}).get('location', 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        success_count = 0
        
        if database in ['default', 'both']:
            if self.create_mysql_backup(db_configs['default'], backup_dir, f'main_{timestamp}.sql'):
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'پشتیبان‌گیری دیتابیس اصلی ({db_configs["default"]["name"]}) ایجاد شد')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'خطا در پشتیبان‌گیری دیتابیس اصلی')
                )
        
        if database in ['logs', 'both']:
            if self.create_mysql_backup(db_configs['logs'], backup_dir, f'logs_{timestamp}.sql'):
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'پشتیبان‌گیری دیتابیس لاگ ({db_configs["logs"]["name"]}) ایجاد شد')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'خطا در پشتیبان‌گیری دیتابیس لاگ')
                )
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'تعداد {success_count} پشتیبان‌گیری با موفقیت ایجاد شد')
            )
        else:
            self.stdout.write(
                self.style.ERROR('هیچ پشتیبان‌گیری ایجاد نشد')
            )

    def create_mysql_backup(self, db_config, backup_dir, filename):
        """ایجاد پشتیبان‌گیری MySQL با mysqldump"""
        try:
            # مسیر فایل backup
            backup_file = os.path.join(backup_dir, filename)
            
            # ساخت دستور mysqldump
            cmd = [
                'mysqldump',
                f'--host={db_config["host"]}',
                f'--port={db_config["port"]}',
                f'--user={db_config["user"]}',
                f'--password={db_config["password"]}',
                '--single-transaction',
                '--routines',
                '--triggers',
                '--add-drop-database',
                '--databases',
                db_config['name']
            ]
            
            # اجرای دستور
            with open(backup_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode == 0:
                # فشرده‌سازی فایل
                self.compress_file(backup_file)
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(f'خطا در mysqldump: {result.stderr}')
                )
                return False
                
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('mysqldump یافت نشد. لطفا MySQL client را نصب کنید.')
            )
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطا در ایجاد پشتیبان‌گیری: {str(e)}')
            )
            return False

    def compress_file(self, file_path):
        """فشرده‌سازی فایل با gzip"""
        try:
            import gzip
            import shutil
            
            with open(file_path, 'rb') as f_in:
                with gzip.open(f'{file_path}.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # حذف فایل اصلی و نگه‌داشتن فایل فشرده
            os.remove(file_path)
            os.rename(f'{file_path}.gz', file_path)
            
        except ImportError:
            # اگر gzip موجود نبود، فایل را بدون فشرده‌سازی نگه دار
            pass
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'خطا در فشرده‌سازی: {str(e)}')
            )
