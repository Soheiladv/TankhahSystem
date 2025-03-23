# signals.py in your accounts app

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import CustomProfile, CustomUser, City

User = get_user_model()
# signals.py
# signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AuditLog

# @receiver(pre_save)
# def store_old_values(sender, instance, **kwargs):
#     if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
#         return
#
#     if instance.pk:  # فقط برای به‌روزرسانی‌ها
#         try:
#             old_instance = sender.objects.get(pk=instance.pk)
#             instance._old_values = {field.name: getattr(old_instance, field.name) for field in instance._meta.fields}
#         except sender.DoesNotExist:
#             instance._old_values = {}

@receiver(pre_save)
def store_old_values(sender, instance, **kwargs):
    if not hasattr(instance, '_old_values'):
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_values = {}
            for field in instance._meta.fields:
                try:
                    instance._old_values[field.name] = getattr(old_instance, field.name, None)
                except Exception:
                    instance._old_values[field.name] = None
        except sender.DoesNotExist:
            instance._old_values = {}


@receiver(post_save)

def log_create_update(sender, instance, created, **kwargs):
    if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
        return

    action = 'create' if created else 'update'
    user = getattr(instance, 'user', None)  # اگر مدل شما فیلد user دارد

    # ثبت تغییرات برای فیلدهای به‌روزرسانی شده
    changes = {}
    if action == 'update' and hasattr(instance, '_old_values'):
        for field in instance._meta.fields:
            old_value = instance._old_values.get(field.name, None)  # مقدار قدیمی
            new_value = getattr(instance, field.name)  # مقدار جدید
            if old_value != new_value:
                changes[field.name] = {
                    'old_value': str(old_value) if old_value is not None else "-",
                    'new_value': str(new_value) if new_value is not None else "-",
                }

    # ثبت لاگ
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=sender.__name__,
        object_id=instance.pk,
        details=f"{action.capitalize()}d {sender.__name__} with id {instance.pk}",
        changes=changes if changes else {"-": {"old_value": "-", "new_value": "-"}},  # مقدار پیش‌فرض برای تغییرات
        related_object=str(instance) if str(instance) else "-"  # مقدار پیش‌فرض برای شیء مرتبط
    )

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
        return

    user = getattr(instance, 'user', None)  # اگر مدل شما فیلد user دارد
    AuditLog.objects.create(
        user=user,
        action='delete',
        model_name=sender.__name__,
        object_id=instance.pk,
        details=f"Deleted {sender.__name__} with id {instance.pk}",
        related_object=str(instance)  # ذخیره نام شیء مرتبط
    )



#############################################
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from accounts.models import ActiveUser
from django.utils.timezone import now  # اضافه کردن import برای now
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def create_active_user(sender, user, request, **kwargs):
    """
    سیگنالی که هنگام لاگین کاربر اجرا می‌شود و یک رکورد ActiveUser ایجاد یا به‌روزرسانی می‌کند.
    """
    # گرفتن کلید سشن از درخواست
    session_key = request.session.session_key
    # گرفتن آی‌پی کاربر
    user_ip = request.META.get('REMOTE_ADDR', None)
    # گرفتن اطلاعات مرورگر
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # ایجاد یا به‌روزرسانی رکورد ActiveUser
    ActiveUser.objects.update_or_create(
        user=user,
        session_key=session_key,
        defaults={
            'login_time': now(),
            'last_activity': now(),
            'user_ip': user_ip,
            'user_agent': user_agent,
            'is_active': True,
            'logout_time': None,
        }
    )
    logger.info(f"کاربر فعال ثبت شد: {user.username} با سشن {session_key}")
#############################################
from django import template
import jdatetime
from datetime import datetime
register = template.Library()
@register.filter
def to_jalali(value, format='%Y/%m/%d %H:%M:%S'):
    if value:
        # تبدیل تاریخ میلادی به جلالی
        jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
        return jalali_date.strftime(format)  # فرمت تاریخ جلالی
    return value
##########################################
