# version_control/signals.py
from django.dispatch import receiver
from django.core.management import call_command
from django.db.models.signals import post_migrate
import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

@receiver(post_migrate)
def update_versions(sender, **kwargs):
    logger.info(f"🚀 post_migrate triggered for {sender.name} 🚀")
    if sender.name == 'version_tracker':
        return
    from django.db import connection
    # بررسی وجود جدول در دیتابیس اصلی (نه لاگ)
    if connection.alias == 'default' and 'version_tracker_appversion' in connection.introspection.table_names():
        logger.info("Calling update_versions command...")
        call_command('update_versions')
    else:
        logger.warning("جدول AppVersion هنوز ایجاد نشده است یا در دیتابیس لاگ است.")
