# ===== IMPORTS =====
import logging
from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Q
from django.contrib.auth.mixins import UserPassesTestMixin
from core.models import EntityType, Status, Action, Transition, Post, Organization, UserPost
from accounts.models import CustomUser
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

# ===== MIXIN برای محدودیت دسترسی =====
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        return JsonResponse({'status': 'error', 'message': 'دسترسی غیرمجاز'}, status=403)

# ===== CBV برای گزارش دسترسی‌های کاربر =====
class UserPermissionReportView(StaffRequiredMixin, View):
    template_name = 'reports/TransitionAccess/user_permission_report_enhanced.html'

    def get(self, request, user_id=None):
        # گرفتن user_id از URL یا GET
        user_id = user_id or request.GET.get('user_id')
        users = CustomUser.objects.filter(is_active=True)

        if user_id:
            user = get_object_or_404(CustomUser, pk=user_id)
        else:
            user = users.first()

        if not user:
            messages.warning(request, "کاربر فعالی یافت نشد.")
            return render(request, self.template_name, {
                'users': users,
                'organizations': Organization.objects.filter(is_active=True),
            })

        # پست‌های فعال کاربر
        user_post_ids = UserPost.objects.filter(user=user, is_active=True, post__is_active=True)\
                                       .values_list('post_id', flat=True)
        user_posts_qs = Post.objects.filter(id__in=user_post_ids).select_related('organization')

        # کشینگ ترنزیشن‌ها
        cache_key = f"user_transitions_{user.id}"
        transitions = cache.get(cache_key)
        if transitions is None:
            transitions = Transition.objects.filter(is_active=True)\
                            .select_related('entity_type', 'from_status', 'to_status', 'action', 'organization')\
                            .prefetch_related('allowed_posts').distinct()
            cache.set(cache_key, transitions, timeout=300)

        # محاسبه has_access
        user_post_set = set(user_post_ids)
        accessible_count = 0
        inaccessible_count = 0
        for t in transitions:
            allowed_post_ids = set(t.allowed_posts.values_list('id', flat=True))
            t.has_access = bool(user_post_set & allowed_post_ids)
            if t.has_access:
                accessible_count += 1
            else:
                inaccessible_count += 1

        # دسترسی‌های جدید PostRuleAssignment
        from core.models import PostRuleAssignment
        user_rule_assignments = PostRuleAssignment.objects.filter(
            post__id__in=user_post_ids,
            is_active=True
        ).select_related('post', 'action', 'organization')

        # آمار دسترسی‌ها
        rule_stats = {
            'total_assignments': user_rule_assignments.count(),
            'payment_order_access': user_rule_assignments.filter(entity_type='PAYMENTORDER').count(),
            'tankhah_access': user_rule_assignments.filter(entity_type='TANKHAH').count(),
            'factor_access': user_rule_assignments.filter(entity_type='FACTOR').count(),
        }

        # اعمال Overrides کاربر (UserRuleOverride)
        from core.models import UserRuleOverride
        overrides = UserRuleOverride.objects.filter(user=user)
        overrides_map = {}
        for o in overrides:
            key = (o.organization_id, o.action_id, o.entity_type_id, o.post_id or 0)
            overrides_map[key] = o.is_enabled

        # برچسب‌گذاری ترنزیشن‌ها با توجه به override ها
        for t in transitions:
            # کلیدهای ممکن (با و بدون پست)
            keys = [
                (t.organization_id, t.action_id, t.entity_type_id, pid)
                for pid in user_post_ids
            ] + [
                (t.organization_id, t.action_id, t.entity_type_id, 0)
            ]
            for k in keys:
                if k in overrides_map and overrides_map[k] is False:
                    t.has_access = False
                    break

        context = {
            'users': users,
            'user': user,
            'user_posts': user_posts_qs,
            'transitions': transitions,
            'organizations': Organization.objects.filter(is_active=True),
            'accessible_count': accessible_count,
            'inaccessible_count': inaccessible_count,
            'user_rule_assignments': user_rule_assignments,
            'rule_stats': rule_stats,
        }
        logger.debug(f"Loaded {len(transitions)} transitions for user {user.username}")
        return render(request, self.template_name, context)

