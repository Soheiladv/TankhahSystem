from collections import defaultdict, OrderedDict
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.db.models import Sum, F, Prefetch
from django.utils import timezone
from django.contrib import messages
from django.views.generic import DetailView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
import logging

from budgets.budget_calculations import get_committed_budget, get_tankhah_available_budget
from core.PermissionBase import PermissionBaseView
from core.models import Transition, UserPost
from django.db import models
from tankhah.models import Factor, ApprovalLog, FactorDocument


from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.views.generic import DetailView

logger = logging.getLogger(__name__)

# Helper: resolve EntityType code for Factor dynamically to avoid hardcoding
def _get_factor_entity_type_code():
    try:
        from django.contrib.contenttypes.models import ContentType
        from core.models import EntityType
        ct = ContentType.objects.get_for_model(Factor)
        et = EntityType.objects.filter(content_type=ct).first()
        return et.code if et else 'FACTOR'
    except Exception:
        return 'FACTOR'

# ===================================================================
# ۱. توابع کمکی مشترک
# ===================================================================

def get_next_steps_with_posts(factor, include_final_reject=False):
    """
    محاسبه اقدامات بعدی و کاربران مسئول برای یک فاکتور.
    شامل مسیر کامل گردش کار و افراد مسئول است.
    """
    if not factor.status or not factor.tankhah or not factor.tankhah.organization:
        logger.warning(f"Factor {factor.pk} has no status or tankhah or organization")
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
    ).select_related('action', 'from_status', 'to_status').prefetch_related('allowed_posts')

    transitions_map = defaultdict(list)
    seen_actions = set()  # برای جلوگیری از تکرار اقدامات مشابه
    
    for t in all_transitions:
        # جلوگیری از تکرار بر اساس ترکیب action و from_status
        action_key = (t.action.id, t.from_status_id)
        if action_key in seen_actions:
            continue
        seen_actions.add(action_key)
        transitions_map[t.from_status_id].append(t)

    path = []
    current_status = factor.status
    visited_statuses = {current_status.pk}

    # مرتب‌سازی پست‌ها بر اساس can_final_approve_factor سپس سطح/نام از مدل Post
    def _sort_posts(posts):
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
        next_possible_transitions = transitions_map.get(current_status.pk, [])
        if not next_possible_transitions:
            break

        main_transition = next(
            (t for t in sorted(next_possible_transitions, key=lambda x: x.id)
             if include_final_reject or not t.to_status.is_final_reject),
            None
        )
        if not main_transition:
            break

        posts_list = list(main_transition.allowed_posts.all())
        # fallback 1: اگر پست مشخص نشده، از PostRuleAssignment استفاده کن
        if not posts_list:
            try:
                from core.models import PostRuleAssignment as _PRA, Post as _Post
                pra_post_ids = list(_PRA.objects.filter(
                    is_active=True,
                    organization_id=main_transition.organization_id,
                    action_id=main_transition.action_id,
                    entity_type='FACTOR'
                ).values_list('post_id', flat=True))
                if pra_post_ids:
                    posts_list = list(_Post.objects.filter(id__in=pra_post_ids, is_active=True))
            except Exception:
                pass
        # fallback 2: اگر PRA هم نبود، تمام پست‌های فعال سازمان
        if not posts_list and getattr(main_transition, 'organization_id', None):
            try:
                from core.models import Post as _Post
                posts_list = list(_Post.objects.filter(organization_id=main_transition.organization_id, is_active=True))
            except Exception:
                pass
        posts_list = _sort_posts(posts_list)
        path.append({
            'action': main_transition.action,
            'from_status': current_status,
            'to_status': main_transition.to_status,
            'posts': posts_list
        })

        logger.debug(f"Factor {factor.pk} next step: {main_transition.action} -> {main_transition.to_status} with posts {[p.name for p in posts_list]}")

        current_status = main_transition.to_status
        if current_status.pk in visited_statuses:
            break
        visited_statuses.add(current_status.pk)

    return path


