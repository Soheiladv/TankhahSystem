from django.urls import path

from reports.views import TankhahFinancialReportView

urlpatterns = [
    path('tankhah/<int:pk>/financial-report/', TankhahFinancialReportView.as_view(), name='tankhah_financial_report'),

    ]