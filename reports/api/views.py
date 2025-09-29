from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
import json

from core.models import Organization, Project
from budgets.models import BudgetPeriod


@method_decorator(csrf_exempt, name='dispatch')
class OrganizationsAPIView(View):
    """API برای دریافت لیست سازمان‌ها"""
    
    def get(self, request):
        try:
            organizations = Organization.objects.filter(is_active=True).values('id', 'name', 'code')
            return JsonResponse(list(organizations), safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProjectsAPIView(View):
    """API برای دریافت لیست پروژه‌ها"""
    
    def get(self, request):
        try:
            projects = Project.objects.filter(is_active=True).values('id', 'name', 'code')
            return JsonResponse(list(projects), safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class BudgetPeriodsAPIView(View):
    """API برای دریافت لیست دوره‌های بودجه"""
    
    def get(self, request):
        periods = BudgetPeriod.objects.filter(is_active=True).values('id', 'name', 'start_date', 'end_date')
        return JsonResponse(list(periods), safe=False)


@method_decorator(login_required, name='dispatch')
class DashboardDataAPIView(View):
    """API برای دریافت داده‌های داشبورد"""
    
    def get(self, request):
        # دریافت فیلترها
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        organization_id = request.GET.get('organization')
        project_id = request.GET.get('project')
        
        # آمار کلی بودجه
        from reports.dashboard.views import DashboardMainView
        dashboard_view = DashboardMainView()
        
        # دریافت آمار
        budget_stats = dashboard_view.get_budget_statistics()
        tankhah_stats = dashboard_view.get_tankhah_statistics()
        factor_stats = dashboard_view.get_factor_statistics()
        payment_stats = dashboard_view.get_payment_statistics()
        return_stats = dashboard_view.get_budget_return_statistics()
        chart_data = dashboard_view.get_chart_data()
        
        return JsonResponse({
            'budget_stats': budget_stats,
            'tankhah_stats': tankhah_stats,
            'factor_stats': factor_stats,
            'payment_stats': payment_stats,
            'return_stats': return_stats,
            'chart_data': chart_data
        })


@method_decorator(login_required, name='dispatch')
class ExportDataAPIView(View):
    """API برای صادرات داده‌ها"""
    
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
