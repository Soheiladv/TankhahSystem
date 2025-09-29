from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, F, Case, When, DecimalField
from django.db.models.functions import TruncMonth, TruncDay, TruncYear
from django.utils import timezone
from datetime import datetime, timedelta
import json
from decimal import Decimal
try:
    import jdatetime
except Exception:
    jdatetime = None

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    PaymentOrder, BudgetItem
)
from tankhah.models import Tankhah, Factor
from core.models import Organization, Project, Status


class DashboardMainView(TemplateView):
    """داشبورد اصلی گزارشات با آمار کلی"""
    template_name = 'reports/dashboard/main_dashboard.html'
    # کدهای دسترسی تب‌ها (قابل تغییر در آینده)
    TAB_PERMISSION_CODES = {
        'overview': 'reports.Dashboard_view',
        'budget': 'reports.Dashboard_budget',
        'tankhah': 'reports.Dashboard_tankhah',
        'factors': 'reports.Dashboard_factors',
        'risk': 'reports.Dashboard_risk',
    }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # فیلترهای دریافت شده (ست اصلی)
        start_date = self._parse_jalali_date(self.request.GET.get('start_date'))
        end_date = self._parse_jalali_date(self.request.GET.get('end_date'))
        organization_id = self.request.GET.get('organization')
        project_id = self.request.GET.get('project')
        
        # آمار کلی بودجه (با فیلترها)
        budget_stats = self.get_budget_statistics(start_date, end_date, organization_id, project_id)
        context['budget_stats'] = budget_stats
        
        # آمار تنخواه‌ها
        tankhah_stats = self.get_tankhah_statistics(start_date, end_date, organization_id, project_id)
        context['tankhah_stats'] = tankhah_stats
        
        # آمار فاکتورها
        factor_stats = self.get_factor_statistics(start_date, end_date, organization_id, project_id)
        context['factor_stats'] = factor_stats
        
        # آمار دستورات پرداخت
        payment_stats = self.get_payment_statistics(start_date, end_date, organization_id, project_id)
        context['payment_stats'] = payment_stats
        
        # آمار مراکز هزینه
        cost_center_stats = self.get_cost_center_statistics(organization_id, project_id)
        context['cost_center_stats'] = cost_center_stats
        
        # آمار برگشت‌های بودجه
        return_stats = self.get_budget_return_statistics(start_date, end_date, organization_id, project_id)
        context['return_stats'] = return_stats
        
        # چارت‌های داده
        chart_data = self.get_chart_data(start_date, end_date, organization_id, project_id)
        context['chart_data'] = json.dumps(chart_data, ensure_ascii=False)

        # متریک‌های پیشرفته بودجه (نرخ جذب، برنامه/واقعی، پیش‌بینی، تمرکز، ایجینگ)
        advanced_budget = self.get_advanced_budget_metrics(start_date, end_date, organization_id, project_id)
        context['advanced_budget'] = json.dumps(advanced_budget, ensure_ascii=False, default=str)

        # متریک‌های پیشرفته تنخواه (تسویه، معوق، سقف، وضعیت، ایجینگ تسویه)
        advanced_tankhah = self.get_advanced_tankhah_metrics(start_date, end_date, organization_id, project_id)
        context['advanced_tankhah'] = json.dumps(advanced_tankhah, ensure_ascii=False, default=str)

        # متریک‌های پیشرفته فاکتور
        advanced_factor = self.get_advanced_factor_metrics(start_date, end_date, organization_id, project_id)
        context['advanced_factor'] = json.dumps(advanced_factor, ensure_ascii=False, default=str)

        # مقایسه‌ها (YoY/MoM و رتبه‌بندی‌ها)
        advanced_comparatives = self.get_advanced_comparatives(start_date, end_date, organization_id, project_id)
        context['advanced_comparatives'] = json.dumps(advanced_comparatives, ensure_ascii=False, default=str)

        # ریسک‌ها
        advanced_risk = self.get_advanced_risk_metrics(start_date, end_date, organization_id, project_id)
        context['advanced_risk'] = json.dumps(advanced_risk, ensure_ascii=False, default=str)

        # فیلترهای مقایسه‌ای (اختیاری: در صورت ارسال)
        compare_start = self._parse_jalali_date(self.request.GET.get('compare_start_date'))
        compare_end = self._parse_jalali_date(self.request.GET.get('compare_end_date'))
        compare_org = self.request.GET.get('compare_organization')
        compare_project = self.request.GET.get('compare_project')

        if any([compare_start, compare_end, compare_org, compare_project]):
            context['budget_stats_compare'] = self.get_budget_statistics(compare_start, compare_end, compare_org, compare_project)
            context['tankhah_stats_compare'] = self.get_tankhah_statistics(compare_start, compare_end, compare_org, compare_project)
            context['factor_stats_compare'] = self.get_factor_statistics(compare_start, compare_end, compare_org, compare_project)
            context['payment_stats_compare'] = self.get_payment_statistics(compare_start, compare_end, compare_org, compare_project)
            context['return_stats_compare'] = self.get_budget_return_statistics(compare_start, compare_end, compare_org, compare_project)
            context['chart_data_compare'] = json.dumps(self.get_chart_data(compare_start, compare_end, compare_org, compare_project), ensure_ascii=False)

        # گزینه‌های واقعی سازمان و پروژه برای فیلترها
        context['organizations'] = list(Organization.objects.values('id', 'name').order_by('name'))
        context['projects'] = list(Project.objects.values('id', 'name').order_by('name'))

        # جدول دسته‌بندی فاکتورها (Top 10)
        context['factor_category_table'] = factor_stats.get('category_stats', [])[:10]

        # مقایسه سازمان/پروژه بر اساس مجموع تخصیص (Top 10)
        alloc_qs = BudgetAllocation.objects.all()
        if start_date:
            alloc_qs = alloc_qs.filter(allocation_date__gte=start_date)
        if end_date:
            alloc_qs = alloc_qs.filter(allocation_date__lte=end_date)
        if organization_id:
            alloc_qs = alloc_qs.filter(organization_id=organization_id)
        if project_id:
            alloc_qs = alloc_qs.filter(project_id=project_id)
        org_compare = alloc_qs.values('organization__name').annotate(total=Sum('allocated_amount')).order_by('-total')[:10]
        project_compare = alloc_qs.values('project__name').annotate(total=Sum('allocated_amount')).order_by('-total')[:10]
        context['org_compare'] = list(org_compare)
        context['project_compare'] = list(project_compare)

        # نشانگرهای ریسک ساده: نسبت برگشت به تخصیص برای سازمان‌ها + Aging تنخواه‌ها
        org_alloc_map = {o['organization__name']: o['total'] for o in org_compare}
        risk_rows = []
        for o in return_stats.get('org_returns', []):
            name = o.get('allocation__organization__name')
            ret_total = o.get('total_amount') or Decimal('0')
            alloc_total = org_alloc_map.get(name) or Decimal('0')
            ratio = float(ret_total) / float(alloc_total) * 100.0 if alloc_total and float(alloc_total) > 0 else 0.0
            risk_rows.append({
                'organization': name or 'نامشخص',
                'return_amount': ret_total,
                'allocated_amount': alloc_total,
                'return_ratio': ratio,
            })
        context['risk_table'] = sorted(risk_rows, key=lambda x: x['return_ratio'], reverse=True)[:10]

        # Aging تنخواه‌ها (ساده)
        today = timezone.now().date()
        def days_ago(n):
            return today - timedelta(days=n)
        aging_counts = Tankhah.objects.aggregate(
            d_0_30=Count('id', filter=Q(date__date__gt=days_ago(30))),
            d_31_60=Count('id', filter=Q(date__date__lte=days_ago(30)) & Q(date__date__gt=days_ago(60))),
            d_61_90=Count('id', filter=Q(date__date__lte=days_ago(60)) & Q(date__date__gt=days_ago(90))),
            d_90_plus=Count('id', filter=Q(date__date__lte=days_ago(90)))
        )
        context['tankhah_aging'] = aging_counts

        # مجوزها فعلاً غیرفعال (نمایش همه)
        context['can_view_overview'] = True
        context['can_view_budget'] = True
        context['can_view_tankhah'] = True
        context['can_view_factors'] = True
        context['can_view_risk'] = True
        
        return context
    
    def _parse_jalali_date(self, value):
        """If input is like 1404/07/01 convert to Gregorian date; else pass through.
        Returns a datetime.date or the original value if not parseable.
        """
        if not value:
            return None
        try:
            # Normalize separators
            val = str(value).strip()
            if '/' in val:
                parts = val.replace('\u200f', '').split('/')
                if len(parts) == 3 and all(parts):
                    y, m, d = [int(p) for p in parts]
                    if jdatetime:
                        return jdatetime.date(y, m, d).togregorian()
            # Fallback: try ISO YYYY-MM-DD
            return val
        except Exception:
            return value
    
    def get_budget_statistics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """آمار کلی بودجه"""
        total_budget = BudgetPeriod.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        allocations = BudgetAllocation.objects.all()
        if start_date:
            allocations = allocations.filter(allocation_date__gte=start_date)
        if end_date:
            allocations = allocations.filter(allocation_date__lte=end_date)
        if organization_id:
            allocations = allocations.filter(organization_id=organization_id)
        if project_id:
            allocations = allocations.filter(project_id=project_id)

        total_allocated = allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        
        transactions = BudgetTransaction.objects.all()
        if start_date:
            transactions = transactions.filter(timestamp__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(timestamp__date__lte=end_date)
        if organization_id:
            transactions = transactions.filter(allocation__organization_id=organization_id)
        if project_id:
            transactions = transactions.filter(allocation__project_id=project_id)

        total_consumed = transactions.filter(
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_returned = transactions.filter(
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        remaining = total_allocated - total_consumed + total_returned
        
        # جلوگیری از تقسیم بر صفر و تبدیل به درصد درست
        consumption_percentage = (float(total_consumed) / float(total_allocated) * 100.0) if total_allocated and float(total_allocated) > 0 else 0.0
        return_percentage = (float(total_returned) / float(total_allocated) * 100.0) if total_allocated and float(total_allocated) > 0 else 0.0
        
        return {
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'total_consumed': total_consumed,
            'total_returned': total_returned,
            'remaining': remaining,
            'consumption_percentage': consumption_percentage,
            'return_percentage': return_percentage,
        }
    
    def get_tankhah_statistics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """آمار تنخواه‌ها"""
        tankhah_qs = Tankhah.objects.all()
        if start_date:
            tankhah_qs = tankhah_qs.filter(date__date__gte=start_date)
        if end_date:
            tankhah_qs = tankhah_qs.filter(date__date__lte=end_date)
        if organization_id:
            tankhah_qs = tankhah_qs.filter(organization_id=organization_id)
        if project_id:
            tankhah_qs = tankhah_qs.filter(project_id=project_id)

        total_tankhah = tankhah_qs.count()
        total_amount = tankhah_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس وضعیت
        status_stats = tankhah_qs.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        # آمار بر اساس سازمان
        org_stats = tankhah_qs.values('organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        return {
            'total_count': total_tankhah,
            'total_amount': total_amount,
            'status_stats': list(status_stats),
            'org_stats': list(org_stats),
        }
    
    def get_factor_statistics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """آمار فاکتورها"""
        factor_qs = Factor.objects.all()
        if start_date:
            factor_qs = factor_qs.filter(date__gte=start_date)
        if end_date:
            factor_qs = factor_qs.filter(date__lte=end_date)
        if organization_id:
            factor_qs = factor_qs.filter(tankhah__organization_id=organization_id)
        if project_id:
            factor_qs = factor_qs.filter(tankhah__project_id=project_id)

        total_factors = factor_qs.count()
        total_amount = factor_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس دسته‌بندی
        category_stats = factor_qs.values('category__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # آمار بر اساس وضعیت
        status_stats = factor_qs.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        return {
            'total_count': total_factors,
            'total_amount': total_amount,
            'category_stats': list(category_stats),
            'status_stats': list(status_stats),
        }
    
    def get_payment_statistics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """آمار دستورات پرداخت"""
        payments_qs = PaymentOrder.objects.all()
        if start_date:
            payments_qs = payments_qs.filter(issue_date__gte=start_date)
        if end_date:
            payments_qs = payments_qs.filter(issue_date__lte=end_date)
        if organization_id:
            payments_qs = payments_qs.filter(organization_id=organization_id)
        if project_id:
            payments_qs = payments_qs.filter(project_id=project_id)

        total_orders = payments_qs.count()
        total_amount = payments_qs.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس وضعیت
        status_stats = payments_qs.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        # آمار بر اساس سازمان
        org_stats = payments_qs.values('organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        return {
            'total_count': total_orders,
            'total_amount': total_amount,
            'status_stats': list(status_stats),
            'org_stats': list(org_stats),
        }
    
    def get_cost_center_statistics(self, organization_id=None, project_id=None):
        """آمار مراکز هزینه (پروژه‌ها)"""
        projects_qs = Project.objects.all()
        if project_id:
            projects_qs = projects_qs.filter(id=project_id)
        if organization_id:
            projects_qs = projects_qs.filter(allocations__organization_id=organization_id)

        total_projects = projects_qs.count()
        
        # آمار بودجه پروژه‌ها
        project_stats = projects_qs.annotate(
            total_budget=Sum('allocations__allocated_amount'),
            consumed_budget=Sum('allocations__transactions__amount', 
                              filter=Q(allocations__transactions__transaction_type='CONSUMPTION')),
            returned_budget=Sum('allocations__transactions__amount',
                              filter=Q(allocations__transactions__transaction_type='RETURN'))
        ).values('name', 'code', 'total_budget', 'consumed_budget', 'returned_budget')
        
        return {
            'total_count': total_projects,
            'project_stats': list(project_stats),
        }
    
    def get_advanced_tankhah_metrics(self, start_date=None, end_date=None, organization_id=None, project_id=None, overdue_days: int = 30):
        """محاسبه متریک‌های پیشرفته برای تنخواه.
        - avg_settlement_days: متوسط فاصله ایجاد تا پرداخت (با PaymentOrder.payment_date)
        - overdue_rate: درصد درخواست‌های باز با عمر > N روز
        - ceiling_usage: نسبت مبلغ به سقف، میانگین و Top 5
        - status distributions by org/project
        - settlement aging buckets (0-30/31-60/61-90/90+)
        """
        tankhah_qs = Tankhah.objects.all().select_related('organization', 'project', 'status')
        if start_date:
            tankhah_qs = tankhah_qs.filter(date__date__gte=start_date)
        if end_date:
            tankhah_qs = tankhah_qs.filter(date__date__lte=end_date)
        if organization_id:
            tankhah_qs = tankhah_qs.filter(organization_id=organization_id)
        if project_id:
            tankhah_qs = tankhah_qs.filter(project_id=project_id)

        # Average settlement time using PaymentOrder.payment_date
        po_qs = PaymentOrder.objects.filter(
            Q(tankhah__in=tankhah_qs) | Q(related_tankhah__in=tankhah_qs),
            payment_date__isnull=False
        ).select_related('tankhah', 'related_tankhah')

        settlement_days = []
        for po in po_qs:
            t = po.tankhah or po.related_tankhah
            try:
                start_dt = t.date.date() if hasattr(t.date, 'date') else t.date
                days = (po.payment_date - start_dt).days
                if days >= 0:
                    settlement_days.append(days)
            except Exception:
                continue
        avg_settlement_days = (sum(settlement_days) / len(settlement_days)) if settlement_days else 0.0

        # Overdue rate among open tankhahs
        open_qs = tankhah_qs.filter(
            Q(status__is_final_approve=False) & Q(status__is_final_reject=False)
        )
        today = timezone.now().date()
        overdue_count = 0
        for t in open_qs.values('date'):
            try:
                start_dt = t['date']
                if hasattr(start_dt, 'date'):
                    start_dt = start_dt.date()
                if (today - start_dt).days > overdue_days:
                    overdue_count += 1
            except Exception:
                continue
        open_total = open_qs.count() or 0
        overdue_rate = (overdue_count / open_total * 100.0) if open_total > 0 else 0.0

        # Ceiling usage
        ceiling_qs = tankhah_qs.filter(is_payment_ceiling_enabled=True, payment_ceiling__isnull=False).exclude(payment_ceiling=0)
        usage_list = []
        for rec in ceiling_qs.values('amount', 'payment_ceiling', 'number'):
            try:
                amt = float(rec['amount'] or 0)
                ceil = float(rec['payment_ceiling'] or 0)
                ratio = (amt / ceil * 100.0) if ceil > 0 else 0.0
                usage_list.append({'number': rec['number'], 'usage_pct': ratio})
            except Exception:
                continue
        avg_ceiling_usage = (sum(x['usage_pct'] for x in usage_list) / len(usage_list)) if usage_list else 0.0
        top_ceiling_usage = sorted(usage_list, key=lambda x: x['usage_pct'], reverse=True)[:5]

        # Status distributions by org/project with counts and amounts
        status_by_org = list(
            tankhah_qs.values('organization__name', 'status__name').annotate(
                count=Count('id'), total_amount=Sum('amount')
            ).order_by('organization__name', 'status__name')
        )
        status_by_project = list(
            tankhah_qs.values('project__name', 'status__name').annotate(
                count=Count('id'), total_amount=Sum('amount')
            ).order_by('project__name', 'status__name')
        )

        # Settlement aging from payment_date - created date
        d_0_30 = d_31_60 = d_61_90 = d_90_plus = 0
        for po in po_qs.values('payment_date', 'tankhah__date', 'related_tankhah__date'):
            try:
                tdate = po.get('tankhah__date') or po.get('related_tankhah__date')
                if hasattr(tdate, 'date'):
                    tdate = tdate.date()
                days = (po['payment_date'] - tdate).days
                if days <= 30:
                    d_0_30 += 1
                elif days <= 60:
                    d_31_60 += 1
                elif days <= 90:
                    d_61_90 += 1
                else:
                    d_90_plus += 1
            except Exception:
                continue

        return {
            'avg_settlement_days': avg_settlement_days,
            'overdue_rate_pct': overdue_rate,
            'overdue_days_threshold': overdue_days,
            'avg_ceiling_usage_pct': avg_ceiling_usage,
            'top_ceiling_usage': top_ceiling_usage,
            'status_by_org': status_by_org,
            'status_by_project': status_by_project,
            'settlement_aging': {
                'd_0_30': d_0_30,
                'd_31_60': d_31_60,
                'd_61_90': d_61_90,
                'd_90_plus': d_90_plus,
            }
        }

    def get_advanced_factor_metrics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """محاسبه متریک‌های پیشرفته برای فاکتورها.
        - avg_cycle_days: از ایجاد تا پرداخت (در صورت وجود PaymentOrder.payment_date)
        - rejection_rate و دلایل پرتکرار (rejected_reason)
        - category_analysis: تعداد و مبلغ به ازای دسته‌بندی
        - high_risk: فاکتورهای پرریسک (Top by amount، تکرار فروشنده، خارج از بودجه)
        """
        factor_qs = Factor.objects.all().select_related('tankhah', 'tankhah__organization', 'tankhah__project', 'status', 'category', 'payee')
        if start_date:
            factor_qs = factor_qs.filter(date__gte=start_date)
        if end_date:
            factor_qs = factor_qs.filter(date__lte=end_date)
        if organization_id:
            factor_qs = factor_qs.filter(tankhah__organization_id=organization_id)
        if project_id:
            factor_qs = factor_qs.filter(tankhah__project_id=project_id)

        total_factors = factor_qs.count() or 0

        # Avg cycle time: use related PaymentOrder payment_date if any
        po_qs = PaymentOrder.objects.filter(related_factors__in=factor_qs, payment_date__isnull=False).values('payment_date', 'related_factors__id', 'related_factors__created_at')
        cycle_days = []
        for po in po_qs:
            try:
                created = po['related_factors__created_at']
                if hasattr(created, 'date'):
                    created = created.date()
                days = (po['payment_date'] - created).days
                if days >= 0:
                    cycle_days.append(days)
            except Exception:
                continue
        avg_cycle_days = (sum(cycle_days) / len(cycle_days)) if cycle_days else 0.0

        # Rejection rate and reasons
        rejected_qs = factor_qs.filter(Q(status__is_final_reject=True) | Q(status__code__icontains='REJECT'))
        rejected_count = rejected_qs.count() or 0
        rejection_rate = (rejected_count / total_factors * 100.0) if total_factors > 0 else 0.0
        top_reject_reasons = list(
            rejected_qs.values('rejected_reason').annotate(count=Count('id')).order_by('-count')[:10]
        )

        # Category analysis
        category_stats = list(
            factor_qs.values('category__name').annotate(count=Count('id'), total_amount=Sum('amount')).order_by('-total_amount')
        )

        # High risk: top by amount
        top_amount = list(factor_qs.order_by('-amount').values('id', 'number', 'amount', 'payee__legal_name', 'payee__name')[:10])

        # High risk: repeated vendor
        repeated_vendors = list(
            factor_qs.values('payee__id', 'payee__legal_name', 'payee__name').annotate(count=Count('id')).filter(count__gt=3).order_by('-count')[:10]
        )

        # High risk: outside budget (amount > budget or negative remaining)
        outside_budget = []
        for f in factor_qs.values('id', 'number', 'amount', 'budget', 'remaining_budget'):
            try:
                amt = float(f['amount'] or 0)
                budget = float(f['budget'] or 0)
                remaining = float(f['remaining_budget'] or 0)
                if (budget and amt > budget) or remaining < 0:
                    outside_budget.append({'id': f['id'], 'number': f['number'], 'amount': amt, 'budget': budget, 'remaining': remaining})
            except Exception:
                continue

        return {
            'totals': {
                'count': total_factors,
                'avg_cycle_days': avg_cycle_days,
                'rejection_rate_pct': rejection_rate,
            },
            'top_reject_reasons': top_reject_reasons,
            'category_stats': category_stats,
            'high_risk': {
                'top_amount': top_amount,
                'repeated_vendors': repeated_vendors,
                'outside_budget': outside_budget[:10],
            }
        }

    def get_advanced_comparatives(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """مقایسه‌های سال‌به‌سال/ماه‌به‌ماه و رتبه‌بندی سازمان/پروژه."""
        # Base filters
        alloc_qs = BudgetAllocation.objects.all()
        if start_date:
            alloc_qs = alloc_qs.filter(allocation_date__gte=start_date)
        if end_date:
            alloc_qs = alloc_qs.filter(allocation_date__lte=end_date)
        if organization_id:
            alloc_qs = alloc_qs.filter(organization_id=organization_id)
        if project_id:
            alloc_qs = alloc_qs.filter(project_id=project_id)

        cons_qs = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION')
        ret_qs = BudgetTransaction.objects.filter(transaction_type='RETURN')
        if start_date:
            cons_qs = cons_qs.filter(timestamp__date__gte=start_date)
            ret_qs = ret_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            cons_qs = cons_qs.filter(timestamp__date__lte=end_date)
            ret_qs = ret_qs.filter(timestamp__date__lte=end_date)
        if organization_id:
            cons_qs = cons_qs.filter(allocation__organization_id=organization_id)
            ret_qs = ret_qs.filter(allocation__organization_id=organization_id)
        if project_id:
            cons_qs = cons_qs.filter(allocation__project_id=project_id)
            ret_qs = ret_qs.filter(allocation__project_id=project_id)

        # Monthly series for last periods
        monthly_cons = list(cons_qs.extra(select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}).values('month').annotate(total=Sum('amount'), count=Count('id')).order_by('month'))
        monthly_ret  = list(ret_qs.extra(select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}).values('month').annotate(total=Sum('amount'), count=Count('id')).order_by('month'))

        def calc_change(series):
            # series: [{'month': 'YYYY-MM-01', 'total': X}]
            if not series:
                return {'mom_pct': 0.0, 'yoy_pct': 0.0}
            try:
                last = series[-1]
                # find previous month
                from datetime import datetime
                cur = datetime.strptime(last['month'], '%Y-%m-%d')
                pm_y = cur.year if cur.month > 1 else cur.year - 1
                pm_m = cur.month - 1 if cur.month > 1 else 12
                prev_month_key = f"{pm_y:04d}-{pm_m:02d}-01"
                prev_month = next((x for x in series if x['month'] == prev_month_key), None)
                mom = ((float(last.get('total') or 0) - float(prev_month.get('total') or 0)) / float(prev_month.get('total') or 1) * 100.0) if prev_month else 0.0
                # year over year
                yoy_key = f"{cur.year-1:04d}-{cur.month:02d}-01"
                prev_year = next((x for x in series if x['month'] == yoy_key), None)
                yoy = ((float(last.get('total') or 0) - float(prev_year.get('total') or 0)) / float(prev_year.get('total') or 1) * 100.0) if prev_year else 0.0
                return {'mom_pct': mom, 'yoy_pct': yoy}
            except Exception:
                return {'mom_pct': 0.0, 'yoy_pct': 0.0}

        changes = {
            'consumption': calc_change(monthly_cons),
            'returns': calc_change(monthly_ret),
        }

        # Rankings by organization
        org_alloc = alloc_qs.values('organization__name').annotate(allocated=Sum('allocated_amount'))
        org_alloc_map = {x['organization__name']: float(x['allocated'] or 0) for x in org_alloc}
        org_cons = cons_qs.values('allocation__organization__name').annotate(total=Sum('amount')).order_by('-total')
        org_ret  = ret_qs.values('allocation__organization__name').annotate(total=Sum('amount')).order_by('-total')
        org_map_con = {x['allocation__organization__name']: float(x['total'] or 0) for x in org_cons}
        org_map_ret = {x['allocation__organization__name']: float(x['total'] or 0) for x in org_ret}
        org_names = list(set(list(org_alloc_map.keys()) + list(org_map_con.keys()) + list(org_map_ret.keys())))
        org_rank = []
        for n in org_names:
            alloc = org_alloc_map.get(n, 0.0)
            cons = org_map_con.get(n, 0.0)
            retn = org_map_ret.get(n, 0.0)
            eff = (cons / alloc * 100.0) if alloc > 0 else 0.0
            org_rank.append({'name': n or 'نامشخص', 'allocated': alloc, 'consumption': cons, 'returns': retn, 'efficiency_pct': eff})
        org_rank = sorted(org_rank, key=lambda x: x['consumption'], reverse=True)[:10]

        # Rankings by project
        proj_alloc = alloc_qs.values('project__name').annotate(allocated=Sum('allocated_amount'))
        proj_alloc_map = {x['project__name']: float(x['allocated'] or 0) for x in proj_alloc}
        proj_cons = cons_qs.values('allocation__project__name').annotate(total=Sum('amount')).order_by('-total')
        proj_ret  = ret_qs.values('allocation__project__name').annotate(total=Sum('amount')).order_by('-total')
        proj_map_con = {x['allocation__project__name']: float(x['total'] or 0) for x in proj_cons}
        proj_map_ret = {x['allocation__project__name']: float(x['total'] or 0) for x in proj_ret}
        proj_names = list(set(list(proj_alloc_map.keys()) + list(proj_map_con.keys()) + list(proj_map_ret.keys())))
        proj_rank = []
        for n in proj_names:
            alloc = proj_alloc_map.get(n, 0.0)
            cons = proj_map_con.get(n, 0.0)
            retn = proj_map_ret.get(n, 0.0)
            eff = (cons / alloc * 100.0) if alloc > 0 else 0.0
            proj_rank.append({'name': n or 'نامشخص', 'allocated': alloc, 'consumption': cons, 'returns': retn, 'efficiency_pct': eff})
        proj_rank = sorted(proj_rank, key=lambda x: x['consumption'], reverse=True)[:10]

        return {
            'monthly': {
                'consumption': monthly_cons,
                'returns': monthly_ret,
            },
            'changes': changes,
            'rankings': {
                'organizations': org_rank,
                'projects': proj_rank,
            }
        }

    def get_advanced_risk_metrics(self, start_date=None, end_date=None, organization_id=None, project_id=None,
                                   overconsumption_threshold_pct: float = 90.0,
                                   long_cycle_days: int = 30,
                                   spike_threshold_pct: float = 100.0):
        """محاسبه ریسک‌ها: اضافه‌مصرف، برگشت بالا، تأخیر، تمرکز، الگوهای غیرعادی."""
        # Filters
        alloc_qs = BudgetAllocation.objects.all()
        if start_date:
            alloc_qs = alloc_qs.filter(allocation_date__gte=start_date)
        if end_date:
            alloc_qs = alloc_qs.filter(allocation_date__lte=end_date)
        if organization_id:
            alloc_qs = alloc_qs.filter(organization_id=organization_id)
        if project_id:
            alloc_qs = alloc_qs.filter(project_id=project_id)

        cons_qs = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION')
        ret_qs = BudgetTransaction.objects.filter(transaction_type='RETURN')
        if start_date:
            cons_qs = cons_qs.filter(timestamp__date__gte=start_date)
            ret_qs = ret_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            cons_qs = cons_qs.filter(timestamp__date__lte=end_date)
            ret_qs = ret_qs.filter(timestamp__date__lte=end_date)
        if organization_id:
            cons_qs = cons_qs.filter(allocation__organization_id=organization_id)
            ret_qs = ret_qs.filter(allocation__organization_id=organization_id)
        if project_id:
            cons_qs = cons_qs.filter(allocation__project_id=project_id)
            ret_qs = ret_qs.filter(allocation__project_id=project_id)

        # Overconsumption risk per allocation
        cons_by_alloc = cons_qs.values('allocation_id').annotate(total=Sum('amount'))
        alloc_map = {a.id: float(a.allocated_amount) for a in alloc_qs.only('id', 'allocated_amount')}
        overconsumption = []
        for row in cons_by_alloc:
            alloc_id = row['allocation_id']
            allocated = alloc_map.get(alloc_id, 0.0)
            consumed = float(row['total'] or 0)
            pct = (consumed / allocated * 100.0) if allocated > 0 else 0.0
            if pct >= overconsumption_threshold_pct or consumed > allocated:
                overconsumption.append({'allocation_id': alloc_id, 'consumed': consumed, 'allocated': allocated, 'pct': pct})
        overconsumption = sorted(overconsumption, key=lambda x: x['pct'], reverse=True)[:10]

        # High return ratio by org/project
        org_alloc = alloc_qs.values('organization__name').annotate(allocated=Sum('allocated_amount'))
        org_alloc_map = {x['organization__name'] or 'نامشخص': float(x['allocated'] or 0) for x in org_alloc}
        org_ret = ret_qs.values('allocation__organization__name').annotate(total=Sum('amount'))
        high_return_org = []
        for x in org_ret:
            name = x['allocation__organization__name'] or 'نامشخص'
            alloc = org_alloc_map.get(name, 0.0)
            total = float(x['total'] or 0)
            ratio = (total / alloc * 100.0) if alloc > 0 else 0.0
            high_return_org.append({'organization': name, 'return_amount': total, 'allocated': alloc, 'ratio_pct': ratio})
        high_return_org = sorted(high_return_org, key=lambda x: x['ratio_pct'], reverse=True)[:10]

        proj_alloc = alloc_qs.values('project__name').annotate(allocated=Sum('allocated_amount'))
        proj_alloc_map = {x['project__name'] or 'نامشخص': float(x['allocated'] or 0) for x in proj_alloc}
        proj_ret = ret_qs.values('allocation__project__name').annotate(total=Sum('amount'))
        high_return_project = []
        for x in proj_ret:
            name = x['allocation__project__name'] or 'نامشخص'
            alloc = proj_alloc_map.get(name, 0.0)
            total = float(x['total'] or 0)
            ratio = (total / alloc * 100.0) if alloc > 0 else 0.0
            high_return_project.append({'project': name, 'return_amount': total, 'allocated': alloc, 'ratio_pct': ratio})
        high_return_project = sorted(high_return_project, key=lambda x: x['ratio_pct'], reverse=True)[:10]

        # Delay risk: long factor cycles and tankhah settlements
        po_factors = PaymentOrder.objects.filter(payment_date__isnull=False)
        if organization_id:
            po_factors = po_factors.filter(organization_id=organization_id)
        if project_id:
            po_factors = po_factors.filter(project_id=project_id)
        long_cycles = []
        for po in po_factors.values('payment_date', 'related_factors__id', 'related_factors__created_at', 'related_factors__number'):
            try:
                created = po['related_factors__created_at']
                if hasattr(created, 'date'):
                    created = created.date()
                days = (po['payment_date'] - created).days
                if days >= long_cycle_days:
                    long_cycles.append({'factor_id': po['related_factors__id'], 'number': po['related_factors__number'], 'cycle_days': days})
            except Exception:
                continue
        long_cycles = sorted(long_cycles, key=lambda x: x['cycle_days'], reverse=True)[:10]

        # Concentration risk: payees concentration
        payee_conc = PaymentOrder.objects.all()
        if start_date:
            payee_conc = payee_conc.filter(issue_date__gte=start_date)
        if end_date:
            payee_conc = payee_conc.filter(issue_date__lte=end_date)
        if organization_id:
            payee_conc = payee_conc.filter(organization_id=organization_id)
        if project_id:
            payee_conc = payee_conc.filter(project_id=project_id)
        payee_totals = list(payee_conc.values('payee__id', 'payee__legal_name', 'payee__name').annotate(total=Sum('amount')).order_by('-total')[:10])

        # Anomalies: spikes in consumption series
        cons_series = list(cons_qs.extra(select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}).values('month').annotate(total=Sum('amount')).order_by('month'))
        spikes = []
        try:
            last_val = None
            last_month = None
            for row in cons_series:
                val = float(row['total'] or 0)
                if last_val is not None and last_val > 0:
                    pct = (val - last_val) / last_val * 100.0
                    if pct >= spike_threshold_pct:
                        spikes.append({'month': row['month'], 'increase_pct': pct})
                last_val = val
                last_month = row['month']
        except Exception:
            spikes = []

        summary = {
            'overconsumption_count': len(overconsumption),
            'high_return_org_count': len(high_return_org),
            'high_return_project_count': len(high_return_project),
            'long_cycles_count': len(long_cycles),
            'payee_concentration_count': len(payee_totals),
            'spike_count': len(spikes),
        }

        return {
            'summary': summary,
            'overconsumption': overconsumption,
            'high_return_org': high_return_org,
            'high_return_project': high_return_project,
            'long_cycles': long_cycles,
            'payee_concentration': payee_totals,
            'spikes': spikes,
            'params': {
                'overconsumption_threshold_pct': overconsumption_threshold_pct,
                'long_cycle_days': long_cycle_days,
                'spike_threshold_pct': spike_threshold_pct,
            }
        }

    def get_advanced_budget_metrics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """محاسبه متریک‌های پیشرفته بودجه مورد نیاز برای تب بودجه.
        - absorption_rate: consumed/allocated
        - planned_vs_actual: سری ماهانه برنامه‌ریزی‌شده (خطی ساده) در مقابل مصرف واقعی
        - forecast_remaining: پیش‌بینی باقی‌مانده با فرض میانگین مصرف اخیر
        - concentration: سهم Top N سازمان/پروژه از تخصیص
        - aging: گروه‌بندی تخصیص‌ها بر اساس سن از تاریخ تخصیص
        """
        allocations = BudgetAllocation.objects.all()
        if start_date:
            allocations = allocations.filter(allocation_date__gte=start_date)
        if end_date:
            allocations = allocations.filter(allocation_date__lte=end_date)
        if organization_id:
            allocations = allocations.filter(organization_id=organization_id)
        if project_id:
            allocations = allocations.filter(project_id=project_id)

        transactions = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION')
        if start_date:
            transactions = transactions.filter(timestamp__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(timestamp__date__lte=end_date)
        if organization_id:
            transactions = transactions.filter(allocation__organization_id=organization_id)
        if project_id:
            transactions = transactions.filter(allocation__project_id=project_id)

        total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        total_consumed = transactions.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_returned = BudgetTransaction.objects.filter(transaction_type='RETURN', allocation__in=allocations).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining = total_allocated - total_consumed + total_returned

        absorption_rate = float(total_consumed) / float(total_allocated) * 100.0 if total_allocated and float(total_allocated) > 0 else 0.0

        # سری ماهانه مصرف واقعی
        actual_monthly = transactions.extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(total=Sum('amount')).order_by('month')

        # برنامه‌ریزی‌شده خطی: مبلغ تخصیص کل به‌صورت یکنواخت در بازه تقسیم می‌شود
        # اگر بازه مشخص نیست، از ماه‌های موجود در مصرف استفاده می‌کنیم
        from datetime import date
        def to_date(val):
            if isinstance(val, (datetime,)):
                return val.date()
            return val

        period_start = to_date(start_date) or (allocations.order_by('allocation_date').values_list('allocation_date', flat=True).first() or (actual_monthly[0]['month'] if actual_monthly else None))
        period_end = to_date(end_date) or (allocations.order_by('-allocation_date').values_list('allocation_date', flat=True).first() or (actual_monthly[-1]['month'] if actual_monthly else None))

        planned_monthly = []
        try:
            # بساز تقویم ماهانه ساده بین period_start و period_end
            if period_start and period_end:
                if isinstance(period_start, str):
                    period_start = datetime.strptime(period_start, '%Y-%m-01').date()
                if isinstance(period_end, str):
                    period_end = datetime.strptime(period_end, '%Y-%m-01').date()
                cur = date(period_start.year, period_start.month, 1)
                last = date(period_end.year, period_end.month, 1)
                months = []
                while cur <= last:
                    months.append(cur.strftime('%Y-%m-01'))
                    # move to next month
                    if cur.month == 12:
                        cur = date(cur.year + 1, 1, 1)
                    else:
                        cur = date(cur.year, cur.month + 1, 1)
                per_month = (float(total_allocated) / len(months)) if months else 0.0
                planned_monthly = [{'month': m, 'total': per_month} for m in months]
        except Exception:
            planned_monthly = []

        # Forecast: با میانگین 3 ماه اخیر مصرف، برای 3 ماه آینده باقی‌مانده را کاهش می‌دهیم
        forecast = []
        try:
            recent = list(actual_monthly)[-3:]
            avg_cons = sum(float(x['total'] or 0) for x in recent) / (len(recent) or 1)
            future_remaining = float(remaining)
            # شروع از ماه بعد آخرین ماه واقعی
            if actual_monthly:
                base = actual_monthly[-1]['month']
                base_dt = datetime.strptime(base, '%Y-%m-01').date()
            else:
                base_dt = timezone.now().date().replace(day=1)
            for i in range(1, 4):
                # next month
                y = base_dt.year + ((base_dt.month - 1 + i) // 12)
                m = ((base_dt.month - 1 + i) % 12) + 1
                month_str = f"{y:04d}-{m:02d}-01"
                future_remaining = max(future_remaining - avg_cons, 0.0)
                forecast.append({'month': month_str, 'remaining': future_remaining})
        except Exception:
            forecast = []

        # Concentration: Top 5 orgs/projects از نظر تخصیص
        org_conc = allocations.values('organization__name').annotate(total=Sum('allocated_amount')).order_by('-total')
        proj_conc = allocations.values('project__name').annotate(total=Sum('allocated_amount')).order_by('-total')
        org_concentration = list(org_conc[:5])
        project_concentration = list(proj_conc[:5])

        # Aging: بر اساس سن تخصیص از allocation_date
        today = timezone.now().date()
        aging_qs = allocations.values('id', 'allocation_date', 'allocated_amount')
        d_0_30 = d_31_60 = d_61_90 = d_90_plus = 0
        for a in aging_qs:
            try:
                alloc_date = a['allocation_date']
                if hasattr(alloc_date, 'date'):
                    alloc_date = alloc_date.date()
                days = (today - alloc_date).days if alloc_date else 0
                if days <= 30:
                    d_0_30 += 1
                elif days <= 60:
                    d_31_60 += 1
                elif days <= 90:
                    d_61_90 += 1
                else:
                    d_90_plus += 1
            except Exception:
                continue

        return {
            'absorption_rate': absorption_rate,
            'totals': {
                'allocated': float(total_allocated or 0),
                'consumed': float(total_consumed or 0),
                'returned': float(total_returned or 0),
                'remaining': float(remaining or 0),
            },
            'planned_vs_actual': {
                'planned': list(planned_monthly),
                'actual': list(actual_monthly),
            },
            'forecast_remaining': list(forecast),
            'concentration': {
                'organizations': [{'name': x.get('organization__name') or 'نامشخص', 'total': float(x.get('total') or 0)} for x in org_concentration],
                'projects': [{'name': x.get('project__name') or 'نامشخص', 'total': float(x.get('total') or 0)} for x in project_concentration],
            },
            'aging': {
                'd_0_30': d_0_30,
                'd_31_60': d_31_60,
                'd_61_90': d_61_90,
                'd_90_plus': d_90_plus,
            }
        }

    def _has_perm(self, code: str) -> bool:
        """بررسی ساده مجوز با کد پرمیشن. با PermissionBaseView سازگار است."""
        try:
            user = self.request.user
            # از has_perm استاندارد جنگو استفاده می‌کنیم
            return bool(user and user.is_authenticated and user.has_perm(code))
        except Exception:
            return False
    
    def get_budget_return_statistics(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """آمار برگشت‌های بودجه"""
        returns_qs = BudgetTransaction.objects.filter(transaction_type='RETURN')
        if start_date:
            returns_qs = returns_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            returns_qs = returns_qs.filter(timestamp__date__lte=end_date)
        if organization_id:
            returns_qs = returns_qs.filter(allocation__organization_id=organization_id)
        if project_id:
            returns_qs = returns_qs.filter(allocation__project_id=project_id)

        total_returns = returns_qs.count()
        
        total_return_amount = returns_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # برگشت بر اساس مرحله (وضعیت)
        stage_returns = returns_qs.values('allocation__budget_period__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # برگشت بر اساس سازمان
        org_returns = returns_qs.values('allocation__organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # برگشت بر اساس پروژه
        project_returns = returns_qs.values('allocation__project__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # روند برگشت‌ها در زمان - استفاده از روش ساده‌تر
        monthly_returns = returns_qs.extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('month')
        
        return {
            'total_count': total_returns,
            'total_amount': total_return_amount,
            'stage_returns': list(stage_returns),
            'org_returns': list(org_returns),
            'project_returns': list(project_returns),
            'monthly_returns': list(monthly_returns),
        }
    
    def get_chart_data(self, start_date=None, end_date=None, organization_id=None, project_id=None):
        """داده‌های چارت‌ها"""
        allocations_qs = BudgetAllocation.objects.all()
        if start_date:
            allocations_qs = allocations_qs.filter(allocation_date__gte=start_date)
        if end_date:
            allocations_qs = allocations_qs.filter(allocation_date__lte=end_date)
        if organization_id:
            allocations_qs = allocations_qs.filter(organization_id=organization_id)
        if project_id:
            allocations_qs = allocations_qs.filter(project_id=project_id)

        # چارت توزیع بودجه بر اساس سازمان
        org_budget = allocations_qs.values('organization__name').annotate(
            total=Sum('allocated_amount')
        ).order_by('-total')[:10]
        
        # چارت مصرف بودجه در زمان - استفاده از روش ساده‌تر
        tx_qs = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION')
        if start_date:
            tx_qs = tx_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            tx_qs = tx_qs.filter(timestamp__date__lte=end_date)
        if organization_id:
            tx_qs = tx_qs.filter(allocation__organization_id=organization_id)
        if project_id:
            tx_qs = tx_qs.filter(allocation__project_id=project_id)

        monthly_consumption = tx_qs.extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # چارت وضعیت تنخواه‌ها
        tankhah_qs = Tankhah.objects.all()
        if start_date:
            tankhah_qs = tankhah_qs.filter(date__date__gte=start_date)
        if end_date:
            tankhah_qs = tankhah_qs.filter(date__date__lte=end_date)
        if organization_id:
            tankhah_qs = tankhah_qs.filter(organization_id=organization_id)
        if project_id:
            tankhah_qs = tankhah_qs.filter(project_id=project_id)

        tankhah_status = tankhah_qs.values('status__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # چارت دسته‌بندی فاکتورها
        factor_qs = Factor.objects.all()
        if start_date:
            factor_qs = factor_qs.filter(date__gte=start_date)
        if end_date:
            factor_qs = factor_qs.filter(date__lte=end_date)
        if organization_id:
            factor_qs = factor_qs.filter(tankhah__organization_id=organization_id)
        if project_id:
            factor_qs = factor_qs.filter(tankhah__project_id=project_id)

        factor_category = factor_qs.values('category__name').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        # Convert Decimal objects to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj
        
        return {
            'org_budget': convert_decimals(list(org_budget)),
            'monthly_consumption': convert_decimals(list(monthly_consumption)),
            'tankhah_status': convert_decimals(list(tankhah_status)),
            'factor_category': convert_decimals(list(factor_category)),
        }


class BudgetAnalyticsView(TemplateView):
    """تحلیل‌های پیشرفته بودجه"""
    template_name = 'reports/analytics/budget_analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # فیلترهای دریافت شده
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        organization_id = self.request.GET.get('organization')
        project_id = self.request.GET.get('project')
        
        # تحلیل بودجه
        budget_analysis = self.get_budget_analysis(start_date, end_date, organization_id, project_id)
        context['budget_analysis'] = json.dumps(budget_analysis, ensure_ascii=False, default=str)
        
        # تحلیل برگشت‌ها
        return_analysis = self.get_return_analysis(start_date, end_date, organization_id, project_id)
        context['return_analysis'] = json.dumps(return_analysis, ensure_ascii=False, default=str)
        
        # تحلیل روندها
        trend_analysis = self.get_trend_analysis(start_date, end_date)
        context['trend_analysis'] = json.dumps(trend_analysis, ensure_ascii=False, default=str)
        
        return context
    
    def get_budget_analysis(self, start_date, end_date, organization_id, project_id):
        """تحلیل بودجه"""
        queryset = BudgetAllocation.objects.all()
        
        if start_date:
            queryset = queryset.filter(allocation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(allocation_date__lte=end_date)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        # آمار کلی
        stats = queryset.aggregate(
            total_allocated=Sum('allocated_amount'),
            total_consumed=Sum('transactions__amount', 
                             filter=Q(transactions__transaction_type='CONSUMPTION')),
            total_returned=Sum('transactions__amount',
                             filter=Q(transactions__transaction_type='RETURN'))
        )
        
        return stats
    
    def get_return_analysis(self, start_date, end_date, organization_id, project_id):
        """تحلیل برگشت‌ها"""
        queryset = BudgetTransaction.objects.filter(transaction_type='RETURN')
        
        if start_date:
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__date__lte=end_date)
        if organization_id:
            queryset = queryset.filter(allocation__organization_id=organization_id)
        if project_id:
            queryset = queryset.filter(allocation__project_id=project_id)
        
        # آمار برگشت‌ها
        stats = queryset.aggregate(
            total_count=Count('id'),
            total_amount=Sum('amount')
        )
        
        # برگشت بر اساس دلایل (از description)
        reason_stats = queryset.values('description').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')[:10]
        
        # برگشت بر اساس سازمان
        org_returns = queryset.values('allocation__organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # برگشت بر اساس پروژه
        project_returns = queryset.values('allocation__project__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        return {
            'stats': stats,
            'reason_stats': list(reason_stats),
            'org_returns': list(org_returns),
            'project_returns': list(project_returns),
        }
    
    def get_trend_analysis(self, start_date, end_date):
        """تحلیل روندها"""
        # روند مصرف بودجه - استفاده از روش ساده‌تر
        consumption_qs = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION')
        if start_date:
            consumption_qs = consumption_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            consumption_qs = consumption_qs.filter(timestamp__date__lte=end_date)
        consumption_trend = consumption_qs.extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # روند برگشت‌ها - استفاده از روش ساده‌تر
        return_qs = BudgetTransaction.objects.filter(transaction_type='RETURN')
        if start_date:
            return_qs = return_qs.filter(timestamp__date__gte=start_date)
        if end_date:
            return_qs = return_qs.filter(timestamp__date__lte=end_date)
        return_trend = return_qs.extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return {
            'consumption_trend': list(consumption_trend),
            'return_trend': list(return_trend),
        }


class ExportReportsView(LoginRequiredMixin, TemplateView):
    """صادرات گزارشات"""
    template_name = 'reports/exports/export_template.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # نوع گزارش
        report_type = self.request.GET.get('type', 'budget')
        
        # فیلترها
        filters = {
            'start_date': self.request.GET.get('start_date'),
            'end_date': self.request.GET.get('end_date'),
            'organization': self.request.GET.get('organization'),
            'project': self.request.GET.get('project'),
        }
        
        # داده‌های گزارش
        if report_type == 'budget':
            context['report_data'] = self.get_budget_report_data(filters)
        elif report_type == 'tankhah':
            context['report_data'] = self.get_tankhah_report_data(filters)
        elif report_type == 'factor':
            context['report_data'] = self.get_factor_report_data(filters)
        elif report_type == 'payment':
            context['report_data'] = self.get_payment_report_data(filters)
        elif report_type == 'returns':
            context['report_data'] = self.get_returns_report_data(filters)
        
        context['report_type'] = report_type
        context['filters'] = filters
        
        return context
    
    def get_budget_report_data(self, filters):
        """داده‌های گزارش بودجه"""
        queryset = BudgetAllocation.objects.all()
        
        if filters['start_date']:
            queryset = queryset.filter(allocation_date__gte=filters['start_date'])
        if filters['end_date']:
            queryset = queryset.filter(allocation_date__lte=filters['end_date'])
        if filters['organization']:
            queryset = queryset.filter(organization_id=filters['organization'])
        if filters['project']:
            queryset = queryset.filter(project_id=filters['project'])
        
        return queryset.select_related('organization', 'project', 'budget_item')
    
    def get_tankhah_report_data(self, filters):
        """داده‌های گزارش تنخواه"""
        queryset = Tankhah.objects.all()
        
        if filters['start_date']:
            queryset = queryset.filter(date__date__gte=filters['start_date'])
        if filters['end_date']:
            queryset = queryset.filter(date__date__lte=filters['end_date'])
        if filters['organization']:
            queryset = queryset.filter(organization_id=filters['organization'])
        if filters['project']:
            queryset = queryset.filter(project_id=filters['project'])
        
        return queryset.select_related('organization', 'project', 'status')
    
    def get_factor_report_data(self, filters):
        """داده‌های گزارش فاکتور"""
        queryset = Factor.objects.all()
        
        if filters['start_date']:
            queryset = queryset.filter(date__gte=filters['start_date'])
        if filters['end_date']:
            queryset = queryset.filter(date__lte=filters['end_date'])
        if filters['organization']:
            queryset = queryset.filter(tankhah__organization_id=filters['organization'])
        if filters['project']:
            queryset = queryset.filter(tankhah__project_id=filters['project'])
        
        return queryset.select_related('tankhah', 'category', 'status')
    
    def get_payment_report_data(self, filters):
        """داده‌های گزارش دستورات پرداخت"""
        queryset = PaymentOrder.objects.all()
        
        if filters['start_date']:
            queryset = queryset.filter(issue_date__gte=filters['start_date'])
        if filters['end_date']:
            queryset = queryset.filter(issue_date__lte=filters['end_date'])
        if filters['organization']:
            queryset = queryset.filter(organization_id=filters['organization'])
        if filters['project']:
            queryset = queryset.filter(project_id=filters['project'])
        
        return queryset.select_related('organization', 'project', 'status', 'payee')
    
    def get_returns_report_data(self, filters):
        """داده‌های گزارش برگشت‌ها"""
        queryset = BudgetTransaction.objects.filter(transaction_type='RETURN')
        
        if filters['start_date']:
            queryset = queryset.filter(timestamp__date__gte=filters['start_date'])
        if filters['end_date']:
            queryset = queryset.filter(timestamp__date__lte=filters['end_date'])
        if filters['organization']:
            queryset = queryset.filter(allocation__organization_id=filters['organization'])
        if filters['project']:
            queryset = queryset.filter(allocation__project_id=filters['project'])
        
        return queryset.select_related('allocation', 'allocation__organization', 'allocation__project')


def debug_dashboard_data(request):
    """Debug view برای بررسی داده‌های داشبورد"""
    try:
        # آمار کلی بودجه
        total_budget = BudgetPeriod.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        total_allocated = BudgetAllocation.objects.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        
        # چارت توزیع بودجه بر اساس سازمان
        org_budget = BudgetAllocation.objects.values('organization__name').annotate(
            total=Sum('allocated_amount')
        ).order_by('-total')[:10]
        
        # چارت مصرف بودجه در زمان
        monthly_consumption = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # چارت وضعیت تنخواه‌ها
        tankhah_status = Tankhah.objects.values('status__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # چارت دسته‌بندی فاکتورها
        factor_category = Factor.objects.values('category__name').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        # Convert Decimal objects to float for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(item) for item in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj
        
        chart_data = {
            'org_budget': convert_decimals(list(org_budget)),
            'monthly_consumption': convert_decimals(list(monthly_consumption)),
            'tankhah_status': convert_decimals(list(tankhah_status)),
            'factor_category': convert_decimals(list(factor_category)),
        }
        
        return JsonResponse({
            'total_budget': float(total_budget),
            'total_allocated': float(total_allocated),
            'chart_data': chart_data,
            'org_budget_count': len(org_budget),
            'monthly_consumption_count': len(monthly_consumption),
            'tankhah_status_count': len(tankhah_status),
            'factor_category_count': len(factor_category),
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


def api_projects_by_org(request):
    """API: فهرست پروژه‌های مرتبط با یک سازمان (بر اساس تخصیص‌ها)"""
    try:
        org_id = request.GET.get('organization')
        if not org_id:
            return JsonResponse({'results': []})
        projects = Project.objects.filter(allocations__organization_id=org_id).distinct().values('id', 'name')
        return JsonResponse({'results': list(projects)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class TestDashboardView(TemplateView):
    """View برای تست داشبورد"""
    template_name = 'reports/dashboard/test_dashboard.html'


class SimpleDashboardView(TemplateView):
    """داشبورد ساده و کارآمد"""
    template_name = 'reports/dashboard/simple_dashboard.html'


class SimpleAnalyticsView(TemplateView):
    """تحلیل‌های ساده و کارآمد"""
    template_name = 'reports/dashboard/simple_analytics.html'


class DashboardSelectorView(TemplateView):
    """صفحه انتخاب داشبورد"""
    template_name = 'reports/dashboard/dashboard_selector.html'


class ChartTestView(TemplateView):
    """تست مستقل چارت‌ها"""
    template_name = 'reports/dashboard/chart_test.html'


class SimpleChartTestView(TemplateView):
    """تست ساده چارت (مثل URL یاد شده)"""
    template_name = 'reports/dashboard/simple_chart_test.html'


class MinimalChartTestView(TemplateView):
    """تست حداقلی چارت"""
    template_name = 'reports/dashboard/minimal_chart_test.html'


class TestAnalyticsView(TemplateView):
    """تست analytics با داده‌های نمونه"""
    template_name = 'reports/analytics/budget_analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # داده‌های تست برای budget_analysis
        budget_analysis = {
            'total_allocated': 50000000,
            'total_consumed': 35000000,
            'total_returned': 5000000,
            'remaining': 10000000
        }
        context['budget_analysis'] = json.dumps(budget_analysis, ensure_ascii=False, default=str)
        
        # داده‌های تست برای return_analysis
        return_analysis = {
            'stats': {
                'total_amount': 5000000,
                'total_count': 25
            },
            'reason_stats': [
                {'description': 'عدم نیاز', 'count': 10, 'total': 2000000},
                {'description': 'خطای تخصیص', 'count': 8, 'total': 1500000},
                {'description': 'تغییر برنامه', 'count': 7, 'total': 1500000}
            ],
            'org_returns': [
                {'allocation__organization__name': 'سازمان ۱', 'count': 12, 'total_amount': 2500000},
                {'allocation__organization__name': 'سازمان ۲', 'count': 8, 'total_amount': 1500000},
                {'allocation__organization__name': 'سازمان ۳', 'count': 5, 'total_amount': 1000000}
            ],
            'project_returns': [
                {'allocation__project__name': 'پروژه A', 'count': 10, 'total_amount': 2000000},
                {'allocation__project__name': 'پروژه B', 'count': 8, 'total_amount': 1800000},
                {'allocation__project__name': 'پروژه C', 'count': 7, 'total_amount': 1200000}
            ]
        }
        context['return_analysis'] = json.dumps(return_analysis, ensure_ascii=False, default=str)
        
        # داده‌های تست برای trend_analysis
        trend_analysis = {
            'consumption_trend': [
                {'month': '2024-01-01', 'total': 5000000},
                {'month': '2024-02-01', 'total': 6000000},
                {'month': '2024-03-01', 'total': 7000000},
                {'month': '2024-04-01', 'total': 8000000},
                {'month': '2024-05-01', 'total': 9000000}
            ],
            'return_trend': [
                {'month': '2024-01-01', 'total': 500000},
                {'month': '2024-02-01', 'total': 800000},
                {'month': '2024-03-01', 'total': 1200000},
                {'month': '2024-04-01', 'total': 1000000},
                {'month': '2024-05-01', 'total': 1500000}
            ]
        }
        context['trend_analysis'] = json.dumps(trend_analysis, ensure_ascii=False, default=str)
        
        return context


class BudgetAnalyticsRedesignedView(TemplateView):
    """نسخه بازطراحی شده تحلیل‌ها - از همان داده‌های اصلی استفاده می‌کند"""
    template_name = 'reports/analytics/analytics_redesigned.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Parse Jalali -> Gregorian if needed
        start_date = self._parse_jalali_date(self.request.GET.get('start_date'))
        end_date = self._parse_jalali_date(self.request.GET.get('end_date'))
        organization_id = self.request.GET.get('organization')
        project_id = self.request.GET.get('project')

        # استفاده از توابع موجود کلاس اصلی BudgetAnalyticsView
        # ما اینجا نمونه‌ای از آن کلاس را فقط برای دسترسی به متدها می‌سازیم
        helper = BudgetAnalyticsView()
        helper.request = self.request

        budget_analysis = helper.get_budget_analysis(start_date, end_date, organization_id, project_id)
        return_analysis = helper.get_return_analysis(start_date, end_date, organization_id, project_id)
        trend_analysis = helper.get_trend_analysis(start_date, end_date)

        context['budget_analysis'] = json.dumps(budget_analysis, ensure_ascii=False, default=str)
        context['return_analysis'] = json.dumps(return_analysis, ensure_ascii=False, default=str)
        context['trend_analysis']  = json.dumps(trend_analysis, ensure_ascii=False, default=str)

        # مقایسه (اختیاری)
        compare_start = self._parse_jalali_date(self.request.GET.get('compare_start_date'))
        compare_end = self._parse_jalali_date(self.request.GET.get('compare_end_date'))
        compare_org = self.request.GET.get('compare_organization')
        compare_project = self.request.GET.get('compare_project')

        if any([compare_start, compare_end, compare_org, compare_project]):
            budget_analysis_compare = helper.get_budget_analysis(compare_start, compare_end, compare_org, compare_project)
            return_analysis_compare = helper.get_return_analysis(compare_start, compare_end, compare_org, compare_project)
            trend_analysis_compare = helper.get_trend_analysis(compare_start, compare_end)
            context['budget_analysis_compare'] = json.dumps(budget_analysis_compare, ensure_ascii=False, default=str)
            context['return_analysis_compare'] = json.dumps(return_analysis_compare, ensure_ascii=False, default=str)
            context['trend_analysis_compare']  = json.dumps(trend_analysis_compare, ensure_ascii=False, default=str)

        # فهرست واقعی سازمان‌ها و پروژه‌ها
        context['organizations'] = list(Organization.objects.values('id', 'name').order_by('name'))
        context['projects'] = list(Project.objects.values('id', 'name').order_by('name'))
        return context

    def _parse_jalali_date(self, value):
        if not value:
            return None
        try:
            val = str(value).strip()
            if '/' in val:
                parts = val.replace('\u200f', '').split('/')
                if len(parts) == 3 and all(parts):
                    y, m, d = [int(p) for p in parts]
                    if jdatetime:
                        return jdatetime.date(y, m, d).togregorian()
            return val
        except Exception:
            return value
