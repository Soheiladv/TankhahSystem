# services/approval_service.py
import logging
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from ..models import Factor, ApprovalLog, UserPost  # Assuming these models are in ..models
from .workflow_service import WorkflowService  # Import WorkflowService
from accounts.models import CustomUser  # Import CustomUser

logger = logging.getLogger('ApprovalService')


class ApprovalService:
    @staticmethod
    @transaction.atomic
    def approve_factor(user, factor, comment="", is_temporary=False):
        """تأیید فاکتور با مدیریت بودجه و پیشرفت گردش کار"""
        logger.info(
            f"Attempting to approve factor {factor.factornumber} by user {user.username}. Temporary: {is_temporary}")

        if not factor.can_approve(user):
            logger.warning(f"Permission denied for user {user.username} to approve factor {factor.factornumber}.")
            raise PermissionDenied(_("عدم دسترسی به تأیید فاکتور"))

        user_post = user.userpost_set.filter(is_active=True).first()
        if not user_post:
            logger.error(f"User {user.username} has no active post to approve factor {factor.factornumber}.")
            raise ValueError(_("کاربر پست فعالی برای ثبت لاگ ندارد."))

        current_stage = factor.tankhah.current_stage
        if not current_stage:
            logger.error(f"Factor {factor.factornumber} has no current stage defined in its tankhah.")
            raise ValueError(_("مرحله فعلی برای تنخواه فاکتور تعریف نشده است."))

        # Reserve budget only if it's the first approval and budget is not yet reserved
        if factor.budget_status == 'NONE' and factor.status == 'PENDING_APPROVAL':
            try:
                factor.reserve_budget()
                logger.info(f"Budget reserved for factor {factor.factornumber} during first approval.")
            except ValidationError as e:
                logger.error(f"Failed to reserve budget for factor {factor.factornumber}: {e}")
                raise ValidationError(_(f"خطا در رزرو بودجه: {e}"))

        # Determine action type for log
        if current_stage.is_final_stage and not is_temporary:
            action_log_type = 'APPROVED_FINAL'

        # Create approval log
        approval_log = ApprovalLog.objects.create(
            factor=factor,
            action=action_log_type,
            stage=current_stage,
            user=user,
            post=user_post.post,
            comment=comment,
            is_temporary=is_temporary,
            content_type=ContentType.objects.get_for_model(factor),
            object_id=factor.id
        )
        logger.debug(f"Approval log created for factor {factor.factornumber}: Action {action_log_type}.")

        # Update factor status
        if action_log_type == 'APPROVED_FINAL':
            factor.status = 'APPROVED_FINAL'
            factor.is_locked = True  # Lock after final approval
            logger.info(f"Factor {factor.factornumber} status set to APPROVED_FINAL.")
        elif action_log_type == 'APPROVE':
            factor.status = 'APPROVED_INTERMEDIATE'
            logger.info(f"Factor {factor.factornumber} status set to APPROVED_INTERMEDIATE.")
        elif action_log_type == 'TEMP_APPROVED':
            if factor.status == 'PENDING_APPROVAL':
                factor.status = 'PENDING_APPROVAL'
            logger.info(f"Factor {factor.factornumber} temporarily approved. Status remains {factor.status}.")

        factor.save()

        # Advance to next stage if auto_advance is enabled and not temporary
        if current_stage.auto_advance and not is_temporary and not current_stage.is_final_stage:
            WorkflowService.advance_to_next_stage(factor, user, "تأیید و پیشرفت خودکار")
            logger.info(f"Factor {factor.factornumber} auto-advanced to next stage.")

        return approval_log

    @staticmethod
    @transaction.atomic
    def reject_factor(user, factor, reason):
        """رد فاکتور با آزادسازی بودجه و قفل کردن فاکتور"""
        logger.info(f"Attempting to reject factor {factor.factornumber} by user {user.username}. Reason: {reason}")

        if not factor.can_approve(user):
            logger.warning(f"Permission denied for user {user.username} to reject factor {factor.factornumber}.")
            raise PermissionDenied(_("عدم دسترسی به رد فاکتور"))

        user_post = user.userpost_set.filter(is_active=True).first()
        if not user_post:
            logger.error(f"User {user.username} has no active post to reject factor {factor.factornumber}.")
            raise ValueError(_("کاربر پست فعالی برای ثبت لاگ ندارد."))

        # Release budget if it was reserved
        if factor.budget_status == 'RESERVED':
            factor.release_budget(f"رد توسط {user.get_full_name()}: {reason}")
            logger.info(f"Budget released for factor {factor.factornumber} due to rejection.")

        # Create rejection log
        ApprovalLog.objects.create(
            factor=factor,
            action='REJECT',
            stage=factor.tankhah.current_stage,
            user=user,
            post=user_post.post,
            comment=reason,
            content_type=ContentType.objects.get_for_model(factor),
            object_id=factor.id
        )
        logger.debug(f"Rejection log created for factor {factor.factornumber}.")

        # Update factor status and lock it
        factor.status = 'REJECTE'
        factor.rejected_reason = reason
        factor.is_locked = True
        factor.save()
        logger.info(f"Factor {factor.factornumber} status set to REJECTE and locked.")

        return True
