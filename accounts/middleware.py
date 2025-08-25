<<<<<<< HEAD
# accounts/middleware.py
import logging

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import ActiveUser, AuditLog  # مدل‌ها باید توی accounts/models.py باشن
from django.contrib.auth import logout as auth_logout  # ایمپورت مستقیم تابع logout


logger = logging.getLogger(__name__)

class ActiveUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_active and not request.user.is_superuser:
            # اگه این شرط باشه و is_active=False باشه، سوپریوزر هم رد می‌شه
            raise PermissionDenied("کاربر غیرفعاله")

        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        ActiveUser.remove_inactive_users()
        ActiveUser.delete_expired_sessions()

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        user_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        logger.info(f"درخواست به: {request.path}, کاربر: {request.user}")

        # ریدایرکت کاربر لاگین‌نکرده
        if request.path != reverse('accounts:login') and not request.user.is_authenticated:
            logger.info(f"کاربر لاگین نکرده - ریدایرکت به accounts:login")
            return redirect('accounts:login')

        # مدیریت لاگین
        if request.path == reverse('accounts:login') and request.method == 'POST':
            if request.user.is_authenticated:
                existing_session = ActiveUser.objects.filter(user=request.user).first()
                if existing_session:  # اگه سشن قبلی وجود داره
                    if existing_session.session_key != session_key:
                        messages.warning(
                            request,
                            f"شما قبلاً با IP {existing_session.user_ip} در تاریخ "
                            f"{existing_session.login_time.strftime('%Y/%m/%d %H:%M:%S')} وارد سیستم شدید. "
                            f"برای ورود با این دستگاه، باید سشن قبلی قطع بشه. آیا موافقید؟ "
                            f"<a href='{reverse('accounts:terminate_session', args=[existing_session.id])}'>بله، قطع کن</a>"
                        )
                        logger.info(f"کاربر {request.user.username} سشن فعال قبلی داره: {existing_session.session_key}")
                        return redirect('accounts:login')
                    # اگه سشن همونه، فقط آپدیت کن
                    existing_session.last_activity = timezone.now()
                    existing_session.user_ip = user_ip
                    existing_session.user_agent = user_agent
                    existing_session.save()
                    logger.info(f"سشن موجود برای {request.user.username} آپدیت شد: {session_key}")
                    return redirect('/')
                else:  # اگه سشن قبلی نیست
                    if not ActiveUser.can_login(session_key):
                        messages.error(request, "تعداد کاربران فعال از حد مجاز بیشتر است.")
                        logger.info(f"ریدایرکت به accounts:login - تعداد کاربران بیش از حد: {session_key}")
                        return redirect('accounts:login')
                    # ثبت سشن جدید
                    ActiveUser.objects.create(
                        user=request.user,
                        session_key=session_key,
                        last_activity=timezone.now(),
                        user_ip=user_ip,
                        user_agent=user_agent
                    )
                    logger.info(f"کاربر فعال ثبت شد: {request.user.username} با سشن {session_key}")
                    return redirect('/')

        # مدیریت لاگ‌اوت
        if request.path == reverse('accounts:logout') and request.method == 'POST':
            if request.user.is_authenticated:
                ActiveUser.objects.filter(user=request.user).delete()
                request.session.flush()
                auth_logout(request)
                logger.info(f"کاربر {request.user.username} خارج شد")
                return redirect('accounts:login')

        # به‌روزرسانی فعالیت کاربر
        if request.user.is_authenticated and session_key:
            active_user = ActiveUser.objects.filter(user=request.user).first()
            if active_user:
                if active_user.session_key != session_key:
                    messages.warning(
                        request,
                        f"شما قبلاً با IP {active_user.user_ip} در تاریخ "
                        f"{active_user.login_time.strftime('%Y/%m/%d %H:%M:%S')} وارد سیستم شدید. "
                        f"برای ادامه با این دستگاه، باید سشن قبلی قطع بشه. آیا موافقید؟ "
                        f"<a href='{reverse('accounts:terminate_session', args=[active_user.id])}'>بله، قطع کن</a>"
                    )
                    logger.info(f"کاربر {request.user.username} سشن فعال قبلی داره: {active_user.session_key}")
                    auth_logout(request)  # کاربر رو لاگ‌اوت می‌کنیم تا مجبور بشه دوباره لاگین کنه
                    return redirect('accounts:login')
                active_user.last_activity = timezone.now()
                active_user.user_ip = user_ip
                active_user.user_agent = user_agent
                active_user.save()

        response = self.get_response(request)
        logger.info(f"پاسخ برای {request.path} - کد وضعیت: {response.status_code}")
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR', '')

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logs_to_create = []

    def __call__(self, request):
        request._audit_log_info = {
            'user': request.user if request.user.is_authenticated else None,
            'method': request.method,
            'path': request.path,
            'ip_address': self.get_client_ip(request),
            'browser': request.META.get('HTTP_USER_AGENT', ''),
        }

        response = self.get_response(request)

        if not hasattr(request, '_audit_log_info') or self._should_skip_logging(request):
            return response
        action = self._get_action_from_method(request.method)
=======
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
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
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
<<<<<<< HEAD
        if len(self.logs_to_create) >= 100:
            AuditLog.objects.bulk_create(self.logs_to_create)
            self.logs_to_create = []
        return response

    def _should_skip_logging(self, request):
        return request.path.startswith('/static/') or request.path.startswith('/media/')

    def _get_action_from_method(self, method):
        return {'GET': 'read', 'POST': 'create', 'PUT': 'update', 'PATCH': 'update', 'DELETE': 'delete'}.get(method, 'read')

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR', '')

=======

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
>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
<<<<<<< HEAD
        from threading import current_thread
        current_thread()._request = request
        return self.get_response(request)


# accounts/middleware.py
from threading import local

_request_locals = local()

class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request_locals.request = request
        response = self.get_response(request)
        return response

def get_current_request():
    return getattr(_request_locals, 'request', None)

def get_current_user():
    request = get_current_request()
    return request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None
=======
        current_thread()._request = request
        response = self.get_response(request)
        return response

>>>>>>> 171b55a74efe3adb976919af53d3bd582bb2266e
