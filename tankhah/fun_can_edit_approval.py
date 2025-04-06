from django.db.models import Max

from core.models import UserPost
from tankhah.models import ApprovalLog

def can_edit_approval(user, tankhah, stage):
    """
    چک می‌کنه آیا کاربر می‌تونه تأیید/رد یا مرحله رو تغییر بده.
    """
    user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
    if not user_post:
        return False
    user_level = user_post.post.level
    max_change_level = user_post.post.max_change_level

    # بالاترین سطح تأییدکننده بعد از این مرحله
    higher_approval = ApprovalLog.objects.filter(
        tankhah=tankhah,
        stage__order__gt=stage.order,
        action='APPROVE'
    ).aggregate(Max('post__level'))['post__level__max']

    # کاربر می‌تونه تغییر بده اگه:
    # 1. هنوز سطح بالاتری تأیید نکرده
    # 2. مرحله فعلی توی محدوده max_change_level کاربر باشه
    return (higher_approval is None or user_level > higher_approval) and stage.order <= max_change_level