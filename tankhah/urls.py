from django import views
from django.urls import path

from budgets.PaymentOrder.view_PaymentOrder import TankhahUpdateStatusView
from budgets.budget_calculations import get_budget_info, get_tankhah_budget_info
from tankhah.Factor import FactorItemsDetailView
from tankhah.Factor.FactorStatusReviewView import FactorStatusReviewView, AdvancedFactorStatusReviewView, \
    ComprehensiveFactorDetailView, UltimateFactorDetailView
from tankhah.Factor.NF.view_Nfactor import New_FactorCreateView
from tankhah.Factor.View_Factor_list import FactorListView, FactorListView2, OptimizedFactorListView
from tankhah.Factor.view_FactorItemApprove import FactorItemApproveView
from tankhah.Factor.view_FactorUpdate import FactorUpdateView
from tankhah.Factor.views_approval_path import FactorApprovalPathView
from tankhah.FactorStatusDashboard.FactorStatusDashboardView import FactorStatusDashboardView
from tankhah.TankhahTrackingView import TankhahTrackingViewOLDer, TankhahStatusView, TankhahApprovalTimelineView
from tankhah.view_folder_tankhah.EnhancedTankhahUpdateStatus import EnhancedTankhahUpdateStatusView
# from tankhah.view.view_Notification import NotificationListView, NotificationCreateView, NotificationUpdateView, \
#     NotificationDeleteView
from tankhah.view_folder_tankhah.view_tankhah import (
    TankhahDetailView, TankhahCreateView, TankhahDeleteView,
    TankhahListView, TankhahApproveView, TankhahUpdateView, TankhahRejectView, get_projects
)
from tankhah.views import (
    ApprovalListView, ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView,
    FactorApproveView, FactorItemRejectView,
    upload_tankhah_documents, ApprovalLogListView, FactorStatusUpdateView, mark_notification_as_read,
    get_subprojects, FactorDetailView, FactorDeleteView, get_unread_notifications,
     ItemCategoryListView, ItemCategoryCreateView, ItemCategoryUpdateView, ItemCategoryDeleteView
)
from tankhah.Factor.view_Factor import (FactorCreateView,
                                        TankhahBudgetInfoAjaxView,  BudgetCheckView)
from tankhah.views import (itemcategory_list,itemcategory_create,itemcategory_update,itemcategory_delete
)
# app_name = 'tankhah'

urlpatterns = [
    # path('', DashboardView.as_view(), name='dashboard'),
    path('tankhah/', TankhahListView.as_view(), name='tankhah_list'),
    path('tankhah/<int:pk>/'       , TankhahDetailView.as_view(),        name='tankhah_detail'),


    path('tankhah/create/', TankhahCreateView.as_view(), name='tankhah_create'),
    path('tankhah/update/<int:pk>/', TankhahUpdateView.as_view(), name='tankhah_update'),
    path('tankhah/<int:pk>/delete/', TankhahDeleteView.as_view(), name='tankhah_delete'),
    path('tankhah/<int:pk>/approve/', TankhahApproveView.as_view(), name='tankhah_approve'),
    path('tankhah/<int:pk>/reject/', TankhahRejectView.as_view(), name='tankhah_reject'),
    path('tankhah/<int:pk>/tracking/', TankhahTrackingViewOLDer.as_view(), name='tankhah_tracking'),
    path('tankhah/status/', TankhahStatusView.as_view(), name='tankhah_status'),
    path('tankhah/<int:pk>/timeline/', TankhahApprovalTimelineView.as_view(), name='tankhah_approval_timeline'),

    path('factors/', FactorListView.as_view(), name='factor_list'),
    # path('factor/list/', FactorListView.as_view(), name='factor_list'),  # Example success URL
    # path('factor/create/wizard/',  FactorWizardView.as_view(views.FACTOR_FORMS), name='factor_wizard'), # Wizard URL
    path('ajax/tankhah-budget-info/<int:tankhah_id>/', TankhahBudgetInfoAjaxView.as_view(), name='tankhah_budget_info_ajax'),  # AJAX URL
    path('factor/list2/', FactorListView2.as_view(), name='factor_list2'),  # Example success URL
    path('factor/list3/', OptimizedFactorListView.as_view(), name='factor_list3'),  # Example success URL


    path('factor/<int:pk>/', FactorDetailView.as_view(), name='factor_detail'),
    path('factor/create/', FactorCreateView.as_view(), name='factor_create'),
    path('factor/create/new/', New_FactorCreateView.as_view(), name='Nfactor_create'),
    path('get-tankhah-budget-info/',  get_tankhah_budget_info, name='get_tankhah_budget_info'),

    # path('factor/create/', FactorCreateWizard.as_view(), name='w_factor_create'),
    # path('factor/<int:pk>/update/', oldd__FactorUpdateView.as_view(), name='factor_update'),

    path('factors/<int:pk>/edit/', FactorUpdateView.as_view(), name='factor_edit'),
    path('factor/<int:pk>/status-update/', FactorStatusUpdateView.as_view(), name='factor_status_update'),

    path('factor/<int:pk>/delete/', FactorDeleteView.as_view(), name='factor_delete'),

    path('factor/<int:pk>/approve/',        FactorApproveView.as_view(),      name='factor_approve'),
    path('factor/<int:pk>/approval-path/',  FactorApprovalPathView.as_view(), name='factor_approval_path'), # مسیر تایید فاکتورها
    path('factor-item/<int:pk>/approve/',   FactorItemApproveView.as_view(), name='factor_item_approve'),

    path('factor-item/<int:pk>/reject/', FactorItemRejectView.as_view(), name='factor_item_reject'),

    # path('factor-items/<int:pk>/factoritemsdetail', FactorItemsDetailView, name='factor_items_detail'),

    path('approvals/', ApprovalListView.as_view(), name='approval_list'),
    path('tankhah/<str:tankhah_number>/approvals/', ApprovalLogListView.as_view(), name='approval_log_list'),
    path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
    path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
    path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
    path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),
    path('<int:tankhah_id>/upload/', upload_tankhah_documents, name='upload_tankhah_documents'),

    path('get_subprojects/', get_subprojects, name='get_subprojects'),
    path('get-budget-info/', get_budget_info, name='get_budget_info'),
    path('get_budget_info/', BudgetCheckView.as_view(), name='budget_check'),
]
urlpatterns += [
    path('factor/factor_status_dashboard/', FactorStatusDashboardView.as_view(), name='factor_status_dashboard'),

]

