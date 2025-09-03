import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.views.generic import DetailView

from budgets.budget_calculations import get_committed_budget, get_tankhah_available_budget
from budgets.models import PaymentOrder
from tankhah.models import Factor, FactorItem, FactorDocument, ApprovalLog
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from core.PermissionBase import PermissionBaseView
from django.shortcuts import redirect

# ===== IMPORTS =====
import logging
from django.views.generic import DetailView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# --- مدل‌ها و کلاس‌های مورد نیاز ---
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor
from core.models import Transition, Action  # <--- مدل کلیدی گردش کار
# views.py
from decimal import Decimal, ROUND_HALF_UP
from django.views.generic import DetailView
from django.db.models import Sum, Q, Prefetch
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect

# tankhah/views.py (اضافه/جایگزین)
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import redirect, get_object_or_404
from django.views.generic import DetailView
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum, F, Prefetch

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# CACHE_TTL = 60 # این را می‌توانید در settings.py تعریف کنید

logger = logging.getLogger('FactorViewsLogger')  # لاگر مخصوص


class _FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_detail.html'  # تمپلیت نمایشی جدید
    context_object_name = 'factor'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    permission_codename = 'tankhah.factor_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tankhah = factor.tankhah

        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()

        # محاسبه جمع کل و جمع هر آیتم
        items_with_total = [
            {'item': item, 'total': item.amount * item.quantity}
            for item in factor.items.all()
        ]
        context['items_with_total'] = items_with_total
        context['total_amount'] = sum(item['total'] for item in items_with_total)
        context['difference'] = factor.amount - context['total_amount'] if factor.amount else 0

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect('factor_list')


