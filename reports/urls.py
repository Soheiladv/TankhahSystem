from django.urls import path, include
from reports.ComprehensiveBudgetReportView import (
    ComprehensiveBudgetReportView,
    APIOrganizationsForPeriodView,
    BudgetItemsForOrgPeriodAPIView,
    APIFactorsForTankhahView,
    APITankhahsForAllocationView,
    OrganizationAllocationsAPIView,
)
from reports.PaymentOrderReport.PaymentOrderReportView import PaymentOrderReportView
from reports.budgets_reports.view_budgets_reports import BudgetWarningReportView
from reports.views import TankhahFinancialReportView, FinancialDashboardView, TankhahDetailView, \
    BudgetAllocationReportView
from reports.views_enhanced import BudgetAllocationReportEnhancedView
from reports.views import print_financial_report, send_to_accounting

urlpatterns = [
    # گزارشات مالی و داشبورد
    path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),
    path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),
    path('reports/print/<int:report_id>/', print_financial_report, name='print-financial-report'),
    path('reports/send/<int:report_id>/', send_to_accounting, name='send-to-accounting'),

    # جزئیات تنخواه
    # path('tankhah/<int:pk>/detail/', TankhahDetailView.as_view(), name='tankhah_detail'),

    # گزارشات بودجه
    path('budget/warnings/', BudgetWarningReportView.as_view(), name='budget_warning_report'),
    path('budget-allocation/<int:pk>/report/', BudgetAllocationReportView.as_view(), name='budget_allocation_report'),
    path('budget-allocation/<int:pk>/report-enhanced/', BudgetAllocationReportEnhancedView.as_view(), name='budget_allocation_report_enhanced'),

    # APIها
    path('api/period/<int:period_pk>/organization-allocations/', OrganizationAllocationsAPIView.as_view(),
         name='api_organization_allocations_for_period'),
    path('api/factors-for-tankhah/<int:tankhah_pk>/', APIFactorsForTankhahView.as_view(),
         name='api_factors_for_tankhah'),
    path('api/tankhahs-for-allocation/<int:alloc_pk>/', APITankhahsForAllocationView.as_view(),
         name='api_tankhahs_for_allocation'),
    path('reports/api/organizations-for-period/<int:period_pk>/', APIOrganizationsForPeriodView.as_view(),
         name='api_organizations_for_period'),
    path('reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/',
         BudgetItemsForOrgPeriodAPIView.as_view(), name='api_budget_items_for_org_period'),
    path('reports/comprehensive-budget/', ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report'),
    path('report/paymentorderreport/', PaymentOrderReportView.as_view(), name='payment_order_report'),
]
from django.urls import path
from reports.TransitionAccess.views_user_permission_report import (
    UserPermissionReportView,
    ToggleTransitionAccessView,
    TransitionAccessReportView
)
from reports.TransitionAccess.export_views import (
    ExportUserPermissionsView,
    GenerateRuleTextView,
    CopyUserPermissionsView,
    GetUserPermissionsSummaryView
)
from reports.views_staff_api_docs import StaffAPIDocumentationView
from reports.dashboard.urls import urlpatterns as dashboard_urls
from reports.api.urls import urlpatterns as api_urls
from reports.api import simple_views

