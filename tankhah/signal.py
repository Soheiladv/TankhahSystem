from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
import logging
from decimal import Decimal

from django.db.models import Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from notifications.signals import notify
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser
from budgets.models import PaymentOrder
from tankhah.models import Tankhah, FactorItem, create_budget_transaction, Factor, ApprovalLog, FactorHistory
# فعال‌سازی سیگنال برای تأیید چندامضایی
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tankhah, TankhahAction
from core.models import AccessRule, Post, WorkflowStage
from django.db.models.signals import pre_save
from django.dispatch import receiver
from tankhah.models import Tankhah, ApprovalLog
from accounts.middleware import get_current_user
from .utils import get_factor_current_stage

logger = logging.getLogger('tankhah.signals')
#///////////////////////////////////////////////////////////////////
@receiver(pre_save, sender=Tankhah)
def log_tanbakh_changes(sender, instance, **kwargs):
    """
    ثبت تغییرات وضعیت تنخواه در ApprovalLog
    """
    if instance.pk:
        try:
            old_instance = Tankhah.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                user = getattr(instance, '_changed_by', None) or get_current_user()
                if not user:
                    logger.warning("کاربر تغییر‌دهنده یافت نشد، لاگ ثبت نمی‌شود")
                    return
                content_type = ContentType.objects.get_for_model(Tankhah)
                stage_order = get_factor_current_stage(None)  # برای تنخواه، stage_order از AccessRule
                ApprovalLog.objects.create(
                    tankhah=instance,
                    action='STATUS_CHANGE',
                    user=user,
                    comment=f"تغییر وضعیت از {old_instance.status} به {instance.status}",
                    stage_order=stage_order,
                    post=user.userpost_set.filter(is_active=True, end_date__isnull=True).first().post if user else None,
                    content_type=content_type,
                    object_id=instance.id
                )
        except Tankhah.DoesNotExist:
            logger.error(f"تنخواه با pk={instance.pk} یافت نشد")
        except Exception as e:
            logger.error(f"خطا در سیگنال log_tanbakh_changes: {e}", exc_info=True)


#///////////////////////////////////////////////////////////////////
@receiver(post_save, sender=FactorItem)
def handle_factor_item_budget_transaction(sender, instance, created, **kwargs):
    if created and instance.status not in ['APPROVED', 'PAID']:
        return
    try:
        original_status = None
        if not created:
            original = FactorItem.objects.get(pk=instance.pk)
            original_status = original.status  # اصلاح
        if instance.status != original_status:
            logger.info(f"FactorItem {instance.pk} status changed from {original_status} to {instance.status}")
            allocation = instance.factor.tankhah.budget_allocation
            if instance.status in ['APPROVED', 'PAID']:
                create_budget_transaction(
                    allocation=allocation,
                    transaction_type='CONSUMPTION',
                    amount=instance.amount,
                    related_obj=instance,
                    created_by=instance.factor.created_by,
                    description=f"مصرف بودجه برای ردیف فاکتور {instance.factor.number} (pk:{instance.pk})",
                    transaction_id=f"TX-FAC-ITEM-{instance.factor.number}-{instance.pk}-{timezone.now().timestamp()}"
                )
            elif instance.status == 'REJECTED' and original_status in ['APPROVED', 'PAID']:
                create_budget_transaction(
                    allocation=allocation,
                    transaction_type='RETURN',
                    amount=instance.amount,
                    related_obj=instance,
                    created_by=instance.factor.created_by,
                    description=f"بازگشت بودجه به دلیل رد ردیف فاکتور {instance.factor.number} (pk:{instance.pk})",
                    transaction_id=f"TX-FAC-ITEM-RET-{instance.factor.number}-{instance.pk}-{timezone.now().timestamp()}"
                )
    except Exception as e:
        logger.error(f"Error in FactorItem budget transaction signal: {e}", exc_info=True)

"""به جای به‌روزرسانی در FactorItem.save، از سیگنال یا متد ویو استفاده کنید:"""
from django.db.models.signals import post_save, post_delete
# @receiver([post_save, post_delete], sender=FactorItem)
# def update_factor_and_tankhah(sender, instance, **kwargs):
#     try:
#         factor = instance.factor
#         factor.amount = factor.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         factor.save(update_fields=['amount'])
#         tankhah = factor.tankhah
#         from budgets.budget_calculations import get_tankhah_remaining_budget
#         tankhah.remaining_budget = get_tankhah_remaining_budget(tankhah)
#         tankhah.save(update_fields=['remaining_budget'])
#     except Exception as e:
#         logger.error(f"Error updating factor/tankhah for FactorItem (Signal Tankhah) {instance.pk}: {e}", exc_info=True)