def get_user_allowed_transitions(user, factor):
    """
    لیست گذارهای مجاز برای کاربر و فاکتور مشخص
    
    این تابع:
    1. بررسی می‌کند که فاکتور، تنخواه و سازمان معتبر باشد
    2. سازمان‌های قابل دسترسی کاربر را از طریق PermissionBaseView دریافت می‌کند
    3. ترنزیشن‌های فعال از وضعیت فعلی فاکتور را برای سازمان‌های مجاز فیلتر می‌کند
    4. بررسی می‌کند که کاربر در پست‌های مجاز برای هر ترنزیشن باشد
    5. قانون قفل‌شدن سطح پایین پس از اقدام سطح بالاتر را اعمال می‌کند
    
    Args:
        user: کاربر درخواست‌کننده
        factor: فاکتور مورد نظر
        
    Returns:
        list: لیست ترنزیشن‌های مجاز برای کاربر
    """
    from core.models import Transition, UserPost, Post
    from core.PermissionBase import PermissionBaseView
    
    # اگر وضعیت/تنخواه/سازمان تعریف نشده باشد، اقدامی مجاز نیست
    if not getattr(factor, 'status', None) or not getattr(factor, 'tankhah', None) or not getattr(factor.tankhah, 'organization', None):
        logger.warning(f"Factor {factor.pk} missing required fields: status, tankhah, or organization")
        return []

    # استفاده از PermissionBaseView برای دریافت سازمان‌های مجاز کاربر
    temp_view = PermissionBaseView()
    user_org_ids = temp_view.get_user_active_organizations(user)
    
    if not user_org_ids:
        logger.warning(f"User {user.username} has no active organizations")
        return []

    # دریافت تمام ترنزیشن‌های فعال از وضعیت فعلی فاکتور برای سازمان‌های مجاز کاربر
    et_code = _get_factor_entity_type_code()
    transitions_qs = Transition.objects.filter(
        entity_type__code=et_code,
        from_status=factor.status,
        organization_id__in=user_org_ids,
        is_active=True,
    ).select_related('action', 'from_status', 'to_status').prefetch_related('allowed_posts')

    # بارگذاری تنظیمات سیستم
    try:
        from core.models import SystemSettings
        sys_settings = SystemSettings.objects.first()
    except Exception:
        sys_settings = None

    # برای ادمین: همه ترنزیشن‌ها مجازند (مگر اینکه enforce_strict_approval_order فعال و bypass غیرفعال باشد)
    if user.is_superuser:
        if sys_settings and getattr(sys_settings, 'enforce_strict_approval_order', False):
            # سوپراگر enforce فعال است هم باید از لاگ سطح بالاتر عبور نکند مگر bypass روشن باشد
            if sys_settings and getattr(sys_settings, 'allow_bypass_org_chart', False):
                result = list(transitions_qs)
                logger.info(f"Superuser {user.username} allowed transitions (bypass enabled): {[t.action.name for t in result]}")
                return result
        else:
            result = list(transitions_qs)
            logger.info(f"Superuser {user.username} allowed transitions: {[t.action.name for t in result]}")
            return result

    # شناسه پست‌های فعال کاربر
    user_post_ids_set = set()
    user_levels = []
    if user.is_authenticated:
        active_userposts = user.userpost_set.filter(is_active=True).select_related('post')
        user_post_ids_set = set(active_userposts.values_list('post_id', flat=True))
        user_levels = [up.post.level for up in active_userposts if getattr(up.post, 'level', None) is not None]

    # قانون قفل‌شدن سطح پایین پس از اقدام سطح بالاتر (کنترل‌شده با SystemSettings)
    if sys_settings and getattr(sys_settings, 'enforce_strict_approval_order', False):
        if not (sys_settings and getattr(sys_settings, 'allow_bypass_org_chart', False)):
            if user_levels:
                try:
                    user_min_level = min(user_levels)  # سطح بالاتر عدد کمتر است
                    higher_action_exists = factor.approval_logs.filter(post__level__lt=user_min_level).exists()
                    if higher_action_exists:
                        logger.info(f"User {user.username} blocked by higher-level action (strict order enforced). user_min_level={user_min_level}")
                        return []
                except Exception as e:
                    logger.debug(f"Level-block check failed: {e}")

    # تشخیص ترنزیشن‌های مجاز بر اساس پست‌های مجاز
    allowed = []
    seen_actions = set()  # برای جلوگیری از تکرار اقدامات مشابه
    
    from core.models import PostRuleAssignment as _PRA

    for t in transitions_qs:
        # جلوگیری از تکرار بر اساس ترکیب action و from_status
        action_key = (t.action.id, t.from_status.id)
        if action_key in seen_actions:
            logger.debug(f"Skipping duplicate action {t.action.name} for status {t.from_status.name}")
            continue
        seen_actions.add(action_key)
        
        # اگر ترنزیشن پست‌های مجاز ندارد، از تخصیص‌های پست (PostRuleAssignment) استفاده کن
        allowed_posts = list(t.allowed_posts.all())
        if not allowed_posts:
            pra_post_ids = list(_PRA.objects.filter(
                is_active=True,
                organization_id=t.organization_id,
                action_id=t.action_id,
                entity_type=et_code
            ).values_list('post_id', flat=True))
            if pra_post_ids:
                # اگر PRA وجود دارد، صرفاً کاربران با پست‌های PRA مجازند
                if not user_post_ids_set.isdisjoint(set(pra_post_ids)):
                    allowed.append(t)
                    logger.debug(f"Added transition via PRA posts: {t.action.name}")
                else:
                    logger.debug(f"Skipped transition - user not in PRA posts: {t.action.name}")
                continue
            else:
                # عمومی تلقی می‌شود
                if not (sys_settings and getattr(sys_settings, 'allow_action_without_org_chart', False)):
                    if not user_post_ids_set:
                        logger.debug(f"Skipped public transition due to no user posts and org-chart required: {t.action.name}")
                        continue
                allowed.append(t)
                logger.debug(f"Added public transition (no allowed_posts and no PRA): {t.action.name}")
                continue
            
        # بررسی اینکه کاربر در پست‌های مجاز باشد
        allowed_post_ids = {p.id for p in allowed_posts}
        if not user_post_ids_set.isdisjoint(allowed_post_ids):
            allowed.append(t)
            logger.debug(f"Added transition for user posts: {t.action.name}")
        else:
            logger.debug(f"Skipped transition - user not in allowed posts: {t.action.name}")

    # مرتب‌سازی ترنزیشن‌ها بر اساس can_final_approve_factor سپس سطح پست
    def _sort_transitions(transitions):
        def _get_transition_priority(transition):
            # دریافت پست‌های مجاز برای این ترنزیشن
            allowed_posts = list(transition.allowed_posts.all())
            if not allowed_posts:
                # اگر پست‌های مجاز ندارند، از PRA استفاده کن
                pra_post_ids = list(_PRA.objects.filter(
                    is_active=True,
                    organization_id=transition.organization_id,
                    action_id=transition.action_id,
                    entity_type=et_code
                ).values_list('post_id', flat=True))
                if pra_post_ids:
                    allowed_posts = list(Post.objects.filter(id__in=pra_post_ids, is_active=True))
                else:
                    # اگر PRA هم ندارند، تمام پست‌های سازمان
                    allowed_posts = list(Post.objects.filter(organization_id=transition.organization_id, is_active=True))
            
            # بررسی اینکه آیا پست‌هایی با can_final_approve_factor=True وجود دارند
            has_final_approve = any(getattr(p, 'can_final_approve_factor', False) for p in allowed_posts)
            min_level = min([getattr(p, 'level', 9999) or 9999 for p in allowed_posts], default=9999)
            
            # اگر پست‌هایی با can_final_approve_factor=True وجود دارند، اولویت با آنها
            if has_final_approve:
                return (0, min_level, transition.id)  # 0 برای اولویت بالا
            else:
                return (1, min_level, transition.id)  # 1 برای اولویت پایین
        
        try:
            transitions.sort(key=_get_transition_priority)
        except Exception as e:
            logger.warning(f"Error sorting transitions: {e}")
        
        return transitions

    # مرتب‌سازی ترنزیشن‌های مجاز
    allowed = _sort_transitions(allowed)
    
    logger.info(f"User {user.username} allowed transitions: {[t.action.name for t in allowed]}")
    return allowed


