import os
import sys
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# تنظیم مسیر پروژه و بارگذاری جنگو
project_path = "D:\\Design & Source Code\\Source Coding\\apartmant"
sys.path.append(project_path)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from django.conf import settings
from django.apps import apps
from version_tracker.models import AppVersion
import threading
import logging

# تنظیم logging به جای print برای ردیابی بهتر
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
sys.stdout.reconfigure(encoding='utf-8')  # اطمینان از نمایش درست فارسی

class VersionWatcher(FileSystemEventHandler):
    def __init__(self):
        self.lock = threading.Lock()
        self.timer = None
        self.debounce_delay = 3  # تأخیر بهینه 3 ثانیه
        self.pending_changes = set()  # اپلیکیشن‌های تغییرکرده
        self.last_processed_time = 0  # زمان آخرین پردازش
        self.min_interval = 5  # حداقل فاصله بین پردازش‌ها (ثانیه)

    def on_modified(self, event):
        # نادیده گرفتن فایل‌های غیرمرتبط
        if event.is_directory or event.src_path.endswith(('.pyc', '.pyo', '.log', '.db', '.sqlite3')):
            return

        # بررسی اپلیکیشن مرتبط
        for app_config in apps.get_app_configs():
            if app_config.path in event.src_path and not AppVersion.should_skip_app(app_config):
                with self.lock:
                    self.pending_changes.add(app_config.name)
                logger.debug(f"تغییر در {app_config.name} شناسایی شد: {event.src_path}")
                self.schedule_check()
                break

    def schedule_check(self):
        """تنظیم تایمر برای پردازش تغییرات"""
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.debounce_delay, self.process_changes)
        self.timer.start()

    def process_changes(self):
        """پردازش تغییرات با کنترل زمان"""
        with self.lock:
            current_time = time.time()
            if not self.pending_changes or (current_time - self.last_processed_time < self.min_interval):
                return

            logger.info(f"پردازش تغییرات برای {len(self.pending_changes)} اپلیکیشن...")
            try:
                AppVersion.check_and_update_versions()
                self.last_processed_time = current_time
                self.pending_changes.clear()
                logger.info("تغییرات با موفقیت پردازش شدند.")
                print("تغییرات با موفقیت پردازش شدند.")
            except Exception as e:
                logger.error(f"خطا در پردازش تغییرات: {str(e)}")
                # print(f"خطا در پردازش تغییرات: {str(e)}")

def start_version_watcher():
    observer = Observer()
    observer.schedule(VersionWatcher(), settings.BASE_DIR, recursive=True)
    observer.start()
    logger.info("ناظر تغییرات نسخه شروع شد...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("ناظر متوقف شد.")
    observer.join()

# if __name__ == "__main__":
#     start_version_watcher()