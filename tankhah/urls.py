from core.views import   FinancialDashboardView
from tankhah.TankhahTrackingView import TankhahTrackingView
from tankhah.reports.FinancialReportView import FinancialReportView, PerformanceReportView
from django.urls import path

from tankhah.views import TankhahDetailView, TankhahCreateView, TankhahDeleteView, \
    FactorListView, FactorDetailView, FactorUpdateView, FactorCreateView, ApprovalListView, FactorDeleteView, \
    ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView, DashboardView, TankhahListView, \
    TankhahApproveView, TankhahRejectView, FactorItemApproveView, FactorApproveView, FactorItemRejectView, \
    upload_tankhah_documents, TankhahUpdateView

urlpatterns = [
    # path('IndexView_dashboard/', IndexView.as_view(), name='IndexView_dashboard'),  # مسیر اصلی داشبورد
    path('', DashboardView.as_view(), name='dashboard'),  # مسیر اصلی داشبورد

    path('tankhah_list/', TankhahListView.as_view(), name='tankhah_list'),
    path('<int:pk>/', TankhahDetailView.as_view(), name='tankhah_detail'),
    path('create/', TankhahCreateView.as_view(), name='tankhah_create'),
    path('update/<int:pk>/', TankhahUpdateView.as_view(), name='tankhah_update'),
    path('<int:pk>/delete/', TankhahDeleteView.as_view(), name='tankhah_delete'),
    # Rehect Approve
    path('<int:pk>/approve/', TankhahApproveView.as_view(), name='tankhah_approve'),
    path('<int:pk>/reject/', TankhahRejectView.as_view(), name='tankhah_reject'),
    # Approve Factor Row
    path('Tankhah/factor/<int:pk>/approve/', FactorItemApproveView.as_view(), name='factor_item_approve'),

    path('factors/', FactorListView.as_view(), name='factor_list'),
    path('factor/<int:pk>/', FactorDetailView.as_view(), name='factor_detail'), # جزئیات فاکتور
    path('factor/create/', FactorCreateView.as_view(), name='factor_create'),
    path('factor/<int:pk>/update/', FactorUpdateView.as_view(), name='factor_update'),
    path('factor/<int:pk>/delete/', FactorDeleteView.as_view(), name='factor_delete'),
    path('factor/<int:pk>/approve/', FactorApproveView.as_view(), name='factor_approve'),# تایید یا رد فاکتور مدیر شعبه

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
    path('tankhah/<int:pk>/tracking/', TankhahTrackingView.as_view(), name='tankhah_tracking'),


]
urlpatterns += [
    path('factor/<int:pk>/approve/', FactorApproveView.as_view(), name='factor_approve'),
    path('factor-item/<int:pk>/approve/', FactorItemApproveView.as_view(), name='factor_item_approve'),
    path('factor-item/<int:pk>/reject/', FactorItemRejectView.as_view(), name='factor_item_reject'),

]
urlpatterns += [
   path('<int:tankhah_id>/upload/', upload_tankhah_documents, name='upload_tankhah_documents'),
] # آپلود تصویر