# ===== VIEWS =====
# class FactorDetailView__OK(PermissionBaseView, DetailView):
#     model = Factor
#     template_name = 'tankhah/Factors/Detials/factor_detail.html'
#     context_object_name = 'factor'
#     permission_codename = 'tankhah.factor_view'  # اطمینان از صحت پرمیشن
#
#     check_organization = True  # این قابلیت از PermissionBaseView شما استفاده می‌کند
#     # http_method_names = ['post'] # این ویو فقط به درخواست‌های POST پاسخ می‌دهد
#
#     def get_context_data(self, **kwargs):
#         """
#         این متد یک context کامل و غنی برای نمایش داشبورد اطلاعاتی فاکتور آماده می‌کند.
#         """
#         # --- بخش ۱: آماده‌سازی اولیه ---
#         context = super().get_context_data(**kwargs)
#         factor = self.object
#         tankhah = factor.tankhah
#         user = self.request.user
#         logger.debug(f"[FactorDetailView] Preparing rich context for Factor PK {factor.pk}")
#         context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"
#
#         # --- بخش ۲: محاسبه و اضافه کردن اطلاعات بودجه تنخواه ---
#         from tankhah.models import Factor, ApprovalLog  # ApprovalLog را اضافه می‌کنیم
#         from budgets.budget_calculations import get_tankhah_available_budget, get_committed_budget
#         if
#             # موجودی اولیه تنخواه
#             tankhah_initial_amount = tankhah.amount or 0
#
#             # هزینه‌های قطعی (فاکتورهای پرداخت شده)
#             tankhah_paid_factors = tankhah.factors.filter(status__code='PAID')
#             tankhah_paid_total = sum(f.amount for f in tankhah_paid_factors)
#
#             # مبلغ در تعهد (فاکتورهای در انتظار و تایید شده)
#             tankhah_committed_total = get_committed_budget(tankhah)
#
#             # موجودی واقعی (نقدی) باقیمانده
#             tankhah_balance = tankhah_initial_amount - tankhah_paid_total
#
#             # موجودی در دسترس برای خرج جدید
#             tankhah_available = get_tankhah_available_budget(tankhah)
#
#             context['tankhah_budget_summary'] = {
#                 'initial': tankhah_initial_amount,
#                 'paid': tankhah_paid_total,
#                 'committed': tankhah_committed_total,
#                 'balance': tankhah_balance,
#                 'available': tankhah_available,
#             }
#             logger.info(f"Tankhah budget summary calculated for Tankhah PK {tankhah.pk}")
#
#         # --- بخش ۳: مشخص کردن تاثیر این فاکتور خاص ---
#         factor_impact = {'type': 'none', 'label': 'نامشخص', 'class': 'secondary'}
#         if factor.status.code in ['PENDING_APPROVAL', 'APPROVED', 'APPROVED_FOR_PAYMENT', 'IN_PAYMENT_PROCESS']:
#             factor_impact = {'type': 'committed', 'label': 'تعهدی (در انتظار پرداخت)', 'class': 'warning'}
#         elif factor.status.code == 'PAID':
#             factor_impact = {'type': 'paid', 'label': 'هزینه قطعی (پرداخت شده)', 'class': 'info'}
#         elif factor.status.code == 'REJECTED':
#             factor_impact = {'type': 'rejected', 'label': 'رد شده (بدون تاثیر مالی)', 'class': 'danger'}
#         elif factor.status.code == 'DRAFT':
#             factor_impact = {'type': 'draft', 'label': 'پیش‌نویس (بدون تاثیر مالی)', 'class': 'light'}
#
#         context['factor_impact'] = factor_impact
#         logger.debug(f"Factor PK {factor.pk} impact is '{factor_impact['label']}'.")
#
#         # --- بخش ۴: ردیابی مسیر بودجه (Budget Trace) ---
#         budget_trace = []
#         if tankhah and tankhah.project_budget_allocation:
#             allocation = tankhah.project_budget_allocation
#             budget_trace.append({'level': 'تخصیص', 'object': allocation})
#             if allocation.budget_period:
#                 budget_trace.append({'level': 'دوره بودجه', 'object': allocation.budget_period})
#         # لیست را برعکس می‌کنیم تا از بالا به پایین نمایش داده شود
#         context['budget_trace'] = reversed(budget_trace)
#
#         # --- بخش ۵: تاریخچه اقدامات (ApprovalLog) ---
#         context['approval_logs'] = ApprovalLog.objects.filter(factor=factor).order_by('timestamp').select_related(
#             'user', 'post', 'action', 'from_status', 'to_status')
#
#         # --- بخش ۶: منطق گردش کار برای نمایش اقدامات مجاز (از پاسخ قبلی) ---
#         allowed_transitions = []
#         if user.is_authenticated:
#             user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
#             if user_post_ids or user.is_superuser:
#                 possible_transitions = Transition.objects.filter(
#                     entity_type__code='FACTOR', from_status=factor.status,
#                     organization=tankhah.organization, is_active=True
#                 ).select_related('action', 'to_status').prefetch_related('allowed_posts')
#
#                 for transition in possible_transitions:
#                     if user.is_superuser or not {post.id for post in transition.allowed_posts.all()}.isdisjoint(
#                             user_post_ids):
#                         allowed_transitions.append(transition)
#
#         context['allowed_transitions'] = allowed_transitions
#         logger.info(
#             f"Final allowed transitions for user on Factor PK {factor.pk}: {[t.action.name for t in allowed_transitions]}")
#
#         return context
#
#     def handle_no_permission(self):
#         """در صورت نداشتن دسترسی، پیام خطا نمایش داده و به لیست فاکتورها هدایت می‌شود."""
#         logger.warning(
#             f"Permission denied for user '{self.request.user.username}' to view Factor PK {self.kwargs.get('pk')}.")
#         messages.error(self.request, self.get_permission_denied_message())
#         return redirect('factor_list')  # اطمینان از اینکه نام URL صحیح است.

CACHE_TTL = 60  # ثانیه
# ===================================================================
# ۱. تابع کمکی مستقل برای جلوگیری از تکرار کد
# ===================================================================

def get_user_allowed_transitions(user, factor):
    """
    یک تابع مستقل که لیست Transition های مجاز برای یک کاربر و فاکتور خاص را برمی‌گرداند.
    """
    tankhah = factor.tankhah
    org = getattr(tankhah, 'organization', None)
    if not user.is_authenticated or not org or not factor.status:
        return []

    # این کوئری برای کارایی بهتر بهینه‌سازی شده است
    qs = Transition.objects.filter(
        entity_type__code='FACTOR',
        from_status=factor.status,
        organization=org,
        is_active=True
    ).select_related('action', 'to_status').prefetch_related('allowed_posts')

    if user.is_superuser:
        return list(qs)

    user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
    if not user_post_ids:
        return []

    return list(qs.filter(allowed_posts__in=user_post_ids).distinct())

