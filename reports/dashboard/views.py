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
