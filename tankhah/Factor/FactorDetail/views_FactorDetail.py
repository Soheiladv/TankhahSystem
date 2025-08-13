import logging

from django.views.generic import DetailView
from tankhah.models import   Factor
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from core.PermissionBase import PermissionBaseView
from django.shortcuts import  redirect

# ===== IMPORTS =====
import logging
from django.views.generic import DetailView
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# --- مدل‌ها و کلاس‌های مورد نیاز ---
from core.PermissionBase import PermissionBaseView
from tankhah.models import Factor
from core.models import Transition  # <--- مدل کلیدی گردش کار

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

class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Factors/Detials/factor_detail.html'
    context_object_name = 'factor'
    permission_codename = 'tankhah.factor_view'  # اطمینان از صحت پرمیشن

    check_organization = True  # این قابلیت از PermissionBaseView شما استفاده می‌کند
    # http_method_names = ['post'] # این ویو فقط به درخواست‌های POST پاسخ می‌دهد

    def get_context_data(self, **kwargs):
        """
        این متد یک context کامل و غنی برای نمایش داشبورد اطلاعاتی فاکتور آماده می‌کند.
        """
        # --- بخش ۱: آماده‌سازی اولیه ---
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        logger.debug(f"[FactorDetailView] Preparing rich context for Factor PK {factor.pk}")
        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"

        # --- بخش ۲: محاسبه و اضافه کردن اطلاعات بودجه تنخواه ---
        from tankhah.models import Factor, ApprovalLog  # ApprovalLog را اضافه می‌کنیم
        from budgets.budget_calculations import get_tankhah_available_budget, get_committed_budget
        if tankhah:
            # موجودی اولیه تنخواه
            tankhah_initial_amount = tankhah.amount or 0

            # هزینه‌های قطعی (فاکتورهای پرداخت شده)
            tankhah_paid_factors = tankhah.factors.filter(status__code='PAID')
            tankhah_paid_total = sum(f.amount for f in tankhah_paid_factors)

            # مبلغ در تعهد (فاکتورهای در انتظار و تایید شده)
            tankhah_committed_total = get_committed_budget(tankhah)

            # موجودی واقعی (نقدی) باقیمانده
            tankhah_balance = tankhah_initial_amount - tankhah_paid_total

            # موجودی در دسترس برای خرج جدید
            tankhah_available = get_tankhah_available_budget(tankhah)

            context['tankhah_budget_summary'] = {
                'initial': tankhah_initial_amount,
                'paid': tankhah_paid_total,
                'committed': tankhah_committed_total,
                'balance': tankhah_balance,
                'available': tankhah_available,
            }
            logger.info(f"Tankhah budget summary calculated for Tankhah PK {tankhah.pk}")

        # --- بخش ۳: مشخص کردن تاثیر این فاکتور خاص ---
        factor_impact = {'type': 'none', 'label': 'نامشخص', 'class': 'secondary'}
        if factor.status.code in ['PENDING_APPROVAL', 'APPROVED', 'APPROVED_FOR_PAYMENT', 'IN_PAYMENT_PROCESS']:
            factor_impact = {'type': 'committed', 'label': 'تعهدی (در انتظار پرداخت)', 'class': 'warning'}
        elif factor.status.code == 'PAID':
            factor_impact = {'type': 'paid', 'label': 'هزینه قطعی (پرداخت شده)', 'class': 'info'}
        elif factor.status.code == 'REJECTED':
            factor_impact = {'type': 'rejected', 'label': 'رد شده (بدون تاثیر مالی)', 'class': 'danger'}
        elif factor.status.code == 'DRAFT':
            factor_impact = {'type': 'draft', 'label': 'پیش‌نویس (بدون تاثیر مالی)', 'class': 'light'}

        context['factor_impact'] = factor_impact
        logger.debug(f"Factor PK {factor.pk} impact is '{factor_impact['label']}'.")

        # --- بخش ۴: ردیابی مسیر بودجه (Budget Trace) ---
        budget_trace = []
        if tankhah and tankhah.project_budget_allocation:
            allocation = tankhah.project_budget_allocation
            budget_trace.append({'level': 'تخصیص', 'object': allocation})
            if allocation.budget_period:
                budget_trace.append({'level': 'دوره بودجه', 'object': allocation.budget_period})
        # لیست را برعکس می‌کنیم تا از بالا به پایین نمایش داده شود
        context['budget_trace'] = reversed(budget_trace)

        # --- بخش ۵: تاریخچه اقدامات (ApprovalLog) ---
        context['approval_logs'] = ApprovalLog.objects.filter(factor=factor).order_by('timestamp').select_related(
            'user', 'post', 'action', 'from_status', 'to_status')

        # --- بخش ۶: منطق گردش کار برای نمایش اقدامات مجاز (از پاسخ قبلی) ---
        allowed_transitions = []
        if user.is_authenticated:
            user_post_ids = set(user.userpost_set.filter(is_active=True).values_list('post_id', flat=True))
            if user_post_ids or user.is_superuser:
                possible_transitions = Transition.objects.filter(
                    entity_type__code='FACTOR', from_status=factor.status,
                    organization=tankhah.organization, is_active=True
                ).select_related('action', 'to_status').prefetch_related('allowed_posts')

                for transition in possible_transitions:
                    if user.is_superuser or not {post.id for post in transition.allowed_posts.all()}.isdisjoint(
                            user_post_ids):
                        allowed_transitions.append(transition)

        context['allowed_transitions'] = allowed_transitions
        logger.info(
            f"Final allowed transitions for user on Factor PK {factor.pk}: {[t.action.name for t in allowed_transitions]}")

        return context

    def handle_no_permission(self):
        """در صورت نداشتن دسترسی، پیام خطا نمایش داده و به لیست فاکتورها هدایت می‌شود."""
        logger.warning(
            f"Permission denied for user '{self.request.user.username}' to view Factor PK {self.kwargs.get('pk')}.")
        messages.error(self.request, self.get_permission_denied_message())
        return redirect('factor_list')  # اطمینان از اینکه نام URL صحیح است.
