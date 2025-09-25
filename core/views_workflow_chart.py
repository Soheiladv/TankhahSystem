import json
from typing import Any, Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpRequest, HttpResponse, Http404
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.shortcuts import render
from django.utils import timezone
from django.db import models

from core.models import EntityType, Organization, Transition, UserPost, Branch, Post, Status, Action


class WorkflowChartView(LoginRequiredMixin, View):
    template_name = 'core/chart_API/workflow_chart.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        entity_types = list(EntityType.objects.values('id', 'code', 'name').order_by('code'))
        organizations = list(Organization.objects.values('id', 'code', 'name', 'is_core').order_by('code'))
        branches = list(Branch.objects.values('id', 'code', 'name').order_by('code'))
        posts = list(Post.objects.values('id', 'name', 'organization_id', 'branch_id').order_by('name'))
        statuses = list(Status.objects.values('id', 'code', 'name').order_by('name'))
        actions = list(Action.objects.values('id', 'code', 'name').order_by('name'))
        context = {
            'title': _('نمودار گردش کار (Transitions)'),
            'entity_types': entity_types,
            'organizations': organizations,
            'organizations_json': json.dumps(list(organizations), ensure_ascii=False),
            'branches': branches,
            'posts_json': json.dumps(list(posts), ensure_ascii=False),
            'statuses_json': json.dumps(list(statuses), ensure_ascii=False),
            'actions_json': json.dumps(list(actions), ensure_ascii=False),
        }
        return render(request, self.template_name, context)


