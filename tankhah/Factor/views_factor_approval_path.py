"""
ویوهای مربوط به نمایش مسیر تأیید فاکتور
"""

from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView
from django.http import JsonResponse
from django.db.models import Prefetch, Q
from django.core.cache import cache
import logging

from core.models import Transition, UserPost, Post, Status, Action, Organization
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor, ApprovalLog
from tankhah.Factor.FactorDetail.views_FactorDetail import get_next_steps_with_posts

logger = logging.getLogger(__name__)


class FactorApprovalPathView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """
    نمایش مسیر کامل تأیید فاکتور
    """
    model = Factor
    template_name = 'core/workflow/factor_approval_path.html'
    context_object_name = 'factor'
    permission_required = 'tankhah.factor_view'
    
    def get_queryset(self):
        return Factor.objects.select_related(
            'tankhah', 'tankhah__organization', 'created_by', 'status',
            'tankhah__project_budget_allocation',
            'tankhah__project_budget_allocation__budget_period',
            'tankhah__project_budget_allocation__budget_item'
        ).prefetch_related(
            Prefetch('approval_logs', queryset=ApprovalLog.objects.order_by('-timestamp').select_related(
                'user', 'post', 'from_status', 'to_status', 'action'
            ))
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        
        # مسیر کامل گردش کار
        full_workflow_path = get_next_steps_with_posts(factor)
        context['full_workflow_path'] = full_workflow_path
        
        # مسیر تأیید با جزئیات کامل
        approval_path = get_detailed_approval_path(factor, user)
        context['approval_path'] = approval_path
        
        # تاریخچه تأییدات
        context['approval_history'] = factor.approval_logs.all()
        
        # وضعیت فعلی و بعدی
        context['current_status'] = factor.status
        context['next_steps'] = self._get_next_steps_for_user(user, factor)
        
        # آمار کلی
        context['path_stats'] = get_approval_path_statistics(factor)
        
        return context
    
    def _get_next_steps_for_user(self, user, factor):
        """
        دریافت مراحل بعدی که کاربر می‌تواند انجام دهد
        """
        from tankhah.Factor.FactorDetail.views_FactorDetail import get_user_allowed_transitions
        
        allowed_transitions = get_user_allowed_transitions(user, factor)
        
        next_steps = []
        for transition in allowed_transitions:
            # دریافت کاربران فعال در پست‌های مجاز
            allowed_posts = list(transition.allowed_posts.all())
            # اگر برای گذار هیچ پست خاصی تعیین نشده باشد، تمام پست‌های فعال سازمان مجازند
            if not allowed_posts and transition.organization_id:
                allowed_posts = list(Post.objects.filter(organization_id=transition.organization_id, is_active=True))
            active_users = []
            
            if allowed_posts:
                userposts = UserPost.objects.filter(
                    post__in=allowed_posts,
                    is_active=True
                ).select_related('user', 'post')
                
                seen_user_ids = set()
                for up in userposts:
                    if up.user and up.user_id not in seen_user_ids:
                        seen_user_ids.add(up.user_id)
                        active_users.append({
                            'user': up.user,
                            'post': up.post,
                            'organization': up.post.organization
                        })
            
            next_steps.append({
                'transition': transition,
                'action': transition.action,
                'to_status': transition.to_status,
                'posts': allowed_posts,
                'users': active_users,
                'organization': transition.organization
            })
        
        return next_steps


def get_detailed_approval_path(factor, user=None):
    """
    ساخت مسیر تأیید با جزئیات کامل شامل افراد و پست‌ها
    """
    if not factor.status or not factor.tankhah or not factor.tankhah.organization:
        return []
    
    # Helper: resolve entity type code for Factor
    def _get_factor_entity_type_code():
        try:
            from django.contrib.contenttypes.models import ContentType
            from core.models import EntityType
            ct = ContentType.objects.get_for_model(Factor)
            et = EntityType.objects.filter(content_type=ct).first()
            return et.code if et else 'FACTOR'
        except Exception:
            return 'FACTOR'

    et_code = _get_factor_entity_type_code()

    # جمع‌آوری تمام سازمان‌های والد
    org_hierarchy_pks = []
    current_org = factor.tankhah.organization
    while current_org:
        org_hierarchy_pks.append(current_org.pk)
        current_org = current_org.parent_organization
    
    # گرفتن تمام گذارها برای سازمان‌ها
    all_transitions = Transition.objects.filter(
        entity_type__code=et_code,
        organization_id__in=org_hierarchy_pks,
        is_active=True
    ).select_related('action', 'from_status', 'to_status', 'organization').prefetch_related('allowed_posts')
    
    # ساخت نقشه گذارها
    transitions_map = {}
    for t in all_transitions:
        key = f"{t.from_status.id}_{t.action.id}"
        if key not in transitions_map:
            transitions_map[key] = []
        transitions_map[key].append(t)
    
    # ساخت مسیر کامل
    path = []
    current_status = factor.status
    visited_statuses = {current_status.pk}
    step_number = 1
    
    # اضافه کردن وضعیت فعلی
    path.append({
        'step_number': 0,
        'status': current_status,
        'is_current': True,
        'is_completed': False,
        'is_pending': True,
        'action': None,
        'posts': [],
        'users': [],
        'organization': factor.tankhah.organization,
        'can_perform': False
    })
    
    # Helper: تعیین پست‌های مؤثر هر گذار با اولویت: allowed_posts → PRA → همه پست‌های فعال سازمان
    def _effective_posts_for_transition(tr):
        posts = list(tr.allowed_posts.all())
        if not posts and tr.organization_id:
            from core.models import PostRuleAssignment as _PRA, Post as _Post
            pra_post_ids = list(_PRA.objects.filter(
                is_active=True,
                organization_id=tr.organization_id,
                action_id=tr.action_id,
                entity_type=et_code
            ).values_list('post_id', flat=True))
            if pra_post_ids:
                posts = list(_Post.objects.filter(id__in=pra_post_ids, is_active=True))
            else:
                posts = list(_Post.objects.filter(organization_id=tr.organization_id, is_active=True))
        try:
            posts.sort(key=lambda p: (
                not getattr(p, 'can_final_approve_factor', False),  # False اول (True اولویت دارد)
                getattr(p, 'level', 9999) or 9999,
                p.name
            ))
        except Exception:
            pass
        return posts

    while current_status:
        next_possible_transitions = []
        for key, transitions in transitions_map.items():
            if key.startswith(f"{current_status.id}_"):
                next_possible_transitions.extend(transitions)
        
        if not next_possible_transitions:
            break
        
        # انتخاب گذار اصلی: اولویت با پست‌هایی که can_final_approve_factor=True دارند
        candidates = [t for t in next_possible_transitions if not t.to_status.is_final_reject]
        if not candidates:
            break
        def _order_key(tr):
            posts = _effective_posts_for_transition(tr)
            # اولویت با پست‌هایی که can_final_approve_factor=True دارند
            has_final_approve = any(getattr(p, 'can_final_approve_factor', False) for p in posts)
            min_level = min([getattr(p, 'level', 9999) or 9999 for p in posts], default=9999)
            # اگر پست‌هایی با can_final_approve_factor=True وجود دارند، اولویت با آنها
            if has_final_approve:
                return (0, min_level, tr.id)  # 0 برای اولویت بالا
            else:
                return (1, min_level, tr.id)  # 1 برای اولویت پایین
        main_transition = min(candidates, key=_order_key)
        
        if not main_transition:
            break
        
        # دریافت پست‌های مؤثر (مرتب‌شده بر اساس can_final_approve_factor سپس سطح/نام)
        allowed_posts = _effective_posts_for_transition(main_transition)
        
        # مرتب‌سازی پست‌ها: اول can_final_approve_factor=True، سپس سطح، سپس نام
        try:
            allowed_posts = sorted(allowed_posts, key=lambda p: (
                not getattr(p, 'can_final_approve_factor', False),  # False اول (True اولویت دارد)
                getattr(p, 'level', 9999) or 9999,
                p.name
            ))
        except Exception:
            pass
        
        # دریافت کاربران فعال در این پست‌ها (مرتب‌سازی بر اساس can_final_approve_factor سپس سطح پست سپس نام)
        active_users = []
        if allowed_posts:
            userposts = UserPost.objects.filter(
                post__in=allowed_posts,
                is_active=True
            ).select_related('user', 'post')
            try:
                userposts = sorted(userposts, key=lambda up: (
                    not getattr(up.post, 'can_final_approve_factor', False),  # False اول (True اولویت دارد)
                    getattr(up.post, 'level', 9999) or 9999,
                    up.user.get_full_name() or up.user.username
                ))
            except Exception:
                pass
            
            seen_user_ids = set()
            for up in userposts:
                if up.user and up.user_id not in seen_user_ids:
                    seen_user_ids.add(up.user_id)
                    active_users.append({
                        'user': up.user,
                        'post': up.post,
                        'organization': up.post.organization
                    })
        
        # بررسی اینکه آیا کاربر فعلی می‌تواند این اقدام را انجام دهد
        user_post_ids = set()
        if user and user.is_authenticated:
            user_post_ids = set(
                user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)
            )
        
        can_perform = any(p.id in user_post_ids for p in allowed_posts) or (user and user.is_superuser)
        
        path.append({
            'step_number': step_number,
            'status': main_transition.to_status,
            'is_current': False,
            'is_completed': False,
            'is_pending': True,
            'action': main_transition.action,
            'from_status': current_status,
            'posts': allowed_posts,
            'users': active_users,
            'organization': main_transition.organization,
            'can_perform': can_perform,
            'transition': main_transition
        })
        
        current_status = main_transition.to_status
        if current_status.pk in visited_statuses:
            break
        visited_statuses.add(current_status.pk)
        step_number += 1
    
    # علامت‌گذاری مراحل تکمیل شده بر اساس تاریخچه
    completed_status_ids = set()
    for log in factor.approval_logs.all():
        completed_status_ids.add(log.to_status_id)
    
    for step in path:
        if step['status'].id in completed_status_ids:
            step['is_completed'] = True
            step['is_pending'] = False
    
    return path


