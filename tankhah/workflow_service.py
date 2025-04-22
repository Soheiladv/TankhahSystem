import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from budgets.models import  BudgetTransaction
from tankhah.models import Tankhah, Factor, ApprovalLog
from accounts.models import CustomUser
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)
class WorkflowService:
    """
    تدهای اصلی: approve_item و reject_item برای تأیید یا رد تنخواه/فاکتور.
    تراکنش‌ها: هنگام تأیید تنخواه، تراکنش مصرف ثبت می‌شود.
    لاگ: هر اقدام (تأیید/رد) در ApprovalLog ثبت می‌شود.
    اعلان: تغییر وضعیت باعث ارسال اعلان به کاربران مرتبط می‌شود.
    تراکنش اتمیک: استفاده از transaction.atomic برای اطمینان از یکپارچگی داده‌ها.
    """
    @staticmethod
    @transaction.atomic
    def approve_item(item, user, reason=""):
        """
        تأیید یک آیتم (تنخواه یا فاکتور)
        :param item: شیء مدل (Tankhah یا Factor)
        :param user: کاربر تأییدکننده
        :param reason: دلیل تأیید (اختیاری)
        """
        if not isinstance(item, (Tankhah, Factor)):
            logger.error(f"Invalid item type: {type(item)}")
            raise ValidationError(_("نوع آیتم نامعتبر است."))

        if item.status != 'PENDING':
            logger.warning(f"Item {item} is not in PENDING state")
            raise ValidationError(_("آیتم در وضعیت انتظار تأیید نیست."))

        item.status = 'APPROVED'
        item.save()

        # ثبت لاگ تأیید
        ApprovalLog.objects.create(
            content_type=ContentType.objects.get_for_model(item),
            object_id=item.pk,
            action='APPROVE',
            actor=user,
            reason=reason
        )

        # برای تنخواه، ثبت تراکنش مصرف
        if isinstance(item, Tankhah):
            BudgetTransaction.objects.create(
                allocation=item.project_budget_allocation.budget_allocation,
                transaction_type='CONSUMPTION',
                amount=item.amount,
                related_tankhah=item,
                created_by=user,
                description=f"تأیید تنخواه {item.number}",
                transaction_id=f"TX-TNK-{item.number}"
            )

        logger.info(f"Item {item} approved by {user}")
        item.project_budget_allocation.budget_allocation.send_notification(
            'approved', f"{item.__class__.__name__} {item} تأیید شد."
        )

    @staticmethod
    @transaction.atomic
    def reject_item(item, user, reason=""):
        """
        رد یک آیتم (تنخواه یا فاکتور)
        :param item: شیء مدل (Tankhah یا Factor)
        :param user: کاربر ردکننده
        :param reason: دلیل رد (اختیاری)
        """
        if not isinstance(item, (Tankhah, Factor)):
            logger.error(f"Invalid item type: {type(item)}")
            raise ValidationError(_("نوع آیتم نامعتبر است."))

        if item.status != 'PENDING':
            logger.warning(f"Item {item} is not in PENDING state")
            raise ValidationError(_("آیتم در وضعیت انتظار تأیید نیست."))

        item.status = 'REJECTED'
        item.save()

        # ثبت لاگ رد
        ApprovalLog.objects.create(
            content_type=ContentType.objects.get_for_model(item),
            object_id=item.pk,
            action='REJECT',
            actor=user,
            reason=reason
        )

        logger.info(f"Item {item} rejected by {user}")
        item.project_budget_allocation.budget_allocation.send_notification(
            'rejected', f"{item.__class__.__name__} {item} رد شد. دلیل: {reason}"
        )