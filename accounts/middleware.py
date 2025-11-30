# accounts/middleware.py
import logging
from threading import local

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import ActiveUser, AuditLog

logger = logging.getLogger(__name__)

_request_locals = local()


class ActiveUserMiddleware:
    """
    Middleware to enforce single-session (optional), track active users and sessions,
    and record basic session-related audit logs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # دریافت IP و User-Agent در ابتدای درخواست تا در تمام کد قابل استفاده باشد
        user_ip = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # بررسی کاربر غیرفعال
        if request.user.is_authenticated and not request.user.is_active and not request.user.is_superuser:
            raise PermissionDenied("کاربر غیرفعاله")

        # از لاگ‌کردن یا پردازش مسیرهای استاتیک صرف‌نظر کن
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)

        # پاکسازی رکوردهای غیرفعال و سشن‌های منقضی
        try:
            ActiveUser.remove_inactive_users()
            ActiveUser.delete_expired_sessions()
        except Exception as e:
            logger.exception("خطا هنگام پاکسازی کاربران غیرفعال یا سشن‌ها: %s", e)

        session_key = request.session.session_key
        # اگر سشن کلید ندارد، سشن جدید ایجاد کن
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

            # اگر کاربر لاگین است، باید رکورد ActiveUser را مدیریت کنیم
            if request.user.is_authenticated:
                # در صورت وجود تنظیمات سیستم، تک‌سشنی بودن را رعایت کن
                try:
                    from core.models import SystemSettings
                    if not SystemSettings.get_solo().enforce_single_browser_session:
                        return redirect('/')
                except Exception:
                    # اگر مدل یا تنظیمات در دسترس نبود، ادامه بده
                    pass

                # حذف رکوردهای اضافی کاربر و نگهداری جدیدترین رکورد
                try:
                    user_sessions = list(ActiveUser.objects.filter(user=request.user).order_by('-last_activity'))
                except Exception as e:
                    user_sessions = []
                    logger.exception("خطا هنگام واکشی ActiveUserها: %s", e)

                existing_session = user_sessions[0] if user_sessions else None
                for extra in user_sessions[1:]:
                    try:
                        if extra.session_key:
                            Session.objects.filter(session_key=extra.session_key).delete()
                        extra.delete()
                    except Exception:
                        logger.exception("خطا هنگام حذف سشن اضافی برای کاربر %s", request.user.username)

                if existing_session:
                    # اگر سشن قدیمی وجود دارد و با سشن فعلی فرق دارد، آن را جایگزین کن
                    if existing_session.session_key != session_key:
                        try:
                            if existing_session.session_key:
                                Session.objects.filter(session_key=existing_session.session_key).delete()
                        except Exception:
                            logger.exception("خطا هنگام حذف سشن قدیمی")

                        messages.warning(
                            request,
                            f"اتصال قبلی شما از IP {existing_session.user_ip} در زمان "
                            f"{existing_session.login_time.strftime('%Y/%m/%d %H:%M:%S')} خاتمه یافت و با اتصال فعلی جایگزین شد."
                        )
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
                            logger.exception("خطا هنگام ثبت AuditLog برای جایگزینی سشن")

                        # بروزرسانی رکورد موجود
                        try:
                            existing_session.session_key = session_key
                            existing_session.login_time = timezone.now()
                            existing_session.last_activity = timezone.now()
                            existing_session.user_ip = user_ip
                            existing_session.user_agent = user_agent
                            existing_session.is_active = True
                            existing_session.logout_time = None
                            existing_session.save(update_fields=[
                                'session_key', 'login_time', 'last_activity', 'user_ip', 'user_agent', 'is_active', 'logout_time'
                            ])
                            logger.info(f"سشن قبلی کاربر {request.user.username} خاتمه یافت و با سشن جدید جایگزین شد")
                        except Exception:
                            logger.exception("خطا هنگام به‌روزرسانی existing_session")
                        return redirect('/')

                    # اگر سشن همان سشن است، فقط آپدیت کن و ادامه بده
                    try:
                        existing_session.last_activity = timezone.now()
                        existing_session.user_ip = user_ip
                        existing_session.user_agent = user_agent
                        existing_session.save()
                        logger.info(f"سشن موجود برای {request.user.username} آپدیت شد: {session_key}")
                    except Exception:
                        logger.exception("خطا هنگام آپدیت existing_session")
                    return redirect('/')
                else:
                    # اگر سشن قبلی وجود ندارد، بررسی کن که امکان لاگین هست یا نه
                    try:
                        if not ActiveUser.can_login(session_key):
                            messages.error(request, "تعداد کاربران فعال از حد مجاز بیشتر است.")
                            logger.info(f"ریدایرکت به accounts:login - تعداد کاربران بیش از حد: {session_key}")
                            return redirect('accounts:login')
                    except Exception:
                        logger.exception("خطا هنگام بررسی محدودیت لاگین")

                    # ثبت سشن جدید
                    try:
                        ActiveUser.objects.create(
                            user=request.user,
                            session_key=session_key,
                            last_activity=timezone.now(),
                            user_ip=user_ip,
                            user_agent=user_agent
                        )
                        logger.info(f"کاربر فعال ثبت شد: {request.user.username} با سشن {session_key}")
                    except Exception:
                        logger.exception("خطا هنگام ایجاد ActiveUser جدید")
                    return redirect('/')

        # مدیریت لاگ‌اوت
        if request.path == reverse('accounts:logout') and request.method == 'POST':
            if request.user.is_authenticated:
                try:
                    ActiveUser.objects.filter(user=request.user).delete()
                    request.session.flush()
                    auth_logout(request)
                    logger.info(f"کاربر {request.user.username} خارج شد")
                except Exception:
                    logger.exception("خطا هنگام لاگ‌اوت کاربر")
                return redirect('accounts:login')

        # به‌روزرسانی فعالیت کاربر و تضمین تک‌سشنی بودن برای درخواست‌های بعدی
        if request.user.is_authenticated and session_key:
            try:
                from core.models import SystemSettings
                if not SystemSettings.get_solo().enforce_single_browser_session:
                    return self.get_response(request)
            except Exception:
                pass

            try:
                user_sessions = list(ActiveUser.objects.filter(user=request.user).order_by('-last_activity'))
            except Exception:
                user_sessions = []
                logger.exception("خطا هنگام واکشی ActiveUserها برای به‌روزرسانی")

            active_user = user_sessions[0] if user_sessions else None
            for extra in user_sessions[1:]:
                try:
                    if extra.session_key:
                        Session.objects.filter(session_key=extra.session_key).delete()
                    extra.delete()
                except Exception:
                    logger.exception("خطا هنگام حذف رکورد اضافی active_user")

            if active_user:
                if active_user.session_key != session_key:
                    try:
                        if active_user.session_key:
                            Session.objects.filter(session_key=active_user.session_key).delete()
                    except Exception:
                        logger.exception("خطا هنگام حذف سشن قبلی active_user")

                    messages.warning(
                        request,
                        f"اتصال قبلی شما از IP {active_user.user_ip} در زمان "
                        f"{active_user.login_time.strftime('%Y/%m/%d %H:%M:%S')} خاتمه یافت و با اتصال فعلی جایگزین شد."
                    )
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
                        logger.exception("خطا هنگام ثبت AuditLog برای جایگزینی سشن در حین درخواست")

                    try:
                        active_user.session_key = session_key
                        active_user.login_time = timezone.now()
                        active_user.last_activity = timezone.now()
                        active_user.user_ip = user_ip
                        active_user.user_agent = user_agent
                        active_user.is_active = True
                        active_user.logout_time = None
                        active_user.save(update_fields=[
                            'session_key', 'login_time', 'last_activity', 'user_ip', 'user_agent', 'is_active', 'logout_time'
                        ])
                        logger.info(f"سشن قبلی کاربر {request.user.username} خاتمه یافت و با سشن جدید جایگزین شد (حین درخواست)")
                    except Exception:
                        logger.exception("خطا هنگام به‌روزرسانی active_user")
                else:
                    try:
                        active_user.last_activity = timezone.now()
                        active_user.user_ip = user_ip
                        active_user.user_agent = user_agent
                        active_user.save()
                    except Exception:
                        logger.exception("خطا هنگام آپدیت last_activity برای active_user")

        # ادامه پردازش درخواست
        response = self.get_response(request)
        try:
            logger.info(f"پاسخ برای {request.path} - کد وضعیت: {response.status_code}")
        except Exception:
            logger.exception("خطا هنگام لاگ کردن پاسخ")
        return response

    def get_client_ip(self, request):
        """
        استخراج IP کلاینت؛ اگر پشت پروکسی هستیم ابتدا X-Forwarded-For را بررسی کن.
        """
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                # X-Forwarded-For ممکن است لیستی از IP ها باشد؛ اولی IP اصلی است
                return x_forwarded_for.split(',')[0].strip()
            return request.META.get('REMOTE_ADDR', '')
        except Exception:
            return ''


class AuditLogMiddleware:
    """
    Middleware برای ثبت لاگ‌های درخواست HTTP به صورت جمع‌شونده و ذخیره دوره‌ای.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.logs_to_create = []

    def __call__(self, request):
        request._audit_log_info = {
            'user': request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            'method': request.method,
            'path': request.path,
            'ip_address': self.get_client_ip(request),
            'browser': request.META.get('HTTP_USER_AGENT', ''),
        }

        response = self.get_response(request)

        if not hasattr(request, '_audit_log_info') or self._should_skip_logging(request):
            return response

        action = self._get_action_from_method(request.method)
        try:
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
        except Exception:
            logger.exception("خطا هنگام ساخت/ذخیره AuditLog درخواست")

        return response

    def _should_skip_logging(self, request):
        return request.path.startswith('/static/') or request.path.startswith('/media/')

    def _get_action_from_method(self, method):
        return {'GET': 'read', 'POST': 'create', 'PUT': 'update', 'PATCH': 'update', 'DELETE': 'delete'}.get(method, 'read')

    def get_client_ip(self, request):
        try:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                return x_forwarded_for.split(',')[0].strip()
            return request.META.get('REMOTE_ADDR', '')
        except Exception:
            return ''


class RequestMiddleware:
    """
    Middleware سبک مبتنی بر threading.local برای دسترسی به درخواست جاری در خارج از view.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            # پاک کردن مرجع درخواست به‌منظور جلوگیری از نشت حافظه در thread-local
            try:
                del _request_locals.request
            except Exception:
                pass
        return response


def get_current_request():
    return getattr(_request_locals, 'request', None)


def get_current_user():
    request = get_current_request()
    return request.user if request and hasattr(request, 'user') and request.user.is_authenticated else None