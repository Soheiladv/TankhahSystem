from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Sum
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import logging

from accounts.middleware import get_current_user
from accounts.models import CustomUser
from budgets.models import PaymentOrder
from notificationApp.models import Notification, NotificationRule
from notificationApp.views import send_notification
from tankhah.models import Tankhah, FactorItem, Factor, ApprovalLog, FactorHistory, create_budget_transaction
from core.models import AccessRule, Post

from budgets.budget_calculations import get_tankhah_total_budget, get_tankhah_remaining_budget
from .utils import get_factor_current_stage

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from tankhah.models import Tankhah, Factor
from budgets.models import BudgetTransaction


logger = logging.getLogger('tankhah.signals')

# سیگنال برای ثبت تغییرات وضعیت تنخواه
@receiver(pre_save, sender=Tankhah)
def log_tankhah_changes(sender, instance, **kwargs):
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
            logger.error(f"خطا در سیگنال log_tankhah_changes: {e}", exc_info=True)

# سیگنال برای مدیریت تراکنش‌های بودجه در FactorItem
@receiver(post_save, sender=FactorItem)
def handle_factor_item_budget_transaction(sender, instance, created, **kwargs):
    """
    مدیریت تراکنش‌های بودجه برای ردیف‌های فاکتور
    """
    if created and instance.status not in ['APPROVED', 'PAID']:
        return
    try:
        original_status = None
        if not created:
            original = FactorItem.objects.get(pk=instance.pk)
            original_status = original.status
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
        logger.error(f"خطا در سیگنال handle_factor_item_budget_transaction: {e}", exc_info=True)

# سیگنال برای به‌روزرسانی مبلغ فاکتور و بودجه تنخواه
@receiver([post_save, post_delete], sender=FactorItem)
def update_factor_and_tankhah(sender, instance, **kwargs):
    """
    به‌روزرسانی مبلغ فاکتور و بودجه باقی‌مانده تنخواه
    """
    try:
        factor = instance.factor
        tankhah = factor.tankhah

        # محاسبه مجموع مبلغ آیتم‌های تأییدشده
        new_spent = sum(
            item.amount for item in FactorItem.objects.filter(factor__tankhah=tankhah, status='APPROVED')
            if item.amount is not None
        )

        # به‌روزرسانی مبلغ فاکتور
        factor.amount = factor.items.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        factor.save(update_fields=['amount'])

        # به‌روزرسانی بودجه باقی‌مانده تنخواه
        tankhah.remaining_budget = get_tankhah_total_budget(tankhah) - new_spent
        tankhah.save(update_fields=['remaining_budget'])
        logger.info(f"[Signal] بودجه باقی‌مانده تنخواه {tankhah.number} به {tankhah.remaining_budget} به‌روزرسانی شد")
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی فاکتور/تنخواه برای FactorItem {instance.pk}: {e}", exc_info=True)

# سیگنال برای ثبت تغییرات فاکتور در تاریخچه
@receiver(post_save, sender=Factor)
def log_factor_changes(sender, instance, created, **kwargs):
    """
    ثبت تغییرات فاکتور در FactorHistory
    """
    user = getattr(instance, '_request_user', instance.created_by)
    if not user:
        logger.warning(f"کاربر برای FactorHistory فاکتور {instance.number} یافت نشد")
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
                    change_type=FactorHistory.ChangeType.MODIFICATION,
                    changed_by=user,
                    old_data={field_name: str(old_value)},
                    new_data={field_name: str(new_value)},
                    description=f"تغییر در فاکتور {instance.number}: {field_name} از {old_value} به {new_value} توسط {user.username}"
                )

# سیگنال برای قفل کردن فاکتور پس از تأیید نهایی
@receiver(post_save, sender=ApprovalLog)
def lock_factor_after_approval(sender, instance, **kwargs):
    """
    قفل کردن فاکتور پس از تأیید نهایی
    """
    if (
        instance.action == 'APPROVE'
        and instance.factor
        and instance.stage.is_final_stage
        and instance.factor.status == 'APPROVED'
        and getattr(instance, '_final_approve', False)
    ):
        instance.factor.locked = True
        instance.factor.save(update_fields=['locked'])
        logger.info(f"فاکتور {instance.factor.number} پس از تأیید نهایی توسط کاربر {instance.user.username} قفل شد")
    else:
        logger.debug(
            f"فاکتور {instance.factor.number} قفل نشد: "
            f"action={instance.action}, "
            f"is_final_stage={instance.stage.is_final_stage}, "
            f"factor_status={instance.factor.status}, "
            f"final_approve={getattr(instance, '_final_approve', False)}"
        )

