from typing import List, Dict
from django.db.models import Q

from core.models import Transition, UserRuleOverride, EntityType


def get_allowed_actions_for_user(user, organization, entity_type_code: str, from_status) -> Dict[str, List[str]]:
    """
    محاسبه اقدامات مجاز کاربر با توجه به Transition ها و UserRuleOverride ها.
    خروجی شامل لیست اقدامات مجاز و بلاک شده است.
    """
    if not user.is_authenticated:
        return {"allowed": [], "blocked": []}

    user_posts = list(user.userpost_set.filter(is_active=True, post__organization=organization).values_list('post_id', flat=True))
    if not user_posts:
        return {"allowed": [], "blocked": []}

    et = EntityType.objects.filter(code=entity_type_code).first()
    if not et:
        return {"allowed": [], "blocked": []}

    transitions = Transition.objects.filter(
        organization=organization,
        entity_type=et,
        from_status=from_status,
        is_active=True,
        allowed_posts__in=user_posts,
    ).distinct()

    action_codes = list(transitions.values_list('action__code', flat=True).distinct())

    # Apply UserRuleOverride: explicit disables remove, explicit enables add
    overrides = UserRuleOverride.objects.filter(
        user=user, organization=organization, entity_type=et
    )

    explicitly_disabled = set(
        overrides.filter(is_enabled=False).values_list('action__code', flat=True)
    )
    explicitly_enabled = set(
        overrides.filter(is_enabled=True).values_list('action__code', flat=True)
    )

    effective_allowed = set(action_codes) - explicitly_disabled
    effective_allowed |= explicitly_enabled

    return {
        "allowed": sorted(effective_allowed),
        "blocked": sorted(explicitly_disabled),
    }


