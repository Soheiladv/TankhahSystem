
from django.shortcuts import render
from django.db.models.functions import Coalesce
from notificationApp.models import NotificationRule, Notification
from notificationApp.views import send_notification
from tankhah.models import   ApprovalLog

from version_tracker.models import FinalVersion
from budgets.budget_calculations import get_project_total_budget, get_project_used_budget, get_project_remaining_budget, \
    calculate_threshold_amount
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from core.PermissionBase import PermissionBaseView
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q, Value, DecimalField, F, Case, When
from django.db.models.functions import TruncMonth, TruncQuarter
from decimal import Decimal
import jdatetime
import json
import logging
from datetime import timedelta
from tankhah.models import Tankhah, Factor
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetTransaction
from core.models import Project
from core.models import SystemSettings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse, NoReverseMatch
logger = logging.getLogger('Main_Dashboard')
# لینک‌های داشبورد - تمیز شده و بدون تکرار

dashboard_links = {
    'مدیریت فاکتورها': {
        'header': 'مدیریت و نظارت بر فاکتورها',
        'links': [
            {'name': _('فهرست فاکتورها'), 'url': 'factor_list', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-clipboard-list'},
            {'name': _('ایجاد فاکتور'), 'url': 'Nfactor_create', 'permission': 'tankhah.add_factor', 'icon': 'fas fa-file-invoice'},
            {'name': _('گردش کار فاکتور'), 'url': 'workflow_chart', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-project-diagram'},
            {'name': _('وضعیت فاکتورها'), 'url': 'factor_status_dashboard', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-file-invoice'},
        ]
    },
    'مدیریت تنخواه': {
        'header': 'مدیریت و نظارت بر تنخواه‌ها',
        'links': [
            {'name': _('فهرست تنخواه'), 'url': 'tankhah_list', 'permission': 'tankhah.view_tankhah', 'icon': 'fas fa-list-alt'},
            {'name': _('ایجاد تنخواه'), 'url': 'tankhah_create', 'permission': 'tankhah.add_tankhah', 'icon': 'fas fa-file-invoice-dollar'},
            {'name': _('وضعیت تنخواه'), 'url': 'tankhah_status', 'permission': 'tankhah.view_tankhah', 'icon': 'fas fa-file-invoice-dollar'},
        ]
    },
    'مدیریت بودجه': {
        'header': 'مدیریت و نظارت بر بودجه‌ها',
        'links': [
            {'name': _('داشبورد مدیریتی بودجه'), 'url': 'budgets_dashboard', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-bar'},
            {'name': _('فهرست تخصیص بودجه'), 'url': 'budgetallocation_list', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-list'},
            {'name': _('هشدارهای بودجه'), 'url': 'budget_warning_report', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-exclamation-triangle'},
        ]
    },
    'دستورات پرداخت': {
        'header': 'مدیریت دستورات پرداخت',
        'links': [
            {'name': _('فهرست دستورات پرداخت'), 'url': 'paymentorder_list', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-receipt'},
            {'name': _('کارتابل پرداخت'), 'url': 'paymentorder_management_list', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-tasks'},
            {'name': _('فاکتورهای تایید نهایی'), 'url': 'paymentorder_approved_factors', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-file-invoice-check'},
            {'name': _('آمار دستورات پرداخت'), 'url': 'paymentorder_stats', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-chart-bar'},
            {'name': _('فهرست دریافت‌کنندگان'), 'url': 'payee_list', 'permission': 'budgets.view_payee', 'icon': 'fas fa-user-friends'},
            {'name': _('انواع تراکنش‌ها'), 'url': 'transactiontype_list', 'permission': 'budgets.view_transactiontype', 'icon': 'fas fa-cogs'},
        ]
    },
    'گزارشات پیشرفته': {
        'header': 'گزارشات و تحلیل‌های پیشرفته',
        'links': [
            {'name': _('داشبورد گزارشات پیشرفته'), 'url': 'reports_dashboard:main_dashboard', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-line', 'note': 'داشبورد جدید با آمار کامل و چارت‌های تعاملی'},
            {'name': _('تحلیل‌های پیشرفته بودجه'), 'url': 'reports_dashboard:analytics_redesigned', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-pie'},
            {'name': _('صادرات گزارشات'), 'url': 'reports_dashboard:export_reports', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-download', 'note': 'صادرات گزارشات در فرمت‌های مختلف'},
            # {'name': _('گزارش پیشرفته تخصیص'), 'url': 'budget_allocation_report_enhanced', 'url_kwargs': {'pk': 84}, 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-line', 'note': 'گزارش پیشرفته برای تخصیص بودجه شماره 84'},
            {'name': _('گزارش دستورات پرداخت'), 'url': 'payment_order_report', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-receipt'},
        ]
    },
    'گزارشات جامع': {
        'header': 'گزارشات جامع و کلی',
        'links': [
            {'name': _('گزارشات تحلیلی'), 'url': 'analytical_reports', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-pie'},
            {'name': _('گزارش لحظه‌ای بودجه'), 'url': 'budgetrealtimeReportView', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-tachometer-alt'},
            {'name': _('داشبورد مالی'), 'url': 'financialDashboardView', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-pie'},
            {'name': _('داشبورد اجرایی'), 'url': 'executive_dashboard', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-tachometer-alt'},
            {'name': _('گزارشات بودجه کلی'), 'url': 'comprehensive_budget_report', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-bar'},
            {'name': _('گزارشات فاکتور کلی'), 'url': 'comprehensive_factor_report', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-file-invoice'},
            {'name': _('گزارشات تنخواه کلی'), 'url': 'comprehensive_tankhah_report', 'permission': 'tankhah.view_tankhah', 'icon': 'fas fa-money-bill-wave'},
            {'name': _('گزارشات عملکرد مالی'), 'url': 'financial_performance_report', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-chart-line'},
        ]
    },
    'مدیریت پروژه‌ها': {
        'header': 'مدیریت مراکز هزینه و پروژه‌ها',
        'links': [
            {'name': _('فهرست پروژه‌ها'), 'url': 'project_list', 'permission': 'core.view_project', 'icon': 'fas fa-folder-open'},
            {'name': _('ایجاد پروژه'), 'url': 'project_create', 'permission': 'core.add_project', 'icon': 'fas fa-folder-plus'},
            {'name': _('ایجاد زیرپروژه'), 'url': 'subproject_create', 'permission': 'core.add_subproject', 'icon': 'fas fa-sitemap'},
        ]
    },
    'مدیریت سازمانی': {
        'header': 'مدیریت ساختار سازمانی',
        'links': [
            {'name': _('فهرست سازمان‌ها'), 'url': 'organization_list', 'permission': 'core.view_organization', 'icon': 'fas fa-building'},
            {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'permission': 'core.add_organization', 'icon': 'fas fa-building-circle-plus'},
            {'name': _('فهرست پست‌ها'), 'url': 'post_list', 'permission': 'core.view_post', 'icon': 'fas fa-id-badge'},
            {'name': _('ایجاد پست'), 'url': 'post_create', 'permission': 'core.add_post', 'icon': 'fas fa-user-plus'},
            {'name': _('شاخه‌های سازمانی'), 'url': 'branch_list', 'permission': 'core.view_branch', 'icon': 'fas fa-sitemap'},
            {'name': _('اتصالات کاربر-پست'), 'url': 'userpost_list', 'permission': 'core.view_userpost', 'icon': 'fas fa-people-arrows'},
            {'name': _('ایجاد اتصال کاربر-پست'), 'url': 'userpost_create', 'permission': 'core.add_userpost', 'icon': 'fas fa-user-tie'},
            {'name': _('تاریخچه پست‌ها'), 'url': 'posthistory_list', 'permission': 'core.view_posthistory', 'icon': 'fas fa-history'},
        ]
    },
    'گردش کار و قوانین': {
        'header': 'مدیریت گردش کار و قوانین سیستم',
        'links': [
            {'name': _('گردش کار سیستم'), 'url': 'workflow_dashboard', 'permission': 'core.view_workflow', 'icon': 'fas fa-gavel'},
            {'name': _('کنترل گردش کار'), 'url': 'admin_workflow_dashboard', 'permission': 'core.view_workflow', 'icon': 'fas fa-user-shield'},
        ]
    },
    'مدیریت سیستم': {
        'header': 'مدیریت کاربران و تنظیمات سیستم',
        'links': [
            {'name': _('مدیریت کاربران'), 'url': 'accounts:admin_dashboard', 'permission': 'accounts.view_user', 'icon': 'fas fa-users-cog'},
            {'name': _('نسخه‌های سیستم'), 'url': 'version_index_view', 'permission': 'version_tracker.view_finalversion', 'icon': 'fas fa-code-branch'},
            {'name': _('راهنمای بودجه‌بندی'), 'url': 'budget_Help', 'permission': None, 'icon': 'fas fa-question-circle'},
            {'name': _('راهنمای سیستم'), 'url': 'soft_help', 'permission': None, 'icon': 'fas fa-question-circle'},
            {'name': _('مستندات API'), 'url': 'staff_api_documentation', 'permission': 'is_staff', 'icon': 'fas fa-code'},
        ]
    },
}

class SimpleChartView(PermissionBaseView, View):
    template_name = 'core/simple_chart.html'
    permission_codename = 'reports.view_dashboard'

    def get_context_data(self, request):
        context = {}
        context['title'] = "تست چارت پروژه‌ها"
        context['can_view_project_status'] = True  # برای تست دسترسی

        # داده‌های فرضی برای چارت پروژه‌ها (مشابه ویو داشبورد)
        projects_status = [
            {
                'name': 'پروژه تستی ۱',
                'allocated': Decimal('1000000'),
                'consumed': Decimal('400000'),
                'remaining': Decimal('600000'),
                'percentage_consumed': 40.0
            },
            {
                'name': 'پروژه تستی ۲',
                'allocated': Decimal('2000000'),
                'consumed': Decimal('1500000'),
                'remaining': Decimal('500000'),
                'percentage_consumed': 75.0
            },
            {
                'name': 'پروژه تستی ۳',
                'allocated': Decimal('500000'),
                'consumed': Decimal('100000'),
                'remaining': Decimal('400000'),
                'percentage_consumed': 20.0
            }
        ]

        # آماده‌سازی داده‌های چارت
        context['project_chart_data'] = {
            'labels': json.dumps([project['name'] for project in projects_status], ensure_ascii=False),
            'allocated': json.dumps([float(project['allocated']) for project in projects_status]),
            'consumed': json.dumps([float(project['consumed']) for project in projects_status]),
            'remaining': json.dumps([float(project['remaining']) for project in projects_status])
        }

        logger.info(f"Chart data prepared: {context['project_chart_data']}")
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        logger.info("Rendering simple chart template")
        return render(request, self.template_name, context)
class ExecutiveDashboardView(PermissionBaseView, View):
    """
    داشبورد اجرایی برای مدیرعامل - نمایش جامع گزارشات بودجه، فاکتور و تنخواه
    """
    template_name = 'core/executive_dashboard.html'
    permission_codename = 'reports.view_executive_dashboard'

    def get_context_data(self, request):
        context = {}
        user = request.user
        now = timezone.now()
        j_now = jdatetime.datetime.now()
        
        # اطلاعات پایه
        context['title'] = _("داشبورد اجرایی - گزارشات جامع")
        context['current_date'] = j_now.strftime('%Y/%m/%d')
        context['current_time'] = j_now.strftime('%H:%M')
        
        # بررسی دسترسی‌ها
        context['is_ceo'] = user.has_perm('core.view_organization') or user.is_superuser
        context['can_view_budget'] = user.has_perm('budgets.view_budgetallocation') or user.is_superuser
        context['can_view_tankhah'] = user.has_perm('tankhah.view_tankhah') or user.is_superuser
        context['can_view_factors'] = user.has_perm('tankhah.view_factor') or user.is_superuser
        
        # آمار کلی بودجه
        if context['can_view_budget']:
            try:
                budget_stats = self._get_budget_statistics()
                context.update(budget_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار بودجه: {e}")
                context['budget_error'] = True
        
        # آمار کلی تنخواه
        if context['can_view_tankhah']:
            try:
                tankhah_stats = self._get_tankhah_statistics()
                context.update(tankhah_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار تنخواه: {e}")
                context['tankhah_error'] = True
        
        # آمار کلی فاکتورها
        if context['can_view_factors']:
            try:
                factor_stats = self._get_factor_statistics()
                context.update(factor_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار فاکتور: {e}")
                context['factor_error'] = True
        
        # گزارشات تحلیلی
        try:
            analytical_data = self._get_analytical_data()
            context.update(analytical_data)
        except Exception as e:
            logger.error(f"خطا در محاسبه داده‌های تحلیلی: {e}")
            context['analytical_error'] = True
        
        return context

    def _get_budget_statistics(self):
        """آمار کلی بودجه"""
        stats = {}
        
        try:
            # آمار دوره‌های بودجه
            active_periods = BudgetPeriod.objects.filter(is_active=True, is_completed=False)
            total_allocated = active_periods.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
            
            # آمار مصرف بودجه
            total_consumed = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            stats.update({
                'total_budget_allocated': total_allocated or Decimal('0'),
                'total_budget_consumed': total_consumed or Decimal('0'),
                'total_budget_remaining': (total_allocated or Decimal('0')) - (total_consumed or Decimal('0')),
                'budget_consumption_percentage': (total_consumed / total_allocated * 100) if total_allocated and total_allocated > 0 else 0,
                'active_budget_periods_count': active_periods.count(),
            })
            
            # آمار تخصیص‌های بودجه
            allocations = BudgetAllocation.objects.filter(is_active=True)
            stats.update({
                'total_allocations_count': allocations.count(),
                'total_allocated_amount': allocations.aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total'] or Decimal('0'),
            })
            
            # روند ماهانه بودجه
            monthly_budget_data = self._get_monthly_budget_trend()
            stats['monthly_budget_trend'] = monthly_budget_data
            
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار بودجه: {e}")
            stats.update({
                'total_budget_allocated': Decimal('0'),
                'total_budget_consumed': Decimal('0'),
                'total_budget_remaining': Decimal('0'),
                'budget_consumption_percentage': 0,
                'active_budget_periods_count': 0,
                'total_allocations_count': 0,
                'total_allocated_amount': Decimal('0'),
                'monthly_budget_trend': {
                    'labels': '[]',
                    'allocated': '[]',
                    'consumed': '[]',
                    'remaining': '[]'
                }
            })
        
        return stats

    def _get_tankhah_statistics(self):
        """آمار کلی تنخواه"""
        stats = {}
        
        try:
            # آمار کلی تنخواه‌ها
            total_tankhah = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            paid_tankhah = Tankhah.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            pending_tankhah = Tankhah.objects.filter(status__code__in=['PENDING', 'APPROVED']).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            stats.update({
                'total_tankhah_amount': total_tankhah or Decimal('0'),
                'paid_tankhah_amount': paid_tankhah or Decimal('0'),
                'pending_tankhah_amount': pending_tankhah or Decimal('0'),
                'tankhah_utilization_percentage': (paid_tankhah / total_tankhah * 100) if total_tankhah and total_tankhah > 0 else 0,
                'total_tankhah_count': Tankhah.objects.count(),
                'paid_tankhah_count': Tankhah.objects.filter(status__code='PAID').count(),
                'pending_tankhah_count': Tankhah.objects.filter(status__code__in=['PENDING', 'APPROVED']).count(),
            })
            
            # روند ماهانه تنخواه
            monthly_tankhah_data = self._get_monthly_tankhah_trend()
            stats['monthly_tankhah_trend'] = monthly_tankhah_data
            
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار تنخواه: {e}")
            stats.update({
                'total_tankhah_amount': Decimal('0'),
                'paid_tankhah_amount': Decimal('0'),
                'pending_tankhah_amount': Decimal('0'),
                'tankhah_utilization_percentage': 0,
                'total_tankhah_count': 0,
                'paid_tankhah_count': 0,
                'pending_tankhah_count': 0,
                'monthly_tankhah_trend': {
                    'labels': '[]',
                    'created': '[]',
                    'paid': '[]',
                    'pending': '[]'
                }
            })
        
        return stats

    def _get_factor_statistics(self):
        """آمار کلی فاکتورها"""
        stats = {}
        
        try:
            # آمار کلی فاکتورها
            total_factors = Factor.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            paid_factors = Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            pending_factors = Factor.objects.filter(status__code__in=['PENDING_APPROVAL', 'APPROVED']).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            rejected_factors = Factor.objects.filter(status__code='REJECTED').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            stats.update({
                'total_factor_amount': total_factors or Decimal('0'),
                'paid_factor_amount': paid_factors or Decimal('0'),
                'pending_factor_amount': pending_factors or Decimal('0'),
                'rejected_factor_amount': rejected_factors or Decimal('0'),
                'factor_approval_percentage': (paid_factors / total_factors * 100) if total_factors and total_factors > 0 else 0,
                'total_factor_count': Factor.objects.count(),
                'paid_factor_count': Factor.objects.filter(status__code='PAID').count(),
                'pending_factor_count': Factor.objects.filter(status__code__in=['PENDING_APPROVAL', 'APPROVED']).count(),
                'rejected_factor_count': Factor.objects.filter(status__code='REJECTED').count(),
            })
            
            # روند ماهانه فاکتورها
            monthly_factor_data = self._get_monthly_factor_trend()
            stats['monthly_factor_trend'] = monthly_factor_data
            
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار فاکتور: {e}")
            stats.update({
                'total_factor_amount': Decimal('0'),
                'paid_factor_amount': Decimal('0'),
                'pending_factor_amount': Decimal('0'),
                'rejected_factor_amount': Decimal('0'),
                'factor_approval_percentage': 0,
                'total_factor_count': 0,
                'paid_factor_count': 0,
                'pending_factor_count': 0,
                'rejected_factor_count': 0,
                'monthly_factor_trend': {
                    'labels': '[]',
                    'created': '[]',
                    'paid': '[]',
                    'pending': '[]'
                }
            })
        
        return stats

    def _get_analytical_data(self):
        """داده‌های تحلیلی"""
        data = {}
        
        try:
            # تحلیل عملکرد مالی
            financial_performance = self._get_financial_performance_analysis()
            data['financial_performance'] = financial_performance
            
            # تحلیل روندها
            trend_analysis = self._get_trend_analysis()
            data['trend_analysis'] = trend_analysis
            
            # تحلیل ریسک‌ها
            risk_analysis = self._get_risk_analysis()
            data['risk_analysis'] = risk_analysis
            
        except Exception as e:
            logger.error(f"خطا در محاسبه داده‌های تحلیلی: {e}")
            data.update({
                'financial_performance': {
                    'budget_utilization_rate': 0,
                    'tankhah_efficiency': 0,
                    'cost_per_tankhah': 0,
                    'average_factor_amount': 0
                },
                'trend_analysis': {
                    'consumption_trend': 0,
                    'consumption_trend_direction': 'stable',
                    'current_month_consumption': 0,
                    'last_month_consumption': 0
                },
                'risk_analysis': {
                    'risks': [],
                    'risk_count': 0,
                    'high_risk_count': 0,
                    'medium_risk_count': 0
                }
            })
        
        return data

    def _get_monthly_budget_trend(self):
        """روند ماهانه بودجه"""
        try:
            now = timezone.now()
            monthly_data = []
            
            for i in range(11, -1, -1):
                month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                
                j_month_start = jdatetime.date.fromgregorian(date=month_start)
                month_label = f"{self._get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                
                allocated = BudgetAllocation.objects.filter(
                    allocation_date__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
                
                consumed = BudgetTransaction.objects.filter(
                    transaction_type='CONSUMPTION',
                    timestamp__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                
                monthly_data.append({
                    'month': month_label,
                    'allocated': float(allocated or 0),
                    'consumed': float(consumed or 0),
                    'remaining': float((allocated or 0) - (consumed or 0))
                })
            
            return {
                'labels': json.dumps([item['month'] for item in monthly_data], ensure_ascii=False),
                'allocated': json.dumps([item['allocated'] for item in monthly_data]),
                'consumed': json.dumps([item['consumed'] for item in monthly_data]),
                'remaining': json.dumps([item['remaining'] for item in monthly_data])
            }
        except Exception as e:
            logger.error(f"خطا در محاسبه روند ماهانه بودجه: {e}")
            return {
                'labels': '[]',
                'allocated': '[]',
                'consumed': '[]',
                'remaining': '[]'
            }

    def _get_monthly_tankhah_trend(self):
        """روند ماهانه تنخواه"""
        try:
            now = timezone.now()
            monthly_data = []
            
            for i in range(11, -1, -1):
                month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                
                j_month_start = jdatetime.date.fromgregorian(date=month_start)
                month_label = f"{self._get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                
                created = Tankhah.objects.filter(
                    created_at__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                
                paid = Tankhah.objects.filter(
                    status__code='PAID',
                    created_at__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                
                monthly_data.append({
                    'month': month_label,
                    'created': float(created or 0),
                    'paid': float(paid or 0),
                    'pending': float((created or 0) - (paid or 0))
                })
            
            return {
                'labels': json.dumps([item['month'] for item in monthly_data], ensure_ascii=False),
                'created': json.dumps([item['created'] for item in monthly_data]),
                'paid': json.dumps([item['paid'] for item in monthly_data]),
                'pending': json.dumps([item['pending'] for item in monthly_data])
            }
        except Exception as e:
            logger.error(f"خطا در محاسبه روند ماهانه تنخواه: {e}")
            return {
                'labels': '[]',
                'created': '[]',
                'paid': '[]',
                'pending': '[]'
            }

    def _get_monthly_factor_trend(self):
        """روند ماهانه فاکتورها"""
        try:
            now = timezone.now()
            monthly_data = []
            
            for i in range(11, -1, -1):
                month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                
                j_month_start = jdatetime.date.fromgregorian(date=month_start)
                month_label = f"{self._get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                
                created = Factor.objects.filter(
                    created_at__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                
                paid = Factor.objects.filter(
                    status__code='PAID',
                    created_at__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                
                monthly_data.append({
                    'month': month_label,
                    'created': float(created or 0),
                    'paid': float(paid or 0),
                    'pending': float((created or 0) - (paid or 0))
                })
            
            return {
                'labels': json.dumps([item['month'] for item in monthly_data], ensure_ascii=False),
                'created': json.dumps([item['created'] for item in monthly_data]),
                'paid': json.dumps([item['paid'] for item in monthly_data]),
                'pending': json.dumps([item['pending'] for item in monthly_data])
            }
        except Exception as e:
            logger.error(f"خطا در محاسبه روند ماهانه فاکتور: {e}")
            return {
                'labels': '[]',
                'created': '[]',
                'paid': '[]',
                'pending': '[]'
            }

    def _get_financial_performance_analysis(self):
        """تحلیل عملکرد مالی"""
        analysis = {}
        
        try:
            # محاسبه شاخص‌های کلیدی
            total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0'))
            )['total']
            
            total_consumed = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            total_tankhah = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            total_factors = Factor.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            tankhah_count = Tankhah.objects.count()
            factor_count = Factor.objects.count()
            
            analysis.update({
                'budget_utilization_rate': (total_consumed / total_budget * 100) if total_budget and total_budget > 0 else 0,
                'tankhah_efficiency': (total_factors / total_tankhah * 100) if total_tankhah and total_tankhah > 0 else 0,
                'cost_per_tankhah': total_tankhah / tankhah_count if tankhah_count > 0 else 0,
                'average_factor_amount': total_factors / factor_count if factor_count > 0 else 0,
            })
            
        except Exception as e:
            logger.error(f"خطا در محاسبه تحلیل عملکرد مالی: {e}")
            analysis.update({
                'budget_utilization_rate': 0,
                'tankhah_efficiency': 0,
                'cost_per_tankhah': 0,
                'average_factor_amount': 0,
            })
        
        return analysis

    def _get_trend_analysis(self):
        """تحلیل روندها"""
        trends = {}
        
        try:
            # روند مصرف بودجه
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
            
            current_consumption = current_consumption or Decimal('0')
            last_consumption = last_consumption or Decimal('0')
            
            consumption_trend = ((current_consumption - last_consumption) / last_consumption * 100) if last_consumption > 0 else 0
            
            trends.update({
                'consumption_trend': consumption_trend,
                'consumption_trend_direction': 'up' if consumption_trend > 0 else 'down' if consumption_trend < 0 else 'stable',
                'current_month_consumption': float(current_consumption),
                'last_month_consumption': float(last_consumption),
            })
            
        except Exception as e:
            logger.error(f"خطا در محاسبه تحلیل روندها: {e}")
            trends.update({
                'consumption_trend': 0,
                'consumption_trend_direction': 'stable',
                'current_month_consumption': 0,
                'last_month_consumption': 0,
            })
        
        return trends

    def _get_risk_analysis(self):
        """تحلیل ریسک‌ها"""
        risks = []
        
        try:
            # ریسک بودجه کم
            total_budget = BudgetPeriod.objects.filter(is_active=True).aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0'))
            )['total']
            
            total_consumed = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
            
            total_budget = total_budget or Decimal('0')
            total_consumed = total_consumed or Decimal('0')
            
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
            
        except Exception as e:
            logger.error(f"خطا در محاسبه تحلیل ریسک‌ها: {e}")
            risks = []
        
        return {
            'risks': risks,
            'risk_count': len(risks),
            'high_risk_count': len([r for r in risks if r['level'] == 'high']),
            'medium_risk_count': len([r for r in risks if r['level'] == 'medium']),
        }

    def _get_jalali_month_name(self, month_number):
        """نام ماه شمسی"""
        j_months_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", 
                       "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        try:
            month_number = int(month_number)
            if 1 <= month_number <= 12:
                return j_months_fa[month_number - 1]
            return str(month_number)
        except (ValueError, IndexError, TypeError):
            return str(month_number)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)
class ReportsDashboardMainView(PermissionBaseView, View):
    """
    مین‌ویوی داشبورد گزارشات جدید
    - تمپلیت: reports/dashboard/main_dashboard.html
    - خروجی: chartData یکپارچه + فلگ‌های دسترسی + آمار ساده
    """
    template_name = 'reports/dashboard/main_dashboard.html'
    permission_codename = 'reports.view_dashboard'

    def get(self, request, *args, **kwargs):
        context = self._build_context(request)
        return render(request, self.template_name, context)

    def _build_context(self, request):
        user = request.user
        can_view_budget = user.has_perm('budgets.view_budgetallocation') or user.is_superuser
        can_view_tankhah = user.has_perm('tankhah.view_tankhah') or user.is_superuser
        can_view_factors = user.has_perm('tankhah.view_factor') or user.is_superuser

        # Base flags used by template tabs
        context = {
            'can_view_budget': can_view_budget,
            'can_view_tankhah': can_view_tankhah,
            'can_view_factors': can_view_factors,
        }

        # Build chartData with safe fallbacks
        chart_data = {
            'org_budget': self._get_org_budget_summary(),
            'monthly_consumption': self._get_monthly_consumption_series(),
            'tankhah_status': self._get_tankhah_status_counts(),
            'factor_category': self._get_factor_category_totals(),
        }
        context['chartData'] = chart_data

        # Minimal KPIs used in the header/cards (safe defaults)
        context.update(self._get_simple_kpis())

        # Advanced placeholders to avoid frontend fetch errors
        context['advanced_budget'] = {}
        context['advanced_tankhah'] = {}
        context['advanced_factor'] = {}
        context['advanced_comparatives'] = {}
        context['advanced_risk'] = {}

        # Resolve dashboard_links with permissions and URLs
        try:
            context['dashboard_links'] = self._resolve_dashboard_links(request)
        except Exception as e:
            logger.error('dashboard_links resolve error: %s', e)
            context['dashboard_links'] = {}

        return context

    def _resolve_dashboard_links(self, request):
        """Build a resolved copy of dashboard_links with url_resolved and allowed fields."""
        resolved = {}
        for group_name, block in dashboard_links.items():
            header = block.get('header') or group_name
            links_out = []
            for link in block.get('links', []):
                name = link.get('name')
                icon = link.get('icon')
                note = link.get('note')
                perm_code = link.get('permission')
                url_name = link.get('url')
                url_kwargs = link.get('url_kwargs') or {}

                # permission check
                if perm_code in (None, ''):
                    allowed = True
                elif perm_code == 'is_staff':
                    allowed = bool(request.user and (request.user.is_staff or request.user.is_superuser))
                else:
                    try:
                        allowed = request.user.has_perm(perm_code)
                    except Exception:
                        allowed = False

                # reverse URL
                url_resolved = '#'
                try:
                    url_resolved = reverse(url_name, kwargs=url_kwargs)
                except NoReverseMatch:
                    try:
                        # Try as namespaced string already (reverse handles that)
                        url_resolved = reverse(url_name)
                    except Exception:
                        url_resolved = '#'

                links_out.append({
                    'name': name,
                    'icon': icon,
                    'note': note,
                    'permission': perm_code,
                    'allowed': allowed,
                    'url_resolved': url_resolved,
                })

            resolved[group_name] = {
                'header': header,
                'links': links_out,
            }
        return resolved

    def _get_org_budget_summary(self):
        try:
            # Sum allocations by organization name (via project.organization if exists)
            qs = BudgetAllocation.objects.filter(is_active=True).values(
                'organization__name'
            ).annotate(
                total=Coalesce(Sum('allocated_amount'), Decimal('0'))
            ).order_by('-total')[:8]
            result = []
            for row in qs:
                org = row.get('organization__name') or 'نامشخص'
                result.append({'organization': org, 'amount': float(row.get('total') or 0)})
            if not result:
                result = [
                    {'organization': 'سازمان ۱', 'amount': 60_000_000},
                    {'organization': 'سازمان ۲', 'amount': 40_000_000},
                ]
            return result
        except Exception as e:
            logger.error("org budget summary error: %s", e)
            return [
                {'organization': 'سازمان ۱', 'amount': 60_000_000},
                {'organization': 'سازمان ۲', 'amount': 40_000_000},
            ]

    def _get_monthly_consumption_series(self):
        try:
            now = timezone.now()
            items = []
            for i in range(5, -1, -1):
                month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                j_month_start = jdatetime.date.fromgregorian(date=month_start)
                label = f"{self._get_j_month_name(j_month_start.month)} {j_month_start.year}"
                total = BudgetTransaction.objects.filter(
                    transaction_type='CONSUMPTION',
                    timestamp__range=(month_start, month_end)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                items.append({'month': label, 'consumed': float(total or 0)})
            if not items:
                items = [
                    {'month': 'فروردین ۱۴۰۳', 'consumed': 12_000_000},
                    {'month': 'اردیبهشت ۱۴۰۳', 'consumed': 18_000_000},
                ]
            return items
        except Exception as e:
            logger.error("monthly consumption error: %s", e)
            return [
                {'month': 'فروردین ۱۴۰۳', 'consumed': 12_000_000},
                {'month': 'اردیبهشت ۱۴۰۳', 'consumed': 18_000_000},
            ]

    def _get_tankhah_status_counts(self):
        try:
            qs = Tankhah.objects.values('status__name').annotate(
                count=Coalesce(Sum(Value(1)), 0)
            ).order_by('-count')
            # Count aggregation above via Sum(Value(1)) is portable; fallback to .count() per status if needed
            if not qs:
                # Fallback path
                status_names = list(Tankhah.objects.values_list('status__name', flat=True))
                counts = {}
                for name in status_names:
                    counts[name or 'نامشخص'] = counts.get(name or 'نامشخص', 0) + 1
                return [{ 'status': k, 'count': v } for k, v in counts.items()]
            return [{ 'status': r.get('status__name') or 'نامشخص', 'count': int(r.get('count') or 0) } for r in qs]
        except Exception as e:
            logger.error("tankhah status error: %s", e)
            return [
                {'status': 'پرداخت‌شده', 'count': 10},
                {'status': 'در انتظار', 'count': 6},
            ]

    def _get_factor_category_totals(self):
        try:
            qs = Factor.objects.filter(status__code='PAID').values('category__name').annotate(
                total=Coalesce(Sum('amount'), Decimal('0'))
            ).order_by('-total')[:8]
            result = []
            for row in qs:
                name = row.get('category__name') or 'نامشخص'
                result.append({'category': name, 'total_amount': float(row.get('total') or 0)})
            if not result:
                result = [
                    {'category': 'کالا', 'total_amount': 8_000_000},
                    {'category': 'خدمت', 'total_amount': 5_000_000},
                    {'category': 'سایر', 'total_amount': 2_000_000},
                    {'category': 'حمل‌ونقل', 'total_amount': 1_000_000},
                ]
            return result
        except Exception as e:
            logger.error("factor category totals error: %s", e)
            return [
                {'category': 'کالا', 'total_amount': 8_000_000},
                {'category': 'خدمت', 'total_amount': 5_000_000},
                {'category': 'سایر', 'total_amount': 2_000_000},
                {'category': 'حمل‌ونقل', 'total_amount': 1_000_000},
            ]

    def _get_simple_kpis(self):
        try:
            total_allocated = BudgetPeriod.objects.filter(is_active=True).aggregate(
                total=Coalesce(Sum('total_amount'), Decimal('0'))
            )['total'] or Decimal('0')
            total_consumed = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION'
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
            remaining = total_allocated - total_consumed
            absorption = float((total_consumed / total_allocated * 100) if total_allocated > 0 else 0)
            return {
                'total_budget_allocated': total_allocated,
                'total_budget_consumed': total_consumed,
                'total_budget_remaining': remaining,
                'budget_consumption_percentage': absorption,
            }
        except Exception as e:
            logger.error("simple KPI error: %s", e)
            return {
                'total_budget_allocated': Decimal('0'),
                'total_budget_consumed': Decimal('0'),
                'total_budget_remaining': Decimal('0'),
                'budget_consumption_percentage': 0,
            }

    def _get_j_month_name(self, month_number: int) -> str:
        names = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                 "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        try:
            m = int(month_number)
            return names[m-1] if 1 <= m <= 12 else str(month_number)
        except Exception:
            return str(month_number)
class DashboardView(PermissionBaseView, View):
    template_name = 'core/dashboard.html'
    permission_codename = 'reports.view_dashboard'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.final_version = FinalVersion.calculate_final_version()
        except Exception:
            self.final_version = "نامشخص"
        
        # Import the new dashboard views for integration
        try:
            from reports.dashboard.views import DashboardMainView
            self.dashboard_main_view = DashboardMainView()
        except ImportError:
            self.dashboard_main_view = None

    def get_jalali_month_name(self, month_number):
        j_months_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        try:
            month_number = int(month_number)
            if 1 <= month_number <= 12:
                return j_months_fa[month_number - 1]
            return str(month_number)
        except (ValueError, IndexError):
            return str(month_number)

    def get_project_total_budget(self, project, filters=None):
        try:
            total = get_project_total_budget(project, filters=filters)
            return total
        except Exception as e:
            logger.error(f"خطا در محاسبه بودجه کل برای پروژه {project.id}: {e}", exc_info=True)
            return Decimal('0')

    def get_project_used_budget(self, project, filters=None):
        try:
            total = get_project_used_budget(project, filters=filters)
            return total
        except Exception as e:
            logger.error(f"خطا در محاسبه بودجه مصرف‌شده برای پروژه {project.id}: {e}", exc_info=True)
            return Decimal('0')

    def get_project_remaining_budget(self, project, filters=None):
        try:
            remaining = get_project_remaining_budget(project, filters=filters)
            return remaining
        except Exception as e:
            logger.error(f"خطا در محاسبه بودجه باقی‌مانده برای پروژه {project.id}: {e}", exc_info=True)
            return Decimal('0')

    def _get_tankhah_stats(self):
        """آمار تنخواه و فاکتورها"""
        now = timezone.now()
        j_now = jdatetime.datetime.now()
        stats = {
            'active_tankhah_count': 0,
            'pending_tankhah_count': 0,
            'rejected_factors_count': 0,
            'current_month_paid_factors': Decimal('0'),
            'total_allocated_tankhah': Decimal('0'),
            'total_spent_factors': Decimal('0'),
            'monthly_factors_data': {'labels': [], 'values': []},
            'quarterly_factors_data': {'labels': [], 'values': []}
        }
        # **اصلاح کلیدی:** تعریف لیست کدهای وضعیت برای استفاده در کوئری‌ها
        active_tankhah_status_codes = ['PENDING', 'APPROVED', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED',
                                       'HQ_FIN_PENDING']
        pending_tankhah_status_codes = ['PENDING', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_FIN_PENDING']
        
        # محاسبه آمار پایه
        stats = {
            'active_tankhah_count': Tankhah.objects.filter(status__code__in=active_tankhah_status_codes).count(),
            'pending_tankhah_count': Tankhah.objects.filter(status__code__in=pending_tankhah_status_codes).count(),
            'rejected_factors_count': Factor.objects.filter(status__code='REJECTED').count(),
            'total_allocated_tankhah': Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'],
            'total_spent_factors': Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'],
        }
        try:
            # محاسبه مبلغ فاکتورهای پرداخت‌شده ماه جاری
            month_start = jdatetime.date(j_now.year, j_now.month, 1).togregorian()
            month_end = (jdatetime.date(j_now.year, j_now.month,
                                        jdatetime.j_days_in_month[j_now.month - 1]).togregorian() + timedelta(days=1))
            stats['current_month_paid_factors'] = Factor.objects.filter(
                status__code='PAID',
                date__range=(month_start, month_end)
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']

            # روند ماهانه فاکتورها
            monthly_factors = []
            seen_months = set()
            for i in range(5, -1, -1):
                month = (j_now.month - i - 1) % 12 + 1
                year = j_now.year + (j_now.month - i - 1) // 12
                start_date = jdatetime.date(year, month, 1).togregorian()
                end_date = (jdatetime.date(year, month, jdatetime.j_days_in_month[month - 1]).togregorian() + timedelta(days=1))
                month_label = f"{self.get_jalali_month_name(month)} {year}"
                if month_label not in seen_months:
                    seen_months.add(month_label)
                    monthly_factors.append({
                        'label': month_label,
                        'value': float(Factor.objects.filter(
                            status__code='PAID',
                            date__range=(start_date, end_date)
                        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'])
                    })

            stats['monthly_factors_data'] = {
                'labels': json.dumps([m['label'] for m in monthly_factors], ensure_ascii=False),
                'values': json.dumps([m['value'] for m in monthly_factors])
            }
            # برای سازگاری با تمپلیت
            stats['monthly_report_data'] = stats['monthly_factors_data']

            # روند فصلی فاکتورها
            quarterly_factors = []
            for i in range(3, -1, -1):
                quarter = ((j_now.month - 1) // 3 - i) % 4 + 1
                year = j_now.year + ((j_now.month - 1) // 3 - i) // 4
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                start_date = jdatetime.date(year, start_month, 1).togregorian()
                end_date = (jdatetime.date(year, end_month,
                                           jdatetime.j_days_in_month[end_month - 1]).togregorian() + timedelta(days=1))
                quarterly_factors.append({
                    'label': f"فصل {quarter} {year}",
                    'value': float(Factor.objects.filter(
                        status__code='PAID',
                        date__range=(start_date, end_date)
                    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'])
                })

            stats['quarterly_factors_data'] = {
                'labels': json.dumps([q['label'] for q in quarterly_factors], ensure_ascii=False),
                'values': json.dumps([q['value'] for q in quarterly_factors])
            }
            # برای سازگاری با تمپلیت
            stats['quarterly_report_data'] = stats['quarterly_factors_data']
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)

        return stats

    def get_enhanced_dashboard_stats(self):
        """دریافت آمار پیشرفته از داشبورد جدید"""
        if not self.dashboard_main_view:
            return {}
        
        try:
            # دریافت آمار از داشبورد جدید
            budget_stats = self.dashboard_main_view.get_budget_statistics()
            tankhah_stats = self.dashboard_main_view.get_tankhah_statistics()
            factor_stats = self.dashboard_main_view.get_factor_statistics()
            payment_stats = self.dashboard_main_view.get_payment_statistics()
            return_stats = self.dashboard_main_view.get_budget_return_statistics()
            chart_data = self.dashboard_main_view.get_chart_data()
            
            return {
                'enhanced_budget_stats': budget_stats,
                'enhanced_tankhah_stats': tankhah_stats,
                'enhanced_factor_stats': factor_stats,
                'enhanced_payment_stats': payment_stats,
                'enhanced_return_stats': return_stats,
                'enhanced_chart_data': chart_data,
            }
        except Exception as e:
            logger.error(f"خطا در دریافت آمار پیشرفته: {e}")
            return {}

    def get_context_data(self, request):
        context = {}
        user = request.user
        now = timezone.now()
        j_now = jdatetime.datetime.now()
        current_jalali_year = j_now.year
        current_jalali_month = j_now.month

        # اطلاعات پایه
        context['title'] = _("داشبورد سیستم جامع نظارتی بر تنخواه و بودجه")
        context['version'] = self.final_version
        
        # اضافه کردن لینک به داشبورد جدید
        context['new_dashboard_url'] = 'reports_dashboard:main_dashboard'
        context['analytics_dashboard_url'] = 'reports_dashboard:budget_analytics'
        context['export_dashboard_url'] = 'reports_dashboard:export_reports'

        # دسترسی‌ها
        context['can_view_budget_stats'] = True
        context['can_view_tankhah_stats'] = True
        context['can_view_project_status'] = True
        context['can_view_budget_alerts'] = True
        
        # متغیرهای دسترسی برای تمپلیت
        context['budget_stats_permission_denied'] = False
        context['tankhah_stats_permission_denied'] = False
        context['project_status_permission_denied'] = False
        context['budget_alerts_permission_denied'] = False
        context['user_activity_permission_denied'] = False
        
        # متغیرهای خطا برای تمپلیت
        context['budget_stats_error'] = False
        context['tankhah_stats_error'] = False

        # لینک‌های داشبورد
        try:
            context['dashboard_links'] = self._get_legacy_dashboard_links(request)
        except Exception as e:
            logger.error('legacy dashboard_links build error: %s', e)
            context['dashboard_links'] = {}
        
        # اضافه کردن آمار پیشرفته از داشبورد جدید
        enhanced_stats = self.get_enhanced_dashboard_stats()
        context.update(enhanced_stats)

        # تنظیمات سیستم (SystemSettings Dashboard)
        try:
            settings_obj = SystemSettings.objects.first()
        except Exception:
            settings_obj = None
        context['system_settings'] = settings_obj
        context['system_settings_info'] = {
            'enforce_strict_approval_order': bool(getattr(settings_obj, 'enforce_strict_approval_order', False)),
            'allow_bypass_org_chart': bool(getattr(settings_obj, 'allow_bypass_org_chart', False)),
            'allow_action_without_org_chart': bool(getattr(settings_obj, 'allow_action_without_org_chart', False)),
            'tankhah_payment_ceiling_enabled_default': bool(getattr(settings_obj, 'tankhah_payment_ceiling_enabled_default', False)),
            'tankhah_payment_ceiling_default': getattr(settings_obj, 'tankhah_payment_ceiling_default', None),
            'budget_locked_percentage_default': getattr(settings_obj, 'budget_locked_percentage_default', None),
            'budget_warning_threshold_default': getattr(settings_obj, 'budget_warning_threshold_default', None),
            'budget_warning_action_default': getattr(settings_obj, 'budget_warning_action_default', None),
        }

        # متغیرهای کلیدی برای تمپلیت
        context['active_budget_periods_count'] = BudgetPeriod.objects.filter(is_active=True, is_completed=False).count() or 0
        context['active_budget_allocations_count'] = BudgetAllocation.objects.filter(is_active=True).count() or 0
        context['active_cost_centers_count'] = Project.objects.filter(is_active=True).count() or 0
        context['total_allocated_tankhah'] = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_spent_on_factors'] = Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_unspent_tankhah'] = (context['total_allocated_tankhah'] - context['total_spent_on_factors']) or Decimal('0')
        
        # متغیرهای اضافی برای تمپلیت
        context['current_month_total_amount'] = context.get('current_month_paid_factors', Decimal('0'))
        context['pending_approval_count'] = context.get('pending_tankhah_count', 0)
        context['recent_rejected_factors'] = context.get('rejected_factors_count', 0)

        # آمار بودجه - بهینه‌سازی شده
        if context['can_view_budget_stats']:
            try:
                # استفاده از آمار پیشرفته اگر در دسترس باشد
                if 'enhanced_budget_stats' in context and context['enhanced_budget_stats']:
                    enhanced_stats = context['enhanced_budget_stats']
                    context['total_allocated_budget'] = enhanced_stats.get('total_allocated', Decimal('0'))
                    context['total_consumed_budget'] = enhanced_stats.get('total_consumed', Decimal('0'))
                    context['remaining_total_budget'] = enhanced_stats.get('remaining', Decimal('0'))
                    context['percentage_consumed_budget'] = float(enhanced_stats.get('consumption_percentage', 0))
                else:
                    # محاسبه سنتی در صورت عدم دسترسی به آمار پیشرفته
                    active_budget_periods = BudgetPeriod.objects.filter(is_active=True, is_completed=False)
                    total_allocated = active_budget_periods.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))['total']
                    total_consumed = BudgetTransaction.objects.filter(
                        allocation__budget_period__in=active_budget_periods,
                        transaction_type='CONSUMPTION'
                    ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']

                    context['total_allocated_budget'] = total_allocated or Decimal('10000000')
                    context['total_consumed_budget'] = total_consumed or Decimal('4000000')
                    context['remaining_total_budget'] = (total_allocated - total_consumed) or Decimal('6000000')
                    context['percentage_consumed_budget'] = (
                        (total_consumed / total_allocated * 100) if total_allocated > 0 else 0
                    )

                # مصرف بودجه بر اساس دسته
                try:
                    category_consumption = Factor.objects.filter(status__code='PAID').values('category__name').annotate(
                        total_spent=Sum('amount')
                    ).order_by('-total_spent')[:7]
                    if not category_consumption:
                        category_consumption = [
                            {'category__name': 'دسته ۱', 'total_spent': 2000000},
                            {'category__name': 'دسته ۲', 'total_spent': 1500000},
                        ]
                except Exception as e:
                    logger.error(f"خطا در محاسبه مصرف بر اساس دسته: {e}")
                    category_consumption = [
                        {'category__name': 'دسته ۱', 'total_spent': 2000000},
                        {'category__name': 'دسته ۲', 'total_spent': 1500000},
                    ]
                
                context['budget_category_consumption'] = {
                    'labels': json.dumps([item['category__name'] or _("نامشخص") for item in category_consumption], ensure_ascii=False),
                    'values': json.dumps([float(item['total_spent'] or 0) for item in category_consumption])
                }

                # بودجه تخصیص‌یافته در مقابل مصرف‌شده
                try:
                    budget_vs_actual_labels = []
                    budget_vs_actual_allocated_data = []
                    budget_vs_actual_consumed_data = []
                    seen_months = set()
                    for i in range(5, -1, -1):
                        month_start_gregorian = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                        month_end_gregorian = (month_start_gregorian + timedelta(days=31)).replace(day=1) - timedelta(days=1)
                        j_month_start = jdatetime.date.fromgregorian(date=month_start_gregorian)
                        month_label = f"{self.get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                        if month_label not in seen_months:
                            seen_months.add(month_label)
                            budget_vs_actual_labels.append(month_label)
                            monthly_allocated = BudgetAllocation.objects.filter(
                                allocation_date__range=(month_start_gregorian, month_end_gregorian)).aggregate(
                                total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
                            monthly_consumed = BudgetTransaction.objects.filter(
                                transaction_type='CONSUMPTION',
                                timestamp__range=(month_start_gregorian, month_end_gregorian)).aggregate(
                                total=Coalesce(Sum('amount'), Decimal('0')))['total']
                            budget_vs_actual_allocated_data.append(float(monthly_allocated or 0))
                            budget_vs_actual_consumed_data.append(float(monthly_consumed or 0))
                    
                    context['budget_vs_actual_data'] = {
                        'labels': json.dumps(budget_vs_actual_labels, ensure_ascii=False),
                        'allocated': json.dumps(budget_vs_actual_allocated_data),
                        'consumed': json.dumps(budget_vs_actual_consumed_data)
                    }
                except Exception as e:
                    logger.error(f"خطا در محاسبه بودجه vs actual: {e}")
                    context['budget_vs_actual_data'] = {
                        'labels': json.dumps([], ensure_ascii=False),
                        'allocated': json.dumps([]),
                        'consumed': json.dumps([])
                    }
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار بودجه: {e}", exc_info=True)
                context['budget_stats_error'] = True

                context['budget_category_consumption'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['budget_vs_actual_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]), 'consumed': json.dumps([])}

        # آمار تنخواه - بهینه‌سازی شده
        if context['can_view_tankhah_stats']:
            try:
                # استفاده از آمار پیشرفته اگر در دسترس باشد
                if 'enhanced_tankhah_stats' in context and context['enhanced_tankhah_stats']:
                    enhanced_tankhah = context['enhanced_tankhah_stats']
                    context['total_allocated_tankhah'] = enhanced_tankhah.get('total_amount', Decimal('0'))
                    context['active_tankhah_count'] = enhanced_tankhah.get('total_count', 0)
                    
                    # محاسبه آمار اضافی
                    tankhah_stats = self._get_tankhah_stats()
                    context.update(tankhah_stats)
                else:
                    # محاسبه سنتی
                    tankhah_stats = self._get_tankhah_stats()
                    context.update(tankhah_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)
                context['tankhah_stats_error'] = True
                # تنظیم مقادیر پیش‌فرض برای آمار تنخواه
                context.update({
                    'active_tankhah_count': 0,
                    'pending_tankhah_count': 0,
                    'rejected_factors_count': 0,
                    'current_month_paid_factors': Decimal('0'),
                    'total_allocated_tankhah': Decimal('0'),
                    'total_spent_factors': Decimal('0'),
                    'monthly_factors_data': {'labels': json.dumps([]), 'values': json.dumps([])},
                    'quarterly_factors_data': {'labels': json.dumps([]), 'values': json.dumps([])},
                    'monthly_report_data': {'labels': json.dumps([]), 'values': json.dumps([])},
                    'quarterly_report_data': {'labels': json.dumps([]), 'values': json.dumps([])}
                })

        # وضعیت پروژه‌ها
        if context['can_view_project_status']:
            try:
                # محاسبه وضعیت پروژه‌ها با کوئری بهینه
                active_projects_with_stats = Project.objects.filter(is_active=True).annotate(
                    allocated=Coalesce(
                        Sum('allocations__allocated_amount', filter=Q(allocations__is_active=True)),
                        Value(Decimal('0')), output_field=DecimalField()
                    ),
                    consumed=Coalesce(
                        Sum('tankhah_set__factors__amount', filter=Q(tankhah_set__factors__status__code='PAID')),
                        Value(Decimal('0')), output_field=DecimalField()
                    )
                ).annotate(
                    remaining=F('allocated') - F('consumed'),
                    percentage_consumed=Case(
                        When(allocated__gt=0, then=(F('consumed') * 100) / F('allocated')),
                        default=Value(Decimal('0')), output_field=DecimalField()
                    )
                ).filter(allocated__gt=0).order_by('-start_date')[:5]

                projects_status = []
                for project in active_projects_with_stats:
                    projects_status.append({
                        'name': project.name,
                        'allocated': project.allocated,
                        'consumed': project.consumed,
                        'remaining': project.remaining,
                        'percentage_consumed': float(project.percentage_consumed)
                    })

                # اگر پروژه‌ای وجود نداشت، داده‌های نمونه نمایش دهیم
                if not projects_status:
                    projects_status = [
                        {'name': 'پروژه نمونه', 'allocated': Decimal('1000000'), 'consumed': Decimal('400000'),
                         'remaining': Decimal('600000'), 'percentage_consumed': 40.0}
                    ]

                context['project_budget_status'] = projects_status
                context['project_chart_data'] = {
                    'labels': json.dumps([p['name'] for p in projects_status], ensure_ascii=False),
                    'allocated': json.dumps([float(p['allocated']) for p in projects_status]),
                    'consumed': json.dumps([float(p['consumed']) for p in projects_status]),
                    'remaining': json.dumps([float(p['remaining']) for p in projects_status])
                }

            except Exception as e:
                logger.error(f"خطا در محاسبه وضعیت پروژه‌ها: {e}", exc_info=True)
                # تنظیم داده‌های پیش‌فرض
                context['project_budget_status'] = [
                    {'name': 'پروژه نمونه', 'allocated': Decimal('1000000'), 'consumed': Decimal('400000'),
                     'remaining': Decimal('600000'), 'percentage_consumed': 40.0}
                ]
                context['project_chart_data'] = {
                    'labels': json.dumps(['پروژه نمونه'], ensure_ascii=False),
                    'allocated': json.dumps([1000000.0]),
                    'consumed': json.dumps([400000.0]),
                    'remaining': json.dumps([600000.0])
                }

        # هشدارهای بودجه
        if context['can_view_budget_alerts']:
            try:
                budget_period_ct = ContentType.objects.get_for_model(BudgetPeriod)
                budget_allocation_ct = ContentType.objects.get_for_model(BudgetAllocation)
                recent_warnings = Notification.objects.filter(
                    Q(target_content_type=budget_period_ct) | Q(target_content_type=budget_allocation_ct),
                    priority__in=['warning', 'error', 'locked']
                ).select_related('recipient', 'actor').prefetch_related('target').order_by('-timestamp')[:5]

                budget_warnings_transformed = []
                for notif in recent_warnings:
                    target_obj_display = str(notif.target) if notif.target else _("نامشخص")
                    actor_username = getattr(notif.actor, 'username', str(notif.actor)) if notif.actor else 'سیستم'
                    budget_warnings_transformed.append({
                        'details': f"{notif.verb}: {target_obj_display} - {notif.description or ''}",
                        'timestamp': notif.timestamp,
                        'created_by': {'username': actor_username}
                    })
                if not budget_warnings_transformed:
                    budget_warnings_transformed = [
                        {'details': 'هشدار نمونه: بودجه کم است', 'timestamp': now, 'created_by': {'username': 'سیستم'}}
                    ]
                context['recent_budget_warnings'] = budget_warnings_transformed
            except Exception as e:
                logger.error(f"خطا در محاسبه هشدارهای بودجه: {e}", exc_info=True)
                context['recent_budget_warnings'] = []

        # گرفتن اعلان‌های خوانده‌نشده کاربر
        context['notifications'] = Notification.objects.filter(
            recipient=request.user, unread=True, deleted=False
        ).select_related('actor', 'target').order_by('-timestamp')[:5]
        context['unread_count'] = Notification.objects.filter(
            recipient=request.user, unread=True, deleted=False
        ).count()

        # فعالیت‌های اخیر
        try:
            context['recent_activities'] = ApprovalLog.objects.select_related('user', 'tankhah', 'factor', 'action').order_by('-timestamp')[:7]
            if not context['recent_activities']:
                context['recent_activities'] = [
                    {
                        'tankhah': {'number': 'T001'},
                        'get_action_display': lambda: 'تأیید',
                        'user': {'username':request.user},
                        'timestamp': now,
                        'comment': 'تأیید نمونه'
                    }
                ]
        except Exception as e:
            logger.error(f"خطا در محاسبه فعالیت‌های اخیر: {e}", exc_info=True)
            context['recent_activities'] = []

        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        return render(request, self.template_name, context)

    def _get_legacy_dashboard_links(self, request):
        """Return links in the legacy structure expected by templates/core/dashboard.html.
        Structure: { 'گروه': [ { name, icon, url?, url_kwargs?, direct_url? } ] }
        Only include links the user is allowed to see.
        """
        legacy = {}
        for group_name, block in dashboard_links.items():
            items = []
            for link in block.get('links', []):
                perm_code = link.get('permission')
                # permission check
                if perm_code in (None, ''):
                    allowed = True
                elif perm_code == 'is_staff':
                    allowed = bool(request.user and (request.user.is_staff or request.user.is_superuser))
                else:
                    try:
                        allowed = request.user.has_perm(perm_code)
                    except Exception:
                        allowed = False
                if not allowed:
                    continue

                url_name = link.get('url')
                url_kwargs = link.get('url_kwargs') or {}
                direct_url = None
                try:
                    if url_kwargs:
                        direct_url = reverse(url_name, kwargs=url_kwargs)
                    else:
                        direct_url = reverse(url_name)
                except Exception:
                    direct_url = None

                items.append({
                    'name': link.get('name'),
                    'icon': link.get('icon') or 'fas fa-link',
                    'url': url_name,
                    'url_kwargs': url_kwargs if url_kwargs else None,
                    'direct_url': direct_url,
                })
            legacy[group_name] = items
        return legacy