def get_approval_path_statistics(factor):
    """
    دریافت آمار مسیر تأیید
    """
    approval_path = get_detailed_approval_path(factor)
    total_steps = len(approval_path)
    completed_steps = factor.approval_logs.count()
    remaining_steps = total_steps - completed_steps
    
    return {
        'total_steps': total_steps,
        'completed_steps': completed_steps,
        'remaining_steps': remaining_steps,
        'completion_percentage': (completed_steps / total_steps * 100) if total_steps > 0 else 0
    }


def get_duplicate_actions_analysis(factor):
    """
    تحلیل اقدامات تکراری در روند تأیید فاکتور
    """
    if not factor.status or not factor.tankhah or not factor.tankhah.organization:
        return []
    
    # جمع‌آوری تمام سازمان‌های والد
    org_hierarchy_pks = []
    current_org = factor.tankhah.organization
    while current_org:
        org_hierarchy_pks.append(current_org.pk)
        current_org = current_org.parent_organization
    
    # گرفتن تمام گذارها برای سازمان‌ها
    all_transitions = Transition.objects.filter(
        entity_type__code='FACTOR',
        organization_id__in=org_hierarchy_pks,
        is_active=True
    ).select_related('action', 'from_status', 'to_status', 'organization').prefetch_related('allowed_posts')
    
    # تحلیل اقدامات تکراری
    action_analysis = {}
    
    for transition in all_transitions:
        action_code = transition.action.code
        if action_code not in action_analysis:
            action_analysis[action_code] = {
                'action_name': transition.action.name,
                'action_code': action_code,
                'occurrences': 0,
                'from_statuses': set(),
                'to_statuses': set(),
                'posts': set(),
                'organizations': set()
            }
        
        action_analysis[action_code]['occurrences'] += 1
        action_analysis[action_code]['from_statuses'].add(transition.from_status.name)
        action_analysis[action_code]['to_statuses'].add(transition.to_status.name)
        action_analysis[action_code]['organizations'].add(transition.organization.name)
        
        for post in transition.allowed_posts.all():
            action_analysis[action_code]['posts'].add(f"{post.name} ({post.organization.name})")
    
    # تبدیل set ها به list برای JSON serialization
    for action_code, data in action_analysis.items():
        data['from_statuses'] = list(data['from_statuses'])
        data['to_statuses'] = list(data['to_statuses'])
        data['posts'] = list(data['posts'])
        data['organizations'] = list(data['organizations'])
    
    return list(action_analysis.values())


