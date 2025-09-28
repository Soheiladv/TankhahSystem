from django.urls import path, include
from django.views.generic import TemplateView

from BudgetsSystem.view.view_Dashboard import SimpleChartView, ExecutiveDashboardView
from core.views_executive_dashboard import (
    ComprehensiveBudgetReportView,
    ComprehensiveFactorReportView, 
    ComprehensiveTankhahReportView,
    FinancialPerformanceReportView,
    AnalyticalReportsView
)
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
    PostListView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView, PostActiveUsersAPIView,
    # اتصال کاربر به پست
    UserPostListView, UserPostCreateView, UserPostUpdateView, UserPostDeleteView,
    # تاریخچه پست‌ها
    PostHistoryListView, PostHistoryCreateView, PostHistoryDeleteView,
    # مراحل گردش کار
    WorkflowStageListView, WorkflowStageCreateView, WorkflowStageUpdateView, WorkflowStageDeleteView,
     PostSearchAPIView,

)
from reports.views import FinancialDashboardView
from . import views_workflow_management
from .workflow.views_Transition import TransitionListView, TransitionCreateView, TransitionUpdateView, \
    TransitionDeleteView

# app_name = 'core'

from .views import (
    SubProjectListView, SubProjectCreateView, SubProjectUpdateView, SubProjectDeleteView
)
from core.views_API.views_api import OrganizationChartAPIView,OrganizationChartView
from core.views_workflow_debug import workflow_debug_view, factor_workflow_shortcuts_view
from core.views_workflow_chart import (
    WorkflowChartView, workflow_chart_api,
    workflow_transition_create, workflow_transition_update,
    workflow_transition_toggle, workflow_transition_delete,
)

from django.urls import path
# from core.AccessRule.views_accessrule import (
#     AccessRuleListView, AccessRuleDetailView, AccessRuleCreateView,
#     AccessRuleUpdateView, AccessRuleDeleteView, userGiud_AccessRule, PostAccessRuleAssignView, PostRuleReportView,
#     UserGuideView, SelectWorkflowView, PostAccessRuleAssignView_old
# )  # حذف شده - مدل AccessRule منسوخ شده است

# core/urls.py
from django.urls import path
from core.Branch.views_branch import (
    BranchListView,
    BranchDetailView,
    BranchCreateView,
    BranchUpdateView,
    BranchDeleteView
)
# from core.AccessRule.views_accessrule import SelectWorkflowView, WorkflowBuilderView  # حذف شده - مدل AccessRule منسوخ شده است
from core.workflow.views_workflow import (
    WorkflowDashboardView,
    StatusListView, StatusCreateView, StatusUpdateView , StatusDeleteView,
)
from core.workflow.views_Action import (
    ActionListView, ActionUpdateView, ActionDeleteView, ActionCreteView,
    # ویوهای Transition و Permission در مراحل بعدی اضافه خواهند شد
)
from core.views_workflow_management import ActionTransitionsReportView, WorkflowAccessAuditView
from BudgetsSystem.view.view_SystemSettings import (
    SystemSettingsDashboardView,
    SystemSettingsCreateView,
    SystemSettingsUpdateView,
    SystemSettingsResetView,
    SystemSettingsExportView,
    SystemSettingsImportView,
    SystemSettingsHealthView,
    SystemSettingsPreviewView,
    OrgActionsReportView,
)
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
            path('posts/<int:post_id>/active-users/', PostActiveUsersAPIView.as_view(), name='post_active_users_api'),
        # ========================================================
        # اتصال کاربر به پست
        # ========================================================
            path('userposts/', UserPostListView.as_view(), name='userpost_list'),
            path('userposts/create/', UserPostCreateView.as_view(), name='userpost_create'),
            path('userposts/<int:pk>/update/', UserPostUpdateView.as_view(), name='userpost_update'),
            path('userposts/<int:pk>/delete/', UserPostDeleteView.as_view(), name='userpost_delete'),
            path('api/posts/', PostSearchAPIView.as_view(), name='post_search_api'),
       # ========================================================
        # تاریخچه پست‌ها
        # ========================================================
            path('posthistory/', PostHistoryListView.as_view(), name='posthistory_list'),
            path('posthistory/create/', PostHistoryCreateView.as_view(), name='posthistory_create'),
            path('posthistory/<int:pk>/delete/', PostHistoryDeleteView.as_view(), name='posthistory_delete'),
       # ========================================================
       # مراحل گردش کار
       # ========================================================
            path('workflow-stages/', WorkflowStageListView.as_view(), name='workflow_stage_list'),
            path('workflow-stages/create/', WorkflowStageCreateView.as_view(), name='workflow_stage_create'),
            path('workflow-stages/<int:pk>/update/', WorkflowStageUpdateView.as_view(), name='workflow_stage_update'),
            path('workflow-stages/<int:pk>/delete/', WorkflowStageDeleteView.as_view(), name='workflow_stage_delete'),
       # ========================================================
]

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

