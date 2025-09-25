from functools import lru_cache
from typing import Dict, Iterable, Tuple

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.models import Status, Action, EntityType, Transition, UserPost


class WorkflowService:
    """
    Centralized, DB-driven access to workflow primitives (Status/Action/EntityType)
    with simple in-process caching. Keeps aliases normalized and avoids scattering
    hardcoded lookups across the codebase.
    """

    STATUS_ALIASES: Dict[str, str] = {
        'SUBMITTED': 'PENDING_APPROVAL',
        'IN_REVIEW': 'PENDING_APPROVAL',
        'APPROVED_FINAL': 'APPROVED',
        'REJECT': 'REJECTED',  # when used as a status
    }

    def _normalize(self, code: str) -> str:
        if not code:
            return code
        upper = code.upper()
        return self.STATUS_ALIASES.get(upper, upper)

    @lru_cache(maxsize=256)
    def get_status(self, code: str) -> Status:
        normalized = self._normalize(code)
        return Status.objects.get(code=normalized)

    @lru_cache(maxsize=256)
    def get_action(self, code: str) -> Action:
        normalized = (code or '').upper()
        return Action.objects.get(code=normalized)

    @lru_cache(maxsize=256)
    def get_entity_type(self, code: str) -> EntityType:
        normalized = (code or '').upper()
        return EntityType.objects.get(code=normalized)

    def ensure_statuses(self, required: Iterable[Dict], creator) -> Dict[str, Status]:
        """Ensure all required statuses exist. Return dict[code] = Status"""
        result: Dict[str, Status] = {}
        with transaction.atomic():
            for sd in required:
                code = self._normalize(sd['code'])
                obj, _ = Status.objects.get_or_create(
                    code=code,
                    defaults=dict(
                        name=sd.get('name') or code,
                        is_initial=sd.get('is_initial', False),
                        is_final_approve=sd.get('is_final_approve', False),
                        is_final_reject=sd.get('is_final_reject', False),
                        is_active=True,
                        description=sd.get('description', ''),
                        created_by=creator,
                    ),
                )
                result[obj.code] = obj
        # Clear caches so further get_* see fresh rows
        self.get_status.cache_clear()
        return result

    def ensure_actions(self, required: Iterable[Dict], creator) -> Dict[str, Action]:
        result: Dict[str, Action] = {}
        with transaction.atomic():
            for ad in required:
                code = (ad['code'] or '').upper()
                obj, _ = Action.objects.get_or_create(
                    code=code,
                    defaults=dict(
                        name=ad.get('name') or code,
                        description=ad.get('description', ''),
                        created_by=creator,
                        is_active=True,
                    ),
                )
                result[obj.code] = obj
        self.get_action.cache_clear()
        return result

    def ensure_entity_types(self, codes: Iterable[str]) -> Dict[str, EntityType]:
        result: Dict[str, EntityType] = {}
        with transaction.atomic():
            for code in codes:
                c = (code or '').upper()
                et, _ = EntityType.objects.get_or_create(code=c, defaults=dict(name=c))
                result[c] = et
        self.get_entity_type.cache_clear()
        return result


# Singleton-style accessor
wf = WorkflowService()



def get_allowed_actions_for_user(user, organization_id: int, entity_type_code: str, from_status) -> Dict[str, Iterable]:
    """
    Compute allowed actions for a user based on Transition.allowed_posts.
    Returns {"actions": [...], "allowed_transitions": [...]}.
    """
    # Resolve status
    if isinstance(from_status, Status):
        st = from_status
    else:
        st = wf.get_status(str(from_status))

    et = wf.get_entity_type(entity_type_code)

    # Active posts of user in org
    from django.utils import timezone
    today = timezone.now().date()
    user_post_ids = set(
        UserPost.objects.filter(user=user, post__organization_id=organization_id, start_date__lte=today)
        .filter(end_date__isnull=True)
        .values_list('post_id', flat=True)
    ) | set(
        UserPost.objects.filter(user=user, post__organization_id=organization_id, start_date__lte=today, end_date__gte=today)
        .values_list('post_id', flat=True)
    )

    trs = Transition.objects.filter(
        organization_id=organization_id,
        entity_type=et,
        from_status=st,
        is_active=True,
    ).select_related('action', 'to_status')

    actions = []
    allowed_transitions = []
    seen = set()

    for tr in trs:
        allowed_posts = set(tr.allowed_posts.values_list('id', flat=True))
        if allowed_posts and not (allowed_posts & user_post_ids):
            continue
        action_code = tr.action.code
        to_code = tr.to_status.code
        key = (action_code, to_code)
        if key not in seen:
            seen.add(key)
            actions.append({"code": action_code, "to_status": to_code})
        allowed_transitions.append({
            "id": tr.id,
            "action": action_code,
            "from": st.code,
            "to": to_code,
            "allowed_post_ids": list(allowed_posts),
        })

    core_actions = {"SUBMIT", "APPROVE", "FINAL_APPROVE", "REJECT"}
    if any(a["code"] in core_actions for a in actions):
        actions = [a for a in actions if a["code"] in core_actions]
        allowed_transitions = [t for t in allowed_transitions if t["action"] in core_actions]

    return {"actions": actions, "allowed_transitions": allowed_transitions}


