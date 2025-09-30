from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Prefetch
from django.conf import settings
from decimal import Decimal
from budgets.models import BudgetPeriod, BudgetTransaction
from core.views import PermissionBaseView
from django.views.generic import DetailView
from decimal import Decimal

from django.db.models import Q, Sum
from django.shortcuts import redirect
from django.views.generic import CreateView, UpdateView, DeleteView,ListView,DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models.deletion import ProtectedError

from BudgetsSystem.utils import parse_jalali_date_jdate
from budgets.budget_calculations import check_budget_status
from core.PermissionBase import PermissionBaseView
from budgets.models import BudgetPeriod, BudgetTransaction, BudgetHistory, BudgetAllocation
from budgets.BudgetPeriod.Forms_BudgetPeriod  import BudgetPeriodForm
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class BudgetPeriodCreateView(PermissionBaseView,CreateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')
    permission_required = 'budgets.add_budgetperiod'
    check_object_permission = 'budgets.add_budgetperiod'
    check_organization = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial']['created_by'] = self.request.user
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد دوره بودجه جدید')
        from core.models import Organization
        context['organizations'] = Organization.objects.filter(
            is_core=True, is_active=True
        ).select_related('org_type')
        return context

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('دوره بودجه با موفقیت ایجاد شد.'))
            return response
        except Exception as e:
            messages.error(self.request, _('خطایی در ایجاد دوره بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid: errors={form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

class BudgetPeriodUpdateView(PermissionBaseView,UpdateView):
    model = BudgetPeriod
    form_class = BudgetPeriodForm
    template_name = 'budgets/budget/budgetperiod_form.html'
    success_url = reverse_lazy('budgetperiod_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش دوره بودجه')
        context['total_allocated'] = self.object.total_allocated
        context['remaining_amount'] = self.object.get_remaining_amount()
        return context

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('دوره بودجه با موفقیت به‌روزرسانی شد.'))
            return response
        except Exception as e:
            messages.error(self.request, _('خطایی در به‌روزرسانی دوره بودجه رخ داد: ') + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

class BudgetPeriodDeleteView(PermissionBaseView, DeleteView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_confirm_delete.html'
    success_url = reverse_lazy('budgetperiod_list')

    def post(self, request, *args, **kwargs):
        budget_period = self.get_object()
        with transaction.atomic():
            # اگر تخصیص دارد: حذف انجام نشود و پیام بده
            from budgets.models import BudgetAllocation
            if BudgetAllocation.objects.filter(budget_period=budget_period).exists():
                messages.error(request, _('این دوره دارای تخصیص است و قابل حذف نیست. ابتدا تخصیص‌ها را حذف/انتقال دهید.'))
                return redirect(self.success_url)

            # در غیر این صورت، حذف را تلاش کن
            try:
                budget_period.delete()
                messages.success(request, f'دوره بودجه {budget_period.name} با موفقیت حذف شد.')
            except ProtectedError:
                # احتمالاً به‌دلیل وجود BudgetItem‌های وابسته
                messages.error(request, _('به دلیل وجود ردیف‌های بودجه وابسته، حذف ممکن نیست. ابتدا ردیف‌ها را حذف کنید.'))
        return redirect(self.success_url)

# --- BudgetPeriod CRUD ---
class BudgetPeriodListView(PermissionBaseView, ListView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_list.html'
    context_object_name = 'budget_periods'
    paginate_by = 10
    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get('q', '')
        status = self.request.GET.get('status', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')

        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(organization__name__icontains=q))
        # نگاشت وضعیت‌ها به فیلترهای مدل
        # توجه: منطق وضعیت شما کمی پیچیده است و ممکن است نیاز به بازبینی داشته باشد
        # اینجا سعی می‌کنیم بر اساس کد قبلی فیلتر کنیم
            # --- اصلاح فیلتر وضعیت بر اساس فیلدهای مدل ---
            if status:
                from django.utils import timezone
                today = timezone.now().date()
                if status == 'active':
                    # فعال: is_active=True, تمام نشده, بایگانی نشده, و تاریخ فعلی در بازه باشد
                    from datetime import timedelta as _td
                    grace_days = getattr(settings, 'BUDGET_PERIOD_GRACE_DAYS', 0) or 0
                    effective_today = today
                    effective_end_offset = _td(days=int(grace_days))
                    queryset = queryset.filter(
                        is_active=True,
                        is_completed=False,
                        is_archived=False,
                        start_date__lte=effective_today,
                        end_date__gte=effective_today - effective_end_offset
                    )
                elif status == 'inactive':
                    # غیرفعال: is_active=False, تمام نشده, بایگانی نشده
                    queryset = queryset.filter(is_active=False, is_completed=False, is_archived=False)
                elif status == 'locked':
                    # قفل شده: فرض می‌کنیم قفل دستی مد نظر است و بایگانی نشده
                    queryset = queryset.filter(lock_condition='MANUAL', is_archived=False)
                    # توجه: این فیلتر ممکن است کامل نباشد اگر قفل شدن شرایط دیگری هم دارد
                elif status == 'completed':
                    # تمام شده: is_completed=True و بایگانی نشده
                    queryset = queryset.filter(is_completed=True, is_archived=False)
                elif status == 'archived':
                    # بایگانی شده
                    queryset = queryset.filter(is_archived=True)
                elif status == 'upcoming':
                    # آینده: is_active=True, تمام نشده, بایگانی نشده, و تاریخ شروع در آینده است
                    queryset = queryset.filter(
                        is_active=True,
                        is_completed=False,
                        is_archived=False,
                        start_date__gt=today
                    )
                elif status == 'expired':
                    # منقضی (اما تمام نشده): is_active=True, تمام نشده, بایگانی نشده, و تاریخ پایان گذشته است
                    from datetime import timedelta as _td
                    grace_days = getattr(settings, 'BUDGET_PERIOD_GRACE_DAYS', 0) or 0
                    effective_cutoff = today - _td(days=int(grace_days))
                    queryset = queryset.filter(
                        is_active=True,
                        is_completed=False,
                        is_archived=False,
                        end_date__lt=effective_cutoff
                    )
            # -------------------------------------------

            status_map = {
                'active': Q(is_active=True),
                'inactive': Q(is_active=False),
                'locked': Q(lock_condition='MANUAL'),
                'completed': Q(is_completed=True),
            }
            queryset = queryset.filter(status_map.get(status, Q()))

        try:
            if date_from:
                queryset = queryset.filter(start_date__gte=parse_jalali_date_jdate(date_from))
            if date_to:
                queryset = queryset.filter(end_date__lte=parse_jalali_date_jdate(date_to))
        except Exception as e:
            logger.error(f"Date filtering error: {str(e)}")

        return queryset.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # دریافت queryset فیلتر شده کامل (قبل از صفحه‌بندی)
        # نکته: get_queryset دوباره فیلترها را اعمال می‌کند
        # اگر محاسبات پیچیده است، می‌توانید نتیجه get_queryset را ذخیره کنید
        # تا دوباره اجرا نشود، اما برای سادگی فعلا اینطور می‌گذاریم.
        queryset = self.get_queryset()  # برای محاسبه status_summary
        full_filtered_queryset = self.get_queryset()
        # --- محاسبه مجموع‌ها برای کل نتایج فیلتر شده ---
        # total_allocated ممکن است نیاز به annotation داشته باشد اگر فیلد مستقیم نیست
        # فرض می‌کنیم total_allocated یک فیلد در مدل است یا قبلا annotate شده
        totals = full_filtered_queryset.aggregate(
            total_sum=Sum('total_amount'),
            # اگر total_allocated فیلد نیست، باید aggregate آن متفاوت باشد یا روش محاسبه مجموع remaining تغییر کند
            allocated_sum=Sum('total_allocated')
        )

        total_sum_decimal = totals.get('total_sum') or Decimal('0')
        allocated_sum_decimal = totals.get('allocated_sum') or Decimal('0')

        # محاسبه مجموع باقی‌مانده (بدون اعمال max(0) روی مجموع)
        total_remaining_decimal = total_sum_decimal - allocated_sum_decimal

        context['total_sum'] = total_sum_decimal
        context['total_remaining'] = total_remaining_decimal
        # ------------------------------------------------

        # --- محاسبه مقادیر برای آیتم‌های صفحه فعلی ---
        # (این بخش کد شما برای محاسبه remaining و status برای آیتم‌های صفحه فعلی است)
        # --- محاسبه وضعیت و remaining برای آیتم‌های صفحه فعلی ---
        from django.utils import timezone
        today = timezone.now().date()  # تاریخ امروز
        context['today'] = today

        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        # شمارنده تخصیص‌ها و برگشتی‌ها
        from budgets.models import BudgetTransaction
        returned_totals = full_filtered_queryset.annotate(
        ).count()

        context['status_summary'] = {
            'active': queryset.filter(is_active=True).count(),
            'locked': queryset.filter(lock_condition='MANUAL').count(),
            'completed': queryset.filter(is_completed=True).count(),
            'total': queryset.count(),
        }

        # آمار تکمیلی برای جدول: remaining_amount، تعداد تخصیص‌ها، مجموع برگشتی‌ها
        from django.db.models import Count
        context['period_stats'] = {
            bp.id: {
                'alloc_count': bp.allocations.count(),
                'returned_sum': BudgetTransaction.objects.filter(allocation__budget_period=bp, transaction_type='RETURN').aggregate(total=Sum('amount'))['total'] or Decimal('0'),
                'remaining_amount': bp.get_remaining_amount(),
            }
            for bp in full_filtered_queryset
        }
        # تعداد نتایج یافت‌شده را به جای کل، تعداد نتایج کوئری‌ست فیلتر شده بگذاریم
        context['result_count'] = full_filtered_queryset.count()

        logger.debug(f"BudgetPeriodListView context calculated totals: sum={context['total_sum']}, remaining={context['total_remaining']}")
        logger.debug(f"BudgetPeriodListView context: {context}")
        return context

class old__BudgetPeriodDetailView(PermissionBaseView, DetailView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_detail.html'
    context_object_name = 'budget_period'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # صفحه‌بندی تراکنش‌ها
        transactions = BudgetTransaction.objects.filter(
            allocation__budget_period=self.object
        ).order_by('-timestamp')
        from django.core.paginator import Paginator
        paginator = Paginator(transactions, 10)
        page_number = self.request.GET.get('page')
        context['transactions'] = paginator.get_page(page_number)
        # جزئیات بودجه
        try:
            from budgets.get_budget_details import get_budget_details
            context['budget_details'] = get_budget_details(self.object)
        except Exception as e:
            logger.error(f"Error in get_budget_details: {str(e)}")
            messages.error(self.request, _('خطایی در محاسبه جزئیات بودجه رخ داد.'))
            context['budget_details'] = {
                'total_budget': Decimal('0'),
                'total_allocated': Decimal('0'),
                'remaining_budget': Decimal('0'),
                'status': 'error',
                'status_message': 'خطا در محاسبه'
            }
        # اعلان وضعیت
        try:
            status_dict = check_budget_status(self.object)
            status = status_dict['status']
            message = status_dict['message']
            if status in ('warning', 'locked', 'completed'):
                messages.warning(self.request, message)
        except Exception as e:
            logger.error(f"Error in check_budget_status: {str(e)}")
            messages.error(self.request, _('خطایی در بررسی وضعیت بودجه رخ داد.'))
        logger.debug(f"BudgetPeriodDetailView context: {context}")
        return context


class BudgetPeriodDetailView(PermissionBaseView, DetailView):
    model = BudgetPeriod
    template_name = 'budgets/budget/budgetperiod_detail.html'
    context_object_name = 'budget_period'

    # تعداد آیتم‌های صفحه‌بندی از تنظیمات
    TRANSACTIONS_PER_PAGE = getattr(settings, 'BUDGET_TRANSACTIONS_PER_PAGE', 10)

    def get_queryset(self):
        """بهینه‌سازی کوئری با پیش‌بارگذاری تخصیص‌ها"""
        return BudgetPeriod.objects.select_related('organization', 'created_by').prefetch_related(
            Prefetch(
                'allocations',
                queryset=BudgetAllocation.objects.select_related('organization', 'budget_item', 'project')
            )
        )

    def get_transactions(self):
        """دریافت تراکنش‌ها با صفحه‌بندی و بهینه‌سازی کوئری"""
        try:
            transactions = BudgetTransaction.objects.filter(
                allocation__budget_period=self.object
            ).select_related('allocation', 'created_by', 'related_tankhah').order_by('-timestamp')
            paginator = Paginator(transactions, self.TRANSACTIONS_PER_PAGE)
            page_number = self.request.GET.get('page')
            return paginator.get_page(page_number)
        except Exception as e:
            logger.error(f"Error fetching transactions for BudgetPeriod {self.object.pk}: {str(e)}", exc_info=True)
            messages.error(self.request, _('خطایی در بارگذاری تراکنش‌ها رخ داد.'))
            return Paginator([], self.TRANSACTIONS_PER_PAGE).get_page(1)

    def get_budget_details(self):
        """دریافت جزئیات بودجه با مدیریت خطاها"""
        try:
            from budgets.get_budget_details import get_budget_details
            return get_budget_details(self.object)
        except ImportError:
            logger.error(f"ImportError: get_budget_details not found for BudgetPeriod {self.object.pk}")
            messages.error(self.request, _('ماژول محاسبه بودجه یافت نشد.'))
        except Exception as e:
            logger.error(f"Error in get_budget_details for BudgetPeriod {self.object.pk}: {str(e)}", exc_info=True)
            messages.error(self.request, _('خطایی در محاسبه جزئیات بودجه رخ داد.'))
        return {
            'total_budget': Decimal('0'),
            'total_allocated': Decimal('0'),
            'remaining_budget': Decimal('0'),
            'status': 'error',
            'status_message': _('خطا در محاسبه')
        }

    def check_budget_status(self):
        """بررسی وضعیت بودجه و ارسال اعلان"""
        try:
            from budgets.utils import check_budget_status
            status_dict = check_budget_status(self.object)
            if status_dict['status'] in ('warning', 'locked', 'completed'):
                messages.warning(self.request, status_dict['message'])
            return status_dict
        except ImportError:
            logger.error(f"ImportError: check_budget_status not found for BudgetPeriod {self.object.pk}")
            messages.error(self.request, _('ماژول بررسی وضعیت بودجه یافت نشد.'))
        except Exception as e:
            logger.error(f"Error in check_budget_status for BudgetPeriod {self.object.pk}: {str(e)}", exc_info=True)
            messages.error(self.request, _('خطایی در بررسی وضعیت بودجه رخ داد.'))
        return {'status': 'error', 'message': _('خطا در بررسی وضعیت')}

    def get_context_data(self, **kwargs):
        """ساخت کنتکست با داده‌های بهینه‌شده"""
        context = super().get_context_data(**kwargs)

        # افزودن تراکنش‌ها و جزئیات بودجه
        context['transactions'] = self.get_transactions()
        context['budget_details'] = self.get_budget_details()
        context['budget_status'] = self.check_budget_status()

        # مجموع و لیست برگشتی‌ها (RETURN)
        try:
            from django.db.models import Sum
            total_returned = BudgetTransaction.objects.filter(
                allocation__budget_period=self.object,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        except Exception:
            total_returned = Decimal('0')
        context['total_returned'] = total_returned
        context['return_transactions'] = BudgetTransaction.objects.filter(
            allocation__budget_period=self.object,
            transaction_type='RETURN'
        ).select_related('allocation','created_by','related_tankhah').order_by('-timestamp')[:50]

        # افزودن اطلاعات اضافی برای رندرینگ
        context['is_locked'] = self.object.is_locked
        context['warning_threshold'] = self.object.warning_threshold
        context['locked_percentage'] = self.object.locked_percentage

        logger.debug(f"BudgetPeriodDetailView context prepared for BudgetPeriod {self.object.pk}")
        return context