@receiver(post_save, sender=FactorItem)
def update_factor_and_tankhah(sender, instance, **kwargs):
    factor = instance.factor
    tankhah = factor.tankhah

    new_spent = sum(
        item.amount for item in FactorItem.objects.filter(factor__tankhah=tankhah, status='APPROVED')
        if item.amount is not None
    )

    try:
        # از تابع get_tankhah_total_budget برای دریافت بودجه کل تنخواه استفاده کنید
        from budgets.budget_calculations import get_tankhah_total_budget
        total_tankhah_budget = get_tankhah_total_budget(tankhah)

        # محاسبه بودجه باقی‌مانده و به‌روزرسانی فیلد remaining_budget
        # (فرض می‌شود remaining_budget یک فیلد موجود در مدل Tankhah است)
        tankhah.remaining_budget = total_tankhah_budget - new_spent
        tankhah.save(update_fields=['remaining_budget'])
        logger.info(f"[Signal] بودجه باقی‌مانده تنخواه {tankhah.number} به {tankhah.remaining_budget} به‌روزرسانی شد")
    except AttributeError as e:
        logger.error(f"[Signal] خطای ویژگی: {e}. مطمئن شوید 'remaining_budget' یک فیلد در مدل Tankhah است.")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی بودجه تنخواه برای FactorItem (Signal Tankhah) {instance.pk}: {e}", exc_info=True)


@receiver(post_save, sender=Factor)
def log_factor_changes(sender, instance, created, **kwargs):
    """
    ثبت تغییرات فاکتور در FactorHistory
    """
    user = getattr(instance, '_request_user', instance.created_by)
    if not user:
        logger.warning(f"No user provided for FactorHistory of Factor {instance.number}")
        user = CustomUser.objects.filter(username='system').first() or instance.created_by

    if created:
        FactorHistory.objects.create(
            factor=instance,
            change_type=FactorHistory.ChangeType.CREATION,
            changed_by=user,
            description=f"فاکتور به شماره {instance.number} توسط {user.username} ایجاد شد."
        )
    else:
        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(instance, f'_original_{field_name}', None)
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                FactorHistory.objects.create(
                    factor=instance,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=user,
                    old_data={field_name: str(old_value)},
                    new_data={field_name: str(new_value)},
                    description=f"تغییر در فاکتور {instance.number}: {field_name} از {old_value} به {new_value} توسط {user.username}"
                )

@receiver(post_save, sender=ApprovalLog)
def lock_factor_after_approval(sender, instance, **kwargs):
    """
    عملکرد: این سیگنال پس از ثبت یک ApprovalLog اجرا می‌شود. اگر اقدام (action) تأیید (APPROVE) باشد و فاکتور (factor) وجود داشته باشد، فاکتور قفل می‌شود (locked = True).
    """
    if (
            instance.action == 'APPROVED'
            and instance.factor
            and instance.stage.is_final_stage
            and instance.factor.status == 'APPROVED'
            and getattr(instance, '_final_approve', False)
    ):
        instance.factor.locked = True
        instance.factor.save(update_fields=['locked'])
        logger.info(f"Factor {instance.factor.number} locked after final approval by user {instance.user.username}")
    else:
        logger.debug(
            f"Factor {instance.factor.number} not locked: "
            f"action={instance.action}, "
            f"is_final_stage={instance.stage.is_final_stage}, "
            f"factor_status={instance.factor.status}, "
            f"final_approve={getattr(instance, '_final_approve', False)}"
        )


def send_notification_to_post_users__(post, action):
    from accounts.models import CustomUser
    users = CustomUser.objects.filter(
        userpost__post=post, is_active=True
    ).distinct()
    message = f"دستور پرداخت جدید (ID: {action.id}) برای امضا در انتظار شماست."
    from budgets.budget_calculations import send_notification
    send_notification(action, 'PENDING_SIGNATURE', message, users)
