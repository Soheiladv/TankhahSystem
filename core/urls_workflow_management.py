"""
URL patterns برای مدیریت قوانین گردش کار
"""

from django.urls import path

from tankhah.Factor.views_factor_approval_path import FactorApprovalPathView
from . import views_workflow_management
from tankhah.Factor import views_factor_approval_path

app_name = 'workflow_management'

urlpatterns = [
    # راهنمای کامل
    path('guide/', views_workflow_management.complete_guide, name='complete_guide'),
    
    # داشبورد اصلی
    path('', views_workflow_management.simple_workflow_dashboard, name='simple_dashboard'),
    
    # تمپلیت‌های قوانین - کامنت شده چون WorkflowRuleTemplate حذف شده
    # path('templates/', views_workflow_management.WorkflowTemplateListView.as_view(), name='template_list'),
    # path('templates/<int:pk>/', views_workflow_management.WorkflowTemplateDetailView.as_view(), name='template_detail'),
    # path('templates/create/', views_workflow_management.WorkflowTemplateCreateView.as_view(), name='template_create'),
    # path('templates/<int:pk>/edit/', views_workflow_management.WorkflowTemplateUpdateView.as_view(), name='template_edit'),
    # path('templates/<int:pk>/delete/', views_workflow_management.WorkflowTemplateDeleteView.as_view(), name='template_delete'),
    
    # عملیات تمپلیت‌ها - کامنت شده چون WorkflowRuleTemplate حذف شده
    # path('templates/create-from-existing/', views_workflow_management.create_template_from_existing, name='create_template_from_existing'),
    # path('templates/<int:template_id>/apply/', views_workflow_management.apply_template_to_organization, name='apply_template'),
    
    # تخصیص قوانین به پست‌ها
    path('post-assignments/', views_workflow_management.PostRuleAssignmentListView.as_view(), name='post_assignment_list'),
    path('post-assignments/create/', views_workflow_management.assign_rule_to_post, name='post_assignment_create'),
    path('post-assignments/assign/', views_workflow_management.assign_rule_to_post, name='assign_rule_to_post'),
    path('post-assignments/<int:assignment_id>/edit/', views_workflow_management.edit_rule_assignment, name='edit_rule_assignment'),
    path('post-assignments/<int:assignment_id>/delete/', views_workflow_management.delete_rule_assignment, name='delete_rule_assignment'),
    path('post-assignments/<int:assignment_id>/effective-rules/', views_workflow_management.get_post_effective_rules, name='get_effective_rules'),
    
    # فرم‌های مدیریت وضعیت‌ها و اقدامات
    path('statuses/', views_workflow_management.StatusListView.as_view(), name='status_list'),
    path('statuses/create/', views_workflow_management.StatusCreateView.as_view(), name='status_create'),
    path('statuses/<int:pk>/edit/', views_workflow_management.StatusUpdateView.as_view(), name='status_edit'),
    path('statuses/<int:pk>/delete/', views_workflow_management.StatusDeleteView.as_view(), name='status_delete'),
    
    path('actions/', views_workflow_management.ActionListView.as_view(), name='action_list'),
    path('actions/create/', views_workflow_management.ActionCreateView.as_view(), name='action_create'),
    path('actions/<int:pk>/edit/', views_workflow_management.ActionUpdateView.as_view(), name='action_edit'),
    path('actions/<int:pk>/delete/', views_workflow_management.ActionDeleteView.as_view(), name='action_delete'),
    
    # StageApprover Management
    path('stage-approvers/', views_workflow_management.StageApproverListView.as_view(), name='stage_approver_list'),
    path('stage-approvers/create/', views_workflow_management.StageApproverCreateView.as_view(), name='stage_approver_create'),
    path('stage-approvers/<int:pk>/edit/', views_workflow_management.StageApproverUpdateView.as_view(), name='stage_approver_edit'),
    path('stage-approvers/<int:pk>/delete/', views_workflow_management.StageApproverDeleteView.as_view(), name='stage_approver_delete'),
    path('stage-approvers/bulk-create/', views_workflow_management.bulk_create_stage_approvers, name='bulk_create_stage_approvers'),
    
    # API endpoints
    path('api/statuses/', views_workflow_management.api_statuses, name='api_statuses'),
    path('api/actions/', views_workflow_management.api_actions, name='api_actions'),
    path('api/organizations/', views_workflow_management.api_organizations, name='api_organizations'),
    path('api/posts/<int:organization_id>/', views_workflow_management.get_posts_by_organization, name='get_posts_by_organization'),
    path('api/validation/<int:organization_id>/<str:entity_type>/', views_workflow_management.workflow_validation, name='workflow_validation'),
    path('api/summary/<int:organization_id>/<str:entity_type>/', views_workflow_management.workflow_summary, name='workflow_summary'),
    path('api/export/<int:organization_id>/<str:entity_type>/', views_workflow_management.export_workflow_rules, name='export_workflow_rules'),
    
    # Unified Workflow Management
    path('unified/', views_workflow_management.UnifiedWorkflowManagementView.as_view(), name='unified_workflow_management'),
    path('api/overview-stats/', views_workflow_management.api_overview_stats, name='api_overview_stats'),
    path('api/post-rules/', views_workflow_management.api_post_rules, name='api_post_rules'),
    path('api/stage-approvers/', views_workflow_management.api_stage_approvers, name='api_stage_approvers'),
    path('api/filter-options/', views_workflow_management.api_filter_options, name='api_filter_options'),
    path('api/check-duplicates/', views_workflow_management.api_check_duplicates, name='api_check_duplicates'),
    
    # Factor Approval Path
    path('factor/<int:pk>/approval-path/',   FactorApprovalPathView.as_view(), name='factor_approval_path'),
    path('api/factor/<int:factor_id>/approval-path/', views_factor_approval_path.api_factor_approval_path, name='api_factor_approval_path'),
]
