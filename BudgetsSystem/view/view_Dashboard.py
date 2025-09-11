
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
from django.contrib.contenttypes.models import ContentType
logger = logging.getLogger('Main_Dashboard')
# لینک‌های داشبورد
_____dashboard_links_ = {
    'روند تنخواه': [
        {'name': _('روند تنخواه'), 'url': 'dashboard_flows', 'icon': 'fas fa-link'},
        {'name': _('BI گزارشات'), 'url': 'financialDashboardView', 'icon': 'fas fa-chart-bar'},
        {'name': _('گزارش جزئیات تنخواه'), 'url': 'tankhah_detail', 'icon': 'fas fa-chart-bar'},
        {'name': _('گزارش لحظه‌ای از بودجه‌بندی'), 'url': 'budgetrealtimeReportView', 'icon': 'fas fa-chart-bar'},
    ],
    'بودجه سازمان': [
        {'name': _('فهرست بودجه کلان'), 'url': 'budgetperiod_list', 'permission': 'budgets.view_budgetperiod',
         'icon': 'fas fa-project-diagram'},
        {'name': _('داشبورد مدیریتی بودجه'), 'url': 'budgets_dashboard', 'permission': 'budgets.view_budgetallocation',
         'icon': 'fas fa-project-diagram'},
        {'name': _('فهرست بودجه شعبات'), 'url': 'budgetallocation_list', 'permission': 'budgets.view_budgetallocation',
         'icon': 'fas fa-plus'},
        {'name': _('گزارش هشدارهای بودجه'), 'url': 'budget_warning_report', 'permission': 'budgets.view_budgethistory',
         'icon': 'fas fa-plus'},
        {'name': _('فهرست بودجه در مراکز هزینه (برگشت بودجه)'), 'url': 'budgetallocation_list',
         'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-plus'},
        {'name': _('انتقال بودجه'), 'url': 'budget_transfer', 'permission': 'budgets.add_budgetreallocation',
         'icon': 'fas fa-plus'},
        {'name': _('فهرست تغییر در بودجه'), 'url': 'budgettransaction_list',
         'permission': 'budgets.view_budgettransaction', 'icon': 'fas fa-plus'},
    ],
    'تنخواه': [
        {'name': _('فهرست تنخواه'), 'url': 'tankhah_list', 'permission': 'tankhah.view_tankhah',
         'icon': 'fas fa-project-diagram'},
        {'name': _('ایجاد تنخواه'), 'url': 'tankhah_create', 'permission': 'tankhah.add_tankhah',
         'icon': 'fas fa-plus'},
    ],
    'فاکتورها': [
        {'name': _('فهرست فاکتورها'), 'url': 'factor_list', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-file-invoice'},
        {'name': _('ایجاد فاکتور'), 'url': 'Nfactor_create', 'permission': 'tankhah.add_factor', 'icon': 'fas fa-plus'},
    ],
    'عنوان مرکز هزینه (پروژه)': [
        {'name': _('فهرست مرکز هزینه (پروژه)'), 'url': 'project_list', 'permission': 'core.view_project',
         'icon': 'fas fa-project-diagram'},
        {'name': _('ایجاد مرکز هزینه (پروژه)'), 'url': 'project_create', 'permission': 'core.add_project',
         'icon': 'fas fa-plus'},
        {'name': _('ایجاد زیر مرکز هزینه (پروژه)'), 'url': 'subproject_create', 'permission': 'core.add_subproject',
         'icon': 'fas fa-plus'},
    ],
    'گردش کار': [
        {'name': _('فهرست گردش کار'), 'url': 'workflow_stage_list', 'permission': 'core.view_workflowstage',
         'icon': 'fas fa-exchange-alt'},
        {'name': _('ثبت گردش کار'), 'url': 'workflow_stage_create', 'permission': 'core.add_workflowstage',
         'icon': 'fas fa-plus'},
    ],
    'پست و سلسله مراتب': [
        {'name': _('فهرست پست‌ها'), 'url': 'post_list', 'permission': 'core.view_post', 'icon': 'fas fa-sitemap'},
        {'name': _('ایجاد پست'), 'url': 'post_create', 'permission': 'core.add_post', 'icon': 'fas fa-plus'},
    ],
    'سازمان': [
        {'name': _('فهرست سازمان‌ها'), 'url': 'organization_list', 'permission': 'core.view_organization',
         'icon': 'fas fa-building'},
        {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'permission': 'core.add_organization',
         'icon': 'fas fa-plus'},
    ],
    'پست همکار در سازمان': [
        {'name': _('فهرست اتصالات کاربر به پست'), 'url': 'userpost_list', 'permission': 'core.view_userpost',
         'icon': 'fas fa-users'},
        {'name': _('ایجاد اتصال'), 'url': 'userpost_create', 'permission': 'core.add_userpost', 'icon': 'fas fa-plus'},
    ],
    'مدیریت دستور پرداخت': [
        {'name': _('دستور پرداخت'), 'url': 'paymentorder_list', 'icon': 'fas fa-plus'},
        # {'name': _('دستور پرداخت'), 'url': 'paymentorder_list', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-plus'},
        # ,'permission': 'budgets.BudgetTransaction_view'
        {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list', 'icon': 'fas fa-plus'},
        # {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list', 'permission': 'budgets.view_payee', 'icon': 'fas fa-plus'},
        # ,'permission': 'budgets.BudgetTransaction_view'
        {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list', 'icon': 'fas fa-plus'},
        # {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list', 'permission': 'budgets.view_transactiontype', 'icon': 'fas fa-plus'},
        # 'permission': 'budgets.BudgetTransaction_view',
        {'name': _('دسته بندی نوع هزینه کرد'), 'url': 'itemcategory_list', 'icon': 'fas fa-link'},
    ],
    'قوانین سیستم (رول‌های دسترسی)': [
        # {'name': _('قوانین سیستم (رول‌های دسترسی)'), 'url': 'accessrule_list', 'icon': 'fas fa-history'},
        {'name': _('قوانین سیستم (رول‌های دسترسی)  '), 'url': 'post_access_rule_assign', 'icon': 'fas fa-history'},
    ],
    'تاریخچه پست‌ها': [
        {'name': _('فهرست تاریخچه پست‌ها'), 'url': 'posthistory_list', 'permission': 'core.view_posthistory',
         'icon': 'fas fa-history'},
    ],
    'دیگر لینک‌ها': [
        {'name': _('مدیریت کاربران'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-link'},
        {'name': _('نسخه‌ها'), 'url': 'version_index_view', 'icon': 'fas fa-link'},
        {'name': _('راهنمای بودجه‌بندی'), 'url': 'budget_Help', 'icon': 'fas fa-link'},
    ],
}
dashboard_links = {
    'فاکتورها': [
        {'name': _('فهرست فاکتورها'), 'url': 'factor_list',    'permission': 'tankhah.view_factor',     'icon': 'fas fa-clipboard-list'},  # لیست کلیپ‌بورد برای فاکتورها
        # {'name': _('فهرست فاکتورها2'), 'url': 'factor_list2', 'permission': 'tankhah.view_factor', 'icon': 'fas fa-clipboard-list'}, # لیست کلیپ‌بورد برای فاکتورها
       {'name': _('ایجاد فاکتور'),    'url': 'Nfactor_create', 'permission': 'tankhah.add_factor',      'icon': 'fas fa-file-invoice'},  # فاکتور خالی

    ],
    'تنخواه': [
        {'name': _('فهرست تنخواه'), 'url': 'tankhah_list', 'permission': 'tankhah.view_tankhah',
         'icon': 'fas fa-list-alt'},  # لیست
        {'name': _('ایجاد تنخواه'), 'url': 'tankhah_create', 'permission': 'tankhah.add_tankhah',
         'icon': 'fas fa-file-invoice-dollar'},  # فاکتور با دلار (یا پول)
        {'name': _('وضعیت تنخواه'), 'url': 'tankhah_status', 'icon': 'fas fa-file-invoice-dollar'},
        # فاکتور با دلار (یا پول)
        # {'name': _('1وضعیت تنخواه'), 'url': 'tankhah_approval_timeline',   'icon': 'fas fa-file-invoice-dollar'}, # فاکتور با دلار (یا پول)

    ],
    'بودجه سازمان': [
        # {'name': _('فهرست بودجه کلان'), 'url': 'budgetperiod_list', 'permission': 'budgets.view_budgetperiod', 'icon': 'fas fa-money-check-alt'}, # چک پول
        {'name': _('داشبورد مدیریتی بودجه'), 'url': 'budgets_dashboard', 'permission': 'budgets.view_budgetallocation',
         'icon': 'fas fa-chart-bar'},  # نمودار میله‌ای برای داشبورد
        # {'name': _('فهرست بودجه شعبات'), 'url': 'budgetallocation_list', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-building'}, # ساختمان برای شعبات
        # {'name': _('گزارش هشدارهای بودجه'), 'url': 'budget_warning_report', 'permission': 'budgets.view_budgethistory', 'icon': 'fas fa-exclamation-triangle'}, # مثلث اخطار
        # {'name': _('فهرست بودجه در مراکز هزینه (برگشت بودجه)'), 'url': 'budgetallocation_list', 'permission': 'budgets.view_budgetallocation', 'icon': 'fas fa-reply'}, # فلش برگشت
        # {'name': _('انتقال بودجه'), 'url': 'budget_transfer', 'permission': 'budgets.add_budgetreallocation', 'icon': 'fas fa-exchange-alt'}, # فلش تبادل
        # {'name': _('فهرست تغییر در بودجه'), 'url': 'budgettransaction_list', 'permission': 'budgets.view_budgettransaction', 'icon': 'fas fa-history'}, # ساعت برای تاریخچه
        # # {'name': _('دستور پرداخت'), 'url': 'paymentorder_list', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-receipt'}, # رسید
        # {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list', 'permission': 'budgets.view_payee', 'icon': 'fas fa-user-friends'}, # چند نفر برای دریافت‌کننده
        # {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list', 'permission': 'budgets.view_transactiontype', 'icon': 'fas fa-cogs'}, # چرخ‌دنده برای تنظیمات پویا
    ],
    'مدیریت دستور پرداخت': [
        {'name': _('دستور پرداخت'), 'url': 'paymentorder_list', 'icon': 'fas fa-plus'},
        # {'name': _('دستور پرداخت'), 'url': 'paymentorder_list', 'permission': 'budgets.view_paymentorder', 'icon': 'fas fa-plus'},
        # ,'permission': 'budgets.BudgetTransaction_view'
        {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list', 'icon': 'fas fa-plus'},
        # {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list', 'permission': 'budgets.view_payee', 'icon': 'fas fa-plus'},
        # ,'permission': 'budgets.BudgetTransaction_view'
        {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list', 'icon': 'fas fa-plus'},
        # {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list', 'permission': 'budgets.view_transactiontype', 'icon': 'fas fa-plus'},
        # 'permission': 'budgets.BudgetTransaction_view',
        {'name': _('دسته بندی نوع هزینه کرد'), 'url': 'itemcategory_list', 'icon': 'fas fa-link'},
        {'name': _(' دستور پرداخت'), 'url': 'payment_order_review', 'icon': 'fas fa-link'},

    ],
    'گزارشات': [
        {'name': _('درخت سیستم'), 'url': 'comprehensive_budget_report', 'icon': 'fas fa-chart-line'},
        # نمودار خطی برای روند
        {'name': _('روند تنخواه'), 'url': 'dashboard_flows', 'icon': 'fas fa-chart-line'},  # نمودار خطی برای روند
        {'name': _('BI گزارشات'), 'url': 'financialDashboardView', 'icon': 'fas fa-chart-pie'},
        # نمودار دایره‌ای برای گزارشات BI
        # {'name': _('گزارش جزئیات تنخواه'), 'url': 'tankhah_detail', 'icon': 'fas fa-file-alt'}, # فایل متنی برای جزئیات
        {'name': _('گزارش لحظه‌ای از بودجه‌بندی'), 'url': 'budgetrealtimeReportView', 'icon': 'fas fa-tachometer-alt'},
        # سرعت‌سنج برای لحظه‌ای
        {'name': _('گزارشات دستور پرداخت'), 'url': 'payment_order_report', 'icon': 'fas fa-tachometer-alt'},
        # سرعت‌سنج برای لحظه‌ای
        {'name': _('گزارش رد/تایید فاکتور'), 'url': 'advance_factor_status_review',
         'permission': 'tankhah.factor_view', 'icon': 'fas fa-file-invoice'},  # فاکتور خالی
        {'name': _(' گزارش وضعیت فاکتورها '), 'url': 'factor_status_dashboard', 'permission': 'tankhah.factor_view',
         'icon': 'fas fa-file-invoice'},  # فاکتور خالی
    ],
    'عنوان مرکز هزینه (پروژه)': [
        {'name': _('فهرست مرکز هزینه (پروژه)'), 'url': 'project_list', 'permission': 'core.view_project',
         'icon': 'fas fa-folder-open'},  # پوشه باز برای پروژه
        {'name': _('ایجاد مرکز هزینه (پروژه)'), 'url': 'project_create', 'permission': 'core.add_project',
         'icon': 'fas fa-folder-plus'},  # پوشه با علامت به اضافه
        {'name': _('ایجاد زیر مرکز هزینه (پروژه)'), 'url': 'subproject_create', 'permission': 'core.add_subproject',
         'icon': 'fas fa-sitemap'},  # چارت سازمانی برای زیرپروژه
    ],
    'گردش کار': [
        {'name': _('فهرست گردش کار'), 'url': 'workflow_stage_list', 'permission': 'core.view_workflowstage',
         'icon': 'fas fa-project-diagram'},  # نمودار پروژه برای گردش کار
        {'name': _('ثبت گردش کار'), 'url': 'workflow_stage_create', 'permission': 'core.add_workflowstage',
         'icon': 'fas fa-plus-circle'},  # دایره به اضافه
    ],
    'پست و سلسله مراتب': [
        {'name': _('فهرست پست‌ها'), 'url': 'post_list', 'permission': 'core.view_post', 'icon': 'fas fa-id-badge'},
        # کارت شناسایی برای پست
        {'name': _('ایجاد پست'), 'url': 'post_create', 'permission': 'core.add_post', 'icon': 'fas fa-user-plus'},
        # اضافه کردن کاربر
        {'name': _('فهرست شاخه های سازمانی'), 'url': 'branch_list', 'permission': 'core.Branch_view',
         'icon': 'fas fa-user-plus'},  # اضافه کردن کاربر
    ],
    'سازمان': [
        {'name': _('فهرست سازمان‌ها'), 'url': 'organization_list', 'permission': 'core.view_organization',
         'icon': 'fas fa-building'},  # ساختمان
        {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'permission': 'core.add_organization',
         'icon': 'fas fa-building-circle-plus'},  # ساختمان با علامت به اضافه (Font Awesome 6) یا fas fa-plus-square
    ],
    'پست همکار در سازمان': [
        {'name': _('فهرست اتصالات کاربر به پست'), 'url': 'userpost_list', 'permission': 'core.view_userpost',
         'icon': 'fas fa-people-arrows'},  # فلش بین افراد
        {'name': _('ایجاد اتصال'), 'url': 'userpost_create', 'permission': 'core.add_userpost',
         'icon': 'fas fa-user-tie'},  # آدم با کراوات
    ],
    'تاریخچه پست‌ها': [
        {'name': _('فهرست تاریخچه پست‌ها'), 'url': 'posthistory_list', 'permission': 'core.view_posthistory',
         'icon': 'fas fa-history'},  # تاریخچه
    ],
    'قوانین سیستم (رول‌های دسترسی)': [
        {'name': _('قوانین سیستم (رول‌های دسترسی)'), 'url': 'post_access_rule_assign_old', 'icon': 'fas fa-gavel'},
        {'name': _('قوانین سیستم (هیبریدی)'), 'url': 'workflow_select', 'icon': 'fas fa-gavel'},
        {'name': _('قوانین سیستم گردش محور'), 'url': 'workflow_dashboard', 'icon': 'fas fa-gavel'},
        # چکش (نماد قانون)
    ],
    'دیگر لینک‌ها': [
        {'name': _('مدیریت کاربران'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-users-cog'},
        # کاربران با چرخ‌دنده
        {'name': _('نسخه‌ها'), 'url': 'version_index_view', 'icon': 'fas fa-code-branch'},  # شاخه‌های کد برای نسخه‌ها
        {'name': _('راهنمای بودجه‌بندی'), 'url': 'budget_Help', 'icon': 'fas fa-question-circle'},
        # علامت سوال برای راهنما
        {'name': _('راهنمای سیستم '), 'url': 'soft_help', 'icon': 'fas fa-question-circle'},  # علامت سوال برای راهنما
    ],
}
class DashboardView__ok___(LoginRequiredMixin, View):
    template_name = 'core/dashboard.html'
    login_url = reverse_lazy('accounts:login')
    final_version = FinalVersion.calculate_final_version()  # فرض می‌کنیم FinalVersion تعریف شده است

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
        stats = {
            # فیلتر بر اساس status__code__in
            'active_tankhah_count': Tankhah.objects.filter(status__code__in=active_tankhah_status_codes).count(),
            'pending_tankhah_count': Tankhah.objects.filter(status__code__in=pending_tankhah_status_codes).count(),
            # فیلتر بر اساس status__code
            'rejected_factors_count': Factor.objects.filter(status__code='REJECT').count(),
            'total_allocated_tankhah': Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'],
            'total_spent_factors':
                Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))[
                    'total'],
        }
        try:
            # آمار پایه
            stats.update({
                'active_tankhah_count': Tankhah.objects.filter(
                    status__code=['DRAFT','PENDING_APPROVAL' 'APPROVED_INTERMEDIATE', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED', 'HQ_FIN_PENDING']
                ).count(),
                'pending_tankhah_count': Tankhah.objects.filter(
                    status__code=['PENDING_APPROVAL', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_FIN_PENDING']
                ).count(),
                'rejected_factors_count': Factor.objects.filter(
                    status__code='REJECTED',
                    date__gte=now - timedelta(days=90)
                ).count(),
                'total_allocated_tankhah': Tankhah.objects.aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
                'total_spent_factors': Factor.objects.filter(status__code='PAID').aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
            })

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
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)

        return stats

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

        # دسترسی‌ها
        context['can_view_budget_stats'] = True
        context['can_view_tankhah_stats'] = True
        context['can_view_project_status'] = True
        context['can_view_budget_alerts'] = True

        # لینک‌های داشبورد
        context['dashboard_links'] = dashboard_links

        # متغیرهای کلیدی برای تمپلیت
        context['active_budget_periods_count'] = BudgetPeriod.objects.filter(is_active=True, is_completed=False).count() or 0
        context['active_budget_allocations_count'] = BudgetAllocation.objects.filter(is_active=True).count() or 0
        context['active_cost_centers_count'] = Project.objects.filter(is_active=True).count() or 0
        context['total_allocated_tankhah'] = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_spent_on_factors'] = Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_unspent_tankhah'] = (context['total_allocated_tankhah'] - context['total_spent_on_factors']) or Decimal('0')

        # آمار بودجه
        if context['can_view_budget_stats']:
            try:
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
                category_consumption = Factor.objects.filter(status__code='PAID').values('category__name').annotate(
                    total_spent=Sum('amount')
                ).order_by('-total_spent')[:7]
                if not category_consumption:
                    category_consumption = [
                        {'category__name': 'دسته ۱', 'total_spent': 2000000},
                        {'category__name': 'دسته ۲', 'total_spent': 1500000},
                    ]
                context['budget_category_consumption'] = {
                    'labels': json.dumps([item['category__name'] or _("نامشخص") for item in category_consumption], ensure_ascii=False),
                    'values': json.dumps([float(item['total_spent'] or 0) for item in category_consumption])
                }

                # بودجه تخصیص‌یافته در مقابل مصرف‌شده
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
                            allocation_date__range=(month_start_gregorian, month_end_gregorian)
                        ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
                        monthly_consumed = BudgetTransaction.objects.filter(
                            transaction_type='CONSUMPTION',
                            timestamp__range=(month_start_gregorian, month_end_gregorian)
                        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                        budget_vs_actual_allocated_data.append(float(monthly_allocated or (1000000 * (6 - i))))
                        budget_vs_actual_consumed_data.append(float(monthly_consumed or (500000 * (6 - i))))

                context['budget_vs_actual_data'] = {
                    'labels': json.dumps(budget_vs_actual_labels, ensure_ascii=False),
                    'allocated': json.dumps(budget_vs_actual_allocated_data),
                    'consumed': json.dumps(budget_vs_actual_consumed_data)
                }
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار بودجه: {e}", exc_info=True)
                context['budget_category_consumption'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['budget_vs_actual_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]), 'consumed': json.dumps([])}

        # آمار تنخواه
        if context['can_view_tankhah_stats']:
            try:
                tankhah_stats = self._get_tankhah_stats()
                context.update(tankhah_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)
                context['monthly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['quarterly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}

        # وضعیت پروژه‌ها
        if context['can_view_project_status']:
            try:



                projects_status = []
                active_projects = Project.objects.filter(is_active=True).annotate(
                    total_budget=Coalesce(Sum('allocations__allocated_amount'), Decimal('0'))
                ).filter(total_budget__gt=0).order_by('-start_date')[:5]
                #
                # active_projects = Project.objects.filter(
                #     is_active=True
                # ).annotate(
                #     total_budget=Coalesce(Sum('allocations__allocated_amount'), Decimal('0'))
                # ).filter(
                #     total_budget__gt=0
                # ).order_by('-start_date')[:5]
                projects_status = []
                for project in active_projects:
                    allocated = self.get_project_total_budget(project)
                    consumed = self.get_project_used_budget(project)
                    remaining = self.get_project_remaining_budget(project)
                    projects_status.append({
                        'name': project.name,
                        'allocated': get_project_total_budget(project),
                        'consumed': get_project_used_budget(project),
                        'remaining': get_project_remaining_budget(project),
                        'percentage_consumed': ((get_project_used_budget(project) / get_project_total_budget(
                            project)) * 100 if get_project_total_budget(project) > 0 else 0)
                    })

                    # ارسال اعلان برای بودجه کم
                    if allocated > 0 and remaining <= calculate_threshold_amount(allocated, Decimal('10')):
                        try:
                            posts = project.organizations.first().posts.filter(userpost__is_active=True).distinct() if project.organizations.exists() else []
                            if posts:
                                send_notification(
                                    sender=user,
                                    posts=posts,
                                    verb='LOW_BUDGET',
                                    description=f"بودجه پروژه {project.name} به آستانه هشدار (10٪) رسیده است.",
                                    target=project,
                                    entity_type='PROJECT',
                                    priority='HIGH'
                                )
                            else:
                                logger.warning(f"هیچ پستی برای پروژه {project.id} یافت نشد")
                        except Exception as e:
                            logger.error(f"خطا در ارسال اعلان برای پروژه {project.id}: {e}", exc_info=True)

                if not projects_status:
                    projects_status = [
                        {'name': 'پروژه نمونه', 'allocated': Decimal('1000000'), 'consumed': Decimal('400000'), 'remaining': Decimal('600000'), 'percentage_consumed': 40.0}
                    ]
                context['project_budget_status'] = projects_status
                context['project_chart_data'] = {
                    'labels': json.dumps([project['name'] for project in projects_status], ensure_ascii=False),
                    'allocated': json.dumps([float(project['allocated']) for project in projects_status]),
                    'consumed': json.dumps([float(project['consumed']) for project in projects_status]),
                    'remaining': json.dumps([float(project['remaining']) for project in projects_status])
                }
            except Exception as e:
                logger.error(f"خطا در محاسبه وضعیت پروژه‌ها: {e}", exc_info=True)
                context['project_budget_status'] = []
                context['project_chart_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]), 'consumed': json.dumps([]), 'remaining': json.dumps([])}

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
            context['recent_activities'] = ApprovalLog.objects.select_related('user', 'tankhah', 'factor', 'stage').order_by('-timestamp')[:7]
            if not context['recent_activities']:
                context['recent_activities'] = [
                    {
                        'tankhah': {'number': 'T001'},
                        'get_action_display': lambda: 'تأیید',
                        'user': {'username': 'کاربر نمونه'},
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
class DashboardView___(LoginRequiredMixin, View):
    template_name = 'core/dashboard.html'
    login_url = reverse_lazy('accounts:login')

    final_version = FinalVersion.calculate_final_version()

    # logger.info(f'final_version is {final_version}')
    def get_jalali_month_name(self, month_number):
        j_months_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن",
                       "اسفند"]
        try:
            month_number = int(month_number)
            if 1 <= month_number <= 12:
                month_name = j_months_fa[month_number - 1]
                # logger.debug(f"get_jalali_month_name: month_number={month_number}, result={month_name}")
                return month_name
            # logger.error(f"get_jalali_month_name: Invalid month_number={month_number}")
            return str(month_number)
        except (ValueError, IndexError):
            # logger.error(f"get_jalali_month_name: Invalid month_number={month_number}")
            return str(month_number)

    def get_project_total_budget(self, project, filters=None):
        try:
            total = get_project_total_budget(project, filters=filters)
            # logger.info(f"get_project_total_budget: project={project.id}, name={project.name}, total={total}, filters={filters}")
            return total
        except Exception as e:
            # logger.error(f"خطا در محاسبه بودجه کل برای پروژه {project.id}: {e}", exc_info=True)
            return Decimal('0')

    def get_project_used_budget(self, project, filters=None):
        try:
            total = get_project_used_budget(project, filters=filters)
            # logger.info(f"get_project_used_budget: project={project.id}, name={project.name}, total={total}, filters={filters}")
            return total
        except Exception as e:
            # logger.error(f"خطا در محاسبه بودجه مصرف‌شده برای پروژه {project.id}: {e}", exc_info=True)
            return Decimal('0')

    def get_project_remaining_budget(self, project, filters=None):
        try:
            remaining = get_project_remaining_budget(project, filters=filters)
            # logger.info(f"get_project_remaining_budget: project={project.id}, name={project.name}, remaining={remaining}, filters={filters}")
            return remaining
        except Exception as e:
            # logger.error(f"خطا در محاسبه بودجه باقی‌مانده برای پروژه {project.id}: {e}", exc_info=True)
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

        try:
            # آمار پایه
            stats.update({
                'active_tankhah_count': Tankhah.objects.filter(
                    status__code__in=['PENDING', 'APPROVED', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED',
                                'HQ_FIN_PENDING']
                ).count(),
                'pending_tankhah_count': Tankhah.objects.filter(
                    status__code__in=['PENDING', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_FIN_PENDING']
                ).count(),
                'rejected_factors_count': Factor.objects.filter(
                    status__code__in='REJECTED',
                    date__gte=now - timedelta(days=90)
                ).count(),
                'total_allocated_tankhah': Tankhah.objects.aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
                'total_spent_factors': Factor.objects.filter(status__code__in='PAID').aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
            })

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
                end_date = (jdatetime.date(year, month, jdatetime.j_days_in_month[month - 1]).togregorian() + timedelta(
                    days=1))
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
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)

        return stats

    def get_context_data(self, request):
        context = {}
        user = request.user
        now = timezone.now()
        j_now = jdatetime.datetime.now()
        current_jalali_year = j_now.year
        current_jalali_month = j_now.month

        # اطلاعات پایه
        context['title'] = _("داشبورد جامع سیستم تنخواه و بودجه")
        context['version'] = self.final_version
        # logger.debug(f"Dashboard context initialized: title={context['title']}, version={context['version']}")

        # دسترسی‌ها
        context['can_view_budget_stats'] = True
        context['can_view_tankhah_stats'] = True
        context['can_view_project_status'] = True
        context['can_view_budget_alerts'] = True
        # logger.debug(f"Permissions set: {context['can_view_budget_stats']=}, {context['can_view_tankhah_stats']=}, "
        #              f"{context['can_view_project_status']=}, {context['can_view_budget_alerts']=}")

        # لینک‌های داشبورد
        context['dashboard_links'] = dashboard_links
        # متغیرهای کلیدی برای تمپلیت
        context['active_budget_periods_count'] = BudgetPeriod.objects.filter(is_active=True,
                                                                             is_completed=False).count() or 0
        context['active_budget_allocations_count'] = BudgetAllocation.objects.filter(is_active=True).count() or 0
        context['active_cost_centers_count'] = Project.objects.filter(is_active=True).count() or 0
        context['total_allocated_tankhah'] = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))[
                                                 'total'] or Decimal('0')
        context['total_spent_on_factors'] = \
        Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal(
            '0')
        context['total_unspent_tankhah'] = (context['total_allocated_tankhah'] - context[
            'total_spent_on_factors']) or Decimal('0')

        # آمار بودجه
        if context['can_view_budget_stats']:
            try:
                active_budget_periods = BudgetPeriod.objects.filter(is_active=True, is_completed=False)
                total_allocated = active_budget_periods.aggregate(total=Coalesce(Sum('total_amount'), Decimal('0')))[
                    'total']
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
                # logger.info(
                #     f"Budget stats: total_allocated={total_allocated}, total_consumed={total_consumed}, "
                #     f"remaining={context['remaining_total_budget']}, percentage={context['percentage_consumed_budget']}, "
                #     f"active_budget_periods_count={context['active_budget_periods_count']}"
                # )

                # مصرف بودجه بر اساس دسته
                category_consumption = Factor.objects.filter(status__code='PAID').values('category__name').annotate(
                    total_spent=Sum('amount')
                ).order_by('-total_spent')[:7]
                if not category_consumption:
                    category_consumption = [
                        {'category__name': 'دسته ۱', 'total_spent': 2000000},
                        {'category__name': 'دسته ۲', 'total_spent': 1500000},
                    ]
                context['budget_category_consumption'] = {
                    'labels': json.dumps([item['category__name'] or _("نامشخص") for item in category_consumption],
                                         ensure_ascii=False),
                    'values': json.dumps([float(item['total_spent'] or 0) for item in category_consumption])
                }
                # logger.info(
                #     f"Category consumption: count={len(category_consumption)}, "
                #     f"categories={[item['category__name'] for item in category_consumption]}, "
                #     f"values={[item['total_spent'] for item in category_consumption]}"
                # )

                # بودجه تخصیص‌یافته در مقابل مصرف‌شده
                budget_vs_actual_labels = []
                budget_vs_actual_allocated_data = []
                budget_vs_actual_consumed_data = []
                seen_months = set()
                for i in range(5, -1, -1):
                    month_start_gregorian = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                    month_end_gregorian = (month_start_gregorian + timedelta(days=31)).replace(day=1) - timedelta(
                        days=1)
                    j_month_start = jdatetime.date.fromgregorian(date=month_start_gregorian)
                    month_label = f"{self.get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                    if month_label not in seen_months:
                        seen_months.add(month_label)
                        budget_vs_actual_labels.append(month_label)
                        monthly_allocated = BudgetAllocation.objects.filter(
                            allocation_date__range=(month_start_gregorian, month_end_gregorian)
                        ).aggregate(total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
                        monthly_consumed = BudgetTransaction.objects.filter(
                            transaction_type='CONSUMPTION',
                            timestamp__range=(month_start_gregorian, month_end_gregorian)
                        ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']
                        budget_vs_actual_allocated_data.append(float(monthly_allocated or (1000000 * (6 - i))))
                        budget_vs_actual_consumed_data.append(float(monthly_consumed or (500000 * (6 - i))))
                        # logger.debug(
                        #     f"Monthly budget stats: month={month_label}, allocated={monthly_allocated}, consumed={monthly_consumed}"
                        # )

                context['budget_vs_actual_data'] = {
                    'labels': json.dumps(budget_vs_actual_labels, ensure_ascii=False),
                    'allocated': json.dumps(budget_vs_actual_allocated_data),
                    'consumed': json.dumps(budget_vs_actual_consumed_data)
                }
                # logger.info(f"Budget vs actual: months={budget_vs_actual_labels}, allocated={budget_vs_actual_allocated_data}, consumed={budget_vs_actual_consumed_data}")
            except Exception as e:
                # logger.error(f"خطا در محاسبه آمار بودجه: {e}", exc_info=True)
                context['budget_category_consumption'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['budget_vs_actual_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]),
                                                    'consumed': json.dumps([])}

        # آمار تنخواه
        if context['can_view_tankhah_stats']:
            try:
                active_tankhah_count = Tankhah.objects.filter(
                    status__in=['PENDING', 'APPROVED', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED',
                                'HQ_FIN_PENDING']
                ).count() or 10
                pending_approval_count = Tankhah.objects.filter(
                    status__in=['PENDING', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_FIN_PENDING']
                ).count() or 3
                rejected_factors = Factor.objects.filter(status='REJECTED').count() or 2
                context['active_tankhah_count'] = active_tankhah_count
                context['pending_approval_count'] = pending_approval_count
                context['recent_rejected_factors'] = rejected_factors
                # logger.info(
                #     f"Tankhah stats: active_tankhah_count={active_tankhah_count}, "
                #     f"pending_approval_count={pending_approval_count}, rejected_factors={rejected_factors}"
                # )

                current_jalali_month_start = jdatetime.date(current_jalali_year, current_jalali_month, 1)
                days_in_month = jdatetime.j_days_in_month[current_jalali_month - 1]
                current_jalali_month_end = jdatetime.date(current_jalali_year, current_jalali_month, days_in_month)
                start_gregorian = current_jalali_month_start.togregorian()
                end_gregorian = current_jalali_month_end.togregorian()

                current_month_total_amount = Factor.objects.filter(
                    status__code='PAID',
                    date__range=(start_gregorian, end_gregorian)
                ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('5000000')
                context['current_month_total_amount'] = current_month_total_amount
                # logger.info(
                #     f"Current month factors: start={start_gregorian}, end={end_gregorian}, "
                #     f"total_amount={current_month_total_amount}"
                # )

                monthly_paid_factors = Factor.objects.filter(
                    status__code='PAID',
                    date__gte=(now - timedelta(days=180))
                ).annotate(month=TruncMonth('date')).values('month').annotate(
                    total_amount=Sum('amount')
                ).order_by('month')

                monthly_labels = []
                monthly_values = []
                seen_months = set()
                for entry in monthly_paid_factors:
                    j_month_date = jdatetime.date.fromgregorian(date=entry['month'])
                    month_label = f"{self.get_jalali_month_name(j_month_date.month)} {j_month_date.year}"
                    if month_label not in seen_months:
                        seen_months.add(month_label)
                        monthly_labels.append(month_label)
                        monthly_values.append(float(entry['total_amount'] or 0))
                        # logger.debug(f"Monthly factor: month={month_label}, total={entry['total_amount']}")
                if not monthly_labels:
                    for i in range(5, -1, -1):
                        j_date = j_now - jdatetime.timedelta(days=i * 30)
                        month_label = f"{self.get_jalali_month_name(j_date.month)} {j_date.year}"
                        if month_label not in seen_months:
                            seen_months.add(month_label)
                            monthly_labels.append(month_label)
                    monthly_values = [1000000 * (i + 1) for i in range(len(monthly_labels))]
                    # logger.debug("Using fallback monthly factor data")

                context['monthly_report_data'] = {
                    'labels': json.dumps(monthly_labels, ensure_ascii=False),
                    'values': json.dumps(monthly_values)
                }
                # logger.info(f"Monthly report: labels={monthly_labels}, values={monthly_values}")

                quarterly_paid_factors = Factor.objects.filter(
                    status__code='PAID',
                    date__gte=(now - timedelta(days=365))
                ).annotate(quarter_date=TruncQuarter('date')).values('quarter_date').annotate(
                    total_amount=Sum('amount')
                ).order_by('quarter_date')

                quarterly_labels = []
                quarterly_values = []
                for entry in quarterly_paid_factors:
                    j_quarter_date = jdatetime.date.fromgregorian(date=entry['quarter_date'])
                    quarter_num = (j_quarter_date.month - 1) // 3 + 1
                    quarter_label = f"فصل {quarter_num} {j_quarter_date.year}"
                    quarterly_labels.append(quarter_label)
                    quarterly_values.append(float(entry['total_amount'] or 0))
                    # logger.debug(f"Quarterly factor: quarter={quarter_label}, total={entry['total_amount']}")
                if not quarterly_labels:
                    quarterly_labels = [f"فصل {i} {current_jalali_year}" for i in range(1, 5)]
                    quarterly_values = [3000000 * i for i in range(1, 5)]
                    # logger.debug("Using fallback quarterly factor data")

                context['quarterly_report_data'] = {
                    'labels': json.dumps(quarterly_labels, ensure_ascii=False),
                    'values': json.dumps(quarterly_values)
                }
                # logger.info(f"Quarterly report: labels={quarterly_labels}, values={quarterly_values}")
            except Exception as e:
                # logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)
                context['monthly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['quarterly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}
            # وضعیت پروژه‌ها
            # وضعیت پروژه‌ها
            if context['can_view_project_status']:
                try:
                    projects_status = []
                    # اصلاح کوئری: استفاده از budget_allocations به جای project_allocations
                    active_projects = Project.objects.filter(
                        is_active=True
                    ).annotate(
                        total_budget=Coalesce(Sum('budget_allocations__allocated_amount'), Decimal('0'))
                    ).filter(
                        total_budget__gt=0
                    ).order_by('-start_date')[:5]
                    # logger.debug(f"Active projects count: {active_projects.count()}")
                    for project in active_projects:
                        allocated = self.get_project_total_budget(project)
                        consumed = self.get_project_used_budget(project)
                        remaining = self.get_project_remaining_budget(project)
                        percentage_consumed = (consumed / allocated * 100) if allocated > 0 else 0
                        projects_status.append({
                            'name': project.name or "پروژه بدون نام",
                            'allocated': allocated,
                            'consumed': consumed,
                            'remaining': remaining,
                            'percentage_consumed': percentage_consumed
                        })

                        # ارسال اعلان برای بودجه کم
                        if allocated > 0 and remaining <= calculate_threshold_amount(allocated, Decimal('10')):
                            try:
                                recipients = project.organizations.first().users.all() if project.organizations.exists() else []
                                if recipients:
                                    # ارسال اعلان
                                    send_notification(
                                        sender=request.user,
                                        posts=NotificationRule.objects.filter(
                                            entity_type='FACTOR',
                                            action='APPROVED',
                                            is_active=True
                                        ).first().recipients.all() if NotificationRule.objects.filter(
                                            entity_type='FACTOR',
                                            action='APPROVED',
                                            is_active=True
                                        ).exists() else [],
                                        verb='APPROVED',
                                        description=f"بودجه پروژه {project.name} به آستانه هشدار (10٪) رسیده است.",
                                        # target=factor,
                                        entity_type='FACTOR',
                                        priority='HIGH'
                                    )
                                else:
                                    logger.warning(f"No recipients found for project {project.id} notification")
                            except Exception as e:
                                logger.error(f"خطا در ارسال اعلان برای پروژه {project.id}: {e}", exc_info=True)

                    if not projects_status:
                        projects_status = [
                            {'name': 'پروژه نمونه', 'allocated': Decimal('1000000'), 'consumed': Decimal('400000'),
                             'remaining': Decimal('600000'), 'percentage_consumed': 40.0}
                        ]
                        # logger.debug("Using fallback project status data")
                    context['project_budget_status'] = projects_status

                    # داده‌های چارت پروژه‌ها
                    context['project_chart_data'] = {
                        'labels': json.dumps([project['name'] for project in projects_status], ensure_ascii=False),
                        'allocated': json.dumps([float(project['allocated']) for project in projects_status]),
                        'consumed': json.dumps([float(project['consumed']) for project in projects_status]),
                        'remaining': json.dumps([float(project['remaining']) for project in projects_status])
                    }
                    logger.info(
                        f"Project chart data: labels={[project['name'] for project in projects_status]}, "
                        f"allocated={[project['allocated'] for project in projects_status]}, "
                        f"consumed={[project['consumed'] for project in projects_status]}, "
                        f"remaining={[project['remaining'] for project in projects_status]}"
                    )
                except Exception as e:
                    # logger.error(f"خطا در محاسبه وضعیت پروژه‌ها: {e}", exc_info=True)
                    context['project_budget_status'] = []
                    context['project_chart_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]),
                                                     'consumed': json.dumps([]), 'remaining': json.dumps([])}

        # هشدارهای بودجه
        if context['can_view_budget_alerts']:
            try:
                budget_period_ct = ContentType.objects.get_for_model(BudgetPeriod)
                budget_allocation_ct = ContentType.objects.get_for_model(BudgetAllocation)
                recent_warnings = NotificationRule.objects.filter(
                    Q(target_content_type=budget_period_ct) | Q(target_content_type=budget_allocation_ct),
                    level__in=['warning', 'error', 'locked']
                ).select_related('recipient').prefetch_related('actor', 'target').order_by('-timestamp')[:5]

                budget_warnings_transformed = []
                for notif in recent_warnings:
                    target_obj_display = str(notif.target) if notif.target else _("نامشخص")
                    actor_username = getattr(notif.actor, 'username', str(notif.actor))
                    budget_warnings_transformed.append({
                        'details': f"{notif.verb}: {target_obj_display} - {notif.description or ''}",
                        'timestamp': notif.timestamp,
                        'created_by': {'username': actor_username}
                    })
                    # logger.debug(f"Budget warning: details={notif.verb}, target={target_obj_display}, timestamp={notif.timestamp}")
                if not budget_warnings_transformed:
                    budget_warnings_transformed = [
                        {'details': 'هشدار نمونه: بودجه کم است', 'timestamp': now, 'created_by': {'username': 'سیستم'}}
                    ]
                    # logger.debug("Using fallback budget warnings")
                context['recent_budget_warnings'] = budget_warnings_transformed
                # logger.info(f"Budget warnings count: {len(budget_warnings_transformed)}")
            except Exception as e:
                # logger.error(f"خطا در محاسبه هشدارهای بودجه: {e}", exc_info=True)
                context['recent_budget_warnings'] = []

        # گرفتن اعلان‌های خوانده‌نشده کاربر
        context['notifications'] = NotificationRule.objects.filter(
            recipient=request.user, unread=True
        )[:5]  # محدود به 5 اعلان
        context['unread_count'] = NotificationRule.objects.filter(
            recipient=request.user, unread=True
        ).count()

        # فعالیت‌های اخیر
        try:
            context['recent_activities'] = ApprovalLog.objects.select_related('user', 'tankhah', 'factor',
                                                                              'stage').order_by('-timestamp')[:7]
            # logger.info(f"Recent activities count: {context['recent_activities'].count()}")
            if not context['recent_activities']:
                context['recent_activities'] = [
                    {
                        'tankhah': {'number': 'T001'},
                        'get_action_display': lambda: 'تأیید',
                        'user': {'username': 'کاربر نمونه'},
                        'timestamp': now,
                        'comment': 'تأیید نمونه'
                    }
                ]
                # logger.debug("Using fallback recent activities")
        except Exception as e:
            # logger.error(f"خطا در محاسبه فعالیت‌های اخیر: {e}", exc_info=True)
            context['recent_activities'] = []

        # logger.info(f"Final context: {context.keys()}")
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request)
        # logger.info("Rendering dashboard template")
        return render(request, self.template_name, context)

class SimpleChartView(LoginRequiredMixin, View):
    template_name = 'core/simple_chart.html'
    login_url = reverse_lazy('accounts:login')

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


class DashboardView(LoginRequiredMixin, View):
    template_name = 'core/dashboard.html'
    login_url = reverse_lazy('accounts:login')
    final_version = FinalVersion.calculate_final_version()  # فرض می‌کنیم FinalVersion تعریف شده است

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
        stats = {
            # فیلتر بر اساس status__code__in
            'active_tankhah_count': Tankhah.objects.filter(status__code__in=active_tankhah_status_codes).count(),
            'pending_tankhah_count': Tankhah.objects.filter(status__code__in=pending_tankhah_status_codes).count(),
            # فیلتر بر اساس status__code
            'rejected_factors_count': Factor.objects.filter(status__code='REJECT').count(),
            'total_allocated_tankhah': Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'],
            'total_spent_factors':
                Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))[
                    'total'],
        }
        try:
            # آمار پایه
            stats.update({
                'active_tankhah_count': Tankhah.objects.filter(
                    status__code=['DRAFT','PENDING_APPROVAL' 'APPROVED_INTERMEDIATE', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED', 'HQ_FIN_PENDING']
                ).count(),
                'pending_tankhah_count': Tankhah.objects.filter(
                    status__code=['PENDING_APPROVAL', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_FIN_PENDING']
                ).count(),
                'rejected_factors_count': Factor.objects.filter(
                    status__code='REJECTED',
                    date__gte=now - timedelta(days=90)
                ).count(),
                'total_allocated_tankhah': Tankhah.objects.aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
                'total_spent_factors': Factor.objects.filter(status__code='PAID').aggregate(
                    total=Coalesce(Sum('amount'), Decimal('0'))
                )['total'],
            })

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
        except Exception as e:
            logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)

        return stats

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

        # دسترسی‌ها
        context['can_view_budget_stats'] = True
        context['can_view_tankhah_stats'] = True
        context['can_view_project_status'] = True
        context['can_view_budget_alerts'] = True

        # لینک‌های داشبورد
        context['dashboard_links'] = dashboard_links

        # متغیرهای کلیدی برای تمپلیت
        context['active_budget_periods_count'] = BudgetPeriod.objects.filter(is_active=True, is_completed=False).count() or 0
        context['active_budget_allocations_count'] = BudgetAllocation.objects.filter(is_active=True).count() or 0
        context['active_cost_centers_count'] = Project.objects.filter(is_active=True).count() or 0
        context['total_allocated_tankhah'] = Tankhah.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_spent_on_factors'] = Factor.objects.filter(status__code='PAID').aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total'] or Decimal('0')
        context['total_unspent_tankhah'] = (context['total_allocated_tankhah'] - context['total_spent_on_factors']) or Decimal('0')

        # آمار بودجه
        if context['can_view_budget_stats']:
            try:
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
                category_consumption = Factor.objects.filter(status__code='PAID').values('category__name').annotate(
                    total_spent=Sum('amount')
                ).order_by('-total_spent')[:7] or [{'category__name': 'دسته نمونه', 'total_spent': 1}]
                if not category_consumption:
                    category_consumption = [
                        {'category__name': 'دسته ۱', 'total_spent': 2000000},
                        {'category__name': 'دسته ۲', 'total_spent': 1500000},
                    ]
                context['budget_category_consumption'] = {
                    'labels': json.dumps([item['category__name'] or _("نامشخص") for item in category_consumption], ensure_ascii=False),
                    'values': json.dumps([float(item['total_spent'] or 0) for item in category_consumption])
                }

                # بودجه تخصیص‌یافته در مقابل مصرف‌شده
                budget_vs_actual_labels = []
                budget_vs_actual_allocated_data = []
                budget_vs_actual_consumed_data = []
                seen_months = set()
                for i in range(5, -1, -1):
                    month_start_gregorian = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
                    month_end_gregorian = (month_start_gregorian + timedelta(days=31)).replace(day=1) - timedelta(
                        days=1)
                    j_month_start = jdatetime.date.fromgregorian(date=month_start_gregorian)
                    month_label = f"{self.get_jalali_month_name(j_month_start.month)} {j_month_start.year}"
                    if month_label not in seen_months:
                        seen_months.add(month_label)
                        budget_vs_actual_labels.append(month_label)
                        monthly_allocated = BudgetAllocation.objects.filter(
                            allocation_date__range=(month_start_gregorian, month_end_gregorian)).aggregate(
                            total=Coalesce(Sum('allocated_amount'), Decimal('0')))['total']
                        monthly_consumed = BudgetTransaction.objects.filter(transaction_type='CONSUMPTION',
                                                                            timestamp__range=(month_start_gregorian,
                                                                                              month_end_gregorian)).aggregate(
                            total=Coalesce(Sum('amount'), Decimal('0')))['total']
                        budget_vs_actual_allocated_data.append(float(monthly_allocated or 0))
                        budget_vs_actual_consumed_data.append(float(monthly_consumed or 0))
                context['budget_vs_actual_data'] = {
                    'labels': json.dumps(budget_vs_actual_labels, ensure_ascii=False),
                    'allocated': json.dumps(budget_vs_actual_allocated_data),
                    'consumed': json.dumps(budget_vs_actual_consumed_data)
                }
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار بودجه: {e}", exc_info=True)
                context['budget_stats_error'] = True

                context['budget_category_consumption'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['budget_vs_actual_data'] = {'labels': json.dumps([]), 'allocated': json.dumps([]), 'consumed': json.dumps([])}

        # آمار تنخواه
        if context['can_view_tankhah_stats']:
            try:
                tankhah_stats = self._get_tankhah_stats()
                context.update(tankhah_stats)
            except Exception as e:
                logger.error(f"خطا در محاسبه آمار تنخواه: {e}", exc_info=True)
                context['monthly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}
                context['quarterly_report_data'] = {'labels': json.dumps([]), 'values': json.dumps([])}

        # وضعیت پروژه‌ها
        if context['can_view_project_status']:
            try:
                # PERFORMANCE_FIX: This single, optimized query replaces the loop and multiple queries.
                # It calculates everything needed in one database hit.
                active_projects_with_stats = Project.objects.filter(is_active=True).annotate(
                    # 1. Calculate total allocated budget from active allocations
                    allocated=Coalesce(
                        Sum('allocations__allocated_amount', filter=Q(allocations__is_active=True)),
                        Value(Decimal('0')), output_field=DecimalField()
                    ),
                    # 2. Calculate total consumed budget from PAID factors linked via Tankhah
                    consumed=Coalesce(
                        Sum('tankhah_set__factors__amount', filter=Q(tankhah_set__factors__status__code='PAID')),
                        Value(Decimal('0')), output_field=DecimalField()
                    )
                ).annotate(
                    # 3. Calculate remaining and percentage in the same query
                    remaining=F('allocated') - F('consumed'),
                    percentage_consumed=Case(
                        When(allocated__gt=0, then=(F('consumed') * 100) / F('allocated')),
                        default=Value(Decimal('0')), output_field=DecimalField()
                    )
                ).filter(allocated__gt=0).order_by('-start_date')[:5]

                # Now, we just format the results. No more database queries inside the loop.
                projects_status = []
                for project in active_projects_with_stats:
                    projects_status.append({
                        'name': project.name,
                        'allocated': project.allocated,
                        'consumed': project.consumed,
                        'remaining': project.remaining,
                        'percentage_consumed': project.percentage_consumed
                    })

                    # Your notification logic can remain here
                    if project.allocated > 0 and project.remaining <= calculate_threshold_amount(project.allocated,
                                                                                                 Decimal('10')):
                        # ... (your notification sending logic) ...
                        pass

                # Handling the case with no projects, as in your original code
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
                context['project_status_error'] = True

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