def workflow_chart_api(request: HttpRequest) -> JsonResponse:
    entity_type_code = request.GET.get('entity_type')
    scope = (request.GET.get('scope') or 'all').lower()  # all|branch|hq
    org_code = request.GET.get('org_code')
    branch_id = request.GET.get('branch_id')

    if not entity_type_code:
        return JsonResponse({'error': 'entity_type is required'}, status=400)

    et = EntityType.objects.filter(code=entity_type_code.upper()).first()
    if not et:
        return JsonResponse({'error': 'EntityType not found'}, status=404)

    org_qs = Organization.objects.all()
    if scope == 'branch':
        org_qs = org_qs.filter(is_core=False)
    elif scope == 'hq':
        org_qs = org_qs.filter(is_core=True)
    if org_code:
        org_qs = org_qs.filter(code=org_code)
    org_ids = list(org_qs.values_list('id', flat=True))

    trans = Transition.objects.filter(
        entity_type=et, organization_id__in=org_ids, is_active=True
    ).select_related('from_status', 'to_status', 'action', 'organization').prefetch_related('allowed_posts')

    # Build vis.js graph: Organization -> Post -> Status(from), plus Status flow edges (from->to)
    nodes_map: Dict[str, Dict[str, Any]] = {}
    stage_allowed_posts: Dict[str, set] = {}
    edges: List[Dict[str, Any]] = []

    # Collect active users per post for tooltips
    all_post_ids = set()
    for t in trans:
        all_post_ids.update(t.allowed_posts.values_list('id', flat=True))
    user_map: Dict[int, List[str]] = {}
    post_meta: Dict[int, Dict[str, Any]] = {}
    if all_post_ids:
        today = timezone.now().date()
        ups = UserPost.objects.filter(post_id__in=list(all_post_ids), start_date__lte=today)
        ups = ups.filter(end_date__isnull=True) | ups.filter(end_date__gte=today)
        for up in ups.select_related('user'):
            user_map.setdefault(up.post_id, []).append(getattr(up.user, 'username', str(up.user)))
        # Fetch post names and branch/organization for display
        for p in Post.objects.filter(id__in=list(all_post_ids)).select_related('branch', 'organization'):
            post_meta[p.id] = {
                'name': getattr(p, 'name', f'Post {p.id}'),
                'branch': getattr(getattr(p, 'branch', None), 'name', None),
                'organization': getattr(getattr(p, 'organization', None), 'name', None),
            }
    # Active user's posts (across all orgs) to mark allowed edges
    today = timezone.now().date()
    user_active_posts = set(
        UserPost.objects.filter(user=request.user, start_date__lte=today)
        .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=today))
        .values_list('post_id', flat=True)
    )

    def ensure_status_node(status_code: str, status_name: str | None = None) -> str:
        node_id = f"status:{status_code}"
        if node_id not in nodes_map:
            label = f"{status_name} ({status_code})" if status_name else status_code
            nodes_map[node_id] = {
                'id': node_id,
                'label': label,
                'group': 'status',
                'shape': 'box',
            }
        return node_id

    def ensure_org_node(org_obj: Dict[str, Any]) -> str:
        node_id = f"org:{org_obj['id']}"
        if node_id not in nodes_map:
            nodes_map[node_id] = {
                'id': node_id,
                'label': f"{org_obj.get('name') or org_obj.get('code')} ({org_obj.get('code')})",
                'group': 'organization',
                'shape': 'box',
            }
        return node_id

    def ensure_branch_node(branch_id: int, branch_name: str, org_name: str | None) -> str:
        node_id = f"branch:{branch_id}"
        if node_id not in nodes_map:
            suffix = f"\n‹{org_name}›" if org_name else ''
            nodes_map[node_id] = {
                'id': node_id,
                'label': f"{branch_name}{suffix}",
                'group': 'branch',
                'shape': 'box',
            }
        return node_id

    def ensure_post_node(post_id: int, name: str, org_name: str | None, branch_name: str | None) -> str:
        node_id = f"post:{post_id}"
        if node_id not in nodes_map:
            suffix = ''
            if branch_name:
                suffix += f" [{branch_name}]"
            if org_name:
                suffix += f"\n‹{org_name}›"
            nodes_map[node_id] = {
                'id': node_id,
                'label': f"{name}{suffix}",
                'group': 'post',
                'shape': 'ellipse',
            }
        return node_id

    # 1) Organization -> Branch -> Post
    org_map: Dict[int, Dict[str, Any]] = {o['id']: o for o in org_qs.values('id', 'code', 'name')}
    posts = list(Post.objects.filter(organization_id__in=org_ids).select_related('branch', 'organization'))
    if branch_id:
        try:
            bid = int(branch_id)
            posts = [p for p in posts if getattr(p, 'branch_id', None) == bid]
        except ValueError:
            pass
    for p in posts:
        org_obj = org_map.get(p.organization_id)
        if not org_obj:
            continue
        org_node = ensure_org_node(org_obj)
        branch_obj = getattr(p, 'branch', None)
        post_node = ensure_post_node(
            p.id,
            getattr(p, 'name', f'Post {p.id}'),
            org_obj.get('name'),
            getattr(branch_obj, 'name', None)
        )
        if branch_obj:
            branch_node = ensure_branch_node(branch_obj.id, branch_obj.name, org_obj.get('name'))
            edges.append({'from': org_node, 'to': branch_node, 'arrows': 'to', 'color': {'color': '#999'}})
            edges.append({'from': branch_node, 'to': post_node, 'arrows': 'to', 'color': {'color': '#bbb'}})
        else:
            edges.append({'id': f"org-post:{org_obj['id']}:{p.id}", 'from': org_node, 'to': post_node, 'arrows': 'to', 'color': {'color': '#999'}})

    # 2) Status flow edges and Post -> Status(from) per Transition
    # Prepare actions per post mapping
    post_actions: Dict[int, List[Dict[str, Any]]]= {}
    for t in trans:
        frm_code = t.from_status.code
        to_code = t.to_status.code
        frm_id = ensure_status_node(frm_code, getattr(t.from_status, 'name', None))
        to_id = ensure_status_node(to_code, getattr(t.to_status, 'name', None))
        # Track posts per stage
        s = stage_allowed_posts.setdefault(frm_code, set())
        s.update(t.allowed_posts.values_list('id', flat=True))
        # Flow edge
        edges.append({'id': f"flow:{t.id}", 'from': frm_id, 'to': to_id, 'arrows': 'to', 'color': {'color': '#c0c4cc'}, 'width': 1})
        # Post -> Status(from) edges with action label
        action_label = getattr(t.action, 'name', t.action.code)
        posts_iter = t.allowed_posts.all()
        if branch_id:
            try:
                bid = int(branch_id)
                posts_iter = [p for p in posts_iter if getattr(p, 'branch_id', None) == bid]
            except ValueError:
                posts_iter = list(posts_iter)
        for p in posts_iter:
            meta = post_meta.get(p.id, {})
            post_node = ensure_post_node(p.id, meta.get('name', getattr(p, 'name', f'Post {p.id}')), meta.get('organization'), meta.get('branch'))
            user_allowed = p.id in user_active_posts
            users = ', '.join(sorted(user_map.get(p.id, []))) or _('بدون کاربر فعال')
            title = f"{action_label} — {users}"
            edges.append({
                'id': f"trpost:{t.id}:{p.id}",
                'from': post_node,
                'to': frm_id,
                'label': action_label,
                'title': title,
                'arrows': 'to',
                'color': { 'color': '#198754' if user_allowed else '#6c757d' },
                'width': 2 if user_allowed else 1,
                'action_code': t.action.code,
            })
            # Record action for post tooltip/details
            post_actions.setdefault(p.id, []).append({
                'from_code': frm_code,
                'from_name': getattr(t.from_status, 'name', frm_code),
                'action_code': t.action.code,
                'action_name': getattr(t.action, 'name', t.action.code),
                'to_code': to_code,
                'to_name': getattr(t.to_status, 'name', to_code),
            })

    # Enrich nodes with tooltip listing posts/users connected at stage (union across outgoing transitions)
    for node_id, node in list(nodes_map.items()):
        if not node_id.startswith('status:'):
            continue
        status_code = node_id.split(':', 1)[1]
        post_ids = stage_allowed_posts.get(status_code, set())
        if not post_ids:
            continue
        # Build tooltip content
        # We need names per post as well; fetch a small sample through transitions already prefetched
        post_user_lines: List[str] = []
        # Build a reverse lookup of post name using any transition
        # As a fallback, only list usernames
        for pid in sorted(post_ids):
            usernames = ', '.join(sorted(user_map.get(pid, []))) or _('بدون کاربر فعال')
            meta = post_meta.get(pid, {})
            bname = meta.get('branch')
            oname = meta.get('organization')
            branch_label = f" [{bname}]" if bname else ''
            org_label = f" ‹{oname}›" if oname else ''
            post_user_lines.append(f"{meta.get('name', f'Post {pid}')}{branch_label}{org_label} — {usernames}")
        node['title'] = "\n".join(post_user_lines)

    # Enrich post nodes with users and actions list
    for node_id, node in list(nodes_map.items()):
        if not node_id.startswith('post:'):
            continue
        try:
            pid = int(node_id.split(':', 1)[1])
        except Exception:
            continue
        usernames = ', '.join(sorted(user_map.get(pid, []))) or _('بدون کاربر فعال')
        actions = post_actions.get(pid, [])
        lines: List[str] = []
        lines.append(f"{_('کاربران')}: {usernames}")
        if actions:
            lines.append(str(_('اکشن‌ها:')))
            for a in actions:
                lines.append(f"- {a['from_name']} ({a['from_code']}) — {a['action_name']} → {a['to_name']} ({a['to_code']})")
        node['title'] = "\n".join(lines)

    return JsonResponse({
        'nodes': list(nodes_map.values()),
        'edges': edges,
    })


