from tankhah.TankhahTrackingView import TankhahTrackingView
from django.urls import path

from tankhah.view.views_factor import  FactorListView, FactorDetailView,FactorUpdateView, FactorCreateView,  FactorDeleteView

from tankhah.views import TankhahDetailView, TankhahCreateView, TankhahDeleteView, \
     ApprovalListView, \
    ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView, DashboardView, TankhahListView, \
    TankhahApproveView, TankhahRejectView, FactorItemApproveView, FactorApproveView, FactorItemRejectView, \
    upload_tankhah_documents, TankhahUpdateView, ApprovalLogListView, FactorStatusUpdateView, mark_notification_as_read, \
    get_subprojects

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
    path('factor/<int:pk>/status-update/', FactorStatusUpdateView.as_view(), name='factor_status_update'),

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

    # path('approvalLog_list/', ApprovalLogListView.as_view(), name='approvalLog_list'),
    path('approvalLog_list/<str:tankhah_number>/', ApprovalLogListView.as_view(),
         name='approval_log_list'),

    # تایید ها برای فکتور

    # گزارش‌ها
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
urlpatterns += [
    path('notifications/mark-as-read/<int:notif_id>/',  mark_notification_as_read,
         name='mark_notification_as_read'),

] # نوت به کاربر

urlpatterns += [
    # لیست همه تأییدات
    path('approvals/', ApprovalListView.as_view(), name='approval_list'),
    # لیست تأییدات یه تنخواه خاص
    path('tankhah/<str:tankhah_number>/approvals/', ApprovalLogListView.as_view(), name='approval_log_list'),
    # جزئیات یه تأیید
    path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
    # ثبت تأیید جدید
    path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
    # ویرایش تأیید
    path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
    # حذف تأیید
    path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),
]
urlpatterns +=[
    path('get_subprojects/',  get_subprojects, name='get_subprojects'),

]