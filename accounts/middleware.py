# accounts/middleware.py
import logging

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import ActiveUser, AuditLog  # مدل‌ها باید توی accounts/models.py باشن
from django.contrib.sessions.models import Session
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
        from django.conf import settings
        login_path = settings.LOGIN_URL
        if request.path == login_path and request.method == 'POST':
            if request.user.is_authenticated:
                # احترام به تنظیمات سیستم برای تک‌سشنی بودن
                try:
                    from core.models import SystemSettings
                    if not SystemSettings.get_solo().enforce_single_browser_session:
                        return redirect('/')
                except Exception:
                    pass
                # در صورت وجود چند رکورد، جدیدترین را نگه دار و بقیه را حذف کن
                user_sessions = list(ActiveUser.objects.filter(user=request.user).order_by('-last_activity'))
                existing_session = user_sessions[0] if user_sessions else None
                for extra in user_sessions[1:]:
                    if extra.session_key:
                        Session.objects.filter(session_key=extra.session_key).delete()
                    extra.delete()
                if existing_session:  # اگه سشن قبلی وجود داره
                    if existing_session.session_key != session_key:
                        # پایان اجباری سشن قبلی و جایگزینی با سشن فعلی
                        if existing_session.session_key:
                            Session.objects.filter(session_key=existing_session.session_key).delete()
                        # پیام هشدار به کاربر و ثبت لاگ
                        messages.warning(request, f"اتصال قبلی شما از IP {existing_session.user_ip} در زمان {existing_session.login_time.strftime('%Y/%m/%d %H:%M:%S')} خاتمه یافت و با اتصال فعلی جایگزین شد.")
                        try:
                            AuditLog.objects.create(
                                user=request.user,
                                action='update',
                                model_name='Session',
                                details=f"Session replaced. Old IP: {existing_session.user_ip}",
                                ip_address=user_ip,
                                browser=user_agent,
                                status_code=200,
                                related_object='SingleSessionEnforced'
                            )
                        except Exception:
                            pass
                        existing_session.session_key = session_key
                        existing_session.login_time = timezone.now()
                        existing_session.last_activity = timezone.now()
                        existing_session.user_ip = user_ip
                        existing_session.user_agent = user_agent
                        existing_session.is_active = True
                        existing_session.logout_time = None
                        existing_session.save(update_fields=['session_key','login_time','last_activity','user_ip','user_agent','is_active','logout_time'])
                        logger.info(f"سشن قبلی کاربر {request.user.username} خاتمه یافت و با سشن جدید جایگزین شد")
                        return redirect('/')
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

        # به‌روزرسانی فعالیت کاربر و تضمین تک‌سشنی بودن
        if request.user.is_authenticated and session_key:
            # احترام به تنظیمات سیستم برای تک‌سشنی بودن
            try:
                from core.models import SystemSettings
                if not SystemSettings.get_solo().enforce_single_browser_session:
                    return self.get_response(request)
            except Exception:
                pass
            # رفع رکوردهای اضافی احتمالی
            user_sessions = list(ActiveUser.objects.filter(user=request.user).order_by('-last_activity'))
            active_user = user_sessions[0] if user_sessions else None
            for extra in user_sessions[1:]:
                if extra.session_key:
                    Session.objects.filter(session_key=extra.session_key).delete()
                extra.delete()
            if active_user:
                if active_user.session_key != session_key:
                    # پایان اجباری سشن قبلی و جایگزینی با سشن فعلی بدون نیاز به تأیید کاربر
                    if active_user.session_key:
                        Session.objects.filter(session_key=active_user.session_key).delete()
                    # پیام هشدار به کاربر و ثبت لاگ
                    messages.warning(request, f"اتصال قبلی شما از IP {active_user.user_ip} در زمان {active_user.login_time.strftime('%Y/%m/%d %H:%M:%S')} خاتمه یافت و با اتصال فعلی جایگزین شد.")
                    try:
                        AuditLog.objects.create(
                            user=request.user,
                            action='update',
                            model_name='Session',
                            details=f"Session replaced during request. Old IP: {active_user.user_ip}",
                            ip_address=user_ip,
                            browser=user_agent,
                            status_code=200,
                            related_object='SingleSessionEnforced'
                        )
                    except Exception:
                        pass
                    active_user.session_key = session_key
                    active_user.login_time = timezone.now()
                    active_user.last_activity = timezone.now()
                    active_user.user_ip = user_ip
                    active_user.user_agent = user_agent
                    active_user.is_active = True
                    active_user.logout_time = None
                    active_user.save(update_fields=['session_key','login_time','last_activity','user_ip','user_agent','is_active','logout_time'])
                    logger.info(f"سشن قبلی کاربر {request.user.username} خاتمه یافت و با سشن جدید جایگزین شد (حین درخواست)")
                    # ادامه پردازش درخواست با سشن جدید
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