from django.urls import path
from . import views
from . import simple_views

app_name = 'reports_api'

urlpatterns = [
    # Simple API endpoints without authentication
    path('organizations/', simple_views.simple_organizations_api, name='organizations'),
    path('projects/', simple_views.simple_projects_api, name='projects'),
    
    # Original API endpoints for dashboard
    path('budget-periods/', views.BudgetPeriodsAPIView.as_view(), name='budget_periods'),
    path('dashboard-data/', views.DashboardDataAPIView.as_view(), name='dashboard_data'),
    path('export-data/', views.ExportDataAPIView.as_view(), name='export_data'),
]
