from django.http import JsonResponse
from core.models import Project

def get_projects_by_organization(request):
    org_id = request.GET.get('organization_id')
    if org_id:
        try:
            projects = Project.objects.filter(
                organizations__id=org_id,
                is_active=True
            ).values('id', 'name')
            return JsonResponse({'projects': list(projects)})
        except ValueError:
            pass
    return JsonResponse({'projects': []})