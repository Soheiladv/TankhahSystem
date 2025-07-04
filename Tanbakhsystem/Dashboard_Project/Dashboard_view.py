# views.py
import json
from decimal import Decimal
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, Count, F, ExpressionWrapper, fields, Case, When, Value
from django.db.models.functions import Coalesce, TruncMonth, TruncQuarter
import jdatetime
from datetime import timedelta, date as py_date  # Renamed to avoid conflict
from django.utils import timezone
from django.urls import reverse_lazy

# Import models (مسیرها را با توجه به ساختار پروژه خودتان تنظیم کنید)
from core.models import Project, Organization
from budgets.models import BudgetPeriod, BudgetAllocation,  BudgetTransaction, BudgetItem
from tankhah.models import Tankhah, Factor

# Import calculation functions (مسیرها را با توجه به ساختار پروژه خودتان تنظیم کنید)
from budgets.budget_calculations import (
    get_project_total_budget,
    get_project_used_budget,
    get_project_remaining_budget,
    # ... و هر تابع دیگری که برای داشبورد نیاز دارید
)


# from Tanbakhsystem.utils import convert_to_farsi_numbers # اگر استفاده می‌کنید

def get_jalali_month_name_static(month_number):  # Static method version
    j_months_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن",
                   "اسفند"]
    try:
        month_number = int(month_number)
        if 1 <= month_number <= 12:
            return j_months_fa[month_number - 1]
        return str(month_number)
    except (ValueError, IndexError):
        return str(month_number)


