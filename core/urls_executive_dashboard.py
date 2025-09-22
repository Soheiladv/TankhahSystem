"""
URL patterns برای داشبورد اجرایی
"""

from django.urls import path

from BudgetsSystem.view.view_Dashboard import ExecutiveDashboardView
from . import views_executive_dashboard

app_name = 'executive_dashboard'

urlpatterns = [
    path('executive-dashboard/', ExecutiveDashboardView.as_view(), name='executive_dashboard'),
    path('comprehensive-budget-report/', views_executive_dashboard.ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report'),
    path('comprehensive-factor-report/', views_executive_dashboard.ComprehensiveFactorReportView.as_view(), name='comprehensive_factor_report'),
    path('comprehensive-tankhah-report/', views_executive_dashboard.ComprehensiveTankhahReportView.as_view(), name='comprehensive_tankhah_report'),
    path('financial-performance-report/', views_executive_dashboard.FinancialPerformanceReportView.as_view(), name='financial_performance_report'),
    path('analytical-reports/', views_executive_dashboard.AnalyticalReportsView.as_view(), name='analytical_reports'),
]
