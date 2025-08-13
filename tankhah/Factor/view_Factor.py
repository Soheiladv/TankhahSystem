from django.utils.translation import gettext_lazy as _
import logging
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions.comparison import Coalesce
from django.forms import DecimalField, inlineformset_factory
from django.http import JsonResponse
from django.shortcuts import redirect
from budgets.models import   BudgetTransaction
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, View
from core.PermissionBase import PermissionBaseView
from django.contrib import messages
from tankhah.Factor.forms_Factor import FactorForm, FactorItemForm, FactorItemFormSet
from tankhah.models import Factor, TankhahDocument, FactorDocument, FactorItem
from budgets.budget_calculations import create_budget_transaction

from tankhah.models import Tankhah
from tankhah.forms import FactorDocumentForm
logger = logging.getLogger('tankhah_older')
from budgets.budget_calculations import get_project_total_budget, get_project_used_budget,get_project_remaining_budget, get_tankhah_total_budget,get_tankhah_remaining_budget,get_tankhah_used_budget
# فقط لاگ‌های سطح INFO و بالاتر
logging.basicConfig(level=logging.INFO)
import  json

class TankhahBudgetInfoAjaxView(PermissionBaseView, View):
    http_method_names = ['get']
    permission_codenames = ['tankhah.a_factor_add'] # User needs factor add permission to see budget?

    def get(self, request, tankhah_id, *args, **kwargs):
        # Basic permission check first
        # if not self.has_permission(): # Assuming has_permission checks request.user
        #     return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

        from django.http import Http404
        try:
            # Get Tankhah with related fields needed for budget calculation
            from django.shortcuts import get_object_or_404
            tankhah = get_object_or_404(
                Tankhah.objects.select_related(
                    'project',
                    'subproject',
                    'project_budget_allocation', # Direct link if available
                    'budget_allocation', # Fallback link
                    'project_budget_allocation__budget_allocation', # Get parent allocation
                ),
                pk=tankhah_id
            )

            # --- Determine the relevant BudgetAllocation ---
            target_allocation_instance = None
            if tankhah.project_budget_allocation:
                target_allocation_instance = tankhah.project_budget_allocation.budget_allocation
                project_allocation_amount = tankhah.project_budget_allocation.allocated_amount
                logger.debug(f"Using BudgetAllocation {tankhah.project_budget_allocation.id} linked to BudgetAllocation {target_allocation_instance.id}")
            elif tankhah.budget_allocation:
                 # Less ideal, assumes Tankhah directly uses a main allocation
                 target_allocation_instance = tankhah.budget_allocation
                 project_allocation_amount = target_allocation_instance.allocated_amount # Use the whole allocation amount? Risky.
                 logger.warning(f"Tankhah {tankhah.id} using direct BudgetAllocation {target_allocation_instance.id}. Budget calculation might be less precise.")
            else:
                 logger.error(f"Tankhah {tankhah.id} has no link to ProjectBudgetAllocation or BudgetAllocation.")
                 return JsonResponse({'success': False, 'error': 'تنخواه به هیچ تخصیص بودجه‌ای متصل نیست.'}, status=400)

            if not target_allocation_instance:
                 logger.error(f"Could not determine target BudgetAllocation for Tankhah {tankhah.id}")
                 return JsonResponse({'success': False, 'error': 'تخصیص بودجه مبنا برای تنخواه یافت نشد.'}, status=400)


            # --- Calculate Project/Subproject Budget Remaining ---
            # This uses the BudgetTransaction model linked to the target_allocation_instance
            consumed_q = Q(allocation=target_allocation_instance, transaction_type='CONSUMPTION')
            returned_q = Q(allocation=target_allocation_instance, transaction_type='RETURN')

            consumption_total = BudgetTransaction.objects.filter(consumed_q).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
            )['total']

            return_total = BudgetTransaction.objects.filter(returned_q).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
            )['total']

            # Remaining = Original Allocation - Consumed + Returned
            # What is the "Original Allocation" amount here? It should be the amount from ProjectBudgetAllocation
            base_amount_for_remaining = project_allocation_amount if tankhah.project_budget_allocation else target_allocation_instance.allocated_amount
            project_remaining_budget = base_amount_for_remaining - consumption_total + return_total
            logger.debug(f"Budget for Allocation {target_allocation_instance.id}: Base={base_amount_for_remaining}, Consumed={consumption_total}, Returned={return_total}, Remaining={project_remaining_budget}")


            # --- Calculate Tankhah Specific Remaining ---
            # Sum of *approved* factors for this *specific* Tankhah
            # Note: This requires factors to have a status indicating approval/payment
            factors_approved_sum = Factor.objects.filter(
                tankhah=tankhah,
                status__in=['APPROVED', 'PAID'] # Adjust statuses as needed
            ).aggregate(
                total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
            )['total']

            tankhah_remaining_budget = tankhah.amount - factors_approved_sum
            logger.debug(f"Tankhah {tankhah.id} Budget: Amount={tankhah.amount}, ApprovedFactorsSum={factors_approved_sum}, Remaining={tankhah_remaining_budget}")


            data = {
                'success': True,
                'project_name': tankhah.project.name if tankhah.project else '-',
                'subproject_name': tankhah.subproject.name if tankhah.subproject else None,
                # Use the calculated project/subproject remaining from transactions
                'project_remaining_budget': project_remaining_budget,
                # Use the tankhah's own amount and approved factors sum
                'tankhah_amount': tankhah.amount,
                'tankhah_consumed_approved': factors_approved_sum, # Sum of approved factors
                'tankhah_remaining': tankhah_remaining_budget, # Tankhah amount - approved factors
            }
            return JsonResponse(data, encoder=DjangoJSONEncoder)

        except Http404:
            logger.warning(f"Tankhah not found: ID={tankhah_id}")
            return JsonResponse({'success': False, 'error': 'تنخواه یافت نشد.'}, status=404)
        except Exception as e:
            logger.error(f"Error fetching budget info for Tankhah {tankhah_id}: {e}", exc_info=True)
            return JsonResponse({'success': False, 'error': 'خطای داخلی در دریافت اطلاعات بودجه.'}, status=500)
class BudgetCheckView(View):
    def post(self, request):
        tankhah_id = request.POST.get('tankhah_id')
        items = request.POST.getlist('items[]')
        try:
            tankhah = Tankhah.objects.get(id=tankhah_id)
            total_amount = Decimal('0')
            for item in items:
                item_data = json.loads(item)
                total_amount += Decimal(item_data['quantity']) * Decimal(item_data['unit_price'])
            remaining_budget = get_tankhah_remaining_budget(tankhah)
            new_remaining = remaining_budget - total_amount
            return JsonResponse({
                'status': 'success',
                'initial_budget': float(tankhah.budget_allocation.allocated_amount),
                'remaining_budget': float(new_remaining),
                'total_amount': float(total_amount),
                'is_valid': new_remaining >= 0
            })
        except Exception as e:
            logger.error(f"Budget check error: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