urlpatterns += [
    # Dashboard Reports
    path('dashboard/', include('reports.dashboard.urls')),
    # API endpoints
    path('api/', include('reports.api.urls')),
    # Simple API endpoints for testing
    path('test-api/organizations/', simple_views.simple_organizations_api, name='test_organizations'),
    path('test-api/projects/', simple_views.simple_projects_api, name='test_projects'),
    # گزارش دسترسی‌های کاربر
    path(
        'user-permissions/',
        UserPermissionReportView.as_view(),
        name='user_permission_report'
    ),
    path(
        'user-permissions/<int:user_id>/',
        UserPermissionReportView.as_view(),
        name='user_permission_report_user'
    ),

    # فعال/غیرفعال کردن دسترسی ترنزیشن (AJAX)
    # path('toggle-transition/<int:user_id>/<int:transition_id>/',        ToggleTransitionAccessView.as_view(), name='toggle_transition_access'),
    path('toggle-transition-access/<int:user_id>/<int:transition_id>/', ToggleTransitionAccessView.as_view(), name='toggle_transition_access'),
    # گزارش جامع Transition
    path(
        'transition-access-report/',
        TransitionAccessReportView.as_view(),
        name='transition_access_report'
    ),

    # خروجی‌های مختلف
    path(
        'user-permissions/<int:user_id>/export/<str:format_type>/',
        ExportUserPermissionsView.as_view(),
        name='export_user_permissions'
    ),
    path(
        'user-permissions/<int:user_id>/rule-text/',
        GenerateRuleTextView.as_view(),
        name='generate_rule_text'
    ),
    path(
        'user-permissions/copy/',
        CopyUserPermissionsView.as_view(),
        name='copy_user_permissions'
    ),
    path(
        'user-permissions/<int:user_id>/summary/',
        GetUserPermissionsSummaryView.as_view(),
        name='get_user_permissions_summary'
    ),

    # مستندات API های سیستم (فقط برای staff)
    path(
        'staff/api-documentation/',
        StaffAPIDocumentationView.as_view(),
        name='staff_api_documentation'
    ),

]

# from django.urls import path
# from reports.ComprehensiveBudgetReportView import (
#     ComprehensiveBudgetReportView,
#     APIOrganizationsForPeriodView,
#     BudgetItemsForOrgPeriodAPIView,
#     APIFactorsForTankhahView,
#     APITankhahsForAllocationView,
#     OrganizationAllocationsAPIView,
# )
# from reports.PaymentOrderReport.PaymentOrderReportView import PaymentOrderReportView
# from reports.budgets_reports.view_budgets_reports import ProjectBudgetReportView, BudgetWarningReportView
# from reports.views import TankhahFinancialReportView, FinancialDashboardView, TankhahDetailView, BudgetAllocationReportView
# from reports.views import print_financial_report, send_to_accounting
#
# urlpatterns = [
#     # گزارشات مالی و داشبورد
#     path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),
#     path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),
#     path('reports/print/<int:report_id>/', print_financial_report, name='print-financial-report'),
#     path('reports/send/<int:report_id>/', send_to_accounting, name='send-to-accounting'),
#
#     # جزئیات تنخواه
#     path('tankhah/<int:pk>/detail/', TankhahDetailView.as_view(), name='tankhah_detail'),
#
#     # گزارشات بودجه و پروژه
#     path('project/<int:pk>/budget-report/', ProjectBudgetReportView.as_view(), name='project_budget_report'),
#     path('budget/warnings/', BudgetWarningReportView.as_view(), name='budget_warning_report'),
#     path('budget-allocation/<int:pk>/report/', BudgetAllocationReportView.as_view(), name='budget_allocation_report'),
#
#     # APIها
#     path('api/period/<int:period_pk>/organization-allocations/', OrganizationAllocationsAPIView.as_view(), name='api_organization_allocations_for_period'),
#     path('api/factors-for-tankhah/<int:tankhah_pk>/', APIFactorsForTankhahView.as_view(), name='api_factors_for_tankhah'),
#     path('api/tankhahs-for-allocation/<int:alloc_pk>/', APITankhahsForAllocationView.as_view(), name='api_tankhahs_for_allocation'),
#     path('reports/api/organizations-for-period/<int:period_pk>/', APIOrganizationsForPeriodView.as_view(), name='api_organizations_for_period'),
#     path('reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/', BudgetItemsForOrgPeriodAPIView.as_view(), name='api_budget_items_for_org_period'),
#     path('reports/comprehensive-budget/', ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report'),
#     path('report/paymentorderreport/', PaymentOrderReportView.as_view(), name='payment_order_report'),
# ]