urlpatterns += [
            path('api/organization-chart/', OrganizationChartAPIView.as_view(), name='organization_chart_api'),
            path('organization-chart/', OrganizationChartView.as_view(), name='organization_chart'),
      
        path('workflow-debug/', workflow_debug_view, name='workflow_debug'),
        path('factor-workflow-tools/', factor_workflow_shortcuts_view, name='factor_workflow_tools'),
        path('workflow-chart/', WorkflowChartView.as_view(), name='workflow_chart'),
        path('api/workflow-chart/', workflow_chart_api, name='workflow_chart_api'),
        path('api/workflow/transitions/create', workflow_transition_create, name='workflow_transition_create'),
        path('api/workflow/transitions/<int:transition_id>/update', workflow_transition_update, name='workflow_transition_update'),
        path('api/workflow/transitions/<int:transition_id>/toggle', workflow_transition_toggle, name='workflow_transition_toggle'),
        path('api/workflow/transitions/<int:transition_id>/delete', workflow_transition_delete, name='workflow_transition_delete'),

        ] # چارت سازمانی

# urlpatterns += [
#             path('access-rules/', AccessRuleListView.as_view(), name='accessrule_list'),
#             path('access-rules/<int:pk>/', AccessRuleDetailView.as_view(), name='accessrule_detail'),
#             path('access-rules/create/', AccessRuleCreateView.as_view(), name='accessrule_create'),
#             path('access-rules/<int:pk>/edit/', AccessRuleUpdateView.as_view(), name='accessrule_update'),
#             path('access-rules/<int:pk>/delete/', AccessRuleDeleteView.as_view(), name='accessrule_delete'),
#
#             path('workflow/select/', SelectWorkflowView.as_view(), name='workflow_select'),
#             path('access-rules/assign/', PostAccessRuleAssignView_old.as_view(), name='post_access_rule_assign_old'),
#             path('workflow/assign/<int:org_pk>/<str:entity_type>/', PostAccessRuleAssignView.as_view(),
#                  name='post_access_rule_assign'),
#
#             path('access-rules/report/', PostRuleReportView.as_view(), name='post_rule_report'),
#
#          ] # قوانین سیستم - حذف شده - مدل AccessRule منسوخ شده است

# ===================================================================
# ==== Branch شاخه های پست در سازمان ====
# ===================================================================
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
# ===================================================================
# ==== # راهنما ====
# ===================================================================
urlpatterns += [
            # path('Help_AccessRule',userGiud_AccessRule , name= 'user_Giud_AccessRule'),  # حذف شده - مدل AccessRule منسوخ شده است
            # path('user-guide/', UserGuideView.as_view(), name='user_guide'),  # حذف شده - مدل AccessRule منسوخ شده است
        path ('simple-chart/', SimpleChartView.as_view(), name='simple_chart'),
        ]#راهنما
# ===================================================================
# ==== #قسمت قانون گذاری جدید ====
# ===================================================================
# urlpatterns += [
#             path('access-management/select/', SelectWorkflowView.as_view(), name='workflow_select'),
#             # URL نهایی برای ویوی یکپارچه ما
#             path('access-management/builder/<int:org_pk>/<str:entity_type>/', WorkflowBuilderView.as_view(),
#                  name='workflow_builder'),
#         ]  # حذف شده - مدل AccessRule منسوخ شده است
# ===================================================================
# ==== #قسمت قانون گذاری جدید ====
# ===================================================================