def get_termination_rules(factor):
    """
    دریافت قوانین خاتمه بر اساس پست‌ها و دسترسی‌های ویژه
    """
    if not factor.status or not factor.tankhah or not factor.tankhah.organization:
        return []
    
    # جمع‌آوری تمام سازمان‌های والد
    org_hierarchy_pks = []
    current_org = factor.tankhah.organization
    while current_org:
        org_hierarchy_pks.append(current_org.pk)
        current_org = current_org.parent_organization
    
    # گرفتن تمام گذارها برای سازمان‌ها
    all_transitions = Transition.objects.filter(
        entity_type__code='FACTOR',
        organization_id__in=org_hierarchy_pks,
        is_active=True
    ).select_related('action', 'from_status', 'to_status', 'organization').prefetch_related('allowed_posts')
    
    termination_rules = []
    
    for transition in all_transitions:
        # بررسی اینکه آیا این گذار منجر به خاتمه می‌شود
        is_termination = (
            transition.to_status.is_final_approve or 
            transition.to_status.is_final_reject or
            transition.action.code in ['FINAL_APPROVE', 'FINAL_REJECT', 'TERMINATE']
        )
        
        if is_termination:
            # دریافت پست‌های مجاز
            allowed_posts = list(transition.allowed_posts.all())
            
            # دریافت کاربران فعال در این پست‌ها
            active_users = []
            if allowed_posts:
                userposts = UserPost.objects.filter(
                    post__in=allowed_posts,
                    is_active=True
                ).select_related('user', 'post')
                
                seen_user_ids = set()
                for up in userposts:
                    if up.user and up.user_id not in seen_user_ids:
                        seen_user_ids.add(up.user_id)
                        active_users.append({
                            'user': up.user,
                            'post': up.post,
                            'organization': up.post.organization
                        })
            
            termination_rules.append({
                'transition': transition,
                'action': transition.action,
                'from_status': transition.from_status,
                'to_status': transition.to_status,
                'organization': transition.organization,
                'posts': allowed_posts,
                'users': active_users,
                'is_final_approve': transition.to_status.is_final_approve,
                'is_final_reject': transition.to_status.is_final_reject,
                'termination_type': 'approve' if transition.to_status.is_final_approve else 'reject'
            })
    
    return termination_rules