urlpatterns += [
    path('categories/',  itemcategory_list, name='itemcategory_list_old'),
    path('categories/add/',  itemcategory_create, name='itemcategory_create_old'),
    path('categories/<int:pk>/edit/', itemcategory_update, name='itemcategory_update_old'),
    path('categories/<int:pk>/delete/', itemcategory_delete, name='itemcategory_delete_old'),
] #categories
urlpatterns += [
    path('categories/', ItemCategoryListView.as_view(), name='itemcategory_list'),
    path('categories/add/', ItemCategoryCreateView.as_view(), name='itemcategory_create'),
    path('categories/edit/<int:pk>/', ItemCategoryUpdateView.as_view(), name='itemcategory_update'),
    path('categories/delete/<int:pk>/', ItemCategoryDeleteView.as_view(), name='itemcategory_delete'),
]#categories


urlpatterns += [
    path('get_projects/', get_projects, name='get_projects'), #به‌روزرسانی پروژه‌ها بر اساس سازمان
]

urlpatterns +=[
    path('factors/status-review/', FactorStatusReviewView.as_view(), name='factor_status_review'),
    path('factors/AdvanceFactorStatusReview/', AdvancedFactorStatusReviewView.as_view(), name='advance_factor_status_review'),
    path('factor/<int:factor_pk>/detail/', ComprehensiveFactorDetailView.as_view(), name='advance_factor_detail'),
    path('factor/<int:factor_pk>/detail/', UltimateFactorDetailView.as_view(),      name='advance_factor_detailA'),

] # پیگیری فاکتور
urlpatterns +=[
    path('tankhah/<int:pk>/update-status/', TankhahUpdateStatusView.as_view(), name='tankhah_update_status'),

]

urlpatterns += [
    path( 'tankhah/<int:pk>/update-status/', EnhancedTankhahUpdateStatusView.as_view(), name='enhancedtankhah_update_status'),
] # ایجاد دستور پرداخت خودکار تنخواه
# urlpatterns += [
#     # لیست تمام اعلان‌ها
#     path('notification_list/',  NotificationListView.as_view(), name='notification_list'),
#
#     # ایجاد اعلان جدید
#     path('notification/create/',  NotificationCreateView.as_view(), name='notification_create'),
#
#     # ویرایش اعلان
#     path('notification/<int:pk>/edit/',  NotificationUpdateView.as_view(), name='notification_update'),
#
#     # حذف اعلان
#     path('notification/<int:pk>/delete/',  NotificationDeleteView.as_view(), name='notification_delete'),
#
#     # علامت گذاری به عنوان خوانده شده (AJAX)
#     path('notification/<int:pk>/mark-as-read/',  mark_notification_as_read, name='mark_as_read'),
#
#     # API برای دریافت اعلان‌های خوانده نشده (اختیاری)
#     path('api/unread/',  get_unread_notifications, name='unread_notifications_api'),
# ]