# ===================================================================
# ۲. API برای انجام اقدام روی فاکتور
# ===================================================================

class PerformFactorTransitionAPI(APIView):
    def post(self, request, pk, transition_id):
        factor = get_object_or_404(Factor, pk=pk)
        target_transition = get_object_or_404(Transition, pk=transition_id)
        comment = request.data.get('comment', '')
        user = request.user

        logger.info(f"API: Attempting transition '{target_transition.name}' on Factor {factor.pk} by user {user.username}")

        # بررسی وضعیت فعلی فاکتور
        if factor.status != target_transition.from_status:
            logger.error(f"Transition Mismatch: Factor {factor.pk} is in status '{factor.status.name}' but transition expects '{target_transition.from_status.name}'.")
            return Response(
                {'error': "این اقدام در وضعیت فعلی فاکتور مجاز نیست. لطفاً صفحه را رفرش کنید."},
                status=status.HTTP_409_CONFLICT
            )

        try:
            with transaction.atomic():
                original_status = factor.status
                factor.status = target_transition.to_status
                factor.save(update_fields=['status'])
                logger.info(f"Factor {factor.pk} status changed from '{original_status.name}' to '{target_transition.to_status.name}'.")

                user_post = user.userpost_set.filter(is_active=True).first()
                ApprovalLog.objects.create(
                    factor=factor,
                    content_object=factor,
                    from_status=original_status,
                    to_status=target_transition.to_status,
                    action=target_transition.action,
                    user=user,
                    post=(user_post.post if user_post else None),
                    comment=comment,
                    created_by=user
                )

        except ValidationError as e:
            logger.error(f"Validation error during transition for factor {factor.pk}: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Critical error in PerformFactorTransitionAPI for factor {factor.pk}: {e}", exc_info=True)
            return Response({'error': "خطای پیش‌بینی نشده در سرور رخ داد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': f"فاکتور با موفقیت به وضعیت '{target_transition.to_status.name}' تغییر یافت.",
            'new_status': target_transition.to_status.name
        }, status=status.HTTP_200_OK)

# ===================================================================
# ۳. ویوی جزئیات فاکتور
# ===================================================================

