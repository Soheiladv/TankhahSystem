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
from tankhah.models import Tankhah, FactorItem, create_budget_transaction, Factor, ApprovalLog
# فعال‌سازی سیگنال برای تأیید چندامضایی
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Tankhah, TankhahAction
from core.models import AccessRule, Post, WorkflowStage

logger = logging.getLogger('tankhah.signals')
#///////////////////////////////////////////////////////////////////
from django.db.models.signals import pre_save
from django.dispatch import receiver
from tankhah.models import Tankhah, ApprovalLog
from accounts.middleware import get_current_user


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
                ApprovalLog.objects.create(
                    tankhah=instance,
                    action='STATUS_CHANGE',
                    user=user,
                    comment=f"تغییر وضعیت از {old_instance.status} به {instance.status}",
                    stage=instance.current_stage,
                    post=user.userpost_set.filter(is_active=True, end_date__isnull=True).first().post if user else None
                )
        except Tankhah.DoesNotExist:
            logger.error(f"تنخواه با pk={instance.pk} یافت نشد")
        except Exception as e:
            logger.error(f"خطا در سیگنال log_tanbakh_changes: {e}", exc_info=True)
#///////////////////////////////////////////////////////////////////

@receiver(post_save, sender=FactorItem)
def handle_factor_item_budget_transaction(sender, instance, created, **kwargs):
    if created and instance.status not in ['APPROVED', 'PAID']:
        return  # برای آیتم‌های جدید با وضعیت غیرتأیید، تراکنش ثبت نمی‌شود
    try:
        original_status = None
        if not created:
            original_status = FactorItem.objects.get(pk=instance.pk).status
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

@receiver([post_save, post_delete], sender=FactorItem)
def update_factor_and_tankhah(sender, instance, **kwargs):
    try:
        factor = instance.factor
        tankhah = factor.tankhah
        # محاسبه مبلغ فاکتور
        new_factor_amount = factor.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        if factor.amount != new_factor_amount:
            factor.amount = new_factor_amount
            factor.save(update_fields=['amount'])

        # فقط اگر فاکتور تأیید شده باشد، spent را به‌روزرسانی کن
        if factor.status == 'APPROVED':
            old_spent = tankhah.spent
            new_spent = tankhah.factors.filter(status='APPROVED').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            if old_spent != new_spent:
                tankhah.spent = new_spent
                tankhah.save(update_fields=['spent'])
                logger.info(f"Updated spent for Tankhah {tankhah.number}: {new_spent}")
    except Exception as e:
        logger.error(f"Error updating factor/tankhah for FactorItem {instance.pk}: {e}", exc_info=True)

@receiver(post_save, sender=Factor)
def log_factor_changes(sender, instance, created, **kwargs):
    """عملکرد: این سیگنال پس از ذخیره یا ایجاد فاکتور (Factor) اجرا می‌شود. اگر فاکتور جدید باشد، ایجاد آن لاگ می‌شود. اگر فاکتور موجود ویرایش شود، تغییرات فیلدها در لاگ ثبت می‌شوند.
    تأثیر: اگر در فرآیند ثبت تنخواه فاکتوری ایجاد یا ویرایش شود، این سیگنال آن را لاگ می‌کند. اما در TankhahCreateView هیچ اشاره‌ای به ایجاد یا ویرایش فاکتور نیست، بنابراین این سیگنال احتمالاً در مرحله ثبت اولیه تنخواه اجرا نمی‌شود.
    """
    user = getattr(instance, '_changed_by', None)  # کاربر تغییر دهنده
    if created:
        logger.info(f"فاکتور جدید ایجاد شد: {instance.number} توسط {user or 'ناشناس'}")
    else:
        changes = instance._meta.fields  # تغییرات را بررسی کنید
        for field in changes:
            field_name = field.name
            old_value = getattr(instance, f'_old_{field_name}', None)
            new_value = getattr(instance, field_name)
            if old_value != new_value:
                logger.info(
                    f"تغییر در فاکتور {instance.number}: {field_name} از {old_value} به {new_value} توسط {user or 'ناشناس'}")


@receiver(post_save, sender=ApprovalLog)
def lock_factor_after_approval(sender, instance, **kwargs):
    """
    عملکرد: این سیگنال پس از ثبت یک ApprovalLog اجرا می‌شود. اگر اقدام (action) تأیید (APPROVE) باشد و فاکتور (factor) وجود داشته باشد، فاکتور قفل می‌شود (locked = True).
    """
    if instance.action == 'APPROVE' and instance.factor:
        instance.factor.locked = True
        instance.factor.save()

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

    current_stage = instance.tankhah.current_stage
    if not current_stage or not current_stage.triggers_payment_order:
        logger.debug(f"Stage {current_stage.name if current_stage else 'None'} does not trigger PaymentOrder.")
        return

    access_rule = AccessRule.objects.filter(
        organization=instance.tankhah.organization,
        stage=current_stage,
        action_type='APPROVE',
        entity_type='FACTOR',
        is_active=True
    ).order_by('-min_level').first()

    if not access_rule:
        logger.warning(f"No AccessRule found for Factor {instance.number}")
        return

    approval_log = ApprovalLog.objects.filter(
        factor=instance,
        action='APPROVE',
        stage=current_stage,
        post__level__gte=access_rule.min_level
    ).exists()

    if not approval_log:
        logger.debug(f"No valid ApprovalLog found for Factor {instance.number}.")
        return

    try:
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
            initial_stage = WorkflowStage.objects.filter(
                entity_type='PAYMENTORDER',
                order=1,
                is_active=True
            ).first()
            if not initial_stage:
                logger.error(f"No valid initial WorkflowStage found for PaymentOrder.")
                raise ValueError(_("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))

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
                current_stage=initial_stage,
                issue_date=timezone.now().date(),
                order_number=f"PO-{instance.tankhah.number}-{int(timezone.now().timestamp())}"
            )
            payment_order.related_factors.add(instance)

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
                stage=initial_stage,
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
                    stage=initial_stage,
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
                        from_email='system@example.com',
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

    except Exception as e:
        logger.error(f"Error creating PaymentOrder for Factor {instance.number}: {e}", exc_info=True)
        from django.contrib import messages
        messages.error(getattr(instance, '_request', None), _(f"خطا در ایجاد دستور پرداخت: {str(e)}"))