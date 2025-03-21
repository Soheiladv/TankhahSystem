# middleware.py
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from .models import ActiveUser

class AuditLogMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        self.logs_to_create = []  # لیست موقت برای ذخیره لاگ‌ها

    def process_request(self, request):
        # ذخیره اطلاعات درخواست در request برای استفاده در process_response
        request._audit_log_info = {
            'user': request.user if not isinstance(request.user, AnonymousUser) else None,
            'method': request.method,
            'path': request.path,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'browser': request.META.get('HTTP_USER_AGENT', ''),
        }

    def process_response(self, request, response):
        # بررسی آیا اطلاعات درخواست ذخیره شده است
        if not hasattr(request, '_audit_log_info'):
            return response

        # فیلتر کردن درخواست‌های غیرضروری
        if self._should_skip_logging(request):
            return response

        try:
            # تشخیص عملیات CRUD بر اساس متد HTTP
            action = self._get_action_from_method(request.method)

            # ایجاد شیء لاگ و اضافه کردن به لیست موقت
            self._add_log_to_batch(request, response, action)

            # ثبت دسته‌ای لاگ‌ها (هر ۱۰۰ لاگ)
            if len(self.logs_to_create) >= 100:
                self._bulk_create_logs()
        except Exception as e:
            # لاگ خطا بدون مختل کردن درخواست اصلی
            logger.error(f"Error logging audit: {e}")

        return response

    def __del__(self):
        # ثبت لاگ‌های باقی‌مانده قبل از تخریب شیء
        if self.logs_to_create:
            self._bulk_create_logs()

    def _should_skip_logging(self, request):
        """بررسی آیا درخواست باید لاگ‌گیری شود یا خیر"""
        return request.path.startswith('/static/') or request.path.startswith('/media/')

    def _get_action_from_method(self, method):
        """تبدیل متد HTTP به عملیات CRUD"""
        method_to_action = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        return method_to_action.get(method, 'read')

    def _add_log_to_batch(self, request, response, action):
        """اضافه کردن لاگ به لیست موقت"""
        log = AuditLog(
            user=request._audit_log_info['user'],
            action=action,
            model_name='HTTP Request',
            details=f"{request.method} {request.path}",
            ip_address=request._audit_log_info['ip_address'],
            browser=request._audit_log_info['browser'],
            status_code=response.status_code,
        )
        self.logs_to_create.append(log)

    def _bulk_create_logs(self):
        """ثبت دسته‌ای لاگ‌ها"""
        try:
            AuditLog.objects.bulk_create(self.logs_to_create)
            self.logs_to_create = []  # پاک کردن لیست پس از ثبت
        except Exception as e:
            logger.error(f"Error logging remaining audits: {e}")

"""
بررسی Session User  و کاربران فعال 
"""
class ActiveUserMiddleware(MiddlewareMixin):
    """
       میدلویر برای مدیریت کاربران فعال، جلوگیری از لاگین بیش از حد مجاز،
       حذف کاربران غیرفعال و پاک‌سازی سشن‌های منقضی شده.
       """

    def __init__(self, get_response):
        self.get_response = get_response

    def get_client_ip(self, request):
        """استخراج آی‌پی کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # logger.info(f"x_forwarded_for  😉😉😉: ",x_forwarded_for.split(',')[0])
            return x_forwarded_for.split(',')[0]
        # logger.info(f"REMOTE_ADDR 😉😉😉: ",request.META.get('REMOTE_ADDR', ''))
        return request.META.get('REMOTE_ADDR', '')

    def __call__(self, request):
        # قبل از پردازش درخواست
        ActiveUser.remove_inactive_users()
        ActiveUser.delete_expired_sessions()  # جدید
        response = self.get_response(request)

        # Get the session key
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        user_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        # Handle user login
        if request.path == reverse('accounts:login') and request.method == 'POST':
            if request.user.is_authenticated:
                if not ActiveUser.can_login(session_key):
                    messages.error(request, "تعداد کاربران فعال از حد مجاز بیشتر است.")
                    # logger.warning(
                    #     f"Login blocked: Too many active users ({ActiveUser.objects.count()}) for session: {session_key}")
                    return redirect('accounts:login')

                if not ActiveUser.objects.filter(session_key=session_key).exists():
                    ActiveUser.objects.create(
                        user=request.user,
                        session_key=session_key,
                        last_activity=timezone.now(),
                        user_ip=user_ip,
                        user_agent=user_agent
                    )
                    # logger.info(
                    #     f"User {request.user.username} logged in with session {session_key}. Active users: {ActiveUser.objects.count()}")

        # Handle user logout
        # **مدیریت خروج کاربران**
        if request.path == reverse('accounts:logout') and request.method == 'POST':
            if request.user.is_authenticated:
                # حذف تمام سشن‌های کاربر فعلی
                active_users = ActiveUser.objects.filter(user=request.user)
                if active_users.exists():
                    for active_user in active_users:
                        # logger.info(
                        #     f"User {active_user.user.username} logged out from session {active_user.session_key}...")
                        active_user.delete()
                else:
                    logger.warning(f"No active session found for user {request.user.username} during logout.")
                # پاک کردن سشن از سیستم جنگو
            request.session.flush()  # جدید
            from django.contrib import auth
            auth.logout(request)  # جدید
        # Update activity and clean up inactive users
        # **به‌روزرسانی فعالیت کاربر**
        if request.user.is_authenticated:
            try:
                active_user = ActiveUser.objects.get(session_key=session_key, user=request.user)
                active_user.last_activity = timezone.now()
                active_user.save()
            except ActiveUser.DoesNotExist:
                if not ActiveUser.objects.filter(session_key=session_key).exists() and ActiveUser.can_login(
                        session_key):
                    ActiveUser.objects.create(
                        user=request.user,
                        session_key=session_key,
                        last_activity=timezone.now(),
                        user_ip=user_ip,
                        user_agent=user_agent
                    )
                    # logger.info(
                    #     f"Created missed ActiveUser {request.user.username} with session {session_key}. Active users: {ActiveUser.objects.count()}")

        # Cleanup inactive users
        ActiveUser.remove_inactive_users()

        if response is None:
            # logger.error(f"Response is None for request {request.path}")
            return redirect('accounts:login')

        return response

#################
"""
    کلاس برای مدیریت کاربر فعال جاری.
"""
from threading import current_thread
class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_thread()._request = request
        response = self.get_response(request)
        return response

