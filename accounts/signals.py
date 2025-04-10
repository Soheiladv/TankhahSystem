# # signals.py in your accounts app
#
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model
# from .models import CustomProfile, CustomUser, City
#
# User = get_user_model()
# # signals.py
# from django.db.models.signals import pre_save, post_save, post_delete
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model
# from .models import AuditLog
#
# # @receiver(pre_save)
# # def store_old_values(sender, instance, **kwargs):
# #     if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
# #         return
# #
# #     if instance.pk:  # فقط برای به‌روزرسانی‌ها
# #         try:
# #             old_instance = sender.objects.get(pk=instance.pk)
# #             instance._old_values = {field.name: getattr(old_instance, field.name) for field in instance._meta.fields}
# #         except sender.DoesNotExist:
# #             instance._old_values = {}
#
# @receiver(pre_save)
# def store_old_values(sender, instance, **kwargs):
#     if not hasattr(instance, '_old_values'):
#         try:
#             old_instance = sender.objects.get(pk=instance.pk)
#             instance._old_values = {}
#             for field in instance._meta.fields:
#                 try:
#                     instance._old_values[field.name] = getattr(old_instance, field.name, None)
#                 except Exception:
#                     instance._old_values[field.name] = None
#         except sender.DoesNotExist:
#             instance._old_values = {}
#
#
# @receiver(post_save)
# def log_create_update(sender, instance, created, **kwargs):
#     if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
#         return
#
#     action = 'create' if created else 'update'
#     user = getattr(instance, 'user', None)  # اگر مدل شما فیلد user دارد
#
#     # ثبت تغییرات برای فیلدهای به‌روزرسانی شده
#     changes = {}
#     if action == 'update' and hasattr(instance, '_old_values'):
#         for field in instance._meta.fields:
#             old_value = instance._old_values.get(field.name, None)  # مقدار قدیمی
#             new_value = getattr(instance, field.name)  # مقدار جدید
#             if old_value != new_value:
#                 changes[field.name] = {
#                     'old_value': str(old_value) if old_value is not None else "-",
#                     'new_value': str(new_value) if new_value is not None else "-",
#                 }
#
#     # ثبت لاگ
#     AuditLog.objects.create(
#         user=user,
#         action=action,
#         model_name=sender.__name__,
#         object_id=instance.pk,
#         details=f"{action.capitalize()}d {sender.__name__} with id {instance.pk}",
#         changes=changes if changes else {"-": {"old_value": "-", "new_value": "-"}},  # مقدار پیش‌فرض برای تغییرات
#         related_object=str(instance) if str(instance) else "-"  # مقدار پیش‌فرض برای شیء مرتبط
#     )
#
# @receiver(post_delete)
# def log_delete(sender, instance, **kwargs):
#     if sender.__name__ == "AuditLog":  # جلوگیری از لاگ‌گیری خود لاگ‌ها
#         return
#
#     user = getattr(instance, 'user', None)  # اگر مدل شما فیلد user دارد
#     AuditLog.objects.create(
#         user=user,
#         action='delete',
#         model_name=sender.__name__,
#         object_id=instance.pk,
#         details=f"Deleted {sender.__name__} with id {instance.pk}",
#         related_object=str(instance)  # ذخیره نام شیء مرتبط
#     )
#
#
#
# #############################################
# from django.contrib.auth.signals import user_logged_in
# from django.dispatch import receiver
# from accounts.models import ActiveUser
# from django.utils.timezone import now  # اضافه کردن import برای now
# import logging
#
# logger = logging.getLogger(__name__)
#
# @receiver(user_logged_in)
# def create_active_user(sender, user, request, **kwargs):
#     """
#     سیگنالی که هنگام لاگین کاربر اجرا می‌شود و یک رکورد ActiveUser ایجاد یا به‌روزرسانی می‌کند.
#     """
#     # گرفتن کلید سشن از درخواست
#     session_key = request.session.session_key
#     if not session_key:  # اگه session_key تولید نشده باشه
#         request.session.create()
#         session_key = request.session.session_key
#
#     # گرفتن آی‌پی کاربر
#     user_ip = request.META.get('REMOTE_ADDR', None)
#     # گرفتن اطلاعات مرورگر
#     user_agent = request.META.get('HTTP_USER_AGENT', '')
#
#     # لاگ ورود
#     logger.info(f"تلاش برای ثبت کاربر فعال: {user.username} با سشن {session_key}")
#
#     # پیدا کردن یا آپدیت ردیف موجود برای این کاربر
#     try:
#         active_user = ActiveUser.objects.get(user=user)
#         # آپدیت ردیف موجود
#         active_user.session_key = session_key
#         active_user.login_time = now()
#         active_user.last_activity = now()
#         active_user.user_ip = user_ip
#         active_user.user_agent = user_agent
#         active_user.is_active = True
#         active_user.logout_time = None
#         active_user.save()
#         logger.info(f"رکورد ActiveUser برای {user.username} به‌روزرسانی شد.")
#     except ActiveUser.DoesNotExist:
#         # اگه ردیفی وجود نداشت، یه ردیف جدید بساز
#         ActiveUser.objects.create(
#             user=user,
#             session_key=session_key,
#             login_time=now(),
#             last_activity=now(),
#             user_ip=user_ip,
#             user_agent=user_agent,
#             is_active=True,
#             logout_time=None
#         )
#         logger.info(f"رکورد ActiveUser برای {user.username} ایجاد شد.")
#
#     # پاک کردن سشن‌های قدیمی (اختیاری)
#     from django.contrib.sessions.models import Session
#     Session.objects.filter(expire_date__lt=now()).delete()
#
# #############################################
# from django import template
# import jdatetime
# from datetime import datetime
# register = template.Library()
# @register.filter
# def to_jalali(value, format='%Y/%m/%d %H:%M:%S'):
#     if value:
#         # تبدیل تاریخ میلادی به جلالی
#         jalali_date = jdatetime.datetime.fromgregorian(datetime=value)
#         return jalali_date.strftime(format)  # فرمت تاریخ جلالی
#     return value
# ##########################################
#
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.conf import settings
# from .models import CustomProfile
# @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         CustomProfile.objects.create(user=instance)
#
# # @receiver(post_save, sender=settings.AUTH_USER_MODEL)
# # def save_user_profile(sender, instance, **kwargs):
# #     instance.profile.save()