# ActionCreateView,
urlpatterns += [
            # --- داشبورد اصلی ---
            # path('workflow/', WorkflowDashboardView.as_view(), name='workflow_dashboard'),
            path('workflow/', views_workflow_management.simple_workflow_dashboard, name='workflow_dashboard'),

    # مدیریت قوانین گردش کار
            path('workflow-management/', include('core.urls_workflow_management')),

            path('workflow/statuses/', StatusListView.as_view(), name='status_list'),
            path('workflow/statuses/create/', StatusCreateView.as_view(), name='status_create'),
            path('workflow/statuses/<int:pk>/update/', StatusUpdateView.as_view(), name='status_update'),
            path('workflow/statuses/<int:pk>/delete/', StatusDeleteView.as_view(), name='status_delete'),

            # --- URL های CRUD برای Action ---
            path('workflow/actions/', ActionListView.as_view(), name='action_list'),
            path('workflow/actions/create/', ActionCreteView.as_view(), name='action_create'),
            path('workflow/actions/<int:pk>/update/', ActionUpdateView.as_view(), name='action_update'),
            path('workflow/actions/<int:pk>/delete/', ActionDeleteView.as_view(), name='action_delete'),
            path('workflow/actions/<int:pk>/report/', ActionTransitionsReportView.as_view(), name='action_transitions_report'),
            path('workflow/audit/', WorkflowAccessAuditView.as_view(), name='workflow_access_audit'),
            path('workflow/user-guide/', TemplateView.as_view(template_name='core/workflow/workflow_user_guide.html'), name='workflow_user_guide'),

            # --- URL های CRUD برای Transition ---
            path('workflow/transition/', TransitionListView.as_view(), name='transition_list'),
            path('workflow/transition/create/', TransitionCreateView.as_view(), name='transition_create'),
            path('workflow/transition/<int:pk>/update/', TransitionUpdateView.as_view(), name='transition_update'),
            path('workflow/transition/<int:pk>/delete/', TransitionDeleteView.as_view(), name='transition_delete'),
            path('workflow/org-actions/', OrgActionsReportView.as_view(), name='workflow_org_actions'),
            
            # داشبورد اجرایی
            path('executive-dashboard/', ExecutiveDashboardView.as_view(), name='executive_dashboard'),
            # System Settings
            path('system-settings/', SystemSettingsDashboardView.as_view(), name='system_settings_dashboard'),
            # path('system-settings/create/', SystemSettingsCreateView.as_view(), name='system_settings_create'),
            path('system-settings/create/', SystemSettingsUpdateView.as_view(), name='system_settings_create'),
            path('system-settings/<int:pk>/edit/', SystemSettingsUpdateView.as_view(), name='system_settings_update'),
            path('system-settings/reset/', SystemSettingsResetView.as_view(), name='system_settings_reset'),
            path('system-settings/export/', SystemSettingsExportView.as_view(), name='system_settings_export'),
            path('system-settings/import/', SystemSettingsImportView.as_view(), name='system_settings_import'),
            path('system-settings/health/', SystemSettingsHealthView.as_view(), name='system_settings_health'),
            path('system-settings/preview/', SystemSettingsPreviewView.as_view(), name='system_settings_preview'),
            
            # گزارشات جامع
            path('comprehensive-budget-report/', ComprehensiveBudgetReportView.as_view(), name='comprehensive_budget_report'),
            path('comprehensive-factor-report/', ComprehensiveFactorReportView.as_view(), name='comprehensive_factor_report'),
            path('comprehensive-tankhah-report/', ComprehensiveTankhahReportView.as_view(), name='comprehensive_tankhah_report'),
            path('financial-performance-report/', FinancialPerformanceReportView.as_view(), name='financial_performance_report'),
            path('analytical-reports/', AnalyticalReportsView.as_view(), name='analytical_reports'),
            
            # الگوی تخصیص کاربران - حذف شده به دلیل خطای import

 ]