# from django.urls import path
#
# from reports.ComprehensiveBudgetReportView import ComprehensiveBudgetReportView, APITankhahsForPBAView, \
#     APIFactorsForTankhahView, \
#     APIBudgetItemsForOrgPeriodView, APITankhahsForAllocationView, OrganizationAllocationsAPIView, \
#     APIOrganizationsForPeriodView, BudgetItemsForOrgPeriodAPIView
#
# from reports.PaymentOrderReport.PaymentOrderReportView import PaymentOrderReportView
#
# # BudgetItemsForOrgPeriodAPIView,, APITankhahsForProjectView \
# #     YourOrgPeriodAllocationsListView, OrganizationAllocationsAPIView, APIOrganizationAllocationsView, \
# #     APIBudgetAllocationsForOrgView, APIProjectAllocationsForBAView,
# #
# from reports.budgets_reports.view_budgets_reports import ProjectBudgetReportView, BudgetWarningReportView
# from reports.views import TankhahFinancialReportView, FinancialDashboardView, TankhahDetailView, \
#     BudgetAllocationReportView
# from reports.views import print_financial_report, send_to_accounting
#
# urlpatterns = [
#     path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),
#     path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),
#
#     path('reports/print/<int:report_id>/', print_financial_report, name='print-financial-report'),
#     path('reports/send/<int:report_id>/', send_to_accounting, name='send-to-accounting'),
#
#     path('tankhah-details/', TankhahDetailView.as_view(), name='tankhah_detail'),
#
#
#     path('project/<int:pk>/budget-report/', ProjectBudgetReportView.as_view(), name='project_budget_report'),
#     path('budget/warnings/', BudgetWarningReportView.as_view(), name='budget_warning_report'),
#     path('budget-allocation/<int:pk>/report/', BudgetAllocationReportView.as_view(), name='budget_allocation_report'),
#     path('api/period/<int:period_pk>/organization-allocations/',OrganizationAllocationsAPIView.as_view(),name='api_organization_allocations_for_period'),
#      path('api/project-budget-allocation/<int:pba_pk>/tankhahs/',   APITankhahsForPBAView.as_view(),name='api_tankhahs_for_pba'),
#     path('api/tankhah/<int:tankhah_pk>/factors/',  APIFactorsForTankhahView.as_view(),  name='api_factors_for_tankhah'),
#     path('api/factors-for-tankhah/<int:tankhah_pk>/', APIFactorsForTankhahView.as_view(),         name='api_factors_for_tankhah'),
#
# ]
#
# urlpatterns += [
#     path('reports/api/organizations-for-period/<int:period_pk>/', APIOrganizationsForPeriodView.as_view(), name='api_organizations_for_period'),
#
#     # path('reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/', APIBudgetItemsForOrgPeriodView.as_view(), name='api_budget_items_for_org_period'),
#     # path('api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/', BudgetItemsForOrgPeriodAPIView.as_view(), name='api_budget_items_for_org_period'),  # API برای تنخواه‌ها
#     path('reports/api/budget-items-for-org-period/<int:period_pk>/<int:org_pk>/',BudgetItemsForOrgPeriodAPIView.as_view(),name='api_budget_items_for_org_period'),
#
#     path('reports/comprehensive-budget/', ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report'),
#     path('api/tankhahs-for-allocation/<int:alloc_pk>/', APITankhahsForAllocationView.as_view(), name='api_tankhahs_for_allocation'),
#     path('budget-allocation/<int:pk>/report/', BudgetAllocationReportView.as_view(), name='budget_allocation_report'),
#     # API جدید: برای بارگذاری سازمان‌های یک دوره خاص
#     path('api/organizations-for-period/<int:period_pk>/', APIOrganizationsForPeriodView.as_view(),name='api_organizations_for_period'),    # API فعلی شما برای سرفصل‌ها و پروژه‌ها
#     path('api/tankhahs-for-pba/<int:pba_pk>/', APITankhahsForPBAView.as_view(), name='api_tankhahs_for_pba'),
#     # API برای فاکتورها
#     # این ویو گزارشات جامع از PaymentOrder با جزئیات بودجه، تنخواه، فاکتور، و ردیف‌های فاکتور را نمایش می‌دهد.
#     path('report/paymentorderreport/', PaymentOrderReportView.as_view(), name='payment_order_report'),
#
#
# ]
#
# # API
