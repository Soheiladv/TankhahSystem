import json
from datetime import timedelta
from django.utils import timezone

from django.db.models import Sum, Q
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
############################################Main
# core/views.py
from django.views.generic.base import TemplateView

from core.PermissionBase import PermissionBaseView
from core.models import WorkflowStage, Project, Organization, OrganizationType
from tankhah.models import Tankhah, ApprovalLog, Notification, Factor

def pdate(request):
    return render(request, template_name='budgets/pdate.html')



""" داشبورد اصلی سیستم"""
class DashboardView( PermissionBaseView , TemplateView):
    """ داشبورد اصلی سیستم"""
    template_name = 'core/dashboard.html'
    permission_codename = 'core.Dashboard_view'
    # check_organization = True  # فعال کردن چک سازمان (اگه نیاز داری فعال کن)

    extra_context = {
        'title': _('داشبورد مدیریت تنخواه'),
        'version': '1.2.3',  # نسخه نرم‌افزار
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

                # {'name': _('تخصیص بودجه به پروژه ها و زیرپروژه'), 'url': 'budget_allocation_view',
                #  'permission': 'core.Project_Budget_allocation_Head_Office',
                #  'icon': 'fas fa-plus'},

                # {'name': _('تخصیص بودجه به شعبات'), 'url': 'budgetallocation_create',
                #  'permission': 'budgets.budgetallocation_add',
                #  'icon': 'fas fa-plus'},

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
                {'name': _('فهرست فاکتورها'), 'url': 'factor_list', 'permission': 'tankhah.a_factor_view', 'icon': 'fas fa-file-invoice'},
                {'name': _('ایجاد فاکتور'), 'url': 'factor_create', 'permission': 'tankhah.a_factor_add', 'icon': 'fas fa-plus'},
            ],
            'عنوان پروژه': [
                {'name': _('فهرست پروژه‌ها'), 'url': 'project_list', 'permission': 'core.Project_view',
                 'icon': 'fas fa-project-diagram'},
                {'name': _('ایجاد پروژه'), 'url': 'project_create', 'permission': 'core.Project_add', 'icon': 'fas fa-plus'},
                {'name': _('ایجاد زیرپروژه'), 'url': 'subproject_create', 'permission': 'core.Project_add', 'icon': 'fas fa-plus'},
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
        context['version'] = '1.2.3'

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

        #تعداد فاکتورهای ردشده
        context['rejected_factors']  = Factor.objects.filter(status='REJECTED').count()

        # فعالیت‌های اخیر (از ApprovalLog)
        context['recent_activities'] = ApprovalLog.objects.filter(
            Q(tankhah__isnull=False) | Q(factor__isnull=False)
        ).order_by('-timestamp')[:5]

        # اعلان‌ها
        context['notifications'] = Notification.objects.filter(user=user, is_read=False).order_by('-created_at')[:5]

        # # آمار کلی تنخواه و فاکتورها (با دسترسی)
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


############################################

# class Tanbakhsystem_DashboardView(LoginRequiredMixin, TemplateView):
#     template_name = "index1.html"  # مسیر تمپلیت
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#         # تعریف کارت‌ها
#         cards = [
#             # مدیریت هزینه‌ها (Tanbakh)
#             {
#                 "title": _("مدیریت هزینه‌ها"),
#                 "icon": "fas fa-cog",
#                 "items": [
#                     {"label": _("لیست تنخواه‌ها"), "url": "tanbakh_list", "icon": "fas fa-list", "color": "info",
#                      "perm": "tanbakh.Tanbakh_view"},
#                     {"label": _("ایجاد تنخواه"), "url": "tanbakh_create", "icon": "fas fa-plus", "color": "success",
#                      "perm": "tanbakh.Tanbakh_add"},
#                     {"label": _("لیست فاکتورها"), "url": "factor_list", "icon": "fas fa-file-invoice", "color": "info",
#                      "perm": "tanbakh.Factor_view"},
#                     {"label": _("ایجاد فاکتور"), "url": "factor_create", "icon": "fas fa-plus", "color": "success",
#                      "perm": "tanbakh.Factor_add"},
#                 ],
#             },
#             {
#                 "title": _("مدیریت سازمان"),
#                 "icon": "fas fa-cog",
#                 "items": [
#                     {"label": _("داشبورد تنخواه گردان"), "url": "dashboard_flows", "icon": "fas fa-list", "color": "info",
#                      "perm": "tanbakh.Tanbakh_view"},
#                     {"label": _("ایجاد تنخواه"), "url": "tanbakh_create", "icon": "fas fa-plus", "color": "success",
#                      "perm": "tanbakh.Tanbakh_add"},
#                     {"label": _("لیست فاکتورها"), "url": "factor_list", "icon": "fas fa-file-invoice", "color": "info",
#                      "perm": "tanbakh.Factor_view"},
#                     {"label": _("ایجاد فاکتور"), "url": "factor_create", "icon": "fas fa-plus", "color": "success",
#                      "perm": "tanbakh.Factor_add"},
#                 ],
#             },
#             # عملیات هزینه (Approval)
#             {
#                 "title": _("عملیات هزینه"),
#                 "icon": "fas fa-dollar-sign",
#                 "items": [
#                     {"label": _("لیست تأییدات"), "url": "approval_list", "icon": "fas fa-list", "color": "info",
#                      "perm": "tanbakh.Approval_view"},
#                     {"label": _("ثبت تأیید"), "url": "approval_create", "icon": "fas fa-check", "color": "success",
#                      "perm": "tanbakh.Approval_add"},
#                 ],
#             },
#             # مدیریت کاربران (Accounts)
#             {
#                 "title": _("مدیریت کاربران"),
#                 "icon": "fas fa-users",
#                 "items": [
#                     {"label": _("لیست کاربران"), "url": "accounts:user_list", "icon": "fas fa-list", "color": "info",
#                      "perm": "accounts.view_user"},
#                     {"label": _("افزودن کاربر"), "url": "accounts:user_create", "icon": "fas fa-user-plus",
#                      "color": "success", "perm": "accounts.add_user"},
#                     {"label": _("تغییر رمز عبور"), "url": "accounts:password_change", "icon": "fas fa-key",
#                      "color": "warning", "perm": "accounts.change_user"},
#                 ],
#             },
#             # مدیریت نقش‌ها
#             {
#                 "title": _("مدیریت نقش‌ها"),
#                 "icon": "fas fa-user-tag",
#                 "items": [
#                     {"label": _("لیست نقش‌ها"), "url": "accounts:role_list", "icon": "fas fa-list", "color": "info",
#                      "perm": "accounts.view_role"},
#                     {"label": _("ایجاد نقش جدید"), "url": "accounts:role_create", "icon": "fas fa-plus",
#                      "color": "success", "perm": "accounts.add_role"},
#                 ],
#             },
#             # مدیریت گروه‌ها
#             {
#                 "title": _("مدیریت گروه‌ها"),
#                 "icon": "fas fa-users-cog",
#                 "items": [
#                     {"label": _("لیست گروه‌ها"), "url": "accounts:group_list", "icon": "fas fa-list", "color": "info",
#                      "perm": "auth.view_group"},
#                     {"label": _("ایجاد گروه جدید"), "url": "accounts:group_create", "icon": "fas fa-plus",
#                      "color": "success", "perm": "auth.add_group"},
#                 ],
#             },
#             # پروفایل کاربری
#             {
#                 "title": _("پروفایل کاربری"),
#                 "icon": "fas fa-id-card",
#                 "items": [
#                     {"label": _("ویرایش پروفایل"), "url": "accounts:profile_update", "icon": "fas fa-user-edit",
#                      "color": "primary", "perm": "accounts.change_user"},
#                     {"label": _("حذف پروفایل"), "url": "accounts:profile_delete", "icon": "fas fa-trash",
#                      "color": "danger", "perm": "accounts.delete_user"},
#                 ],
#             },
#             # گزارش‌ها و لاگ‌ها
#             {
#                 "title": _("گزارش‌ها و لاگ‌ها"),
#                 "icon": "fas fa-file-alt",
#                 "items": [
#                     {"label": _("گزارش فعالیت‌ها"), "url": "accounts:audit_log_list", "icon": "fas fa-history",
#                      "color": "secondary", "perm": "accounts.view_auditlog"},
#                 ],
#             },
#             # مدیریت نسخه
#             {
#                 "title": _("مدیریت نسخه"),
#                 "icon": "fas fa-lock",
#                 "items": [
#                     {"label": _("ثبت قفل جدید و نمایش وضعیت"), "url": "accounts:set_time_lock", "icon": "fas fa-lock",
#                      "color": "warning", "perm": "accounts.view_timelock"},
#                     {"label": _("نمایش لیست تنظیمات قفل"), "url": "accounts:timelock_list", "icon": "fas fa-list",
#                      "color": "warning", "perm": "accounts.view_timelock"},
#                     {"label": _("وضعیت قفل"), "url": "accounts:lock_status", "icon": "fas fa-info-circle", "color": "warning",
#                      "perm": "accounts.view_timelock"},
#                     {"label": _("فهرست کاربران فعال سیستم"), "url": "accounts:active_user_list", "icon": "fas fa-users",
#                      "color": "warning", "perm": "accounts.view_user"},
#                 ],
#             },
#         ]
#
#         # فیلتر کردن آیتم‌ها بر اساس پرمیشن‌ها
#         filtered_cards = []
#         for card in cards:
#             filtered_items = [item for item in card["items"] if user.has_perm(item["perm"])]
#             if filtered_items:  # فقط کارت‌هایی که حداقل یک آیتم مجاز دارند
#                 card["items"] = filtered_items
#                 filtered_cards.append(card)
#
#         context["cards"] = filtered_cards
#         return context

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

