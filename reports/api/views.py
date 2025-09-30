from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
import json

from core.models import Organization, Project
from core.PermissionBase import PermissionBaseView
from budgets.models import BudgetPeriod


@method_decorator(csrf_exempt, name='dispatch')
class OrganizationsAPIView(PermissionBaseView, View):
    """API برای دریافت لیست سازمان‌ها"""
    permission_codename = 'core.view_organization'
    
    def get(self, request):
        try:
            organizations = Organization.objects.filter(is_active=True).values('id', 'name', 'code')
            return JsonResponse(list(organizations), safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProjectsAPIView(PermissionBaseView, View):
    """API برای دریافت لیست پروژه‌ها"""
    permission_codename = 'core.view_project'
    
    def get(self, request):
        try:
            projects = Project.objects.filter(is_active=True).values('id', 'name', 'code')
            return JsonResponse(list(projects), safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class BudgetPeriodsAPIView(PermissionBaseView, View):
    """API برای دریافت لیست دوره‌های بودجه"""
    permission_codename = 'budgets.view_budgetperiod'
    
    def get(self, request):
        periods = BudgetPeriod.objects.filter(is_active=True).values('id', 'name', 'start_date', 'end_date')
        return JsonResponse(list(periods), safe=False)


class DashboardDataAPIView(PermissionBaseView, View):
    """API برای دریافت داده‌های داشبورد"""
    permission_codename = 'reports.view_dashboard'
    
    def get(self, request):
        # دریافت فیلترها
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        organization_id = request.GET.get('organization')
        project_id = request.GET.get('project')
        
        # آمار کلی بودجه و متریک‌های پیشرفته
        from reports.dashboard.views import DashboardMainView
        dashboard_view = DashboardMainView()
        dashboard_view.request = request
        
        # دریافت آمار پایه
        budget_stats = dashboard_view.get_budget_statistics(start_date, end_date, organization_id, project_id)
        tankhah_stats = dashboard_view.get_tankhah_statistics(start_date, end_date, organization_id, project_id)
        factor_stats = dashboard_view.get_factor_statistics(start_date, end_date, organization_id, project_id)
        payment_stats = dashboard_view.get_payment_statistics(start_date, end_date, organization_id, project_id)
        return_stats = dashboard_view.get_budget_return_statistics(start_date, end_date, organization_id, project_id)
        chart_data = dashboard_view.get_chart_data(start_date, end_date, organization_id, project_id)

        # دریافت متریک‌های پیشرفته
        advanced_budget = dashboard_view.get_advanced_budget_metrics(start_date, end_date, organization_id, project_id)
        advanced_tankhah = dashboard_view.get_advanced_tankhah_metrics(start_date, end_date, organization_id, project_id)
        advanced_factor = dashboard_view.get_advanced_factor_metrics(start_date, end_date, organization_id, project_id)
        advanced_comparatives = dashboard_view.get_advanced_comparatives(start_date, end_date, organization_id, project_id)
        advanced_risk = dashboard_view.get_advanced_risk_metrics(start_date, end_date, organization_id, project_id)
        
        return JsonResponse({
            'budget_stats': budget_stats,
            'tankhah_stats': tankhah_stats,
            'factor_stats': factor_stats,
            'payment_stats': payment_stats,
            'return_stats': return_stats,
            'chart_data': chart_data,
            'advanced_budget': advanced_budget,
            'advanced_tankhah': advanced_tankhah,
            'advanced_factor': advanced_factor,
            'advanced_comparatives': advanced_comparatives,
            'advanced_risk': advanced_risk,
        })


class ExportDataAPIView(PermissionBaseView, View):
    """API برای صادرات داده‌ها"""
    permission_codename = 'reports.export_reports'
    
    def get(self, request):
        report_type = request.GET.get('type', 'budget')
        format_type = request.GET.get('format', 'json')
        
        # دریافت فیلترها
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        organization_id = request.GET.get('organization')
        project_id = request.GET.get('project')
        
        # دریافت داده‌ها بر اساس نوع گزارش
        from reports.dashboard.views import ExportReportsView
        export_view = ExportReportsView()
        
        filters = {
            'start_date': start_date,
            'end_date': end_date,
            'organization': organization_id,
            'project': project_id,
        }
        
        if report_type == 'budget':
            data = export_view.get_budget_report_data(filters)
        elif report_type == 'tankhah':
            data = export_view.get_tankhah_report_data(filters)
        elif report_type == 'factor':
            data = export_view.get_factor_report_data(filters)
        elif report_type == 'payment':
            data = export_view.get_payment_report_data(filters)
        elif report_type == 'returns':
            data = export_view.get_returns_report_data(filters)
        else:
            data = []
        
        # تبدیل به فرمت مورد نظر
        if format_type == 'json':
            return JsonResponse(list(data.values()), safe=False)
        elif format_type == 'csv':
            # در اینجا می‌توانید CSV تولید کنید
            return JsonResponse({'message': 'CSV export not implemented yet'})
        else:
            return JsonResponse({'error': 'Invalid format'}, status=400)
