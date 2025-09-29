from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.models import Organization, Project

@csrf_exempt
@require_http_methods(["GET"])
def simple_organizations_api(request):
    """API ساده برای دریافت لیست سازمان‌ها"""
    try:
        organizations = Organization.objects.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(organizations), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def simple_projects_api(request):
    """API ساده برای دریافت لیست پروژه‌ها"""
    try:
        projects = Project.objects.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse(list(projects), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