# ===================================================================
class PerformFactorTransitionAPI(APIView):
    # permission_classes = [IsAuthenticated]
    def post(self, request, pk, transition_id):
        factor = get_object_or_404(Factor, pk=pk)
        target_transition = get_object_or_404(Transition, pk=transition_id)
        comment = request.data.get('comment', '')  # دریافت کامنت از بدنه درخواست POST
        user = request.user

        logger.info(
            f"API: Attempting transition '{target_transition.name}' on Factor {factor.pk} by user {user.username}")

        # --- ۱. بررسی دسترسی با استفاده از تابع can_perform_action ---
        # **مهم:** این تابع باید با مدل‌های گردش کار جدید شما کار کند.
        # action_code = target_transition.action.code
        # if not can_perform_action(user, factor, action_code):
        #     logger.warning(f"Permission denied for user {user.username} to perform action '{action_code}' on factor {factor.pk}")
        #     return Response({'error': _("شما مجاز به انجام این اقدام نیستید.")}, status=status.HTTP_403_FORBIDDEN)
        # **توجه:** فعلاً فرض می‌کنیم دسترسی از قبل چک شده است.

        # --- ۲. بررسی اینکه آیا گذار برای وضعیت فعلی فاکتور معتبر است ---
        if factor.status != target_transition.from_status:
            logger.error(
                f"Transition Mismatch: Factor {factor.pk} is in status '{factor.status.name}' but transition {target_transition.pk} expects status '{target_transition.from_status.name}'.")
            return Response(
                {'error': _(
                    "این اقدام در وضعیت فعلی فاکتور مجاز نیست. ممکن است شخص دیگری قبلاً وضعیت آن را تغییر داده باشد. لطفاً صفحه را رفرش کنید.")},
                status=status.HTTP_409_CONFLICT  # 409 Conflict
            )

        try:
            with transaction.atomic():
                original_status = factor.status

                # ۱. تغییر وضعیت فاکتور
                factor.status = target_transition.to_status
                # ممکن است بخواهید فیلدهای دیگری را هم آپدیت کنید، مثلاً locked_by_stage
                # factor.locked_by_stage = ...
                factor.save(update_fields=['status'])  # فقط فیلد وضعیت را آپدیت کن
                logger.info(
                    f"Factor {factor.pk} status changed from '{original_status.name}' to '{target_transition.to_status.name}'.")

                # ۲. ایجاد رکورد در ApprovalLog (با فیلد action)
                # **نقطه کلیدی اصلاح:**
                approval_log = ApprovalLog.objects.create(
                    factor=factor,  # فاکتور مرتبط
                    content_object=factor,  # برای GenericForeignKey
                    from_status=original_status,  # وضعیت قبلی
                    to_status=target_transition.to_status,  # وضعیت جدید
                    action=target_transition.action,  # **اصلاح اصلی: اقدام انجام شده**
                    user=user,  # کاربر انجام دهنده
                    post=user.userpost_set.filter(is_active=True).first().post if user.userpost_set.filter(
                        is_active=True).exists() else None,  # پست کاربر
                    comment=comment,  # توضیحات کاربر
                    created_by=user  # (اختیاری) اگر می‌خواهید ثبت کنید چه کسی لاگ را ایجاد کرده
                )
                logger.info(f"ApprovalLog {approval_log.pk} created for Factor {factor.pk} transition.")

                # ۳. ارسال اعلان (Notification)
                # ... (منطق ارسال اعلان به کاربر مرحله بعد یا کاربر ایجاد کننده) ...

        except ValidationError as e:
            logger.error(f"Validation error during transition for factor {factor.pk}: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Critical error in PerformFactorTransitionAPI for factor {factor.pk}: {e}", exc_info=True)
            return Response({'error': _("خطای پیش‌بینی نشده در سرور رخ داد.")},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'message': _("عملیات با موفقیت انجام شد و فاکتور به وضعیت '{}' تغییر یافت.").format(
                target_transition.to_status.name),
            'new_status': target_transition.to_status.name
        }, status=status.HTTP_200_OK)


