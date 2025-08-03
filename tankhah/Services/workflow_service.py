# services/workflow_service.py
import logging
logger = logging.getLogger('workflow_service')
import logging
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from ..models import AccessRule, ApprovalLog

class WorkflowService:
    @staticmethod
    def get_workflow_stages(organization, entity_type='FACTOR'):
        """دریافت تمام مراحل گردش کار برای یک سازمان و نوع موجودیت خاص"""
        logger.debug(f"Fetching workflow stages for organization {organization.name}, entity type {entity_type}")
        return AccessRule.objects.filter(
            organization=organization,
            entity_type=entity_type,
            is_active=True
        ).order_by('stage_order')

    @staticmethod
    def get_current_stage_info(factor):
        """اطلاعات مرحله فعلی فاکتور در گردش کار"""
        logger.debug(f"Getting current stage info for factor {factor.factornumber}")
        current_stage = factor.tankhah.current_stage

        if not current_stage:
            logger.warning(f"Factor {factor.factornumber} has no current stage defined in its tankhah.")
            return {
                'current_stage': None,
                'current_index': 0,
                'total_stages': 0,
                'progress_percentage': 0,
                'all_stages': [],
                'is_final': False
            }

        all_stages = WorkflowService.get_workflow_stages(
            factor.tankhah.organization,
            entity_type='FACTOR'
        )

        current_index = -1
        for i, stage in enumerate(all_stages):
            if stage.stage_order == current_stage.stage_order:
                current_index = i
                break

        total_stages = all_stages.count()
        progress_percentage = ((current_index + 1) / total_stages) * 100 if total_stages > 0 else 0

        logger.debug(
            f"Current stage for factor {factor.factornumber}: {current_stage.stage} (Order: {current_stage.stage_order}), Progress: {progress_percentage:.2f}%")

        return {
            'current_stage': current_stage,
            'current_index': current_index,
            'total_stages': total_stages,
            'progress_percentage': progress_percentage,
            'all_stages': all_stages,
            'is_final': current_stage.is_final_stage
        }

    @staticmethod
    @transaction.atomic
    def advance_to_next_stage(factor, user, comment="پیشرفت خودکار"):
        """انتقال فاکتور به مرحله بعدی در گردش کار"""
        logger.info(f"Attempting to advance factor {factor.factornumber} to next stage by user {user.username}.")
        current_stage = factor.tankhah.current_stage

        if not current_stage:
            logger.warning(f"Cannot advance factor {factor.factornumber}: No current stage defined.")
            return None

        next_stage = AccessRule.objects.filter(
            organization=factor.tankhah.organization,
            entity_type='FACTOR',
            stage_order__gt=current_stage.stage_order,
            is_active=True
        ).order_by('stage_order').first()

        if next_stage:
            user_post = user.userpost_set.filter(is_active=True).first()
            if not user_post:
                logger.error(
                    f"User {user.username} has no active post to log stage change for factor {factor.factornumber}.")
                raise ValueError(_("کاربر پست فعالی برای ثبت لاگ ندارد."))

            ApprovalLog.objects.create(
                factor=factor,
                action='STAGE_CHANGE',
                stage=next_stage,
                user=user,
                post=user_post.post,
                comment=f"انتقال از {current_stage.stage} به {next_stage.stage} - {comment}",
                content_type=ContentType.objects.get_for_model(factor),
                object_id=factor.id
            )

            factor.tankhah.current_stage = next_stage
            factor.tankhah.save()
            logger.info(f"Factor {factor.factornumber} successfully advanced to stage {next_stage.stage_order}.")
            return next_stage
        else:
            logger.info(f"Factor {factor.factornumber} is already at the final stage or no next stage found.")
            return None