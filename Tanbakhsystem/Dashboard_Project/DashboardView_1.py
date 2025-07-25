# views.py
import json
from decimal import Decimal
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, Count, Case, When, Value, F, ExpressionWrapper, fields
from django.db.models.functions import Coalesce, TruncMonth, TruncQuarter
import jdatetime
from datetime import timedelta, date as py_date
from django.utils import timezone
from django.urls import reverse_lazy

# Import models
from core.models import Project, Organization
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction, BudgetItem
from tankhah.models import Tankhah, Factor, ItemCategory # ItemCategory را برای سرفصل هزینه‌های فاکتور اضافه کردم

# Import calculation functions
from budgets.budget_calculations import (
    get_project_total_budget, get_project_used_budget, get_project_remaining_budget,
    get_organization_budget, calculate_remaining_amount,
    # ... سایر توابع
)

def get_jalali_month_name_static(month_number):
    j_months_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    try:
        month_number = int(month_number)
        if 1 <= month_number <= 12: return j_months_fa[month_number - 1]
        return str(month_number)
    except (ValueError, IndexError): return str(month_number)

def get_jalali_quarter_name_static(gregorian_date):
    j_date = jdatetime.date.fromgregorian(date=gregorian_date)
    quarter = (j_date.month - 1) // 3 + 1
    return f"فصل {quarter} {j_date.year}"


