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
]
