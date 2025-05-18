import logging
from django.db.models import Max
from core.models import UserPost
from tankhah.models import ApprovalLog
from django.utils import timezone

logger = logging.getLogger(__name__)


def can_edit_approval(user, tankhah, stage):
    """
    چک می‌کند آیا کاربر می‌تواند تأیید/رد یا مرحله را تغییر دهد.
    کاربر می‌تواند تا قبل از اینکه سطح بالاتر تأیید را ببیند تغییر دهد، صرف‌نظر از مرحله فعلی.
    """
    # user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
    user_post = UserPost.objects.filter(user=user, is_active=True, end_date__isnull=True).first()
    if not user_post:
        logger.info(f"No active UserPost found for user {user.username}")
        return False
    # اگر کاربر HQ است، دسترسی کامل
    if user_post.post.organization.is_core:
        return True

    user_level = user_post.post.level
    max_change_level = user_post.post.max_change_level

    # آیا سطح بالاتری تأیید را دیده است؟
    higher_approval_seen = ApprovalLog.objects.filter(
        tankhah=tankhah,
        post__level__gt=user_level,
        seen_by_higher=True
    ).exists()

    # آیا تأیید سطح بالاتری بعد از این مرحله ثبت شده است؟
    higher_approval = ApprovalLog.objects.filter(
        tankhah=tankhah,
        stage__order__gt=stage.order,
        action__in=['APPROVE', 'REJECT']
    ).aggregate(Max('post__level'))['post__level__max']

    logger.info(f"can_edit_approval: user_level={user_level}, max_change_level={max_change_level}, "
                f"stage_order={stage.order}, higher_approval={higher_approval}, "
                f"higher_approval_seen={higher_approval_seen}")

    # کاربر می‌تواند تغییر دهد اگر:
    # 1. سطح بالاتری هنوز تأیید را ندیده باشد
    # 2. یا هیچ تأیید سطح بالاتری بعد از این مرحله وجود نداشته باشد
    return (
            not higher_approval_seen and
            (higher_approval is None or user_level >= higher_approval)
    )