class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Factors/Detials/factor_detail.html'
    context_object_name = 'factor'
    permission_codename = ['factor_view','factor_update','factor_reject','factor_approve']
    check_organization = True

    def get_queryset(self):
        return Factor.objects.select_related(
            'tankhah', 'tankhah__organization', 'created_by', 'status',
            'tankhah__project_budget_allocation',
            'tankhah__project_budget_allocation__budget_period',
            'tankhah__project_budget_allocation__budget_item'
        ).prefetch_related(
            'items',
            Prefetch('documents', queryset=FactorDocument.objects.select_related('uploaded_by')),
            Prefetch('approval_logs', queryset=ApprovalLog.objects.order_by('-timestamp').select_related(
                'user', 'post', 'from_status', 'to_status', 'action'
            ))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user

        # خلاصه بودجه
        if factor.tankhah:
            context['tankhah_budget_summary'] = self._compute_tankhah_budget_summary(factor.tankhah)

        # مسیر تأیید کامل
        from tankhah.Factor.views_factor_approval_path import (
            get_detailed_approval_path, 
            get_approval_path_statistics,
            get_duplicate_actions_analysis,
            get_termination_rules,
            get_post_rules_per_branch
        )
        
        context['approval_path'] = get_detailed_approval_path(factor, user)
        context['path_stats'] = get_approval_path_statistics(factor)
        context['duplicate_actions'] = get_duplicate_actions_analysis(factor)
        context['termination_rules'] = get_termination_rules(factor)
        context['post_rules_per_branch'] = get_post_rules_per_branch(factor)

        # اقدامات مجاز و مسیر گردش کار
        if not factor.status or not getattr(factor, 'tankhah', None) or not getattr(factor.tankhah, 'organization', None):
            logger.warning(
                "[FACTOR_DETAIL] Missing essentials -> status:%s tankhah:%s org:%s",
                getattr(factor, 'status', None), bool(getattr(factor, 'tankhah', None)),
                bool(getattr(getattr(factor, 'tankhah', None), 'organization', None))
            )
        full_path = get_next_steps_with_posts(factor)
        context['full_workflow_path'] = full_path
        context['available_transitions'] = get_user_allowed_transitions(user, factor)

        # مسیر تأیید برای تمپلیت موجود (با برچسب کاربر)
        try:
            user_post_ids = set()
            if user.is_authenticated:
                user_post_ids = set(
                    user.userpost_set.filter(is_active=True).values_list('post_id', flat=True)
                )
            approval_path = []
            for step in full_path:
                posts = step.get('posts', [])
                is_user_in_post = any(getattr(p, 'id', None) in user_post_ids for p in posts)
                approval_path.append({
                    'action': step.get('action'),
                    'from_status': step.get('from_status'),
                    'to_status': step.get('to_status'),
                    'posts': posts,
                    'is_user_in_post': is_user_in_post,
                })
            context['approval_path'] = approval_path
        except Exception as e:
            logger.error("[FACTOR_DETAIL] Building approval_path failed: %s", e, exc_info=True)
            context['approval_path'] = []

        # هم‌نام‌سازی برای تمپلیت "budget_summary"
        if 'tankhah_budget_summary' in context:
            context['budget_summary'] = context['tankhah_budget_summary']

        # استخراج کاربران فعال هر پست برای گام‌های بعدی (نمایش افراد موثر)
        next_approvers_by_step = []
        workflow_participants = []
        for step in full_path:
            posts_list = step.get('posts', [])
            if not posts_list:
                next_approvers_by_step.append({
                    'action': step.get('action'),
                    'to_status': step.get('to_status'),
                    'users': []
                })
                workflow_participants.append({
                    'action': step.get('action'),
                    'to_status': step.get('to_status'),
                    'posts': []
                })
                continue

            userposts_qs = UserPost.objects.filter(
                post__in=posts_list,
                is_active=True
            ).select_related('user', 'post')

            seen_user_ids = set()
            users = []
            posts_info = []
            for up in userposts_qs:
                if up.user and up.user_id not in seen_user_ids:
                    seen_user_ids.add(up.user_id)
                    users.append(up.user)
            # جمع آوری اطلاعات هر پست (سطح و کاربرانش)
            for p in posts_list:
                p_users = [up.user for up in userposts_qs if up.post_id == p.id and up.user_id]
                posts_info.append({'post': p, 'level': getattr(p, 'level', None), 'users': p_users})

            next_approvers_by_step.append({
                'action': step.get('action'),
                'to_status': step.get('to_status'),
                'users': users
            })

        context['next_approvers_by_step'] = next_approvers_by_step

        # لاگ‌های شمارشی برای عیب‌یابی سریع
        transitions_str = [f"{s['action'].name}->{s['to_status'].name}" for s in full_path]
        logger.info(
            "[FACTOR_DETAIL] factor=%s status=%s org=%s path_len=%d allowed_len=%d next_users_steps=%d",
            factor.pk,
            getattr(getattr(factor, 'status', None), 'code', None),
            getattr(getattr(getattr(factor, 'tankhah', None), 'organization', None), 'pk', None),
            len(full_path),
            len(context['available_transitions']) if context.get('available_transitions') is not None else -1,
            len(next_approvers_by_step)
        )
        logger.debug("[FACTOR_DETAIL] full_workflow_path=%s", transitions_str)

        # سایر اطلاعات
        context['approval_logs'] = factor.approval_logs.all()
        context['factor_impact'] = self._compute_factor_impact(factor)
        context['is_payment_ready'] = factor.status.is_final_approve if factor.status else False

        # محاسبه جمع اقلام برای نمایش در فوتر جدول
        try:
            items_qs = getattr(factor, 'items', None)
            if items_qs is not None:
                items_total = sum([(itm.amount or Decimal('0')) for itm in items_qs.all()])
                context['items_total'] = items_total
        except Exception:
            context['items_total'] = Decimal('0')

        return context

    # -----------------------------------------------------------------
    # متدهای کمکی
    # -----------------------------------------------------------------
    def _compute_tankhah_budget_summary(self, tankhah):
        key = f"tankhah_budget_summary:{tankhah.pk}"
        cached = cache.get(key)
        if cached:
            return cached

        initial = tankhah.amount or Decimal('0')
        paid_total = tankhah.factors.filter(status__code='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        committed = get_committed_budget(tankhah)
        available = Decimal(get_tankhah_available_budget(tankhah))
        balance = initial - paid_total

        summary_data = {'initial': initial, 'paid': paid_total, 'committed': committed, 'balance': balance, 'available': available}

        if initial > 0:
            summary_data['paid_percentage'] = ((paid_total / initial) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
            summary_data['committed_percentage'] = ((committed / initial) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        else:
            summary_data['paid_percentage'] = Decimal('0')
            summary_data['committed_percentage'] = Decimal('0')

        cache.set(key, summary_data, 60)
        return summary_data

    def _compute_factor_impact(self, factor):
        code = getattr(factor.status, 'code', 'DRAFT') or 'DRAFT'
        mapping = {
            'PENDING_APPROVAL': ('committed', 'تعهدی (در انتظار پرداخت)', 'warning'),
            'APPROVED': ('committed', 'تعهدی (تأیید شده)', 'primary'),
            'PAID': ('paid', 'هزینه قطعی (پرداخت شده)', 'success'),
            'REJECTED': ('rejected', 'رد شده (بدون تاثیر مالی)', 'danger'),
            'DRAFT': ('draft', 'پیش‌نویس (بدون تاثیر مالی)', 'light'),
        }
        typ, label, klass = mapping.get(code, ('none', 'نامشخص', 'secondary'))
        return {'type': typ, 'label': label, 'class': klass}


# from collections import defaultdict, OrderedDict
# from decimal import Decimal, ROUND_HALF_UP
#
# from django.core.cache import cache
# from django.shortcuts import get_object_or_404, redirect
# from django.db import transaction
# from django.db.models import Sum, F, Prefetch
# from django.utils import timezone
# from django.contrib import messages
# from django.views.generic import DetailView
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.core.exceptions import ValidationError
# import logging
#
# from budgets.budget_calculations import get_committed_budget, get_tankhah_available_budget
# from core.PermissionBase import PermissionBaseView
# from core.models import Transition
# from tankhah.models import Factor, ApprovalLog, FactorDocument
#
# logger = logging.getLogger(__name__)
#
# # ===================================================================
# # ۱. تابع دریافت گذارهای مجاز کاربر
# # ===================================================================
# def get_user_allowed_transitions(user, factor):
#     """
#     یک تابع مستقل که لیست Transition های مجاز برای یک کاربر و فاکتور خاص را برمی‌گرداند.
#     """
#     tankhah = factor.tankhah
#     org = getattr(tankhah, 'organization', None)
#
#     if not user.is_authenticated or not org or not factor.status:
#         return []
#
#     qs = Transition.objects.filter(
#         entity_type__code='FACTOR',
#         from_status=factor.status,
#         organization=org,
#         is_active=True
#     ).select_related('action', 'to_status').prefetch_related('allowed_posts')
#
#     if user.is_superuser:
#         return list(qs)
#
#     # فقط یکبار گرفتن شناسه‌های پست کاربر
#     user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post', flat=True))
#     if not user_post_ids:
#         return []
#
#     return list(qs.filter(allowed_posts__id__in=user_post_ids).distinct())
#
# # ===================================================================
# # ۲. API برای انجام اقدام روی فاکتور
# # ===================================================================
# class PerformFactorTransitionAPI(APIView):
#     def post(self, request, pk, transition_id):
#         factor = get_object_or_404(Factor, pk=pk)
#         target_transition = get_object_or_404(Transition, pk=transition_id)
#         comment = request.data.get('comment', '')
#         user = request.user
#
#         logger.info(f"API: Attempting transition '{target_transition.name}' on Factor {factor.pk} by user {user.username}")
#
#         if factor.status != target_transition.from_status:
#             logger.error(f"Transition Mismatch: Factor {factor.pk} is in status '{factor.status.name}' but transition expects '{target_transition.from_status.name}'.")
#             return Response(
#                 {'error': "این اقدام در وضعیت فعلی فاکتور مجاز نیست. لطفاً صفحه را رفرش کنید."},
#                 status=status.HTTP_409_CONFLICT
#             )
#
#         try:
#             with transaction.atomic():
#                 original_status = factor.status
#                 factor.status = target_transition.to_status
#                 factor.save(update_fields=['status'])
#                 logger.info(f"Factor {factor.pk} status changed from '{original_status.name}' to '{target_transition.to_status.name}'.")
#
#                 user_post = user.userpost_set.filter(is_active=True).first()
#                 ApprovalLog.objects.create(
#                     factor=factor,
#                     content_object=factor,
#                     from_status=original_status,
#                     to_status=target_transition.to_status,
#                     action=target_transition.action,
#                     user=user,
#                     post=(user_post.post if user_post else None),
#                     comment=comment,
#                     created_by=user
#                 )
#
#         except ValidationError as e:
#             logger.error(f"Validation error during transition for factor {factor.pk}: {e}", exc_info=True)
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             logger.error(f"Critical error in PerformFactorTransitionAPI for factor {factor.pk}: {e}", exc_info=True)
#             return Response({'error': "خطای پیش‌بینی نشده در سرور رخ داد."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#         return Response({
#             'success': True,
#             'message': f"فاکتور با موفقیت به وضعیت '{target_transition.to_status.name}' تغییر یافت.",
#             'new_status': target_transition.to_status.name
#         }, status=status.HTTP_200_OK)
#
# # ===================================================================
# # ۳. ویو جزئیات فاکتور
# # ===================================================================
# # در فایل views.py
#
# # ... (سایر import های شما)
# from collections import defaultdict
# from django.db.models import Prefetch
#
#
# # ===================================================================
# # ویوی جزئیات فاکتور (نسخه نهایی، پاکسازی و اصلاح شده)
# # ===================================================================
# class FactorDetailView(PermissionBaseView, DetailView):
#     model = Factor
#     template_name = 'tankhah/Factors/Detials/factor_detail.html'
#     context_object_name = 'factor'
#     permission_codename = 'tankhah.factor_view'
#     check_organization = True
#
#     def get_queryset(self):
#         # این کوئری بهینه و کامل است و نیازی به تغییر ندارد
#         return Factor.objects.select_related(
#             'tankhah', 'tankhah__organization', 'created_by', 'status',
#             'tankhah__project_budget_allocation',
#             'tankhah__project_budget_allocation__budget_period',
#             'tankhah__project_budget_allocation__budget_item'
#         ).prefetch_related(
#             'items',
#             Prefetch('documents', queryset=FactorDocument.objects.select_related('uploaded_by')),
#             Prefetch('approval_logs', queryset=ApprovalLog.objects.order_by('-timestamp').select_related(
#                 'user', 'post', 'from_status', 'to_status', 'action'
#             ))
#         )
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         factor = self.object
#         user = self.request.user
#
#         # محاسبه خلاصه بودجه
#         if factor.tankhah:
#             context['tankhah_budget_summary'] = self._compute_tankhah_budget_summary(factor.tankhah)
#
#         # اقدامات بعدی و مسئولین
#         full_path = get_next_steps_with_posts(factor)
#         context['full_workflow_path'] = full_path
#
#         # اقدامات مجاز برای کاربر
#         allowed_transitions = []
#         user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
#         for step in full_path:
#             allowed_posts_ids = {p.id for p in step['posts']}
#             if user.is_superuser or not allowed_posts_ids.isdisjoint(user_post_ids):
#                 allowed_transitions.append(step)
#         context['available_transitions'] = allowed_transitions
#
#         # log برای بررسی
#         logger.info(f"Factor {factor.pk} available_transitions: {[t['action'].name for t in allowed_transitions]}")
#
#         # سایر اطلاعات
#         context['approval_logs'] = factor.approval_logs.all()
#         context['factor_impact'] = self._compute_factor_impact(factor)
#         context['is_payment_ready'] = factor.status.is_final_approve if factor.status else False
#
#         # --- ۱. محاسبه و افزودن خلاصه بودجه ---
#         if factor.tankhah:
#             context['tankhah_budget_summary'] = self._compute_tankhah_budget_summary(factor.tankhah)
#
#         #
#         # # --- ۳. محاسبه مسیر کامل گردش کار ---
#         # context['full_workflow_path'] = self._get_full_workflow_path(factor)
#
#         # --- ۴. سایر اطلاعات مورد نیاز تمپلیت ---
#         context['approval_logs'] = factor.approval_logs.all()  # از prefetch استفاده می‌شود
#         context['factor_impact'] = self._compute_factor_impact(factor)
#         context['is_payment_ready'] = factor.status.is_final_approve if factor.status else False
#
#         return context
#
#     def _get_full_workflow_path(self, factor):
#         if not factor.status:
#             return []
#
#         org_hierarchy_pks = []
#         current_org = factor.tankhah.organization
#         if current_org:
#             org_hierarchy_pks.append(current_org.pk)
#             while current_org.parent_organization:
#                 current_org = current_org.parent_organization
#                 org_hierarchy_pks.append(current_org.pk)
#
#         all_transitions = Transition.objects.filter(
#             entity_type__code='FACTOR',
#             organization_id__in=org_hierarchy_pks,
#             is_active=True
#         ).select_related('action', 'from_status', 'to_status').prefetch_related('allowed_posts')
#
#         transitions_map = defaultdict(list)
#         for t in all_transitions:
#             transitions_map[t.from_status_id].append(t)
#
#         path = []
#         current_status = factor.status
#         visited_statuses = {current_status.pk}
#
#         while current_status and not current_status.is_final_approve and not current_status.is_final_reject:
#             next_possible_transitions = transitions_map.get(current_status.pk, [])
#             if not next_possible_transitions:
#                 break
#
#             main_transition = next((t for t in sorted(next_possible_transitions, key=lambda x: x.id)
#                                     if not t.to_status.is_final_reject), None)
#             if not main_transition:
#                 break
#
#             path.append({
#                 'action': main_transition.action,
#                 'to_status': main_transition.to_status,
#                 'posts': list(main_transition.allowed_posts.all())
#             })
#
#             current_status = main_transition.to_status
#             if current_status.pk in visited_statuses:
#                 break
#             visited_statuses.add(current_status.pk)
#
#         return path
#
#     # متدهای کمکی _compute_tankhah_budget_summary و _compute_factor_impact را اینجا کپی کنید
#     # (آنها صحیح بودند و نیازی به تغییر ندارند)
#     def _compute_tankhah_budget_summary(self, tankhah):
#         # ... محتوای این متد را از کد قبلی خود کپی کنید ...
#         key = f"tankhah_budget_summary:{tankhah.pk}"
#         cached = cache.get(key)
#         if cached: return cached
#         initial = tankhah.amount or Decimal('0')
#         paid_total = tankhah.factors.filter(status__code='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         committed = get_committed_budget(tankhah)
#         available = Decimal(get_tankhah_available_budget(tankhah))
#         balance = initial - paid_total
#         summary_data = {'initial': initial, 'paid': paid_total, 'committed': committed, 'balance': balance,
#                         'available': available}
#         if initial > 0:
#             summary_data['paid_percentage'] = ((paid_total / initial) * 100).quantize(Decimal('0.1'),
#                                                                                       rounding=ROUND_HALF_UP) if initial else Decimal(
#                 '0')
#             summary_data['committed_percentage'] = ((committed / initial) * 100).quantize(Decimal('0.1'),
#                                                                                           rounding=ROUND_HALF_UP) if initial else Decimal(
#                 '0')
#
#         else:
#             summary_data['paid_percentage'] = Decimal('0')
#             summary_data['committed_percentage'] = Decimal('0')
#         cache.set(key, summary_data, 60)
#         return summary_data
#
#     def _compute_factor_impact(self, factor):
#         # ... محتوای این متد را از کد قبلی خود کپی کنید ...
#         code = getattr(factor.status, 'code', 'DRAFT') or 'DRAFT'
#         mapping = {
#             'PENDING_APPROVAL': ('committed', 'تعهدی (در انتظار پرداخت)', 'warning'),
#             'APPROVED': ('committed', 'تعهدی (تأیید شده)', 'primary'),
#             'PAID': ('paid', 'هزینه قطعی (پرداخت شده)', 'success'),
#             'REJECTED': ('rejected', 'رد شده (بدون تاثیر مالی)', 'danger'),
#             'DRAFT': ('draft', 'پیش‌نویس (بدون تاثیر مالی)', 'light'),
#         }
#         typ, label, klass = mapping.get(code, ('none', 'نامشخص', 'secondary'))
#         return {'type': typ, 'label': label, 'class': klass}
#
# # ===================================================================
# # ۴. توابع کمکی
# # ===================================================================
# def get_factor_approval_context(factor, user=None):
#     approval_logs = factor.approval_logs.select_related(
#         'user', 'post', 'action', 'from_status', 'to_status'
#     ).order_by('-timestamp')
#
#     next_steps = []
#     allowed_transitions_qs = factor.tankhah.organization.transition_set.filter(
#         entity_type__code='FACTOR',
#         from_status=factor.status,
#         is_active=True
#     ).select_related('action', 'to_status').prefetch_related('allowed_posts')
#
#     if user and not user.is_superuser:
#         user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post', flat=True))
#         allowed_transitions_qs = allowed_transitions_qs.filter(allowed_posts__id__in=list(user_post_ids)).distinct()
#
#     action_map = defaultdict(lambda: {'posts': set(), 'to_status': None})
#     for t in allowed_transitions_qs:
#         action_map[t.action]['posts'].update(t.allowed_posts.all())
#         action_map[t.action]['to_status'] = t.to_status
#
#     for action, info in action_map.items():
#         next_steps.append({'action': action, 'to_status': info['to_status'], 'posts': sorted(info['posts'], key=lambda p: p.name)})
#
#     next_steps = sorted(next_steps, key=lambda x: x['action'].name)
#     return {'approval_logs': approval_logs, 'next_steps_with_posts': next_steps}
#
#
# def get_full_factor_approval_path(factor, user=None):
#     path = []
#     visited_statuses = set()
#     current_status = factor.status
#
#     user_posts_ids = set()
#     if user and user.is_authenticated:
#         user_posts_ids = set(user.userpost_set.filter(is_active=True).values_list('post', flat=True))
#
#     while current_status and current_status.code not in visited_statuses:
#         visited_statuses.add(current_status.code)
#
#         transitions = Transition.objects.filter(
#             entity_type__code='FACTOR',
#             from_status=current_status,
#             organization=factor.tankhah.organization,
#             is_active=True
#         ).select_related('action', 'to_status').prefetch_related('allowed_posts')
#
#         if not transitions.exists():
#             break
#
#         for t in transitions:
#             posts = list(t.allowed_posts.all())
#             path.append({
#                 'action': t.action,
#                 'from_status': current_status,
#                 'to_status': t.to_status,
#                 'posts': posts,
#                 'is_user_in_post': any(p.id in user_posts_ids for p in posts)
#             })
#
#         current_status = transitions.first().to_status
#
#     return path
#
#
# def get_project_tankhah_budget_summary(factor):
#     tankhah = factor.tankhah
#     if not tankhah:
#         return {}
#
#     initial_budget = tankhah.amount or Decimal('0')
#     paid_total = tankhah.factors.filter(status__code='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0')
#     committed_total = sum(f.amount for f in tankhah.factors.filter(status__code='APPROVED'))
#     balance = initial_budget - paid_total
#     available = initial_budget - paid_total - committed_total
#
#     return {
#         'initial': initial_budget,
#         'paid': paid_total,
#         'committed': committed_total,
#         'balance': balance,
#         'available': available,
#         'paid_percentage': ((paid_total / initial_budget) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if initial_budget else 0,
#         'committed_percentage': ((committed_total / initial_budget) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP) if initial_budget else 0,
#     }
#
# def get_next_steps_with_posts(factor, include_final_reject=False):
#     """
#     محاسبه اقدامات بعدی و کاربران مسئول برای یک فاکتور.
#     شامل مسیر کامل گردش کار و افراد مسئول است.
#     """
#     if not factor.status or not factor.tankhah or not factor.tankhah.organization:
#         logger.warning(f"Factor {factor.pk} has no status or tankhah or organization")
#         return []
#
#     # جمع‌آوری تمام سازمان‌های والد
#     org_hierarchy_pks = []
#     current_org = factor.tankhah.organization
#     while current_org:
#         org_hierarchy_pks.append(current_org.pk)
#         current_org = current_org.parent_organization
#
#     # گرفتن تمام گذارها برای سازمان‌ها
#     all_transitions = Transition.objects.filter(
#         entity_type__code='FACTOR',
#         organization_id__in=org_hierarchy_pks,
#         is_active=True
#     ).select_related('action', 'from_status', 'to_status').prefetch_related('allowed_posts')
#
#     transitions_map = defaultdict(list)
#     for t in all_transitions:
#         transitions_map[t.from_status_id].append(t)
#
#     path = []
#     current_status = factor.status
#     visited_statuses = {current_status.pk}
#
#     while current_status:
#         next_possible_transitions = transitions_map.get(current_status.pk, [])
#         if not next_possible_transitions:
#             break
#
#         # انتخاب گذار اصلی که به رد نهایی ختم نمی‌شود مگر اینکه allow final reject
#         main_transition = next(
#             (t for t in sorted(next_possible_transitions, key=lambda x: x.id)
#              if include_final_reject or not t.to_status.is_final_reject),
#             None
#         )
#         if not main_transition:
#             break
#
#         posts_list = list(main_transition.allowed_posts.all())
#         path.append({
#             'action': main_transition.action,
#             'from_status': current_status,
#             'to_status': main_transition.to_status,
#             'posts': posts_list
#         })
#
#         logger.debug(f"Factor {factor.pk} next step: {main_transition.action} -> {main_transition.to_status} with posts {[p.name for p in posts_list]}")
#
#         current_status = main_transition.to_status
#         if current_status.pk in visited_statuses:
#             break
#         visited_statuses.add(current_status.pk)
#
#     return path
