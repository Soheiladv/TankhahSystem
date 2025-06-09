"""
برای تشخیص دقیق‌تر خروج کاربر، می‌توانید از یک مکانیزم Heartbeat با استفاده از JavaScript استفاده کنید. در این روش، یک اسکریپت JavaScript به صورت دوره‌ای (مثلاً هر دقیقه) یک درخواست AJAX به سرور ارسال می‌کند. اگر سرور برای مدتی مشخص (مثلاً دو برابر بازه زمانی ارسال درخواست) هیچ درخواستی از کاربر دریافت نکند، به این نتیجه می‌رسد که کاربر از سیستم خارج شده است و سشن او را از جدول ActiveUser حذف می‌کند.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import logging
logger = logging.getLogger(__name__)
@login_required
def heartbeat_view(request):
    # logger.info(f"Heartbeat request - User: {request.user}, Session: {request.session.session_key}")
    request.session.modified = True  # Refresh the session
    return HttpResponse("OK")