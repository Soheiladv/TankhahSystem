from django.urls import path

from Tanbakhsystem.view.view_Dashboard import SimpleChartView
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
from core.views_API.views_api import OrganizationChartAPIView,OrganizationChartView

urlpatterns += [
    path('api/organization-chart/', OrganizationChartAPIView.as_view(), name='organization_chart_api'),
    path('organization-chart/', OrganizationChartView.as_view(), name='organization_chart'),

] # چارت سازمانی

from django.urls import path
from core.AccessRule.views_accessrule import (
    AccessRuleListView, AccessRuleDetailView, AccessRuleCreateView,
    AccessRuleUpdateView, AccessRuleDeleteView, userGiud_AccessRule, PostAccessRuleAssignView, PostRuleReportView,
    UserGuideView
)

urlpatterns += [
    path('access-rules/', AccessRuleListView.as_view(), name='accessrule_list'),
    path('access-rules/<int:pk>/', AccessRuleDetailView.as_view(), name='accessrule_detail'),
    path('access-rules/create/', AccessRuleCreateView.as_view(), name='accessrule_create'),
    path('access-rules/<int:pk>/edit/', AccessRuleUpdateView.as_view(), name='accessrule_update'),
    path('access-rules/<int:pk>/delete/', AccessRuleDeleteView.as_view(), name='accessrule_delete'),

    path('access-rules/assign/', PostAccessRuleAssignView.as_view(), name='post_access_rule_assign'),
    path('access-rules/report/', PostRuleReportView.as_view(), name='post_rule_report'),

 ] # قوانین سیستم


# core/urls.py
from django.urls import path
from core.Branch.views_branch import (
    BranchListView,
    BranchDetailView,
    BranchCreateView,
    BranchUpdateView,
    BranchDeleteView
)

urlpatterns += [
    # لیست تمام شاخه‌ها
    path('branches/', BranchListView.as_view(), name='branch_list'),
    # ایجاد شاخه جدید
    path('branches/add/', BranchCreateView.as_view(), name='branch_add'),
    # نمایش جزئیات یک شاخه (بر اساس PK)
    path('branches/<int:pk>/', BranchDetailView.as_view(), name='branch_detail'),
    # ویرایش یک شاخه (بر اساس PK)
    path('branches/<int:pk>/edit/', BranchUpdateView.as_view(), name='branch_edit'),
    # حذف یک شاخه (بر اساس PK)
    path('branches/<int:pk>/delete/', BranchDeleteView.as_view(), name='branch_delete'),
]#Branch شاخه های پست در سازمان


urlpatterns += [
    path('Help_AccessRule',userGiud_AccessRule , name= 'user_Giud_AccessRule'),
    path('user-guide/', UserGuideView.as_view(), name='user_guide'),
path ('simple-chart/', SimpleChartView.as_view(), name='simple_chart'),
]#راهنما


