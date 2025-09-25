from typing import Any, Dict, List

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from core.models import EntityType, Transition, UserPost, Post, Organization
from core.services.workflow import wf


def _get_instance(entity_type_code: str, object_id: int):
    et = EntityType.objects.filter(code=entity_type_code.upper()).select_related('content_type').first()
    if not et or not et.content_type:
        raise Http404("EntityType or content type not configured")
    model = et.content_type.model_class()
    obj = model.objects.filter(pk=object_id).first()
    if not obj:
        raise Http404("Object not found")
    return et, obj


def _get_user_active_posts_in_org(user, organization_id: int) -> List[int]:
    today = timezone.now().date()
    qs = UserPost.objects.filter(
        user=user,
        post__organization_id=organization_id,
        start_date__lte=today,
    )
    qs = qs.filter(end_date__isnull=True) | qs.filter(end_date__gte=today)
    return list(qs.values_list('post_id', flat=True))


@login_required
def workflow_debug_view(request: HttpRequest) -> HttpResponse:
    entity_type_code = request.GET.get('entity_type')
    object_id = request.GET.get('id')  # optional; if absent we show scope view
    scope = (request.GET.get('scope') or 'all').lower()  # all|branch|hq
    org_code = request.GET.get('org')  # optional filter for org code

    if not entity_type_code:
        return render(request, 'core/workflow_debug.html', {
            'error': 'Provide entity_type (and optionally id, scope=all|branch|hq, org=<ORGCODE>)'
        })

    # Instance mode (object-specific):
    if object_id:
        et, obj = _get_instance(entity_type_code, int(object_id))
        status = getattr(obj, 'status', None)
        organization = getattr(obj, 'organization', None)
        org_id = getattr(organization, 'id', None)

        is_terminal = wf.is_terminal_for_instance(instance=obj, status=status, organization_id=org_id)

        outgoing = []
        allowed_action_codes = []
        user_post_ids: List[int] = []

        if status and org_id:
            trans_qs = Transition.objects.filter(
                organization_id=org_id,
                entity_type=et,
                from_status=status,
                is_active=True,
            ).select_related('action', 'to_status')

            user_post_ids = _get_user_active_posts_in_org(request.user, org_id)
            for tr in trans_qs:
                allowed_posts = set(tr.allowed_posts.values_list('id', flat=True))
                user_allowed = bool(allowed_posts.intersection(user_post_ids)) if allowed_posts else False
                outgoing.append({
                    'id': tr.id,
                    'name': tr.name,
                    'action': tr.action.code,
                    'to_status': tr.to_status.code,
                    'user_allowed': user_allowed,
                    'allowed_posts_count': len(allowed_posts),
                })
                if user_allowed:
                    allowed_action_codes.append(tr.action.code)

        context: Dict[str, Any] = {
            'mode': 'instance',
            'entity_type': et.code,
            'object_id': obj.id,
            'status': getattr(status, 'code', None),
            'organization': getattr(organization, 'code', None),
            'is_terminal': is_terminal,
            'user_posts': user_post_ids,
            'outgoing': outgoing,
            'allowed_actions': sorted(set(allowed_action_codes)),
            'user': request.user,
            'scope': scope,
            'org_filter': org_code,
            'error': None,
        }
        return render(request, 'core/workflow_debug.html', context)

    # Scope mode (no specific object): summarize active transitions by org scope
    et = EntityType.objects.filter(code=entity_type_code.upper()).first()
    if not et:
        raise Http404("EntityType not found")

    org_qs = Organization.objects.all()
    if scope == 'branch':
        org_qs = org_qs.filter(is_core=False)
    elif scope == 'hq':
        org_qs = org_qs.filter(is_core=True)
    if org_code:
        org_qs = org_qs.filter(code=org_code)

    orgs = list(org_qs.values('id', 'code', 'name'))
    summary = []
    for org in orgs:
        trans = Transition.objects.filter(
            organization_id=org['id'], entity_type=et, is_active=True
        ).select_related('from_status', 'to_status', 'action').prefetch_related('allowed_posts')

        # Collect all allowed post ids for this org to fetch active users in one query
        all_post_ids = set()
        for t in trans:
            all_post_ids.update(t.allowed_posts.values_list('id', flat=True))

        # Map post_id -> [usernames] of active users in this org
        today = timezone.now().date()
        user_map = {}
        if all_post_ids:
            up_qs = UserPost.objects.filter(
                post_id__in=list(all_post_ids),
                post__organization_id=org['id'],
                start_date__lte=today,
            )
            up_qs = up_qs.filter(end_date__isnull=True) | up_qs.filter(end_date__gte=today)
            for up in up_qs.select_related('user'):
                user_map.setdefault(up.post_id, []).append(getattr(up.user, 'username', str(up.user)))

        edges = []
        for t in trans:
            posts = list(t.allowed_posts.all())
            edges.append({
                'from': t.from_status.code,
                'action': t.action.code,
                'to': t.to_status.code,
                'allowed_posts_count': len(posts),
                'allowed_posts': [
                    {
                        'id': p.id,
                        'name': getattr(p, 'name', f"Post {p.id}"),
                        'users': sorted(user_map.get(p.id, [])),
                    }
                    for p in posts
                ],
            })

        summary.append({
            'organization': org['code'],
            'count': len(edges),
            'edges': edges,
        })

    context: Dict[str, Any] = {
        'mode': 'scope',
        'entity_type': et.code,
        'scope': scope,
        'org_filter': org_code,
        'summary': summary,
        'error': None,
    }
    return render(request, 'core/workflow_debug.html', context)


@login_required
def factor_workflow_shortcuts_view(request: HttpRequest) -> HttpResponse:
    """Simple page with handy links for FACTOR workflow debug (no hardcoded business logic)."""
    return render(request, 'core/factor_workflow_tools.html', {})


