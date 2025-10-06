from django.urls import path
from . import views
from .api import router as pr_router
# app_name = 'purchase_requests'
urlpatterns = [
    path('requests/', views.PurchaseRequestListView.as_view(), name='pr_list'),
    path('requests/create/', views.PurchaseRequestCreateView.as_view(), name='pr_create'),
    path('requests/<int:pk>/', views.PurchaseRequestDetailView.as_view(), name='pr_detail'),
    path('requests/<int:pk>/update/', views.PurchaseRequestUpdateView.as_view(), name='pr_update'),
    path('requests/<int:pk>/approve/', views.PurchaseRequestApproveView.as_view(), name='pr_approve'),
    path('ajax/filter-projects/', views.FilterProjectsView.as_view(), name='pr_ajax_filter_projects'),
    path('ajax/filter-subprojects/', views.FilterSubProjectsView.as_view(), name='pr_ajax_filter_subprojects'),
]

# DRF endpoints
urlpatterns += pr_router.urls