# سیگنال برای شروع فرآیند تأیید دستور پرداخت
@receiver(post_save, sender=PaymentOrder)
def start_approval_process(sender, instance, created, **kwargs):
    """
    شروع فرآیند تأیید برای دستور پرداخت جدید
    """
    if created and instance.action_type == 'ISSUE_PAYMENT_ORDER':
        logger.info(f"شروع فرآیند تأیید برای دستور پرداخت {instance.id}")
        required_posts = AccessRule.objects.filter(
            organization=instance.tankhah.organization,
            stage=instance.stage,
            action_type='SIGN_PAYMENT',
            entity_type='PAYMENTORDER',
            is_active=True
        ).select_related('post')

        if not required_posts.exists():
            logger.warning(f"هیچ قانون دسترسی برای دستور پرداخت {instance.id} یافت نشد")
            return

        for rule in required_posts:
            ApprovalLog.objects.create(
                tankhah=instance.tankhah,
                content_type=ContentType.objects.get_for_model(PaymentOrder),
                object_id=instance.id,
                action='PENDING_SIGNATURE',
                stage_order=instance.stage_order,
                post=rule.post,
                comment=f"نیاز به امضای {rule.post.name} برای دستور پرداخت {instance.order_number}"
            )
            # ارسال اعلان به کاربران پست مربوطه
            users = CustomUser.objects.filter(
                userpost__post=rule.post,
                userpost__is_active=True,
                userpost__post__organization=instance.tankhah.organization
            ).distinct()
            send_notification(
                sender=instance.created_by,
                users=users,
                posts=[rule.post],
                verb='PENDING_SIGNATURE',
                description=f"دستور پرداخت {instance.order_number} نیاز به امضای شما دارد.",
                target=instance,
                entity_type='PAYMENTORDER',
                priority='HIGH'
            )
            # ارسال ایمیل
            for user in users:
                send_mail(
                    subject=f"دستور پرداخت جدید: {instance.order_number}",
                    message=f"دستور پرداخت {instance.order_number} نیاز به امضای شما دارد.",
                    from_email='soheiladv@gmail.com',
                    recipient_list=[user.email],
                    fail_silently=True
                )
            logger.info(f"ایجاد ApprovalLog برای پست {rule.post.name} در دستور پرداخت {instance.id}")

# سیگنال برای ایجاد دستور پرداخت پس از تأیید فاکتور
@receiver(post_save, sender=Factor)
def start_payment_order_process(sender, instance, **kwargs):
    """
    ایجاد دستور پرداخت پس از تأیید فاکتور
    """
    if instance.status != 'APPROVED':
        logger.debug(f"فاکتور {instance.number} تأیید نشده است، دستور پرداخت ایجاد نمی‌شود.")
        return

    try:
        # بررسی قفل بودن دوره بودجه
        budget_allocation = instance.tankhah.project_budget_allocation
        if budget_allocation:
            is_locked, lock_reason = budget_allocation.budget_period.is_locked
            if is_locked:
                logger.warning(f"نمی‌توان دستور پرداخت برای فاکتور {instance.number} ایجاد کرد: {lock_reason}")
                return

        # دریافت مرحله فعلی از تنخواه
        current_stage_order = instance.tankhah.current_stage.stage_order if instance.tankhah.current_stage else 1
        logger.debug(f"[start_payment_order_process] مرحله فعلی: {current_stage_order}")

        # بررسی AccessRule برای مرحله تأیید
        access_rule = AccessRule.objects.filter(
            organization=instance.tankhah.organization,
            action_type='APPROVE',
            entity_type='FACTOR',
            is_active=True,
            stage_order=current_stage_order
        ).order_by('-min_level').first()

        if not access_rule:
            logger.warning(f"هیچ قانون دسترسی برای فاکتور {instance.number} در مرحله {current_stage_order} یافت نشد")
            return

        # بررسی وجود ApprovalLog
        approval_log = ApprovalLog.objects.filter(
            factor=instance,
            action='APPROVE',
            stage_order=current_stage_order,
            post__level__gte=access_rule.min_level
        ).exists()

        if not approval_log:
            logger.debug(f"هیچ ApprovalLog معتبر برای فاکتور {instance.number} یافت نشد.")
            return

        with transaction.atomic():
            # بررسی بودجه تنخواه و پروژه
            tankhah_remaining = get_tankhah_remaining_budget(instance.tankhah)
            project_remaining = instance.tankhah.project.budget - instance.tankhah.project.spent if instance.tankhah.project else Decimal('0')
            if instance.amount > tankhah_remaining or (instance.tankhah.project and instance.amount > project_remaining):
                logger.error(f"بودجه کافی برای فاکتور {instance.number} نیست: تنخواه باقی‌مانده={tankhah_remaining}, پروژه باقی‌مانده={project_remaining}")
                raise ValueError(_("بودجه کافی برای تنخواه یا پروژه وجود ندارد."))

            # تعیین گیرنده پرداخت
            payee = instance.tankhah.payee or instance.tankhah.organization.payees.first()
            if not payee:
                logger.error(f"گیرنده پرداخت برای تنخواه {instance.tankhah.number} یافت نشد.")
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
                logger.error(f"هیچ قانون دسترسی اولیه معتبر برای دستور پرداخت یافت نشد.")
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

            # ثبت لاگ‌های امضا و ارسال اعلان
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
                # ارسال اعلان به کاربران پست مربوطه
                users = CustomUser.objects.filter(
                    userpost__post=rule.post,
                    userpost__is_active=True,
                    userpost__post__organization=instance.tankhah.organization
                ).distinct()
                send_notification(
                    sender=created_by,
                    users=users,
                    posts=[rule.post],
                    verb='PENDING_SIGNATURE',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} نیاز به امضای شما دارد.",
                    target=payment_order,
                    entity_type='PAYMENTORDER',
                    priority='HIGH'
                )
                # ارسال ایمیل
                for user in users:
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
                send_notification(
                    sender=created_by,
                    users=[user],
                    verb='PAYMENT_ORDER_CREATED',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} ایجاد شد.",
                    target=payment_order,
                    entity_type='PAYMENTORDER',
                    priority='HIGH'
                )
                send_mail(
                    subject=f"دستور پرداخت جدید: {payment_order.order_number}",
                    message=f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} ایجاد شد و در انتظار تأیید است.",
                    from_email='soheiladv@gmail.com',
                    recipient_list=[user.email],
                    fail_silently=True
                )

            logger.info(f"دستور پرداخت {payment_order.order_number} برای فاکتور {instance.number} ایجاد شد")

            # به‌روزرسانی وضعیت قفل بودجه
            if budget_allocation:
                budget_allocation.budget_period.update_lock_status()
                status, message = budget_allocation.budget_period.check_budget_status_no_save()
                if status in ['warning', 'locked', 'completed']:
                    budget_allocation.budget_period.send_notification(status, message)

    except Exception as e:
        logger.error(f"خطا در ایجاد دستور پرداخت برای فاکتور {instance.number}: {e}", exc_info=True)
        if hasattr(instance, '_request') and instance._request:
            messages.error(instance._request, _(f"خطا در ایجاد دستور پرداخت: {str(e)}"))


