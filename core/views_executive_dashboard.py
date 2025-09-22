"""
ویوهای داشبورد اجرایی و گزارشات جامع
"""

from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, Count, Avg, F, Case, When, Value
from django.db.models.functions import Coalesce, TruncMonth, TruncQuarter
from decimal import Decimal
import jdatetime
import json
import logging

from tankhah.models import Tankhah, Factor
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
from core.models import Project, Organization

logger = logging.getLogger(__name__)


class ComprehensiveBudgetReportView(LoginRequiredMixin, View):
    """
    گزارش جامع بودجه
    """
    template_name = 'core/reports/comprehensive_budget_report.html'
    login_url = '/accounts/login/'

    def get_context_data(self, request):
        context = {}
        user = request.user
        
        # بررسی دسترسی
        if not (user.has_perm('budgets.view_budgetallocation') or user.is_superuser):
            context['access_denied'] = True
            return context
        
        try:
            # آمار کلی بودجه
            budget_stats = self._get_budget_statistics()
            context.update(budget_stats)
            
            # گزارش تفصیلی بودجه
            detailed_report = self._get_detailed_budget_report()
            context.update(detailed_report)
            
        except Exception as e:
            logger.error(f"خطا در گزارش بودجه: {e}")
            context['error'] = str(e)
        
        return context

    def _get_budget_statistics(self):
        """آمار کلی بودجه"""
        stats = {}
        
        # آمار دوره‌های بودجه
        active_periods = BudgetPeriod.objects.filter(is_active=True, is_completed=False)
        total_allocated = active_periods.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
        total_consumed = BudgetTransaction.objects.filter(
            allocation__budget_period__in=active_periods,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        stats.update({
            'total_budget_allocated': total_allocated,
            'total_budget_consumed': total_consumed,
            'total_budget_remaining': total_allocated - total_consumed,
            'budget_consumption_percentage': (total_consumed / total_allocated * 100) if total_allocated > 0 else 0,
            'active_budget_periods_count': active_periods.count(),
        })
        
        return stats

    def _get_detailed_budget_report(self):
        """گزارش تفصیلی بودجه"""
        report = {}
        
        # گزارش بودجه بر اساس پروژه
        project_budget = Project.objects.filter(is_active=True).annotate(
            allocated=Coalesce(Sum('allocations__allocated_amount', filter=Q(allocations__is_active=True)), Decimal('0')),
            consumed=Coalesce(Sum('tankhah_set__factors__amount', filter=Q(tankhah_set__factors__status__code='PAID')), Decimal('0'))
        ).annotate(
            remaining=F('allocated') - F('consumed'),
            percentage_consumed=Case(
                When(allocated__gt=0, then=(F('consumed') * 100) / F('allocated')),
                default=Value(0)
            )
        ).filter(allocated__gt=0).order_by('-allocated')
        
        report['project_budget_data'] = list(project_budget.values(
            'name', 'allocated', 'consumed', 'remaining', 'percentage_consumed'
        ))
        
        return report

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)


class ComprehensiveFactorReportView(LoginRequiredMixin, View):
    """
    گزارش جامع فاکتورها
    """
    template_name = 'core/reports/comprehensive_factor_report.html'
    login_url = '/accounts/login/'

    def get_context_data(self, request):
        context = {}
        user = request.user
        
        # بررسی دسترسی
        if not (user.has_perm('tankhah.view_factor') or user.is_superuser):
            context['access_denied'] = True
            return context
        
        try:
            # آمار کلی فاکتورها
            factor_stats = self._get_factor_statistics()
            context.update(factor_stats)
            
            # گزارش تفصیلی فاکتورها
            detailed_report = self._get_detailed_factor_report()
            context.update(detailed_report)
            
        except Exception as e:
            logger.error(f"خطا در گزارش فاکتور: {e}")
            context['error'] = str(e)
        
        return context

    def _get_factor_statistics(self):
        """آمار کلی فاکتورها"""
        stats = {}
        
        # آمار کلی فاکتورها
        total_factors = Factor.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        paid_factors = Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        pending_factors = Factor.objects.filter(status__code__in=['PENDING_APPROVAL', 'APPROVED']).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        rejected_factors = Factor.objects.filter(status__code='REJECTED').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        stats.update({
            'total_factor_amount': total_factors,
            'paid_factor_amount': paid_factors,
            'pending_factor_amount': pending_factors,
            'rejected_factor_amount': rejected_factors,
            'factor_approval_percentage': (paid_factors / total_factors * 100) if total_factors > 0 else 0,
            'total_factor_count': Factor.objects.count(),
            'paid_factor_count': Factor.objects.filter(status__code='PAID').count(),
            'pending_factor_count': Factor.objects.filter(status__code__in=['PENDING_APPROVAL', 'APPROVED']).count(),
            'rejected_factor_count': Factor.objects.filter(status__code='REJECTED').count(),
        })
        
        return stats

    def _get_detailed_factor_report(self):
        """گزارش تفصیلی فاکتورها"""
        report = {}
        
        # گزارش فاکتورها بر اساس دسته
        category_report = Factor.objects.values('category__name').annotate(
            count=Count('id'),
            total_amount=Sum('amount'),
            paid_amount=Sum('amount', filter=Q(status__code='PAID')),
            pending_amount=Sum('amount', filter=Q(status__code__in=['PENDING_APPROVAL', 'APPROVED'])),
            rejected_amount=Sum('amount', filter=Q(status__code='REJECTED'))
        ).order_by('-total_amount')
        
        report['category_report'] = list(category_report)
        
        # گزارش فاکتورها بر اساس وضعیت
        status_report = Factor.objects.values('status__name', 'status__code').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        report['status_report'] = list(status_report)
        
        return report

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)


