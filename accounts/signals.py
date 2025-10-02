from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.utils.timezone import now
from django.contrib.sessions.models import Session
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def enforce_single_session_on_login(sender, request, user, **kwargs):
    """Ensure only one active session per user and sync ActiveUser record."""
    try:
        if not request.session.session_key:
            request.session.create()
        current_session_key = request.session.session_key

        user_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        from .models import ActiveUser
        other_entries = ActiveUser.objects.filter(user=user).exclude(session_key=current_session_key)
        for entry in other_entries:
            if entry.session_key:
                Session.objects.filter(session_key=entry.session_key).delete()
            entry.delete()

        active_entry, created = ActiveUser.objects.get_or_create(user=user, defaults={
            'session_key': current_session_key,
            'login_time': now(),
            'last_activity': now(),
            'user_ip': user_ip,
            'user_agent': user_agent,
            'is_active': True,
            'logout_time': None,
        })
        if not created:
            active_entry.session_key = current_session_key
            active_entry.login_time = now()
            active_entry.last_activity = now()
            active_entry.user_ip = user_ip
            active_entry.user_agent = user_agent
            active_entry.is_active = True
            active_entry.logout_time = None
            active_entry.save(update_fields=['session_key','login_time','last_activity','user_ip','user_agent','is_active','logout_time'])

        Session.objects.filter(expire_date__lt=now()).delete()
        logger.info(f"Single-session enforced for user={user.username}, session={current_session_key}")
        # ثبت لاگ ورود موفق
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                user=user,
                action='create',
                model_name='Session',
                details=f"User logged in. Session={current_session_key}",
                ip_address=user_ip,
                browser=user_agent,
                status_code=200,
                related_object='Login'
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"enforce_single_session_on_login failed for user={getattr(user,'username',None)}: {e}")


# Ensure a CustomProfile is created whenever a new user is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile_on_user_create(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from .models import CustomProfile
        CustomProfile.objects.get_or_create(user=instance)
    except Exception as exc:
        logger.error(f"Failed to ensure profile for user id={getattr(instance, 'id', None)}: {exc}")
