from tanbakh.reports.FinancialReportView import FinancialReportView, PerformanceReportView
from django.urls import path

from tanbakh.views import TanbakhDetailView, TanbakhCreateView, TanbakhDeleteView, \
    FactorListView, FactorDetailView, FactorUpdateView, FactorCreateView, ApprovalListView, FactorDeleteView, \
    ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView, DashboardView, TanbakhListView, \
    TanbakhApproveView, TanbakhRejectView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),  # مسیر اصلی داشبورد
    path('tanbakh_list/', TanbakhListView.as_view(), name='tanbakh_list'),
    path('tanbakh/<int:pk>/', TanbakhDetailView.as_view(), name='tanbakh_detail'),
    path('tanbakh/create/', TanbakhCreateView.as_view(), name='tanbakh_create'),
    path('tanbakh/<int:pk>/delete/', TanbakhDeleteView.as_view(), name='tanbakh_delete'),

    path('factors/', FactorListView.as_view(), name='factor_list'),
    path('factor/<int:pk>/', FactorDetailView.as_view(), name='factor_detail'),
    path('factor/create/', FactorCreateView.as_view(), name='factor_create'),
    path('factor/<int:pk>/update/', FactorUpdateView.as_view(), name='factor_update'),
    path('factor/<int:pk>/delete/', FactorDeleteView.as_view(), name='factor_delete'),
    path('approvals/', ApprovalListView.as_view(), name='approval_list'),
    path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
    path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
    path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
    path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),


    path('tanbakh/<int:pk>/approve/', TanbakhApproveView.as_view(), name='tanbakh_approve'),
    path('tanbakh/<int:pk>/reject/', TanbakhRejectView.as_view(), name='tanbakh_reject'),

    # گزارش‌ها
    path('reports/financial/', FinancialReportView.as_view(), name='financial_report'),
    path('reports/performance/', PerformanceReportView.as_view(), name='performance_report'),

]
