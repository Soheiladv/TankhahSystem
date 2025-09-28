from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Q, F, Case, When, DecimalField
from django.db.models.functions import TruncMonth, TruncDay, TruncYear
from django.utils import timezone
from datetime import datetime, timedelta
import json
from decimal import Decimal

from budgets.models import (
    BudgetPeriod, BudgetAllocation, BudgetTransaction, 
    PaymentOrder, BudgetItem
)
from tankhah.models import Tankhah, Factor
from core.models import Organization, Project, Status


class DashboardMainView(LoginRequiredMixin, TemplateView):
    """داشبورد اصلی گزارشات با آمار کلی"""
    template_name = 'reports/dashboard/main_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # آمار کلی بودجه
        budget_stats = self.get_budget_statistics()
        context['budget_stats'] = budget_stats
        
        # آمار تنخواه‌ها
        tankhah_stats = self.get_tankhah_statistics()
        context['tankhah_stats'] = tankhah_stats
        
        # آمار فاکتورها
        factor_stats = self.get_factor_statistics()
        context['factor_stats'] = factor_stats
        
        # آمار دستورات پرداخت
        payment_stats = self.get_payment_statistics()
        context['payment_stats'] = payment_stats
        
        # آمار مراکز هزینه
        cost_center_stats = self.get_cost_center_statistics()
        context['cost_center_stats'] = cost_center_stats
        
        # آمار برگشت‌های بودجه
        return_stats = self.get_budget_return_statistics()
        context['return_stats'] = return_stats
        
        # چارت‌های داده
        chart_data = self.get_chart_data()
        context['chart_data'] = json.dumps(chart_data)
        
        return context
    
    def get_budget_statistics(self):
        """آمار کلی بودجه"""
        total_budget = BudgetPeriod.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        total_allocated = BudgetAllocation.objects.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')
        
        total_consumed = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_returned = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        remaining = total_allocated - total_consumed + total_returned
        
        return {
            'total_budget': total_budget,
            'total_allocated': total_allocated,
            'total_consumed': total_consumed,
            'total_returned': total_returned,
            'remaining': remaining,
            'consumption_percentage': (total_consumed / total_allocated * 100) if total_allocated > 0 else 0,
            'return_percentage': (total_returned / total_allocated * 100) if total_allocated > 0 else 0,
        }
    
    def get_tankhah_statistics(self):
        """آمار تنخواه‌ها"""
        total_tankhah = Tankhah.objects.count()
        total_amount = Tankhah.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس وضعیت
        status_stats = Tankhah.objects.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        # آمار بر اساس سازمان
        org_stats = Tankhah.objects.values('organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        return {
            'total_count': total_tankhah,
            'total_amount': total_amount,
            'status_stats': list(status_stats),
            'org_stats': list(org_stats),
        }
    
    def get_factor_statistics(self):
        """آمار فاکتورها"""
        total_factors = Factor.objects.count()
        total_amount = Factor.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس دسته‌بندی
        category_stats = Factor.objects.values('category__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # آمار بر اساس وضعیت
        status_stats = Factor.objects.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        return {
            'total_count': total_factors,
            'total_amount': total_amount,
            'category_stats': list(category_stats),
            'status_stats': list(status_stats),
        }
    
    def get_payment_statistics(self):
        """آمار دستورات پرداخت"""
        total_orders = PaymentOrder.objects.count()
        total_amount = PaymentOrder.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        # آمار بر اساس وضعیت
        status_stats = PaymentOrder.objects.values('status__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-count')
        
        # آمار بر اساس سازمان
        org_stats = PaymentOrder.objects.values('organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        return {
            'total_count': total_orders,
            'total_amount': total_amount,
            'status_stats': list(status_stats),
            'org_stats': list(org_stats),
        }
    
    def get_cost_center_statistics(self):
        """آمار مراکز هزینه (پروژه‌ها)"""
        total_projects = Project.objects.count()
        
        # آمار بودجه پروژه‌ها
        project_stats = Project.objects.annotate(
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
    
    def get_budget_return_statistics(self):
        """آمار برگشت‌های بودجه"""
        total_returns = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).count()
        
        total_return_amount = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # برگشت بر اساس مرحله (وضعیت)
        stage_returns = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).values('allocation__budget_period__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # برگشت بر اساس سازمان
        org_returns = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).values('allocation__organization__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # برگشت بر اساس پروژه
        project_returns = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).values('allocation__project__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # روند برگشت‌ها در زمان - استفاده از روش ساده‌تر
        monthly_returns = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).extra(
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
    
    def get_chart_data(self):
        """داده‌های چارت‌ها"""
        # چارت توزیع بودجه بر اساس سازمان
        org_budget = BudgetAllocation.objects.values('organization__name').annotate(
            total=Sum('allocated_amount')
        ).order_by('-total')[:10]
        
        # چارت مصرف بودجه در زمان - استفاده از روش ساده‌تر
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
        
        return {
            'org_budget': convert_decimals(list(org_budget)),
            'monthly_consumption': convert_decimals(list(monthly_consumption)),
            'tankhah_status': convert_decimals(list(tankhah_status)),
            'factor_category': convert_decimals(list(factor_category)),
        }


class BudgetAnalyticsView(LoginRequiredMixin, TemplateView):
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
        context['budget_analysis'] = budget_analysis
        
        # تحلیل برگشت‌ها
        return_analysis = self.get_return_analysis(start_date, end_date, organization_id, project_id)
        context['return_analysis'] = return_analysis
        
        # تحلیل روندها
        trend_analysis = self.get_trend_analysis(start_date, end_date)
        context['trend_analysis'] = trend_analysis
        
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
        
        return {
            'stats': stats,
            'reason_stats': list(reason_stats),
        }
    
    def get_trend_analysis(self, start_date, end_date):
        """تحلیل روندها"""
        # روند مصرف بودجه - استفاده از روش ساده‌تر
        consumption_trend = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).extra(
            select={'month': "DATE_FORMAT(timestamp, '%%Y-%%m-01')"}
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # روند برگشت‌ها - استفاده از روش ساده‌تر
        return_trend = BudgetTransaction.objects.filter(
            transaction_type='RETURN'
        ).extra(
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