# or
def send_notification_to_post_users(post, payment_order):

    from accounts.models import CustomUser
    users = CustomUser.objects.filter(
        userpost__post=post, userpost__is_active=True
    ).distinct()
    message = f"دستور پرداخت جدید ({payment_order.order_number}) برای امضا در انتظار شماست."
    from notifications.signals import notify
    notify.send(
        sender=None,
        recipient=users,
        verb='pending_signature',
        action_object=payment_order,
        description=message
    )

@receiver(post_save, sender=PaymentOrder)
def start_approval_process(sender, instance, created, **kwargs):
    if created and instance.action_type == 'ISSUE_PAYMENT_ORDER':
        logger.info(f"Starting approval process for PaymentOrder {instance.id}")
        required_posts = AccessRule.objects.filter(
            organization=instance.tankhah.organization,
            stage=instance.stage,
            action_type='SIGN_PAYMENT',
            entity_type='PAYMENTORDER',
            is_active=True
        ).select_related('post')

        if not required_posts.exists():
            logger.warning(f"No approval rules found for TankhahAction {instance.id}")
            return

        for rule in required_posts:
            ApprovalLog.objects.create(
                action=instance,
                approver_post=rule.post,
                status = 'PENDING'
            )
            # اینجا می‌تونی نوتیفیکیشن به کاربران دارای پست مربوطه بفرستی
            send_notification_to_post_users(rule.post, instance)
            logger.info(f"Created ActionApproval for post {rule.post.name} on TankhahAction {instance.id}")