User = get_user_model()

# 1. ثبت تنخواه
@receiver(post_save, sender=Tankhah)
def notify_tankhah_creation(sender, instance, created, **kwargs):
    if created:
        # کاربران مرتبط با سازمان
        organization = instance.organization
        posts = organization.posts.filter(userpost__is_active=True).distinct()
        send_notification(
            sender=instance.created_by,
            posts=posts,
            verb='CREATED',
            description=f"تنخواه {instance.number} در شعبه {organization.name} ثبت شد.",
            target=instance,
            entity_type='TANKHAH',
            priority='MEDIUM'
        )

# 2. ارجاع فاکتور
@receiver(post_save, sender=Factor)
def notify_factor_referral(sender, instance, created, **kwargs):
    if not created and instance.status == 'REFERRED':
        # کاربران مرتبط با سازمان
        posts = instance.organization.posts.filter(userpost__is_active=True).distinct()
        send_notification(
            sender=instance.created_by,
            posts=posts,
            verb='REFERRED',
            description=f"فاکتور {instance.number} ارجاع داده شد.",
            target=instance,
            entity_type='FACTOR',
            priority='MEDIUM'
        )

# 3. رد/تأیید فاکتور
@receiver(post_save, sender=Factor)
def notify_factor_status_change(sender, instance, created, **kwargs):
    if not created and instance.status in ['APPROVED', 'REJECTED']:
        action = "تأیید" if instance.status == 'APPROVED' else "رد"
        posts = instance.organization.posts.filter(userpost__is_active=True).distinct()
        send_notification(
            sender=instance.created_by,
            posts=posts,
            verb=instance.status,
            description=f"فاکتور {instance.number} {action} شد.",
            target=instance,
            entity_type='FACTOR',
            priority='HIGH' if instance.status == 'APPROVED' else 'MEDIUM'
        )

# 4. ثبت یا برگشت بودجه
@receiver(post_save, sender=BudgetTransaction)
def notify_budget_transaction(sender, instance, created, **kwargs):
    if created:
        action = "مصرف" if instance.transaction_type == 'CONSUMPTION' else "برگشت"
        posts = instance.allocation.budget_period.organization.posts.filter(userpost__is_active=True).distinct()
        send_notification(
            sender=instance.created_by,
            posts=posts,
            verb=instance.transaction_type,
            description=f"تراکنش بودجه ({action}) به مبلغ {instance.amount} ثبت شد.",
            target=instance,
            entity_type='BUDGET',
            priority='MEDIUM'
        )

# 5. ارسال ایمیل برای اعلان‌ها (اختیاری، در صورت نیاز به ایمیل جداگانه)
@receiver(post_save, sender=Notification)
def send_notification_email(sender, instance, created, **kwargs):
    if created and instance.recipient.email:
        rule = NotificationRule.objects.filter(
            entity_type=instance.entity_type,
            action=instance.verb,
            is_active=True,
            channel='EMAIL'
        ).first()
        if rule:
            send_mail(
                subject=f"اعلان جدید: {instance.verb}",
                message=instance.description or f"{instance.actor.username if instance.actor else 'سیستم'} {instance.verb} {instance.target or ''}",
                from_email='soheiladv@gmail.com',
                recipient_list=[instance.recipient.email],
                fail_silently=True,
            )