def get_post_rules_per_branch(factor):
    """
    بررسی قوانین هر پست در هر شعبه برای فاکتور
    """
    if not factor.tankhah or not factor.tankhah.organization:
        return []
    
    # جمع‌آوری تمام سازمان‌های والد
    org_hierarchy_pks = []
    current_org = factor.tankhah.organization
    while current_org:
        org_hierarchy_pks.append(current_org.pk)
        current_org = current_org.parent_organization
    
    # گرفتن تمام گذارها برای سازمان‌ها
    all_transitions = Transition.objects.filter(
        entity_type__code='FACTOR',
        organization_id__in=org_hierarchy_pks,
        is_active=True
    ).select_related('action', 'from_status', 'to_status', 'organization').prefetch_related('allowed_posts')
    
    # گروه‌بندی بر اساس پست و سازمان
    post_rules = {}
    
    for transition in all_transitions:
        for post in transition.allowed_posts.all():
            key = f"{post.id}_{post.organization.id}"
            if key not in post_rules:
                post_rules[key] = {
                    'post': post,
                    'organization': post.organization,
                    'transitions': [],
                    'actions': set(),
                    'from_statuses': set(),
                    'to_statuses': set()
                }
            
            post_rules[key]['transitions'].append(transition)
            post_rules[key]['actions'].add(transition.action.name)
            post_rules[key]['from_statuses'].add(transition.from_status.name)
            post_rules[key]['to_statuses'].add(transition.to_status.name)
    
    # تبدیل set ها به list برای JSON serialization
    for key, data in post_rules.items():
        data['actions'] = list(data['actions'])
        data['from_statuses'] = list(data['from_statuses'])
        data['to_statuses'] = list(data['to_statuses'])
    
    return list(post_rules.values())


@login_required
def api_factor_approval_path(request, factor_id):
    """
    API برای دریافت مسیر تأیید فاکتور
    """
    try:
        factor = get_object_or_404(Factor, id=factor_id)
        
        # بررسی دسترسی کاربر
        temp_view = PermissionBaseView()
        if not temp_view.has_permission(request.user, factor.tankhah.organization):
            return JsonResponse({
                'success': False,
                'message': 'شما دسترسی به این فاکتور ندارید.'
            })
        
        # ساخت مسیر تأیید
        approval_path = get_detailed_approval_path(factor, request.user)
        
        # تاریخچه تأییدات
        approval_history = []
        for log in factor.approval_logs.all():
            approval_history.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user.id if log.user else None,
                'username': log.user.username if log.user else None,
                'user_full_name': log.user.get_full_name() if log.user else None,
                'post_id': log.post.id if log.post else None,
                'post_name': log.post.name if log.post else None,
                'action_id': log.action.id if log.action else None,
                'action_name': log.action.name if log.action else None,
                'from_status_id': log.from_status.id if log.from_status else None,
                'from_status_name': log.from_status.name if log.from_status else None,
                'to_status_id': log.to_status.id if log.to_status else None,
                'to_status_name': log.to_status.name if log.to_status else None,
                'comment': log.comment
            })
        
        # آمار مسیر
        path_stats = get_approval_path_statistics(factor)
        
        # تحلیل اقدامات تکراری
        duplicate_actions = get_duplicate_actions_analysis(factor)
        
        # قوانین خاتمه
        termination_rules = get_termination_rules(factor)
        
        # قوانین پست‌ها در هر شعبه
        post_rules_per_branch = get_post_rules_per_branch(factor)
        
        return JsonResponse({
            'success': True,
            'factor_id': factor.id,
            'current_status_id': factor.status.id if factor.status else None,
            'current_status_name': factor.status.name if factor.status else None,
            'approval_path': approval_path,
            'approval_history': approval_history,
            'path_statistics': path_stats,
            'duplicate_actions': duplicate_actions,
            'termination_rules': termination_rules,
            'post_rules_per_branch': post_rules_per_branch
        })
        
    except Exception as e:
        logger.error(f"خطا در دریافت مسیر تأیید فاکتور: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت مسیر تأیید: {str(e)}'
        })