# ===================================================================
# ۲. ویوی جزئیات فاکتور (اصلاح شده)
# ===================================================================
class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Factors/Detials/factor_detail.html'
    context_object_name = 'factor'
    permission_codename = 'tankhah.factor_view'
    check_organization = True

    def get_queryset(self):
        # return (
        #     Factor.objects
        #     .select_related('tankhah', 'status', 'tankhah__project', 'tankhah__organization', 'created_by')
        #     .prefetch_related(
        #         Prefetch('items',
        #                  queryset=FactorItem.objects.only('id', 'factor_id', 'quantity', 'unit_price', 'description')),
        #         Prefetch('documents', queryset=FactorDocument.objects.select_related('uploaded_by')),
        #         Prefetch('payment_orders', queryset=PaymentOrder.objects.select_related('status')),
        #         # prefetch کردن allowed_posts برای جلوگیری از کوئری N+1 در _get_allowed_transitions
        #         Prefetch('tankhah__organization__transition_set',
        #                  queryset=Transition.objects.select_related('action', 'to_status').prefetch_related(
        #                      'allowed_posts'), to_attr='prefetched_transitions')
        #     )
        # )

        return (
            Factor.objects
            # ابتدا روابط مستقیم و مهم را select می‌کنیم
            .select_related(
                'tankhah',
                'tankhah__project',
                'tankhah__organization',
                'created_by',
                'status'  # status یک رابطه مستقیم است و اینجا جایش درست است
            )
            # سپس روابط معکوس یا چندگانه را prefetch می‌کنیم
            .prefetch_related(
                'items',  # .only() را برای سادگی حذف کردیم، ORM جنگو هوشمند است
                Prefetch('documents', queryset=FactorDocument.objects.select_related('uploaded_by')),
                Prefetch('payment_orders', queryset=PaymentOrder.objects.select_related('status')),
            )
        )

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

        summary_data = {
            'initial': initial, 'paid': paid_total, 'committed': committed,
            'balance': balance, 'available': available,
        }

        if initial > 0:
            summary_data['paid_percentage'] = ((paid_total / initial) * 100).quantize(Decimal('0.1'),
                                                                                      rounding=ROUND_HALF_UP)
            summary_data['committed_percentage'] = ((committed / initial) * 100).quantize(Decimal('0.1'),
                                                                                          rounding=ROUND_HALF_UP)
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

    def _get_budget_trace(self, tankhah):
        trace = []
        allo = getattr(tankhah, 'project_budget_allocation', None)
        if allo:
            trace.append({'level': 'تخصیص', 'object': allo})
            if allo.budget_period:
                trace.append({'level': 'دوره بودجه', 'object': allo.budget_period})
        return list(reversed(trace))

    def _get_allowed_transitions(self, user, factor):
        tankhah = factor.tankhah
        org = getattr(tankhah, 'organization', None)
        if not user.is_authenticated or not org or not factor.status:
            return []

        qs = Transition.objects.filter(
            entity_type__code='FACTOR', from_status=factor.status,
            organization=org, is_active=True
        )
        if user.is_superuser:
            return list(qs)

        user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
        if not user_post_ids:
            return []

        return list(qs.filter(allowed_posts__in=user_post_ids).distinct())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"

        if tankhah:
            context['tankhah_budget_summary'] = self._compute_tankhah_budget_summary(tankhah)

        context['factor_impact'] = self._compute_factor_impact(factor)
        context['budget_trace'] = self._get_budget_trace(tankhah) if tankhah else []

        context['approval_logs'] = factor.approval_logs.order_by('-timestamp').select_related('user', 'post',
                                                                                              'from_status',
                                                                                              'to_status')
        allowed_transitions = self._get_allowed_transitions(user, factor)
        context['allowed_transitions'] = allowed_transitions

        # منطق جدید برای نمایش مراحل بعدی و پست‌های مجاز
        next_steps_with_posts = []
        if allowed_transitions:
            unique_actions = {t.action for t in allowed_transitions}
            for action in unique_actions:
                related_transitions = [t for t in allowed_transitions if t.action == action]
                all_posts_for_action = set()
                for t in related_transitions:
                    all_posts_for_action.update(p.pk for p in t.allowed_posts.all())

                next_steps_with_posts.append({
                    'action': action,
                    'to_status': related_transitions[0].to_status,
                    'posts': sorted(list(all_posts_for_action))
                })
        context['next_steps_with_posts'] = sorted(next_steps_with_posts, key=lambda x: x['action'].name)

        context['items_count'] = factor.items.count()
        context['items_total'] = factor.items.aggregate(total=Sum(F('quantity') * F('unit_price')))['total'] or Decimal(
            '0')
        context['attachments_count'] = factor.documents.count()

        # منطق نمایش دکمه‌ها را بهتر است در View مدیریت کرد
        context['can_edit'] = user.has_perm('tankhah.change_factor') and factor.status.code in ['DRAFT', 'REJECTED']
        context['can_delete'] = user.has_perm('tankhah.delete_factor') and factor.status.code == 'DRAFT'
        context['can_view_budget'] = user.has_perm('budgets.view_budgetperiod')

        context['is_overdue'] = factor.date < timezone.now().date() and factor.status.code not in ['PAID', 'REJECTED']


        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).values_list('post', flat=True)
        if user_posts:
            # پیدا کردن گذارهای ممکن برای وضعیت فعلی فاکتور که کاربر به آنها دسترسی دارد
            possible_transitions = Transition.objects.filter(
                entity_type__code='FACTOR',
                from_status=factor.status,
                organization=factor.tankhah.organization,
                allowed_posts__id__in=list(user_posts),
                is_active=True
            ).select_related('action', 'to_status').distinct()
            context['possible_transitions'] = possible_transitions

        return context

    def handle_no_permission(self):
        logger.warning(
            f"Permission denied for user '{self.request.user.username}' to view Factor PK {self.kwargs.get('pk')}.")
        messages.error(self.request, self.get_permission_denied_message())
        return redirect('factor_list')

    def post(self, request, pk, format=None):
        try:
            with transaction.atomic():
                factor = get_object_or_404(Factor.objects.select_for_update(), pk=pk)
                action_id = request.data.get('action_id')
                description = request.data.get('description', '')

                if not action_id:
                    return Response({'success': False, 'error': 'Action ID is required.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                # حالا از تابع کمکی جدید و مطمئن استفاده می‌کنیم
                allowed_transitions = get_user_allowed_transitions(request.user, factor)
                target_transition = next((t for t in allowed_transitions if str(t.action.id) == str(action_id)), None)

                if not target_transition:
                    logger.warning(
                        f"Forbidden action by user {request.user.username} on factor {pk}. Action ID: {action_id}")
                    return Response({'success': False, 'error': 'This action is not allowed for your role.'},
                                    status=status.HTTP_403_FORBIDDEN)

                old_status = factor.status
                new_status = target_transition.to_status
                user_post = request.user.userpost_set.filter(is_active=True).first()

                # به‌روزرسانی وضعیت فاکتور
                factor.status = new_status
                factor.save(update_fields=['status'])

                # ایجاد لاگ تایید
                ApprovalLog.objects.create(
                    factor=factor,
                    user=request.user,
                    post=(user_post.post if user_post else None),
                    from_status=old_status,
                    to_status=new_status,
                    action=target_transition.action,
                    comment=description
                )

                logger.info(
                    f"Factor {factor.number} successfully transitioned to '{new_status.name}' by user {request.user.username}.")
                return Response({
                    'success': True,
                    'message': f"فاکتور با موفقیت به وضعیت '{new_status.name}' تغییر یافت."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            # این خط خطای دقیق را در کنسول جنگو چاپ می‌کند
            logger.error(f"Critical error in PerformFactorTransitionAPI for factor {pk}: {e}", exc_info=True)
            # و یک پیام عمومی به کاربر نمایش می‌دهد
            return Response({'success': False, 'error': 'یک خطای پیش‌بینی نشده در سرور رخ داد.'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PerformFactorTransitionAPI__(APIView):
    permission_classes = [IsAuthenticated]

    def _get_allowed_transitions_for_user(self, user, factor):
        """
        تابع کمکی (شبیه متد ویو) که ترنزیشن‌های مجاز برای user و factor را برمی‌گرداند.
        """
        tankhah = factor.tankhah
        org = getattr(tankhah, 'organization', None)
        if not user.is_authenticated or not org or not factor.status:
            return []

        qs = (
            Transition.objects
            .filter(entity_type__code='FACTOR', from_status=factor.status, organization=org, is_active=True)
            .select_related('action', 'to_status')
            .prefetch_related('allowed_posts')
        )
        if user.is_superuser:
            return list(qs)

        user_post_ids = list(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
        if not user_post_ids:
            return []

        return list(qs.filter(allowed_posts__in=user_post_ids).distinct())

    def post(self, request, pk, format=None):
        try:
            with transaction.atomic():
                # قفل رکورد factor برای جلوگیری از race condition
                factor = get_object_or_404(Factor.objects.select_for_update(), pk=pk)
                action_id = request.data.get('action_id')
                description = request.data.get('description', '') or request.data.get('comment', '')

                if not action_id:
                    return Response({'success': False, 'error': 'Action ID is required.'},
                                    status=status.HTTP_400_BAD_REQUEST)

                logger.info(f"action_id (raw) from request: {action_id}")

                allowed_transitions = get_user_allowed_transitions(request.user, factor)
                logger.info(f"Allowed transitions for user {request.user.username} on factor {factor.pk}: " +
                            f"{[(t.id, getattr(t.action, 'id', None), t.to_status.code) for t in allowed_transitions]}")

                target_transition = next(
                    (t for t in allowed_transitions if t.action and str(t.action.id) == str(action_id)), None)
                logger.info(f"Matched transition: {target_transition}")

                if not target_transition:
                    return Response(
                        {'success': False, 'error': 'This action is not allowed for the current factor or user.'},
                        status=status.HTTP_403_FORBIDDEN)

                # ---------- بررسی‌های بودجه (مثال: اگر باید مانع از تأیید بیش از موجودی تخصیص شویم)
                # اگر ترنزیشن به وضعیت پرداخت/تأیید نهایی می‌رود، بررسی تخصیص:
                alloc = getattr(factor.tankhah, 'project_budget_allocation', None)
                if alloc:
                    remaining_alloc = alloc.get_remaining_amount()
                    # تصمیم‌گیری بستگی به منطق شما دارد؛ نمونه:
                    if target_transition.to_status and getattr(target_transition.to_status, 'code', '') in (
                            'APPROVED', 'PAID'):
                        if factor.amount > remaining_alloc:
                            return Response({
                                'success': False,
                                'error': 'بودجه تخصیص‌یافته برای این تخصیص کافی نیست.'
                            }, status=status.HTTP_400_BAD_REQUEST)

                # ---------- اعمال تغییر وضعیت
                old_status = factor.status
                factor.status = target_transition.to_status
                factor.save(update_fields=['status'])

                # ---------- ثبت ApprovalLog (فیلدها باید مطابق مدل شما باشند)
                user_post = request.user.userpost_set.filter(is_active=True).first()
                result = ApprovalLog.objects.create(
                    factor=factor,
                    user=request.user,
                    post=(user_post.post if user_post else None),
                    from_status=old_status,
                    to_status=target_transition.to_status,
                    action=target_transition.action if target_transition.action else None,
                    comment=description
                )
                logger.info(f' result {result}')
                # ---------- پاسخ مفید: نفرات بعدی + مسیر بودجه
                next_transitions = Transition.objects.filter(entity_type__code='FACTOR',
                                                             from_status=target_transition.to_status,
                                                             organization=factor.tankhah.organization,
                                                             is_active=True).prefetch_related('allowed_posts')
                next_posts = []
                for nt in next_transitions:
                    for p in nt.allowed_posts.all():
                        next_posts.append({'id': p.pk, 'name': str(p)})

                budget_trace = []
                if alloc:
                    budget_trace.append({'level': 'allocation', 'id': alloc.pk, 'repr': str(alloc)})
                    if alloc.budget_period:
                        budget_trace.append(
                            {'level': 'budget_period', 'id': alloc.budget_period.pk, 'repr': str(alloc.budget_period)})

                return Response({
                    'success': True,
                    'message': f"Factor moved from '{old_status.name}' to '{factor.status.name}'.",
                    'next_posts': next_posts,
                    'budget_trace': budget_trace
                }, status=status.HTTP_200_OK)

        except Exception as e:
            # logger.exception(e)
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
