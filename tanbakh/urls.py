from core.views import IndexView, FinancialDashboardView
from tanbakh.reports.FinancialReportView import FinancialReportView, PerformanceReportView
from django.urls import path

from tanbakh.views import TanbakhDetailView, TanbakhCreateView, TanbakhDeleteView, \
    FactorListView, FactorDetailView, FactorUpdateView, FactorCreateView, ApprovalListView, FactorDeleteView, \
    ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView, DashboardView, TanbakhListView, \
    TanbakhApproveView, TanbakhRejectView, FactorItemApproveView, FactorApprovalView

urlpatterns = [
    # path('IndexView_dashboard/', IndexView.as_view(), name='IndexView_dashboard'),  # مسیر اصلی داشبورد
    path('', DashboardView.as_view(), name='dashboard'),  # مسیر اصلی داشبورد

    path('tanbakh_list/', TanbakhListView.as_view(), name='tanbakh_list'),
    path('tanbakh/<int:pk>/', TanbakhDetailView.as_view(), name='tanbakh_detail'),
    path('tanbakh/create/', TanbakhCreateView.as_view(), name='tanbakh_create'),
    path('tanbakh/<int:pk>/delete/', TanbakhDeleteView.as_view(), name='tanbakh_delete'),
    # Rehect Approve
    path('tanbakh/<int:pk>/approve/', TanbakhApproveView.as_view(), name='tanbakh_approve'),
    path('tanbakh/<int:pk>/reject/', TanbakhRejectView.as_view(), name='tanbakh_reject'),
    # Approve Factor Row
    path('tanbakh/factor/<int:pk>/approve/', FactorItemApproveView.as_view(), name='factor_item_approve'),

    path('factors/', FactorListView.as_view(), name='factor_list'),
    path('factor/<int:pk>/', FactorDetailView.as_view(), name='factor_detail'),
    path('factor/create/', FactorCreateView.as_view(), name='factor_create'),
    path('factor/<int:pk>/update/', FactorUpdateView.as_view(), name='factor_update'),
    path('factor/<int:pk>/delete/', FactorDeleteView.as_view(), name='factor_delete'),
    path('factor/<int:pk>/approve/', FactorApprovalView.as_view(), name='factor_approve'),# تایید یا رد فاکتور مدیر شعبه

    #
    path('approvals/', ApprovalListView.as_view(), name='approval_list'),
    path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
    path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
    path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
    path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),


    # تایید ها برای فکتور

    # گزارش‌ها
    path('reports/financial/', FinancialReportView.as_view(), name='financial_report'),
    path('reports/performance/', PerformanceReportView.as_view(), name='performance_report'),
    path('financialDashboardView/', FinancialDashboardView.as_view(), name='financialDashboardView'),

]