# from django.urls import path
#
# from budgets.views import get_budget_info
# from tankhah.TankhahTrackingView import TankhahTrackingView
# from tankhah.view_folder_tankhah.view_tankhah import TankhahDetailView, TankhahCreateView, TankhahDeleteView, \
#     TankhahListView, TankhahApproveView, TankhahUpdateView, TankhahRejectView
# from tankhah.views import ApprovalListView, \
#     ApprovalCreateView, ApprovalDetailView, ApprovalUpdateView, ApprovalDeleteView, DashboardView, \
#     FactorItemApproveView, FactorApproveView, FactorItemRejectView, \
#     upload_tankhah_documents, ApprovalLogListView, FactorStatusUpdateView, mark_notification_as_read, \
#     get_subprojects, FactorListView, FactorDetailView, FactorUpdateView, FactorCreateView, FactorDeleteView
#
# urlpatterns = [
#     # path('IndexView_dashboard/', IndexView.as_view(), name='IndexView_dashboard'),  # مسیر اصلی داشبورد
#     path('', DashboardView.as_view(), name='dashboard'),  # مسیر اصلی داشبورد
#     path('tankhah_list/', TankhahListView.as_view(), name='tankhah_list'),
#     path('<int:pk>/', TankhahDetailView.as_view(), name='tankhah_detail'),
#     path('create/', TankhahCreateView.as_view(), name='tankhah_create'),
#     path('update/<int:pk>/', TankhahUpdateView.as_view(), name='tankhah_update'),
#     path('<int:pk>/delete/', TankhahDeleteView.as_view(), name='tankhah_delete'),
#     # Rehect Approve
#     path('<int:pk>/approve/', TankhahApproveView.as_view(), name='tankhah_approve'),
#     path('<int:pk>/reject/', TankhahRejectView.as_view(), name='tankhah_reject'),
#     # Approve Factor Row
#     path('Tankhah/factor/<int:pk>/approve/', FactorItemApproveView.as_view(), name='factor_item_approve'),
#     path('factor/<int:pk>/status-update/', FactorStatusUpdateView.as_view(), name='factor_status_update'),
#
#     path('factors/', FactorListView.as_view(), name='factor_list'),
#     path('factor/<int:pk>/', FactorDetailView.as_view(), name='factor_detail'), # جزئیات فاکتور
#     path('factor/create/', FactorCreateView.as_view(), name='factor_create'),
#     path('factor/<int:pk>/update/', FactorUpdateView.as_view(), name='factor_update'),
#     path('factor/<int:pk>/delete/', FactorDeleteView.as_view(), name='factor_delete'),
#     path('factor/<int:pk>/approve/', FactorApproveView.as_view(), name='factor_approve'),# تایید یا رد فاکتور مدیر شعبه
#
#     #
#     path('approvals/', ApprovalListView.as_view(), name='approval_list'),
#     path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
#     path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
#     path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
#     path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),
#
#     # path('approvalLog_list/', ApprovalLogListView.as_view(), name='approvalLog_list'),
#     path('approvalLog_list/<str:tankhah_number>/', ApprovalLogListView.as_view(),
#          name='approval_log_list'),
#
#     # تایید ها برای فکتور
#
#     # گزارش‌ها
#      path('tankhah/<int:pk>/tracking/', TankhahTrackingView.as_view(), name='tankhah_tracking'),
#
# ]
# urlpatterns += [
#     path('factor/<int:pk>/approve/', FactorApproveView.as_view(), name='factor_approve'),
#     path('factor-item/<int:pk>/approve/', FactorItemApproveView.as_view(), name='factor_item_approve'),
#     path('factor-item/<int:pk>/reject/', FactorItemRejectView.as_view(), name='factor_item_reject'),
#
# ]
# urlpatterns += [
#    path('<int:tankhah_id>/upload/', upload_tankhah_documents, name='upload_tankhah_documents'),
# ] # آپلود تصویر
# urlpatterns += [
#     path('notifications/mark-as-read/<int:notif_id>/',  mark_notification_as_read,
#          name='mark_notification_as_read'),
# ] # نوت به کاربر
#
# urlpatterns += [
#     # لیست همه تأییدات
#     path('approvals/', ApprovalListView.as_view(), name='approval_list'),
#     # لیست تأییدات یه تنخواه خاص
#     path('tankhah/<str:tankhah_number>/approvals/', ApprovalLogListView.as_view(), name='approval_log_list'),
#     # جزئیات یه تأیید
#     path('approval/<int:pk>/', ApprovalDetailView.as_view(), name='approval_detail'),
#     # ثبت تأیید جدید
#     path('approval/create/', ApprovalCreateView.as_view(), name='approval_create'),
#     # ویرایش تأیید
#     path('approval/<int:pk>/update/', ApprovalUpdateView.as_view(), name='approval_update'),
#     # حذف تأیید
#     path('approval/<int:pk>/delete/', ApprovalDeleteView.as_view(), name='approval_delete'),
# ]
# urlpatterns +=[
#     path('get_subprojects/',  get_subprojects, name='get_subprojects'),
#     path('get-budget-info/',  get_budget_info, name='get_budget_info'),
#
# ]