@receiver(post_save, sender=Factor)
def start_payment_order_process(sender, instance, **kwargs):
    if instance.status != 'APPROVED':
        logger.debug(f"Factor {instance.number} is not APPROVED, skipping PaymentOrder creation.")
        return

    try:
        # بررسی قفل بودن دوره بودجه
        budget_allocation = instance.tankhah.project_budget_allocation
        if budget_allocation:
            is_locked, lock_reason = budget_allocation.budget_period.is_locked
            if is_locked:
                logger.warning(f"Cannot create PaymentOrder for Factor {instance.number}: {lock_reason}")
                return

        # دریافت مرحله فعلی از تنخواه
        current_stage_order = instance.tankhah.current_stage.stage_order if instance.tankhah.current_stage else 1
        logger.debug(f"[start_payment_order_process] Current stage_order: {current_stage_order}")

        # بررسی AccessRule برای مرحله تأیید
        access_rule = AccessRule.objects.filter(
            organization=instance.tankhah.organization,
            action_type='APPROVED',
            entity_type='FACTOR',
            is_active=True,
            stage_order=current_stage_order
        ).order_by('-min_level').first()

        if not access_rule:
            logger.warning(f"No AccessRule found for Factor {instance.number} at stage {current_stage_order}")
            return

        # بررسی وجود ApprovalLog
        approval_log = ApprovalLog.objects.filter(
            factor=instance,
            action='APPROVED',
            stage_order=current_stage_order,
            post__level__gte=access_rule.min_level
        ).exists()

        if not approval_log:
            logger.debug(f"No valid ApprovalLog found for Factor {instance.number}.")
            return

        with transaction.atomic():
            # بررسی بودجه تنخواه و پروژه
            tankhah_remaining = instance.tankhah.budget - instance.tankhah.spent
            project_remaining = instance.tankhah.project.budget - instance.tankhah.project.spent if instance.tankhah.project else Decimal('0')
            if instance.amount > tankhah_remaining or (instance.tankhah.project and instance.amount > project_remaining):
                logger.error(f"Insufficient budget for Factor {instance.number}: Tankhah remaining={tankhah_remaining}, Project remaining={project_remaining}")
                raise ValueError(_("بودجه کافی برای تنخواه یا پروژه وجود ندارد."))

            # تعیین گیرنده پرداخت
            payee = instance.tankhah.payee or instance.tankhah.organization.payees.first()
            if not payee:
                logger.error(f"No payee found for Tankhah {instance.tankhah.number}.")
                raise ValueError(_("گیرنده پرداخت یافت نشد."))

            # محاسبه مبلغ دقیق
            amount = instance.items.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or instance.amount

            # تعیین مرحله اولیه دستور پرداخت
            initial_rule = AccessRule.objects.filter(
                entity_type='PAYMENTORDER',
                action_type='SIGN_PAYMENT',
                stage_order=1,
                is_active=True,
                organization=instance.tankhah.organization
            ).first()
            if not initial_rule:
                logger.error(f"No valid initial AccessRule found for PaymentOrder.")
                raise ValueError(_("مرحله اولیه برای دستور پرداخت تعریف نشده است."))

            # ایجاد دستور پرداخت
            created_by = instance.approved_by.last() or instance.created_by
            user_post = created_by.userpost_set.filter(is_active=True).first()
            payment_order = PaymentOrder.objects.create(
                tankhah=instance.tankhah,
                amount=amount,
                payee=payee,
                description=f"پرداخت فاکتور {instance.number}",
                created_by=created_by,
                created_by_post=user_post.post if user_post else None,
                organization=instance.tankhah.organization,
                project=instance.tankhah.project,
                status='PENDING_APPROVAL',
                min_signatures=access_rule.min_signatures or 2,
                stage_order=initial_rule.stage_order,
                issue_date=timezone.now().date(),
                order_number=f"PO-{instance.tankhah.number}-{int(timezone.now().timestamp())}"
            )
            payment_order.related_factors.add(instance)
            payment_order._request = getattr(instance, '_request', None)
            payment_order.save()

            # ثبت تراکنش بودجه
            create_budget_transaction(
                allocation=instance.tankhah.project_budget_allocation,
                transaction_type='CONSUMPTION',
                amount=amount,
                related_obj=payment_order,
                created_by=created_by,
                description=f"پرداخت دستور {payment_order.order_number} برای فاکتور {instance.number}",
                transaction_id=f"TX-PO-{payment_order.order_number}-{int(timezone.now().timestamp())}"
            )

            # ثبت لاگ‌های امضا
            required_posts = AccessRule.objects.filter(
                organization=instance.tankhah.organization,
                stage_order=initial_rule.stage_order,
                action_type='SIGN_PAYMENT',
                entity_type='PAYMENTORDER',
                is_active=True
            ).select_related('post')

            content_type = ContentType.objects.get_for_model(PaymentOrder)
            for rule in required_posts:
                ApprovalLog.objects.create(
                    tankhah=instance.tankhah,
                    content_type=content_type,
                    object_id=payment_order.id,
                    action='PENDING_SIGNATURE',
                    stage_order=initial_rule.stage_order,
                    post=rule.post,
                    comment=f"نیاز به امضای {rule.post.name} برای دستور پرداخت {payment_order.order_number}"
                )

                # ارسال اعلان به پست‌های مجاز
                users = CustomUser.objects.filter(
                    userpost__post=rule.post,
                    userpost__is_active=True,
                    userpost__post__organization=instance.tankhah.organization
                ).distinct()
                for user in users:
                    notify.send(
                        sender=created_by,
                        recipient=user,
                        verb='pending_signature',
                        action_object=payment_order,
                        description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} نیاز به امضای شما دارد.",
                        level='HIGH'
                    )
                    send_mail(
                        subject=f"دستور پرداخت جدید: {payment_order.order_number}",
                        message=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} نیاز به امضای شما دارد.",
                        from_email='soheiladv@gmail.com',
                        recipient_list=[user.email],
                        fail_silently=True
                    )

            # اعلان به خزانه‌دار
            treasurer_users = CustomUser.objects.filter(
                userpost__post__name='خزانه‌دار',
                userpost__is_active=True,
                userpost__post__organization=instance.tankhah.organization
            ).distinct()
            for user in treasurer_users:
                notify.send(
                    sender=created_by,
                    recipient=user,
                    verb='payment_order_created',
                    action_object=payment_order,
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} ایجاد شد.",
                    level='HIGH'
                )
                send_mail(
                    subject=f"دستور پرداخت جدید: {payment_order.order_number}",
                    message=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} ایجاد شد و در انتظار تأیید است.",
                    from_email='system@example.com',
                    recipient_list=[user.email],
                    fail_silently=True
                )

            logger.info(f"PaymentOrder {payment_order.order_number} created for Factor {instance.number}")

            # به‌روزرسانی وضعیت قفل بودجه
            if budget_allocation:
                budget_allocation.budget_period.update_lock_status()
                status, message = budget_allocation.budget_period.check_budget_status_no_save()
                if status in ['warning', 'locked', 'completed']:
                    budget_allocation.budget_period.send_notification(status, message)

    except Exception as e:
        logger.error(f"Error creating PaymentOrder for Factor {instance.number}: {e}", exc_info=True)
        if hasattr(instance, '_request') and instance._request:
            messages.error(instance._request, _(f"خطا در ایجاد دستور پرداخت: {str(e)}"))