class ComprehensiveTankhahReportView(LoginRequiredMixin, View):
    """
    گزارش جامع تنخواه
    """
    template_name = 'core/reports/comprehensive_tankhah_report.html'
    login_url = '/accounts/login/'

    def get_context_data(self, request):
        context = {}
        user = request.user
        
        # بررسی دسترسی
        if not (user.has_perm('tankhah.view_tankhah') or user.is_superuser):
            context['access_denied'] = True
            return context
        
        try:
            # آمار کلی تنخواه
            tankhah_stats = self._get_tankhah_statistics()
            context.update(tankhah_stats)
            
            # گزارش تفصیلی تنخواه
            detailed_report = self._get_detailed_tankhah_report()
            context.update(detailed_report)
            
        except Exception as e:
            logger.error(f"خطا در گزارش تنخواه: {e}")
            context['error'] = str(e)
        
        return context

    def _get_tankhah_statistics(self):
        """آمار کلی تنخواه"""
        stats = {}
        
        # آمار کلی تنخواه‌ها
        total_tankhah = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        paid_tankhah = Tankhah.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        pending_tankhah = Tankhah.objects.filter(status__code__in=['PENDING', 'APPROVED']).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        stats.update({
            'total_tankhah_amount': total_tankhah,
            'paid_tankhah_amount': paid_tankhah,
            'pending_tankhah_amount': pending_tankhah,
            'tankhah_utilization_percentage': (paid_tankhah / total_tankhah * 100) if total_tankhah > 0 else 0,
            'total_tankhah_count': Tankhah.objects.count(),
            'paid_tankhah_count': Tankhah.objects.filter(status__code='PAID').count(),
            'pending_tankhah_count': Tankhah.objects.filter(status__code__in=['PENDING', 'APPROVED']).count(),
        })
        
        return stats

    def _get_detailed_tankhah_report(self):
        """گزارش تفصیلی تنخواه"""
        report = {}
        
        # گزارش تنخواه بر اساس پروژه
        project_tankhah = Project.objects.filter(is_active=True).annotate(
            total_tankhah=Coalesce(Sum('tankhah_set__amount'), Decimal('0')),
            paid_tankhah=Coalesce(Sum('tankhah_set__amount', filter=Q(tankhah_set__status__code='PAID')), Decimal('0')),
            pending_tankhah=Coalesce(Sum('tankhah_set__amount', filter=Q(tankhah_set__status__code__in=['PENDING', 'APPROVED'])), Decimal('0'))
        ).filter(total_tankhah__gt=0).order_by('-total_tankhah')
        
        report['project_tankhah_data'] = list(project_tankhah.values(
            'name', 'total_tankhah', 'paid_tankhah', 'pending_tankhah'
        ))
        
        # گزارش تنخواه بر اساس وضعیت
        status_report = Tankhah.objects.values('status__name', 'status__code').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        report['status_report'] = list(status_report)
        
        return report

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)


class FinancialPerformanceReportView(LoginRequiredMixin, View):
    """
    گزارش عملکرد مالی
    """
    template_name = 'core/reports/financial_performance_report.html'
    login_url = '/accounts/login/'

    def get_context_data(self, request):
        context = {}
        user = request.user
        
        # بررسی دسترسی
        if not (user.has_perm('budgets.view_budgetallocation') or user.is_superuser):
            context['access_denied'] = True
            return context
        
        try:
            # تحلیل عملکرد مالی
            performance_analysis = self._get_performance_analysis()
            context.update(performance_analysis)
            
            # شاخص‌های کلیدی عملکرد
            kpi_data = self._get_kpi_data()
            context.update(kpi_data)
            
        except Exception as e:
            logger.error(f"خطا در گزارش عملکرد مالی: {e}")
            context['error'] = str(e)
        
        return context

    def _get_performance_analysis(self):
        """تحلیل عملکرد مالی"""
        analysis = {}
        
        # محاسبه شاخص‌های کلیدی
        total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        total_consumed = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        total_tankhah = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        total_factors = Factor.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        analysis.update({
            'budget_utilization_rate': (total_consumed / total_budget * 100) if total_budget > 0 else 0,
            'tankhah_efficiency': (total_factors / total_tankhah * 100) if total_tankhah > 0 else 0,
            'cost_per_tankhah': total_tankhah / Tankhah.objects.count() if Tankhah.objects.count() > 0 else 0,
            'average_factor_amount': total_factors / Factor.objects.count() if Factor.objects.count() > 0 else 0,
        })
        
        return analysis

    def _get_kpi_data(self):
        """شاخص‌های کلیدی عملکرد"""
        kpi = {}
        
        # محاسبه KPI ها
        total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        total_consumed = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        kpi.update({
            'budget_utilization_rate': (total_consumed / total_budget * 100) if total_budget > 0 else 0,
            'cost_efficiency': (total_consumed / total_budget * 100) if total_budget > 0 else 0,
            'budget_variance': ((total_consumed - total_budget) / total_budget * 100) if total_budget > 0 else 0,
        })
        
        return kpi

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)


