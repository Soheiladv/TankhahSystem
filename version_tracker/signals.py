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
    if 'version_tracker_appversion' in connection.introspection.table_names():
        logger.info("Calling update_versions command...")
        call_command('update_versions')
    else:
        logger.warning("جدول AppVersion هنوز ایجاد نشده است.")
<<<<<<< HEAD
=======
#
# @receiver(post_migrate)
# def update_versions(sender, **kwargs):
#     message = "ارسال مهاجرت برای: post migrate triggered for version_tracker"
#     # logger.info(f"🚀 {message} 🚀")
#     print(f"{message}🚀  {sender.name} 🚀"  ) # "👍📩  ارسال مهاجرت برای :👍📩 post migrate triggered for{sender.name}
#     if sender.name == 'version_tracker':
#         return
#     from django.db import connection
#     if 'version_tracker_appversion' in connection.introspection.table_names():
#         print("فراخوانی آپدیت Calling update_versions command...")
#         call_command('update_versions')
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
