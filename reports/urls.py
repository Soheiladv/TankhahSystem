from django.urls import path

from reports.views import TankhahFinancialReportView, FinancialDashboardView ,TankhahDetailView
from reports.views import print_financial_report, send_to_accounting

urlpatterns = [
    path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),
    path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),

    path('reports/print/<int:report_id>/', print_financial_report, name='print-financial-report'),
    path('reports/send/<int:report_id>/', send_to_accounting, name='send-to-accounting'),

    path('tankhah-details/', TankhahDetailView.as_view(), name='tankhah_detail'),

]