class AnalyticalReportsView(LoginRequiredMixin, View):
    """
    گزارشات تحلیلی
    """
    template_name = 'core/reports/analytical_reports.html'
    login_url = '/accounts/login/'

    def get_context_data(self, request):
        context = {}
        user = request.user
        
        # بررسی دسترسی
        if not (user.has_perm('budgets.view_budgetallocation') or user.is_superuser):
            context['access_denied'] = True
            return context
        
        try:
            # تحلیل روندها
            trend_analysis = self._get_trend_analysis()
            context.update(trend_analysis)
            
            # تحلیل ریسک‌ها
            risk_analysis = self._get_risk_analysis()
            context.update(risk_analysis)
            
            # تحلیل مقایسه‌ای
            comparative_analysis = self._get_comparative_analysis()
            context.update(comparative_analysis)
            
        except Exception as e:
            logger.error(f"خطا در گزارشات تحلیلی: {e}")
            context['error'] = str(e)
        
        return context

    def _get_trend_analysis(self):
        """تحلیل روندها"""
        trends = {}
        
        # روند مصرف بودجه
        from django.utils import timezone
        from datetime import timedelta
        
        current_month = timezone.now().replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        current_consumption = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION',
            timestamp__gte=current_month
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        last_consumption = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION',
            timestamp__gte=last_month,
            timestamp__lt=current_month
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        consumption_trend = ((current_consumption - last_consumption) / last_consumption * 100) if last_consumption > 0 else 0
        
        trends.update({
            'consumption_trend': consumption_trend,
            'consumption_trend_direction': 'up' if consumption_trend > 0 else 'down',
            'current_month_consumption': float(current_consumption),
            'last_month_consumption': float(last_consumption),
        })
        
        return trends

    def _get_risk_analysis(self):
        """تحلیل ریسک‌ها"""
        risks = []
        
        # ریسک بودجه کم
        total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'))
        )['total']
        
        total_consumed = BudgetTransaction.objects.filter(
            transaction_type='CONSUMPTION'
        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
        
        budget_usage_percentage = (total_consumed / total_budget * 100) if total_budget > 0 else 0
        
        if budget_usage_percentage > 80:
            risks.append({
                'type': 'high_budget_usage',
                'level': 'high',
                'message': f'مصرف بودجه به {budget_usage_percentage:.1f}% رسیده است',
                'recommendation': 'بررسی و کنترل بیشتر هزینه‌ها ضروری است'
            })
        elif budget_usage_percentage > 60:
            risks.append({
                'type': 'medium_budget_usage',
                'level': 'medium',
                'message': f'مصرف بودجه به {budget_usage_percentage:.1f}% رسیده است',
                'recommendation': 'نظارت بر هزینه‌ها توصیه می‌شود'
            })
        
        # ریسک فاکتورهای رد شده
        rejected_factors_count = Factor.objects.filter(status__code='REJECTED').count()
        total_factors_count = Factor.objects.count()
        rejection_rate = (rejected_factors_count / total_factors_count * 100) if total_factors_count > 0 else 0
        
        if rejection_rate > 20:
            risks.append({
                'type': 'high_rejection_rate',
                'level': 'high',
                'message': f'نرخ رد فاکتورها {rejection_rate:.1f}% است',
                'recommendation': 'بررسی فرآیند تأیید فاکتورها ضروری است'
            })
        
        return {
            'risks': risks,
            'risk_count': len(risks),
            'high_risk_count': len([r for r in risks if r['level'] == 'high']),
            'medium_risk_count': len([r for r in risks if r['level'] == 'medium']),
        }

    def _get_comparative_analysis(self):
        """تحلیل مقایسه‌ای"""
        comparison = {}
        
        # مقایسه عملکرد پروژه‌ها
        project_performance = Project.objects.filter(is_active=True).annotate(
            allocated=Coalesce(Sum('allocations__allocated_amount', filter=Q(allocations__is_active=True)), Decimal('0')),
            consumed=Coalesce(Sum('tankhah_set__factors__amount', filter=Q(tankhah_set__factors__status__code='PAID')), Decimal('0'))
        ).annotate(
            efficiency=Case(
                When(allocated__gt=0, then=(F('consumed') * 100) / F('allocated')),
                default=Value(0)
            )
        ).filter(allocated__gt=0).order_by('-efficiency')
        
        comparison['project_performance'] = list(project_performance.values(
            'name', 'allocated', 'consumed', 'efficiency'
        ))
        
        return comparison

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)