# ---------- CRUD APIs for Transition editing ----------
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required, login_required
from django.middleware.csrf import get_token
from django.forms.models import model_to_dict


@login_required
@require_POST
@permission_required('core.add_transition', raise_exception=True)
def workflow_transition_create(request: HttpRequest) -> JsonResponse:
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    try:
        et = EntityType.objects.get(code=data['entity_type'].upper())
        org = Organization.objects.get(code=data['organization'])
        from_status = Status.objects.get(code=data['from_status'])
        action = Action.objects.get(code=data['action'])
        to_status = Status.objects.get(code=data['to_status'])
        allowed_post_ids = data.get('allowed_post_ids', [])
        is_active = bool(data.get('is_active', True))
        created_by = request.user
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    tr, created = Transition.objects.get_or_create(
        organization=org,
        entity_type=et,
        from_status=from_status,
        action=action,
        defaults={
            'name': f"{org.code} {et.code}: {from_status.code} --{action.code}--> {to_status.code}",
            'to_status': to_status,
            'is_active': is_active,
            'created_by': created_by,
        }
    )
    if not created:
        return JsonResponse({'error': 'transition already exists'}, status=409)
    if allowed_post_ids:
        tr.allowed_posts.set(list(Post.objects.filter(id__in=allowed_post_ids).values_list('id', flat=True)))
    return JsonResponse({'ok': True, 'transition_id': tr.id})


@login_required
@require_POST
@permission_required('core.change_transition', raise_exception=True)
def workflow_transition_update(request: HttpRequest, transition_id: int) -> JsonResponse:
    try:
        tr = Transition.objects.get(id=transition_id)
        data = json.loads(request.body.decode('utf-8'))
    except Transition.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    # Update fields if provided
    if 'to_status' in data:
        tr.to_status = Status.objects.get(code=data['to_status'])
    if 'action' in data:
        tr.action = Action.objects.get(code=data['action'])
    if 'is_active' in data:
        tr.is_active = bool(data['is_active'])
    if 'name' in data and data['name']:
        tr.name = data['name']
    tr.save()
    if 'allowed_post_ids' in data:
        tr.allowed_posts.set(list(Post.objects.filter(id__in=data['allowed_post_ids']).values_list('id', flat=True)))
    return JsonResponse({'ok': True})


@login_required
@require_POST
@permission_required('core.change_transition', raise_exception=True)
def workflow_transition_toggle(request: HttpRequest, transition_id: int) -> JsonResponse:
    try:
        tr = Transition.objects.get(id=transition_id)
    except Transition.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    tr.is_active = not tr.is_active
    tr.save(update_fields=['is_active'])
    return JsonResponse({'ok': True, 'is_active': tr.is_active})


@login_required
@require_POST
@permission_required('core.delete_transition', raise_exception=True)
def workflow_transition_delete(request: HttpRequest, transition_id: int) -> JsonResponse:
    try:
        tr = Transition.objects.get(id=transition_id)
    except Transition.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    tr.delete()
    return JsonResponse({'ok': True})