class TabbedFinancialDashboardView(LoginRequiredMixin, View):
    template_name = 'Dashboard/Dash_tabbed_financial_dashboard.html'
    login_url = reverse_lazy('accounts:login')

    def _get_active_period_or_default(self, period_id=None):
        # ... (بدون تغییر از مثال قبلی) ...
        if period_id:
            try:
                return BudgetPeriod.objects.get(pk=period_id)
            except BudgetPeriod.DoesNotExist:
                pass
        return BudgetPeriod.objects.filter(is_active=True, is_completed=False).order_by('-start_date').first()


    def get_filters(self, request):
        filters = {}
        budget_period_id = request.GET.get('budget_period')
        organization_id = request.GET.get('organization')

        filters['budget_period_obj'] = self._get_active_period_or_default(budget_period_id)

        if organization_id:
            try:
                filters['organization_obj'] = Organization.objects.get(pk=organization_id)
            except Organization.DoesNotExist:
                pass
        else:
            filters['organization_obj'] = None # برای نمایش کل سازمان‌ها
        return filters

    # --- توابع داده برای تب بودجه ---
    def get_budget_tab_data(self, active_period, organization_obj):
        data = {}
        # KPI های اصلی بودجه
        # ... (مشابه kpi_data در مثال قبلی، با تمرکز بر بودجه کلان و تخصیص‌ها) ...
        data['budget_kpis'] = {
            'total_period_budget': active_period.total_amount if active_period else Decimal('0'),
            # ... سایر KPI های بودجه ...
        }

        # نمودار مصرف بودجه برای هر BudgetItem (سرفصل اصلی بودجه)
        item_spending_labels, item_spending_values = [], []
        base_trans_q = Q(transaction_type='CONSUMPTION')
        if active_period: base_trans_q &= Q(allocation__budget_period=active_period)
        if organization_obj: base_trans_q &= Q(allocation__organization=organization_obj)

        budget_items_consumption = BudgetTransaction.objects.filter(base_trans_q)\
            .values('allocation__budget_item__name')\
            .annotate(total_consumed=Sum('amount'))\
            .order_by('-total_consumed')

        for item in budget_items_consumption:
            item_spending_labels.append(item['allocation__budget_item__name'] or _("نامشخص"))
            item_spending_values.append(float(item['total_consumed'] or 0))

        data['budget_item_consumption_chart'] = {
            'labels': json.dumps(item_spending_labels, ensure_ascii=False),
            'values': json.dumps(item_spending_values)
        }
        # داده نمونه
        if not item_spending_labels:
            data['budget_item_consumption_chart'] = {
                'labels': json.dumps([_("حقوق و دستمزد"), _("اجاره"), _("پشتیبانی و نگهداری"), _("بازاریابی")], ensure_ascii=False),
                'values': json.dumps([1200, 800, 500, 300])
            }


        # جدول تخصیص‌ها به سازمان‌ها (اگر organization_obj انتخاب نشده)
        if not organization_obj and active_period:
            allocations_to_orgs = []
            orgs_with_budget = Organization.objects.filter(
                is_active=True, org_type__is_budget_allocatable=True,
                budget_allocations__budget_period=active_period
            ).distinct()

            for org in orgs_with_budget:
                allocated = org.budget_allocations.filter(budget_period=active_period).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                consumed = BudgetTransaction.objects.filter(allocation__budget_period=active_period, allocation__organization=org, transaction_type='CONSUMPTION').aggregate(total=Sum('amount'))['total'] or Decimal('0')
                remaining = calculate_remaining_amount(org.budget_allocations.filter(budget_period=active_period).first()) if org.budget_allocations.filter(budget_period=active_period).exists() else allocated - consumed # تقریبی
                allocations_to_orgs.append({
                    'name': org.name,
                    'allocated': float(allocated),
                    'consumed': float(consumed),
                    'remaining': float(remaining),
                    'utilization': (float(consumed) / float(allocated) * 100) if allocated > 0 else 0
                })
            data['allocations_to_organizations_table'] = sorted(allocations_to_orgs, key=lambda x: x['allocated'], reverse=True)
        else:
             data['allocations_to_organizations_table'] = None


        return data

    # --- توابع داده برای تب تنخواه ---
    def get_tankhah_tab_data(self, active_period, organization_obj):
        data = {}
        now = timezone.now()
        # KPI های تنخواه
        tankhah_q = Q()
        if active_period: tankhah_q &= Q(request_date__gte=active_period.start_date, request_date__lte=active_period.end_date)
        if organization_obj: tankhah_q &= Q(organization=organization_obj)

        data['tankhah_kpis'] = {
            'total_tankhah_requested': Tankhah.objects.filter(tankhah_q).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
            'paid_tankhah_amount': Tankhah.objects.filter(tankhah_q, status='PAID').aggregate(total=Sum('amount'))['total'] or Decimal('0'),
            'open_tankhah_count': Tankhah.objects.filter(tankhah_q, status__in=['DRAFT', 'PENDING']).count(),
            # ...
        }
        # داده نمونه
        data['tankhah_kpis'].setdefault('total_tankhah_requested', Decimal('750000000'))
        data['tankhah_kpis'].setdefault('paid_tankhah_amount', Decimal('550000000'))
        data['tankhah_kpis'].setdefault('open_tankhah_count', 8)


        # نمودار فصلی میزان مصرف تنخواه (مبلغ تنخواه‌های پرداخت شده)
        # نمودار فصلی فاکتورهای ارائه شده (مبلغ فاکتورهای پرداخت شده)
        quarter_labels, tankhah_quarterly_spent, factor_quarterly_spent = [], [], []
        for i in range(3, -1, -1): # 4 فصل گذشته
            # محاسبه تاریخ شروع و پایان فصل
            # این بخش نیاز به منطق دقیق‌تری برای محاسبه تاریخ‌های فصلی شمسی دارد
            # مثال ساده:
            end_of_quarter_approx = (now - timedelta(days=i * 90))
            start_of_quarter_approx = (now - timedelta(days=(i + 1) * 90))
            quarter_labels.append(get_jalali_quarter_name_static(end_of_quarter_approx.date()))

            tankhah_q_seasonal = Q(status='PAID', date__range=(start_of_quarter_approx, end_of_quarter_approx))
            factor_q_seasonal = Q(status='PAID', date__range=(start_of_quarter_approx, end_of_quarter_approx))

            if active_period:
                #  اگر دوره بودجه فعال است، محدود به آن دوره هم می‌کنیم (اگر فصل با دوره همپوشانی دارد)
                # tankhah_q_seasonal &= Q(date__gte=max(active_period.start_date, start_of_quarter_approx.date()), date__lte=min(active_period.end_date, end_of_quarter_approx.date()))
                # factor_q_seasonal &= Q(date__gte=max(active_period.start_date, start_of_quarter_approx.date()), date__lte=min(active_period.end_date, end_of_quarter_approx.date()))
                pass # برای سادگی، فیلتر دوره را اینجا برای چارت فصلی اعمال نمی‌کنیم تا روند کلی دیده شود

            if organization_obj:
                tankhah_q_seasonal &= Q(organization=organization_obj)
                factor_q_seasonal &= Q(tankhah__organization=organization_obj)


            tankhah_val = Tankhah.objects.filter(tankhah_q_seasonal).aggregate(total=Sum('amount'))['total']
            factor_val = Factor.objects.filter(factor_q_seasonal).aggregate(total=Sum('amount'))['total']

            tankhah_quarterly_spent.append(float(tankhah_val or 0))
            factor_quarterly_spent.append(float(factor_val or 0))

        # داده نمونه
        if not quarter_labels :
            j_now = jdatetime.datetime.now()
            quarter_labels = [f"فصل {( (j_now.month -1) // 3 - i ) % 4 + 1} {j_now.year + ((j_now.month -1) // 3 - i ) // 4}" for i in range(3,-1,-1)]
            tankhah_quarterly_spent = [150, 180, 120, 200] # میلیون تومان
            factor_quarterly_spent = [130, 160, 110, 190]  # میلیون تومان

        data['tankhah_factor_quarterly_chart'] = {
            'labels': json.dumps(list(reversed(quarter_labels)), ensure_ascii=False), # معکوس برای نمایش از قدیم به جدید
            'tankhah_values': json.dumps(list(reversed(tankhah_quarterly_spent))),
            'factor_values': json.dumps(list(reversed(factor_quarterly_spent))),
        }


        # توزیع تنخواه‌ها بر اساس وضعیت
        tankhah_status_dist = Tankhah.objects.filter(tankhah_q)\
            .values('status')\
            .annotate(count=Count('id'))\
            .order_by('status')
        status_labels = [dict(Tankhah.STATUS_CHOICES).get(s['status'], s['status']) for s in tankhah_status_dist]
        status_values = [s['count'] for s in tankhah_status_dist]
        if not status_labels: # داده نمونه
            status_labels = [_("پیش‌نویس"), _("در حال بررسی"), _("تأییدشده"), _("پرداخت‌شده")]
            status_values = [5, 10, 25, 60]

        data['tankhah_status_distribution_chart'] = {
            'labels': json.dumps(status_labels, ensure_ascii=False),
            'values': json.dumps(status_values)
        }
        return data

    # --- توابع داده برای تب مراکز هزینه (پروژه‌ها) ---
    def get_projects_tab_data(self, active_period, organization_obj):
        data = {}
        project_q = Q(is_active=True)
        if organization_obj: project_q &= Q(organizations=organization_obj)
        if active_period: project_q &= Q(budget_allocations__budget_allocation__budget_period=active_period) # پروژه‌هایی که در این دوره تخصیص داشته‌اند

        active_projects = Project.objects.filter(project_q).distinct().order_by('-start_date')

        # KPI های پروژه‌ها
        total_projects_budget = Decimal('0')
        total_projects_consumed = Decimal('0')
        for proj in active_projects:
            # برای محاسبه بودجه پروژه، فیلترهای دوره را هم پاس می‌دهیم اگر active_period وجود دارد
            project_budget_filters = {'date_from': active_period.start_date, 'date_to': active_period.end_date} if active_period else None
            total_projects_budget += get_project_total_budget(proj, filters=project_budget_filters)
            total_projects_consumed += get_project_used_budget(proj, filters=project_budget_filters)

        data['projects_kpis'] = {
            'active_projects_count': active_projects.count(),
            'total_projects_allocated_budget': total_projects_budget,
            'total_projects_consumed_budget': total_projects_consumed,
            'overall_project_utilization': (total_projects_consumed / total_projects_budget * 100) if total_projects_budget > 0 else 0
        }
        # داده نمونه
        data['projects_kpis'].setdefault('active_projects_count', 15)
        data['projects_kpis'].setdefault('total_projects_allocated_budget', Decimal('3200000000'))
        data['projects_kpis'].setdefault('total_projects_consumed_budget', Decimal('1800000000'))
        data['projects_kpis'].setdefault('overall_project_utilization', 56.25)


        # نمودار درصد پیشرفت (مصرف) بودجه برای تاپ N پروژه
        project_performance_chart_labels = []
        project_performance_chart_utilization = []
        for proj in active_projects[:7]: # تاپ ۷ پروژه
            project_budget_filters = {'date_from': active_period.start_date, 'date_to': active_period.end_date} if active_period else None
            allocated = get_project_total_budget(proj, filters=project_budget_filters)
            consumed = get_project_used_budget(proj, filters=project_budget_filters)
            utilization = (consumed / allocated * 100) if allocated > 0 else 0
            project_performance_chart_labels.append(proj.name)
            project_performance_chart_utilization.append(float(utilization))

        if not project_performance_chart_labels: #داده نمونه
            project_performance_chart_labels = [_("پروژه راه اندازی شعبه X"), _("پروژه توسعه نرم افزار Y"), _("پروژه کمپین بازاریابی Z")]
            project_performance_chart_utilization = [75, 40, 92]


        data['project_utilization_chart'] = {
            'labels': json.dumps(project_performance_chart_labels, ensure_ascii=False),
            'values': json.dumps(project_performance_chart_utilization)
        }

        # جدول خلاصه وضعیت پروژه‌ها
        projects_summary_table = []
        for proj in active_projects:
            project_budget_filters = {'date_from': active_period.start_date, 'date_to': active_period.end_date} if active_period else None
            allocated = get_project_total_budget(proj, filters=project_budget_filters)
            consumed = get_project_used_budget(proj, filters=project_budget_filters)
            remaining = get_project_remaining_budget(proj, filters=project_budget_filters) # یا allocated - consumed
            projects_summary_table.append({
                'name': proj.name, 'code': proj.code,
                'allocated': float(allocated), 'consumed': float(consumed), 'remaining': float(remaining),
                'utilization': (float(consumed) / float(allocated) * 100) if allocated > 0 else 0
            })
        data['projects_summary_table'] = projects_summary_table[:10] # نمایش ۱۰ تای اول

        return data

    def get_context_data(self, request, *args, **kwargs):
        context = {}
        filters = self.get_filters(request)
        active_period = filters.get('budget_period_obj')
        organization_obj = filters.get('organization_obj')

        context['title'] = _("داشبورد مالی جامع")
        # لینک‌های اصلی داشبورد (اگر در فایل دیگری تعریف شده‌اند، import کنید)
        # context['dashboard_main_links'] = ...

        # فیلترها برای ارسال به تمپلیت
        context['budget_periods_for_filter'] = BudgetPeriod.objects.filter(is_active=True).order_by('-start_date')
        context['organizations_for_filter'] = Organization.objects.filter(is_active=True, org_type__is_budget_allocatable=True).order_by('name')
        context['selected_budget_period_id'] = active_period.id if active_period else None
        context['selected_organization_id'] = organization_obj.id if organization_obj else None
        context['selected_organization_name'] = organization_obj.name if organization_obj else _("کل سازمان")


        # داده‌های هر تب
        context['budget_tab_data'] = self.get_budget_tab_data(active_period, organization_obj)
        context['tankhah_tab_data'] = self.get_tankhah_tab_data(active_period, organization_obj)
        context['projects_tab_data'] = self.get_projects_tab_data(active_period, organization_obj)

        return context

    # def get(self, request, *args, **kwargs):
    #     context = self.get_context_data(request)
    #     return render(request, self.template_name, context)