from django.urls import path

from reports.ComprehensiveBudgetReportView import ComprehensiveBudgetReportView,APITankhahsForPBAView, APIFactorsForTankhahView, \
    APIOrganizationsForPeriodView
from reports.PaymentOrderReport.PaymentOrderReportView import PaymentOrderReportView

# BudgetItemsForOrgPeriodAPIView,, APITankhahsForProjectView \
#     YourOrgPeriodAllocationsListView, OrganizationAllocationsAPIView, APIOrganizationAllocationsView, \
#     APIBudgetAllocationsForOrgView, APIProjectAllocationsForBAView,
#
from reports.budgets_reports.view_budgets_reports import ProjectBudgetReportView, BudgetWarningReportView
from reports.views import TankhahFinancialReportView, FinancialDashboardView, TankhahDetailView, \
    BudgetAllocationReportView
from reports.views import print_financial_report, send_to_accounting

urlpatterns = [
    path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),
    path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),

    path('reports/print/<int:report_id>/', print_financial_report, name='print-financial-report'),
    path('reports/send/<int:report_id>/', send_to_accounting, name='send-to-accounting'),

    path('tankhah-details/', TankhahDetailView.as_view(), name='tankhah_detail'),

]

urlpatterns += [
    path('project/<int:pk>/budget-report/', ProjectBudgetReportView.as_view(), name='project_budget_report'),
    path('budget/warnings/', BudgetWarningReportView.as_view(), name='budget_warning_report'),

    path('budget-allocation/<int:pk>/report/', BudgetAllocationReportView.as_view(), name='budget_allocation_report'),

    path('comprehensive-budget-drilldown/', ComprehensiveBudgetReportView.as_view(),
         name='comprehensive_budget_report'),

    # path('api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/',   BudgetItemsForOrgPeriodAPIView.as_view(),  # نام ویو API شما
    #      name='api_budget_items_for_org_period'),
    # ... سایر URL های اپلیکیشن reports ...

    # URL فرضی که برای لینک "مشاهده تمام تخصیص‌های این سازمان از این دوره" نیاز دارید
    # شما باید ویوی مربوط به این URL را هم بسازید
    # path('org-period-allocations/<int:period_pk>/<int:org_pk>/',
    #      YourOrgPeriodAllocationsListView.as_view(),  # یک ویوی فرضی، شما باید آن را ایجاد کنید
    #      name='budget_allocations_by_org_period_report'),

    # path('api/period/<int:period_pk>/organization-allocations/',OrganizationAllocationsAPIView.as_view(),name='api_organization_allocations_for_period'),

] #گزارشات بودجه و مراکز هزینه ( بودجه)



urlpatterns += [
    path('comprehensive-budget-drilldown/', ComprehensiveBudgetReportView.as_view(),
         name='comprehensive_budget_report'),

    # API Endpoints for AJAX drill-down
    # path('api/period/<int:period_pk>/organizations/',
    #      APIOrganizationAllocationsView.as_view(),
    #      name='api_organization_allocations_for_period'),
    #
    # path('api/period/<int:period_pk>/org/<int:org_pk>/budget-allocations/',  # سرفصل‌ها
    #      APIBudgetAllocationsForOrgView.as_view(),
    #      name='api_budget_allocations_for_org'),
    #
    # path('api/budget-allocation/<int:ba_pk>/project-allocations/',  # تخصیص‌ها به پروژه
    #      APIProjectAllocationsForBAView.as_view(),
    #      name='api_project_allocations_for_ba'),

    path('api/project-budget-allocation/<int:pba_pk>/tankhahs/',  # تنخواه‌ها
         APITankhahsForPBAView.as_view(),
         name='api_tankhahs_for_pba'),

    # اگر تنخواه مستقیما به پروژه هم لینک است (بدون PBA واسط)
    # path('api/project/<int:project_pk>/tankhahs/',
    #      APITankhahsForProjectView.as_view(),  # ویو جدید
    #      name='api_tankhahs_for_project'),

    path('api/tankhah/<int:tankhah_pk>/factors/',  # فاکتورها
         APIFactorsForTankhahView.as_view(),
         name='api_factors_for_tankhah'),

    # API جدید: برای بارگذاری سازمان‌های یک دوره خاص
    path('api/organizations-for-period/<int:period_pk>/', APIOrganizationsForPeriodView.as_view(), name='api_organizations_for_period'),

    # API فعلی شما برای سرفصل‌ها و پروژه‌ها
    # path('api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/', BudgetItemsForOrgPeriodAPIView.as_view(), name='api_budget_items_for_org_period'),

    # API برای تنخواه‌ها
    path('api/tankhahs-for-pba/<int:pba_pk>/', APITankhahsForPBAView.as_view(), name='api_tankhahs_for_pba'),

    # API برای فاکتورها
    path('api/factors-for-tankhah/<int:tankhah_pk>/', APIFactorsForTankhahView.as_view(), name='api_factors_for_tankhah'),

    #این ویو گزارشات جامع از PaymentOrder با جزئیات بودجه، تنخواه، فاکتور، و ردیف‌های فاکتور را نمایش می‌دهد.

    path('report/paymentorderreport/', PaymentOrderReportView.as_view(), name='payment_order_report'),

]