class BudgetDashboardView(LoginRequiredMixin, View):
    template_name = 'Dashboard/dashboard_ui_filled.html'  # تمپلیت جدید
    login_url = reverse_lazy('accounts:login')

    def get_filters(self, request):
        # دریافت فیلترها از درخواست (برای سادگی فعلا فیلترها را در نظر نمی‌گیریم)
        # در حالت واقعی:
        # budget_period_id = request.GET.get('budget_period')
        # organization_id = request.GET.get('organization')
        # ...
        # return {'budget_period_id': budget_period_id, ...}
        return {}

    def get_context_data(self, request, *args, **kwargs):
        context = {}
        filters = self.get_filters(request)  # در آینده برای اعمال فیلترها
        now = timezone.now()
        j_now = jdatetime.datetime.now()

        # --- 1. KPI Scorecards Data ---
        # (مشابه لینک Looker Studio - بخش بالایی با اعداد بزرگ)
        # شما باید این مقادیر را از مدل‌ها و توابع خودتان محاسبه کنید
        # مثال ساده شده:
        active_period = BudgetPeriod.objects.filter(is_active=True, is_completed=False).first()
        total_budget_amount = Decimal('0')
        total_spent_amount = Decimal('0')
        total_allocated_to_projects = Decimal('0')

        if active_period:
            total_budget_amount = active_period.total_amount or Decimal('5000000000')  # داده نمونه

            # کل هزینه شده واقعی از BudgetTransaction
            total_spent_amount = BudgetTransaction.objects.filter(
                allocation__budget_period=active_period,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('1500000000')

            # کل بودجه تخصیص یافته به پروژه‌ها در این دوره
            total_allocated_to_projects = BudgetAllocation.objects.filter(
                budget_allocation__budget_period=active_period
            ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total'] or Decimal('3000000000')

        context['kpi_data'] = {
            'total_budget': total_budget_amount,
            'total_spent': total_spent_amount,
            'remaining_budget': total_budget_amount - total_spent_amount,
            'utilization_percentage': (
                        total_spent_amount / total_budget_amount * 100) if total_budget_amount > 0 else 0,
            'active_projects_count': Project.objects.filter(is_active=True,
                                                            budget_allocations__budget_allocation__budget_period=active_period).distinct().count() if active_period else Project.objects.filter(
                is_active=True).count() or 5,
            'open_tankhahs_amount': Tankhah.objects.filter(
                status__in=['PENDING', 'DRAFT', 'SENT_TO_HQ'],
                # project__budget_allocations__budget_allocation__budget_period=active_period # اگر می‌خواهید به دوره فعال محدود کنید
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('250000000')
        }

        # --- 2. Budget vs. Actual Trend (Time Series Chart) ---
        # (مشابه نمودار خطی در Looker Studio)
        # داده‌های نمونه برای 6 ماه گذشته
        trend_labels = []
        trend_allocated = []
        trend_spent = []
        for i in range(5, -1, -1):
            month_dt = now - timedelta(days=i * 30)
            j_month_dt = jdatetime.date.fromgregorian(date=month_dt)
            month_label = f"{get_jalali_month_name_static(j_month_dt.month)} {j_month_dt.year}"
            trend_labels.append(month_label)

            # مقادیر نمونه - شما باید اینها را از دیتابیس محاسبه کنید
            # بودجه تخصیص یافته در آن ماه
            # allocated_in_month = BudgetAllocation.objects.filter(
            #     allocation_date__year=month_dt.year,
            #     allocation_date__month=month_dt.month
            # ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
            # trend_allocated.append(float(allocated_in_month or Decimal( (6-i) * 100000000) ))
            trend_allocated.append(float(Decimal((6 - i) * 100000000) + (i * 15000000)))

            # هزینه شده در آن ماه
            # spent_in_month = BudgetTransaction.objects.filter(
            #     timestamp__year=month_dt.year,
            #     timestamp__month=month_dt.month,
            #     transaction_type='CONSUMPTION'
            # ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            # trend_spent.append(float(spent_in_month or Decimal( (6-i) * 70000000) ))
            trend_spent.append(float(Decimal((6 - i) * 70000000) - (i * 10000000)))

        context['budget_trend_data'] = {
            'labels': json.dumps(trend_labels, ensure_ascii=False),
            'allocated': json.dumps(trend_allocated),
            'spent': json.dumps(trend_spent),
        }

        # --- 3. Spending by Category/Project (Pie or Bar Chart) ---
        # (مشابه نمودارهای تفکیکی در Looker Studio)
        # مثال: هزینه بر اساس پروژه
        project_spending_labels = []
        project_spending_values = []
        # top_projects = Project.objects.filter(is_active=True).annotate(
        #     total_spent_on_project=Sum(
        #         Case(
        #             When(tankhah_set__factor__status='PAID', then=F('tankhah_set__factor__amount')),
        #             default=Value(0),
        #             output_field=fields.DecimalField()
        #         ) # این کوئری نیاز به بازبینی دقیق دارد
        #     )
        # ).order_by('-total_spent_on_project')[:5] # ۵ پروژه با بیشترین هزینه

        # برای سادگی، داده نمونه میگذاریم چون کوئری بالا پیچیده است
        sample_projects_spending = [
            {"name": "پروژه آلفا", "spent": 120000000},
            {"name": "پروژه بتا", "spent": 95000000},
            {"name": "پروژه گاما", "spent": 70000000},
            {"name": "پروژه دلتا", "spent": 50000000},
            {"name": "پروژه امگا", "spent": 30000000},
        ]

        for proj_data in sample_projects_spending:  # به جای top_projects
            project_spending_labels.append(proj_data['name'])
            # project_spending_values.append(float(proj_data.total_spent_on_project or 0))
            project_spending_values.append(float(proj_data['spent']))

        context['project_spending_data'] = {
            'labels': json.dumps(project_spending_labels, ensure_ascii=False),
            'values': json.dumps(project_spending_values),
        }

        # --- 4. Project Performance Table ---
        # (مشابه جداول داده در Looker Studio)
        project_performance = []
        active_projects = Project.objects.filter(is_active=True).order_by('-start_date')[:7]  # ۷ پروژه اخیر
        for proj in active_projects:
            allocated = get_project_total_budget(proj) or Decimal('100000000') + (proj.id % 5 * 20000000)  # داده نمونه
            # consumed = get_project_used_budget(proj) or Decimal('40000000') + (proj.id % 3 * 15000000)  # داده نمونه
            # remaining = get_project_remaining_budget(proj) # یا allocated - consumed

            # برای نمایش واقعی تر
            from budgets.budget_calculations import get_actual_project_remaining_budget
            # actual_remaining, consumed, returned = get_actual_project_remaining_budget(proj,
            #                                                                            return_consumed_returned=True)
            # remaining = actual_remaining

            project_performance.append({
                'id': proj.pk,
                'name': proj.name,
                'code': proj.code,
                'allocated': allocated,
                # 'consumed': consumed,
                # 'remaining': remaining,
                # 'percentage_consumed': (consumed / allocated * 100) if allocated > 0 else 0,
                'status': proj.get_priority_display()  # یا یک فیلد وضعیت دیگر اگر دارید
            })
        context['project_performance_data'] = project_performance

        # --- 5. Recent Activities (Optional, from ApprovalLog) ---
        # context['recent_activities'] = ApprovalLog.objects.order_by('-timestamp')[:5]

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)