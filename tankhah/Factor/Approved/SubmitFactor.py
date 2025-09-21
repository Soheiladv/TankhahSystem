from django.views import View
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, ApprovalLog
from core.models import Post, Status
from notificationApp.utils import send_notification
import logging
logger = logging.getLogger('SubmitFactor')
class SubmitFactorForApprovalView(PermissionBaseView, View):
    """
    این ویو مسئول شروع فرآیند گردش کار برای یک فاکتور پیش‌نویس است.
    """
    permission_codenames = ['tankhah.factor_add']  # کاربری که می‌تواند فاکتور اضافه کند، می‌تواند آن را ارسال هم بکند.

    def post(self, request, *args, **kwargs):
        logger.info(f"--- [SUBMIT FACTOR] User '{request.user.username}' is submitting Factor PK: {kwargs['pk']} ---")
        factor = get_object_or_404(Factor, pk=kwargs['pk'])

        # --- مرحله ۱: بررسی‌های دسترسی و وضعیت ---
        # آیا کاربر فعلی، همان ایجادکننده فاکتور است؟
        if factor.created_by != request.user and not request.user.is_superuser:
            logger.warning(
                f"Access DENIED for user '{request.user.username}' to submit factor created by '{factor.created_by.username}'.")
            return HttpResponseForbidden(_("شما فقط می‌توانید فاکتورهایی را که خودتان ایجاد کرده‌اید، ارسال کنید."))

        # آیا فاکتور در وضعیت "پیش‌نویس" است؟
        if factor.status != 'DRAFT':
            logger.warning(f"Attempted to submit a factor that is not in DRAFT status. Current status: {factor.status}")
            messages.error(request, _("این فاکتور قبلاً برای تأیید ارسال شده است."))
            return redirect(factor.get_absolute_url())  # به صفحه جزئیات فاکتور برگرد

        try:
            with transaction.atomic():
                # --- مرحله ۲: شروع گردش کار ---
                tankhah = factor.tankhah

                # پیدا کردن اولین مرحله از گردش کار تعریف شده
                initial_stage = AccessRule.objects.filter(
                    organization=tankhah.organization,
                    entity_type='FACTORITEM'
                ).order_by('stage_order').first()

                if not initial_stage:
                    messages.error(request, _('هیچ گردش کاری برای فاکتور در این سازمان تعریف نشده است.'))
                    return redirect(factor.get_absolute_url())

                # --- مرحله ۳: آپدیت وضعیت و مرحله ---
                factor.status = 'PENDING_APPROVAL'
                factor.save(update_fields=['status'])

                tankhah.current_stage = initial_stage
                tankhah.save(update_fields=['current_stage'])
                logger.info(
                    f"Factor {factor.pk} status updated to PENDING_APPROVAL. Tankhah {tankhah.pk} stage updated to '{initial_stage.stage}'.")

                # --- مرحله ۴: ثبت لاگ و ارسال نوتیفیکیشن ---
                user_post = request.user.userpost_set.filter(is_active=True).first()
                ApprovalLog.objects.create(
                    factor=factor, user=request.user, post=user_post.post if user_post else None,
                    action="SUBMIT",
                    stage_rule=initial_stage,
                    comment=f"فاکتور توسط {request.user.username} برای تأیید ارسال شد."
                )

                # پیدا کردن تمام پست‌های تأییدکننده در مرحله اول
                approver_posts_ids = AccessRule.objects.filter(
                    organization=tankhah.organization,
                    entity_type='FACTORITEM',
                    stage_order=initial_stage.stage_order
                ).values_list('post_id', flat=True).distinct()

                if approver_posts_ids:
                    send_notification(
                        sender=request.user,
                        posts=Post.objects.filter(id__in=approver_posts_ids),
                        verb=_("برای تأیید ارسال شد"),
                        target=factor,
                        description=_(f"فاکتور جدید #{factor.number} برای تأیید شما ارسال شد."),
                        entity_type='FACTOR'
                    )
                    logger.info(
                        f"Notification sent to {len(approver_posts_ids)} post(s) for initial approval of factor {factor.pk}.")
                else:
                    logger.warning(
                        f"No approver posts found for stage order {initial_stage.stage_order} to send notification.")

                messages.success(request, _("فاکتور با موفقیت برای تأیید ارسال شد."))

        except Exception as e:
            logger.error(f"FATAL: Exception during factor submission: {e}", exc_info=True)
            messages.error(request, _("خطایی در هنگام ارسال فاکتور رخ داد."))

        return redirect(factor.get_absolute_url())
