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

class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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