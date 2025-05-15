import json
import logging
from datetime import timedelta
from django.utils import timezone

from django.db.models import Sum, Q
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
############################################Main
# core/views.py
from django.views.generic.base import TemplateView
from core.PermissionBase import PermissionBaseView
from core.models import WorkflowStage, Project
from tankhah.models import Tankhah, ApprovalLog, Factor
from version_tracker.models import FinalVersion, AppVersion

def pdate(request):
    return render(request, template_name='budgets/pdate.html')


def home_view(request, *args, **kwargs):
    final_version = FinalVersion.calculate_final_version()
    latest_version = AppVersion.objects.order_by('-release_date').first()
    return render(request, 'index.html', {'latest_version': latest_version, 'final_version': final_version})

""" داشبورد اصلی سیستم"""
class DashboardView( PermissionBaseView , TemplateView):
    """ داشبورد اصلی سیستم"""
    template_name = 'core/dashboard.html'
    permission_codename = 'core.Dashboard_view'
    # check_organization = True  # فعال کردن چک سازمان (اگه نیاز داری فعال کن)
    final_version = FinalVersion.calculate_final_version()
    # logging.info(f' final_version is {final_version} ')
    extra_context = {
        'title': _('داشبورد مدیریت تنخواه'),
        'version': final_version,  # نسخه نرم‌افزار
        'dashboard_links': {
            'روند تنخواه': [
                {'name': _('روند تنخواه'), 'url': 'dashboard_flows',  'icon': 'fas fa-link'}, #'permission': 'Dashboard__view',
                {'name': _('BI گزارشات'), 'url': 'financialDashboardView', 'icon': 'fas fa-chart-bar'},
                {'name': _('گزارش جزئیات تنخواه'), 'url': 'tankhah_detail', 'icon': 'fas fa-chart-bar'},
                {'name': _('گزارش لحظه ای از بودجه بندی '), 'url': 'budgetrealtimeReportView', 'icon': 'fas fa-chart-bar'},
            ],
            'بودجه سازمان': [
                {'name': _('فهرست  بودجه کلان'), 'url': 'budgetperiod_list', 'permission': 'budgets.budgetperiod_view',
                 'icon': 'fas fa-project-diagram'},
                # {'name': _('ثبت بودجه کلان'), 'url': 'budgetperiod_create', 'permission': 'budgets.budgetperiod_add',
                #  'icon': 'fas fa-project-diagram'},

                {'name': _('داشبورد مدریتی بودجه '), 'url': 'budgets_dashboard',       'icon': 'fas fa-project-diagram'},
                {'name': _('فهرست بودجه شعبات'), 'url': 'budgetallocation_list', 'permission': 'budgets.budgetallocation_view',
                 'icon': 'fas fa-plus'},

                {'name': _(' گزارش هشدارهای بودجه '), 'url': 'budget_warning_report',
                 # 'permission': 'core.budget_warning_report',
                 'icon': 'fas fa-plus'},

                {'name': _('  (برگشت بودجه )فهرست بودجه در مراکز هزینه '), 'url': 'budgetallocation_list',
                 'permission': 'budgets.view_budgetallocation',
                 'icon': 'fas fa-plus'},
                {'name': _('انتقال بودجه'), 'url': 'budget_transfer',
                 # 'permission': 'budgets.view_budgetallocation',
                 'icon': 'fas fa-plus'},

                {'name': _('فهرست تغییر در بودجه'), 'url': 'budgettransaction_list',
                 'permission': 'BudgetTransaction_view',
                 'icon': 'fas fa-plus'},

                {'name': _('دستور پرداخت'), 'url': 'paymentorder_list',
                 'permission': 'budgets.BudgetTransaction_view',
                 'icon': 'fas fa-plus'},

                {'name': _('فهرست دریافت‌کننده'), 'url': 'payee_list',
                 'permission': 'budgets.BudgetTransaction_view',
                 'icon': 'fas fa-plus'},

                {'name': _('فهرست تعریف پویا نوع تراکنش‌ها'), 'url': 'transactiontype_list',
                 'permission': 'budgets.BudgetTransaction_view',
                 'icon': 'fas fa-plus'},
            ],
            'تنخواه': [
                {'name': _('فهرست تنخواه'), 'url': 'tankhah_list', 'permission': 'tankhah.Tankhah_view', 'icon': 'fas fa-project-diagram'},
                {'name': _('ایجاد تنخواه'), 'url': 'tankhah_create', 'permission': 'tankhah.Tankhah_add', 'icon': 'fas fa-plus'},
            ],
            'فاکتورها': [
                {'name': _('فهرست فاکتورها'), 'url': 'factor_list', 'permission': 'tankhah.factor_view', 'icon': 'fas fa-file-invoice'},
                # {'name': _('ایجاد فاکتور'), 'url': 'factor_create', 'permission': 'tankhah.factor_add', 'icon': 'fas fa-plus'},
                {'name': _('ایجاد فاکتور'), 'url': 'Nfactor_create', 'permission': 'tankhah.factor_add', 'icon': 'fas fa-plus'},
             ],
            'عنوان مرکز هزینه (پروژه)': [
                {'name': _('فهرست مرکز هزینه (پروژه)'), 'url': 'project_list', 'permission': 'core.Project_view',
                 'icon': 'fas fa-project-diagram'},
                {'name': _('ایجاد مرکز هزینه (پروژه)'), 'url': 'project_create', 'permission': 'core.Project_add', 'icon': 'fas fa-plus'},
                {'name': _('ایجاد زیر مرکز هزینه (پروژه)'), 'url': 'subproject_create', 'permission': 'core.Project_add', 'icon': 'fas fa-plus'},
            ],
            'گردش کار': [
                {'name': _('فهرست گردش کار'), 'url': 'workflow_stage_list', 'permission': 'core.WorkflowStage_view',
                 'icon': 'fas fa-exchange-alt'},
                {'name': _('ثبت گردش کار'), 'url': 'workflow_stage_create', 'permission': 'core.WorkflowStage_add',
                 'icon': 'fas fa-plus'},
            ],
            'پست و سلسله مراتب': [
                {'name': _('فهرست پست‌ها'), 'url': 'post_list', 'permission': 'core.Post_view', 'icon': 'fas fa-sitemap'},
                {'name': _('ایجاد پست'), 'url': 'post_create', 'permission': 'core.Post_add', 'icon': 'fas fa-plus'},
            ],
            'سازمـان': [
                {'name': _('فهرست سازمان‌ها'), 'url': 'organization_list', 'permission': 'core.Organization_view',
                 'icon': 'fas fa-building'},
                {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'permission': 'core.Organization_add',
                 'icon': 'fas fa-plus'},
            ],
            'پست همکار در سازمان': [
                {'name': _('فهرست اتصالات کاربر به پست'), 'url': 'userpost_list', 'permission': 'core.UserPost_view', 'icon': 'fas fa-users'},
                {'name': _('ایجاد اتصال'), 'url': 'userpost_create', 'permission': 'core.UserPost_add', 'icon': 'fas fa-plus'},
            ],
            'تاریخچه پست‌ها': [
                {'name': _('فهرست تاریخچه پست‌ها'), 'url': 'posthistory_list', 'permission': 'core.view_posthistory', 'icon': 'fas fa-history'},
                # {'name': _('ثبت تاریخچه'), 'url': 'posthistory_create', 'permission': 'add_posthistory', 'icon': 'fas fa-plus'},
            ],

            'دیگر لینک‌ها': [
                {'name': _('همه لینک‌ها'), 'url': 'all_links', 'icon': 'fas fa-link'},
                {'name': _('مدیریت کاربران'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-link'},
                {'name': _('نسخه ها'), 'url': 'version_index_view', 'icon': 'fas fa-link'},
                {'name': _('P Test '), 'url': 'pdate', 'icon': 'fas fa-link'},
                {'name': _('راهنمای بودجه بندی'), 'url': 'budget_Help', 'icon': 'fas fa-link'},
                {'name': _('دسته بندی نوع هزینه کرد'), 'url': 'itemcategory_list', 'icon': 'fas fa-link'},
            ],
        }
    }


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user

        # فیلتر کردن لینک‌ها بر اساس مجوز کاربر
        filtered_links = {}
        for category, links in self.extra_context['dashboard_links'].items():
            permitted_links = [
                link for link in links
                if not link.get('permission') or user.has_perm(link['permission'])
            ]
            if permitted_links:
                filtered_links[category] = permitted_links
        context['dashboard_links'] = filtered_links

        # اطلاعات پایه
        context['user'] = user
        context['title'] = _('داشبورد مدیریت تنخواه')
        final_version = FinalVersion.calculate_final_version()
        context['version'] = final_version  # '1.2.3'

        # تعداد تنخواه فعال
        context['active_tankhah_count'] = Tankhah.objects.filter(
            status__in=['PENDING', 'APPROVED', 'SENT_TO_HQ', 'HQ_OPS_PENDING', 'HQ_OPS_APPROVED', 'HQ_FIN_PENDING'],
            is_archived=False
        ).count()

        # هزینه ماه جاری
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        context['current_month_total_amount'] = Tankhah.objects.filter(
            created_at__gte=current_month,
            status='PAID'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # درخواست‌های منتظر تأیید
        context['pending_approval_count'] = Tankhah.objects.filter(
            status='PENDING',
            approved_by=user
        ).count()

        # پروژه‌های در دست اقدام و آرشیو شده
        context['active_projects_count'] = Project.objects.filter(is_active=True).count()
        context['archived_projects_count'] = Project.objects.filter(is_active=False).count()

        # تنخواه‌های آرشیو شده
        context['archived_tankhah_count'] = Tankhah.objects.filter(is_archived=True).count()

        # گزارش‌های ماهانه (12 ماه)
        monthly_data = self.get_monthly_report_data()
        context['monthly_report_data'] = {'labels': json.dumps(monthly_data['labels']),
                                          'values': json.dumps(monthly_data['values'])}

        # گزارش‌های فصلی
        quarterly_data = self.get_quarterly_report_data()
        context['quarterly_report_data'] = {'labels': json.dumps(quarterly_data['labels']),
                                            'values': json.dumps(quarterly_data['values'])}

        # تعداد فاکتورهای ردشده
        context['rejected_factors'] = Factor.objects.filter(status='REJECTED').count()

        # فعالیت‌های اخیر (از ApprovalLog)
        context['recent_activities'] = ApprovalLog.objects.filter(
            Q(tankhah__isnull=False) | Q(factor__isnull=False)
        ).order_by('-timestamp')[:5]

        # اعلان‌ها
        # context['notifications'] = Notification.objects.filter(recipient=user, unread=False).order_by('-created_at')[:5]

        # آمار کلی تنخواه و فاکتورها (با دسترسی)
        if user.has_perm('core.Dashboard_Stats_view'):
            tankhah_stats = self.get_tankhah_statistics()
            context.update(tankhah_stats)
        else:
            context['stats_permission_denied'] = True

        return context

    def get_monthly_report_data(self):
        now = timezone.now()
        data = {'labels': [], 'values': []}
        for i in range(11, -1, -1):
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = month_start + timedelta(days=30)
            total = Tankhah.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end,
                status='PAID'
            ).aggregate(total=Sum('amount'))['total'] or 0
            data['labels'].append(month_start.strftime('%B'))
            data['values'].append(float(total))
        return data

    def get_quarterly_report_data(self):
        now = timezone.now()
        data = {'labels': [], 'values': []}
        for i in range(3, -1, -1):
            quarter_start = now - timedelta(days=90 * i)
            quarter_end = quarter_start + timedelta(days=90)
            total = Tankhah.objects.filter(
                created_at__gte=quarter_start,
                created_at__lt=quarter_end,
                status='PAID'
            ).aggregate(total=Sum('amount'))['total'] or 0
            data['labels'].append(f"فصل {i + 1} {quarter_start.year}")
            data['values'].append(float(total))
        return data

    def get_tankhah_statistics(self):
        stats = {
            'total_allocated': Tankhah.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'total_spent': Factor.objects.filter(status='APPROVED').aggregate(total=Sum('amount'))['total'] or 0,
            'total_factors_amount': Factor.objects.aggregate(total=Sum('amount'))['total'] or 0,
            'tankhah_factors': {},
            'branch_stats': {}
        }
        stats['total_unspent'] = stats['total_allocated'] - stats['total_spent']

        # جمع فاکتورها برای هر تنخواه
        tankhahs = Tankhah.objects.all()
        for tankhah in tankhahs:
            factors_total = tankhah.factors.aggregate(total=Sum('amount'))['total'] or 0
            stats['tankhah_factors'][tankhah.number] = factors_total

        # آمار بر اساس شعبه
        # branches = Organization.objects.filter(org_type__in=['COMPLEX', 'HOTEL', 'PROVINCE', 'RENTAL'])
        # branches = OrganizationType.objects.filter(org_type__in=['COMPLEX', 'HOTEL', 'PROVINCE', 'RENTAL'])
        # for branch in branches:
        #     branch_tankhahs = Tankhah.objects.filter(organization=branch)
        #     stats['branch_stats'][branch.org_type] = {
        #         'allocated': branch_tankhahs.aggregate(total=Sum('amount'))['total'] or 0,
        #         'spent': Factor.objects.filter(tankhah__organization=branch, status='APPROVED').aggregate(
        #             total=Sum('amount'))['total'] or 0
        #     }
        #
        # branches = OrganizationType.objects.filter(is_budget_allocatable=True).values_list('org_type', flat=True)
        # for branch in branches:
        #     # logging.info(f'branch.org_type is {branch.org_type}')
        #     branch_tankhahs = Tankhah.objects.filter(organization=branch)
        #     stats['branch_stats'][branch.org_type] = {
        #         'allocated': branch_tankhahs.aggregate(total=Sum('amount'))['total'] or 0,
        #         'spent': Factor.objects.filter(tankhah__organization=branch, status='APPROVED').aggregate(
        #             total=Sum('amount'))['total'] or 0
        #     }

        return stats

class TanbakhWorkflowView(TemplateView): #help
    template_name =  'help/run_tankhahSystem.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جریان کار تنخواه‌گردانی')
        context['stages'] = WorkflowStage.objects.all().order_by('order')
        return context

def about(request):
    return render(request, template_name='about.html')

class GuideView(TemplateView):
    template_name = 'help/guide.html'
# class Tanbakhsystem_DashboardView(LoginRequiredMixin, TemplateView):
#     template_name = 'index.html'  # استفاده از index.html شما
#     extra_context = {'title': _('منوی مدیریت سیستم')}
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#
#         # تعریف لینک‌ها در دسته‌بندی‌های مختلف
#         context['cards'] = {
#             'مدیریت هزینه‌ها': [
#                 {'url': 'tanbakh_list', 'label': _('لیست تنخواه‌ها'), 'perm': 'tanbakh.Tanbakh_view'},
#                 {'url': 'tanbakh_create', 'label': _('ایجاد تنخواه'), 'perm': 'tanbakh.Tanbakh_add'},
#                 {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'perm': 'tanbakh.Factor_view'},
#                 {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'perm': 'tanbakh.Factor_add'},
#             ],
#
#             'عملیات هزینه': [
#                 {'url': 'approval_list', 'label': _('لیست تأییدات'), 'perm': 'tanbakh.Approval_view'},
#                 {'url': 'approval_create', 'label': _('ثبت تأیید'), 'perm': 'tanbakh.Approval_add'},
#             ],
#
#         }
#
#         # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
#         for card_title, links in context['cards'].items():
#             context['cards'][card_title] = [link for link in links if user.has_perm(link['perm'])] if links else []
#
#         return context

