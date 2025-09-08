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
    for t in all_transitions:
        transitions_map[t.from_status_id].append(t)

    path = []
    current_status = factor.status
    visited_statuses = {current_status.pk}

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
    """
    # اگر وضعیت/تنخواه/سازمان تعریف نشده باشد، اقدامی مجاز نیست
    if not getattr(factor, 'status', None) or not getattr(factor, 'tankhah', None) or not getattr(factor.tankhah, 'organization', None):
        return []

    # سلسله‌مراتب سازمان (برای ارث‌بری قوانین از سازمان‌های والد)
    org_hierarchy_pks = []
    current_org = factor.tankhah.organization
    while current_org:
        org_hierarchy_pks.append(current_org.pk)
        current_org = getattr(current_org, 'parent_organization', None)

    # دریافت تمام ترنزیشن‌های فعال از وضعیت فعلی فاکتور برای این سازمان/سازمان‌های والد
    transitions_qs = Transition.objects.filter(
        entity_type__code='FACTOR',
        from_status=factor.status,
        organization_id__in=org_hierarchy_pks,
        is_active=True,
    ).select_related('action', 'from_status', 'to_status').prefetch_related('allowed_posts')

    # برای ادمین: همه ترنزیشن‌ها مجازند
    if user.is_superuser:
        result = list(transitions_qs)
        logger.info(f"User {user.username} allowed transitions: {[t.action.name for t in result]}")
        return result

    # شناسه پست‌های فعال کاربر (با درنظر گرفتن end_date)
    user_post_ids = []
    if user.is_authenticated:
        user_post_ids = list(
            user.userpost_set.filter(is_active=True, end_date__isnull=True).values_list('post_id', flat=True)
        )

    # ترنزیشن‌های عمومی (بدون پست) + ترنزیشن‌هایی که با پست‌های کاربر همپوشان دارند
    filtered = transitions_qs.filter(
        models.Q(allowed_posts__isnull=True) | models.Q(allowed_posts__in=user_post_ids)
    ).distinct()

    result = list(filtered)
    logger.info(f"User {user.username} allowed transitions: {[t.action.name for t in result]}")
    return result

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
    permission_codename = 'tankhah.factor_view'
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
                    user.userpost_set.filter(is_active=True, end_date__isnull=True).values_list('post_id', flat=True)
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
                is_active=True,
                end_date__isnull=True
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
            workflow_participants.append({
                'action': step.get('action'),
                'to_status': step.get('to_status'),
                'posts': posts_info
            })

        context['next_approvers_by_step'] = next_approvers_by_step
        context['workflow_participants'] = workflow_participants

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

        # لاگ تشخیصی برای خالی بودن اقدامات مجاز
        try:
            user_post_ids_dbg = list(user.userpost_set.filter(is_active=True, end_date__isnull=True).values_list('post_id', flat=True)) if user.is_authenticated else []
            dbg_transitions = []
            for step in full_path:
                posts_ids = [getattr(p, 'id', None) for p in step.get('posts', [])]
                dbg_transitions.append({'action': step.get('action').name, 'to': step.get('to_status').code, 'posts': posts_ids})
            logger.debug("[FACTOR_DETAIL] user_posts=%s transitions_posts=%s", user_post_ids_dbg, dbg_transitions)
        except Exception as e:
            logger.debug("[FACTOR_DETAIL] debug building failed: %s", e)

        # سایر اطلاعات
        context['approval_logs'] = factor.approval_logs.all()
        context['factor_impact'] = self._compute_factor_impact(factor)
        context['is_payment_ready'] = factor.status.is_final_approve if factor.status else False

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
