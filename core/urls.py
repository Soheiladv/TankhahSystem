from django.urls import path
from core.views import (
    # داشبوردها
    DashboardView_flows_1, DashboardView_flows, FinancialDashboardView, AllLinksView,
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


# urlpatterns += [
#     path('organizations/', OrganizationListView.as_view(), name='organization_list'),
#     path('organization/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
#     path('organization/create/', OrganizationCreateView.as_view(), name='organization_create'),
#     path('organization/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization_update'),
#     path('organization/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),
#     path('projects/', ProjectListView.as_view(), name='project_list'),
#     path('project/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
#     path('project/create/', ProjectCreateView.as_view(), name='project_create'),
#     path('project/<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
#     path('project/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
#
#     path('all_links/', AllLinksView.as_view(), name='all_links'),
#     path('dashboard_flows/', DashboardView_flows.as_view(), name='dashboard_flows'), # داشبورد تنخواه ها
#
# ]
# urlpatterns += [
#     # Post URLs
#     path('posts/', PostListView.as_view(), name='post_list'),
#     path('post/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
#     path('post/create/', PostCreateView.as_view(), name='post_create'),
#     path('post/<int:pk>/update/', PostUpdateView.as_view(), name='post_update'),
#     path('post/<int:pk>/delete/', PostDeleteView.as_view(), name='post_delete'),
#
#     # UserPost URLs
#     path('userposts/', UserPostListView.as_view(), name='userpost_list'),
#     path('userpost/create/', UserPostCreateView.as_view(), name='userpost_create'),
#     path('userpost/<int:pk>/update/', UserPostUpdateView.as_view(), name='userpost_update'),
#     path('userpost/<int:pk>/delete/', UserPostDeleteView.as_view(), name='userpost_delete'),
#
#     # PostHistory URLs
#     path('posthistories/', PostHistoryListView.as_view(), name='posthistory_list'),
#     path('posthistory/create/', PostHistoryCreateView.as_view(), name='posthistory_create'),
#     path('posthistory/<int:pk>/delete/', PostHistoryDeleteView.as_view(), name='posthistory_delete'),
#
# ]
# urlpatterns += [
#     path("workflow-stages/", WorkflowStageListView.as_view(), name="workflow_stage_list"),
#     path("workflow-stages/new/", WorkflowStageCreateView.as_view(), name="workflow_stage_create"),
#     path("workflow-stages/<int:pk>/edit/", WorkflowStageUpdateView.as_view(), name="workflow_stage_update"),
#     path("workflow-stages/<int:pk>/delete/", WorkflowStageDeleteView.as_view(), name="workflow_stage_delete"),
# ] # workflow_stage
