from django.urls import path
from . import views

app_name = 'reports_dashboard'

urlpatterns = [
    # داشبورد اصلی
    path('', views.DashboardMainView.as_view(), name='main_dashboard'),
    
    # تحلیل‌های بودجه
    path('analytics/', views.BudgetAnalyticsView.as_view(), name='budget_analytics'),
    
    # صادرات گزارشات
    path('export/', views.ExportReportsView.as_view(), name='export_reports'),
    
    # Debug endpoint
    path('debug-data/', views.debug_dashboard_data, name='debug_data'),
    
    # Test dashboard
    path('test/', views.TestDashboardView.as_view(), name='test_dashboard'),
    
    # Simple dashboard
    path('simple/', views.SimpleDashboardView.as_view(), name='simple_dashboard'),
    
    # Simple analytics
    path('simple-analytics/', views.SimpleAnalyticsView.as_view(), name='simple_analytics'),
    
    # Dashboard selector
    path('selector/', views.DashboardSelectorView.as_view(), name='dashboard_selector'),
    
    # Chart test
    path('chart-test/', views.ChartTestView.as_view(), name='chart_test'),
    
    # Simple chart test
    path('simple-chart-test/', views.SimpleChartTestView.as_view(), name='simple_chart_test'),
    
    # Minimal chart test
    path('minimal-chart-test/', views.MinimalChartTestView.as_view(), name='minimal_chart_test'),
    
    # Test analytics
    path('test-analytics/', views.TestAnalyticsView.as_view(), name='test_analytics'),

    # Redesigned analytics page
    path('analytics-redesigned/', views.BudgetAnalyticsRedesignedView.as_view(), name='analytics_redesigned'),
    # API for dependent projects
    path('api/projects-by-org/', views.api_projects_by_org, name='api_projects_by_org'),
]