# ===== CBV برای فعال/غیرفعال کردن دسترسی ترنزیشن (AJAX) =====
@method_decorator(csrf_exempt, name='dispatch')
class ToggleTransitionAccessView(StaffRequiredMixin, View):

    def post(self, request, user_id, transition_id):
        logger.debug(f"Toggle access called with user_id={user_id}, transition_id={transition_id}")
        user = get_object_or_404(CustomUser, pk=user_id)
        transition = get_object_or_404(Transition, pk=transition_id)

        user_posts = UserPost.objects.filter(user=user, is_active=True, post__is_active=True)\
                                     .values_list('post_id', flat=True)
        action = request.POST.get('action')

        try:
            if action not in ['enable', 'disable']:
                raise ValueError(f"Invalid action: {action}")

            if action == 'enable':
                transition.allowed_posts.add(*user_posts)
                message = f"دسترسی به Transition {transition} برای {user.username} فعال شد."
                logger.info(f"Enabled transition {transition_id} for user {user.username}")
            else:
                transition.allowed_posts.remove(*user_posts)
                message = f"دسترسی به Transition {transition} برای {user.username} غیرفعال شد."
                logger.info(f"Disabled transition {transition_id} for user {user.username}")

            cache.delete(f"user_transitions_{user_id}")
            return JsonResponse({'status': 'success', 'message': message})
        except Exception as e:
            logger.error(f"Error toggling transition {transition_id} for user {user.username}: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f"خطا: {str(e)}"}, status=400)

# ===== CBV گزارش جامع Transition =====
class TransitionAccessReportView(StaffRequiredMixin, View):
    template_name = 'reports/TransitionAccess/transition_access_report.html'

    def get(self, request):
        user_id = request.GET.get('user_id')
        organization_id = request.GET.get('organization_id')
        entity_type_id = request.GET.get('entity_type_id')
        status_id = request.GET.get('status_id')
        page = request.GET.get('page', 1)

        cache_key = f"transition_report_{user_id}_{organization_id}_{entity_type_id}_{status_id}_{page}"
        context = cache.get(cache_key)

        if context is None:
            transitions = Transition.objects.filter(is_active=True)\
                            .select_related('entity_type', 'from_status', 'to_status', 'action', 'organization')\
                            .prefetch_related('allowed_posts')

            if user_id:
                user = get_object_or_404(CustomUser, pk=user_id)
                user_post_ids = UserPost.objects.filter(user=user, is_active=True, post__is_active=True)\
                                               .values_list('post_id', flat=True)
                transitions = transitions.filter(allowed_posts__in=user_post_ids)
            if organization_id:
                transitions = transitions.filter(organization_id=organization_id)
            if entity_type_id:
                transitions = transitions.filter(entity_type_id=entity_type_id)
            if status_id:
                transitions = transitions.filter(Q(from_status_id=status_id) | Q(to_status_id=status_id))

            paginator = Paginator(transitions, 10)
            page_obj = paginator.get_page(page)

            context = {
                'transitions': page_obj,
                'users': CustomUser.objects.filter(is_active=True),
                'organizations': Organization.objects.filter(is_active=True),
                'entity_types': EntityType.objects.all(),
                'statuses': Status.objects.all(),
                'filter_user_id': user_id,
                'filter_organization_id': organization_id,
                'filter_entity_type_id': entity_type_id,
                'filter_status_id': status_id,
            }
            cache.set(cache_key, context, timeout=300)

        logger.debug(f"Loaded comprehensive transition report with filters: user_id={user_id}, org_id={organization_id}")
        return render(request, self.template_name, context)
