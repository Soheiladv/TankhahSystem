from django.urls import path

from budgets.BudgetAllocation.get_projects_by_organization import get_budget_items_by_organization, \
    get_budget_item_remaining, get_budget_item_details
from core.views import (
    # داشبوردها
    DashboardView_flows_1, DashboardView_flows, AllLinksView,
    # سازمان‌ها
    OrganizationListView, OrganizationDetailView, OrganizationCreateView,
    OrganizationUpdateView, OrganizationDeleteView,
    # پروژه‌ها
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView,
    # پست‌ها
    PostListView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView,
    # اتصال کاربر به پست
    UserPostListView, UserPostCreateView, UserPostUpdateView, UserPostDeleteView,
    # تاریخچه پست‌ها
    PostHistoryListView, PostHistoryCreateView, PostHistoryDeleteView,
    # مراحل گردش کار
    WorkflowStageListView, WorkflowStageCreateView, WorkflowStageUpdateView, WorkflowStageDeleteView,
)
from reports.views import FinancialDashboardView

# app_name = 'core'

urlpatterns = [
    # داشبوردها
    path('dashboard/flows-1/', DashboardView_flows_1.as_view(), name='dashboard_flows_1'),
    path('dashboard/flows/', DashboardView_flows.as_view(), name='dashboard_flows'),
    path('dashboard/financial/', FinancialDashboardView.as_view(), name='financial_dashboard'),
    path('all_links/', AllLinksView.as_view(), name='all_links'),  # صفحه اصلی
    # path('all-links/',  AllLinksView.as_view(), name='all_links'),

    # سازمان‌ها
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/create/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organizations/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),

    # پروژه‌ها
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/create/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),

    # پست‌ها
    path('posts/', PostListView.as_view(), name='post_list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('posts/create/', PostCreateView.as_view(), name='post_create'),
    path('posts/<int:pk>/update/', PostUpdateView.as_view(), name='post_update'),
    path('posts/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),

    # اتصال کاربر به پست
    path('userposts/', UserPostListView.as_view(), name='userpost_list'),
    path('userposts/create/', UserPostCreateView.as_view(), name='userpost_create'),
    path('userposts/<int:pk>/update/', UserPostUpdateView.as_view(), name='userpost_update'),
    path('userposts/<int:pk>/delete/', UserPostDeleteView.as_view(), name='userpost_delete'),

    # تاریخچه پست‌ها
    path('posthistory/', PostHistoryListView.as_view(), name='posthistory_list'),
    path('posthistory/create/', PostHistoryCreateView.as_view(), name='posthistory_create'),
    path('posthistory/<int:pk>/delete/', PostHistoryDeleteView.as_view(), name='posthistory_delete'),

    # مراحل گردش کار
    path('workflow-stages/', WorkflowStageListView.as_view(), name='workflow_stage_list'),
    path('workflow-stages/create/', WorkflowStageCreateView.as_view(), name='workflow_stage_create'),
    path('workflow-stages/<int:pk>/update/', WorkflowStageUpdateView.as_view(), name='workflow_stage_update'),
    path('workflow-stages/<int:pk>/delete/', WorkflowStageDeleteView.as_view(), name='workflow_stage_delete'),
]

from .views import (
    SubProjectListView, SubProjectCreateView, SubProjectUpdateView, SubProjectDeleteView
)

urlpatterns += [
    path('subprojects/', SubProjectListView.as_view(), name='subproject_list'),
    path('subproject/add/', SubProjectCreateView.as_view(), name='subproject_create'),
    path('subproject/<int:pk>/edit/', SubProjectUpdateView.as_view(), name='subproject_update'),
    path('subproject/<int:pk>/delete/', SubProjectDeleteView.as_view(), name='subproject_delete'),
]
urlpatterns += [
    # ... سایر URL‌ها ...
    path('budget-items/',  get_budget_items_by_organization, name='get_budget_items_by_organization'),
    path('budget-item-remaining/', get_budget_item_remaining, name='get_budget_item_remaining'),
    path('budget-item-details/',  get_budget_item_details, name='get_budget_item_details'),
]
