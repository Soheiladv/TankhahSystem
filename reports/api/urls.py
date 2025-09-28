from django.urls import path
from . import views

app_name = 'reports_api'

urlpatterns = [
    # API endpoints for dashboard
    path('organizations/', views.OrganizationsAPIView.as_view(), name='organizations'),
    path('projects/', views.ProjectsAPIView.as_view(), name='projects'),
    path('budget-periods/', views.BudgetPeriodsAPIView.as_view(), name='budget_periods'),
    path('dashboard-data/', views.DashboardDataAPIView.as_view(), name='dashboard_data'),
    path('export-data/', views.ExportDataAPIView.as_view(), name='export_data'),
]
