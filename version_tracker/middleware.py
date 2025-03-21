import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .models import AppVersion
logger = logging.getLogger(__name__)
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .models import AppVersion
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class VersionTrackerMiddleware(MiddlewareMixin):
    """میان‌افزار بررسی تغییرات کد (غیرفعال‌شده، فقط برای دیباگ استفاده می‌شود)"""

    def process_request(self, request):
        """
        درخواست را بدون بررسی تغییرات پردازش می‌کند.

        Args:
            request: درخواست HTTP دریافت‌شده
        """
        if settings.DEBUG:
            logger.debug("درخواست در حال پردازش است: %s", request.path)
        return None

    """برای ارسال کدها بصورت خودکار کار میکرد"""
# class VersionTrackerMiddleware(MiddlewareMixin):
#     """میان‌افزار بررسی تغییرات کد در هر درخواست"""
#     def process_request(self, request):
#         """بررسی تغییرات قبل از پردازش درخواست"""
#         # فعال‌سازی میان‌افزار فقط در محیط توسعه
#         if not settings.DEBUG:
#             return
#         try:
#             updates = AppVersion.check_and_update_versions()
#             if updates:
#                 logger.info("🔄 تغییرات نسخه شناسایی شد:")
#                 for app_name, new_version in updates.items():
#                     print("🔄 تغییرات نسخه شناسایی شد:", f"  • {app_name}: نسخه {new_version}")
#                     logger.info(f"  • {app_name}: نسخه {new_version}")
#         except Exception as e:
#             logger.error(f"خطا در بررسی تغییرات نسخه: {str(e)}", exc_info=True)