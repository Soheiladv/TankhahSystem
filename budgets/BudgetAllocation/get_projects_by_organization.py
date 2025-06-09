from django.http import JsonResponse
from django.views.decorators.http import require_GET
from core.models import Project, Organization
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from budgets.models import BudgetItem
from django.db.models import Sum
from decimal import Decimal

import logging

logger = logging.getLogger(__name__)

@require_GET
@login_required
def get_projects_by_organization(request):
    organization_id = request.GET.get('organization_id')
    if not organization_id:
        return JsonResponse({'projects': []}, status=400)

    try:
        organization = Organization.objects.get(id=organization_id)
        # فرض بر این است که Project رابطه ManyToMany با Organization دارد
        projects = Project.objects.filter(
            organizations=organization,  # فیلتر پروژه‌های مرتبط
            is_active=True
        ).values('id', 'name').order_by('name')
        return JsonResponse({'projects': list(projects)})
    except Organization.DoesNotExist:
        return JsonResponse({'projects': []}, status=404)
    except Exception as e:
        logger.error(f"Error fetching projects for organization {organization_id}: {e}")
        return JsonResponse({'projects': []}, status=500)

def get_budget_items_by_organization(request):
    organization_id = request.GET.get('organization_id')
    budget_period_id = request.GET.get('budget_period_id')
    if not organization_id or not budget_period_id:
        return JsonResponse({'budget_items': [], 'total_budget': 0})

    budget_items = BudgetItem.objects.filter(
        organization_id=organization_id,
        budget_period_id=budget_period_id,
        is_active=True
    ).select_related('organization')

    total_budget = budget_items.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    data = [{
        'id': item.id,
        'name': item.name,
        'organization_name': item.organization.name
    } for item in budget_items]

    return JsonResponse({'budget_items': data, 'total_budget': float(total_budget)})

def get_budget_item_remaining(request):
    budget_item_id = request.GET.get('budget_item_id')
    if not budget_item_id:
        return JsonResponse({'remaining_amount': 0})

    try:
        budget_item = BudgetItem.objects.get(id=budget_item_id, is_active=True)
        remaining = budget_item.get_remaining_amount()
        return JsonResponse({'remaining_amount': float(remaining)})
    except BudgetItem.DoesNotExist:
        return JsonResponse({'remaining_amount': 0})

def get_budget_item_details(request):
    budget_item_id = request.GET.get('budget_item_id')
    if not budget_item_id:
        return JsonResponse({'total_amount': 0, 'remaining_amount': 0})

    try:
        budget_item = BudgetItem.objects.get(id=budget_item_id, is_active=True)
        return JsonResponse({
            'total_amount': float(budget_item.total_amount),
            'remaining_amount': float(budget_item.get_remaining_amount())
        })
    except BudgetItem.DoesNotExist:
        return JsonResponse({'total_amount': 0, 'remaining_amount': 0})