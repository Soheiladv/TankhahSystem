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
from tankhah.models import Factor, TankhahDocument, FactorDocument, FactorItem, create_budget_transaction
from tankhah.models import Tankhah
from tankhah.forms import FactorDocumentForm
logger = logging.getLogger('tankhah_older')

from django.views.decorators.http import require_GET
from budgets.budget_calculations import get_project_total_budget, get_project_used_budget,get_project_remaining_budget, get_tankhah_total_budget,get_tankhah_remaining_budget,get_tankhah_used_budget
# فقط لاگ‌های سطح INFO و بالاتر
logging.basicConfig(level=logging.INFO)
import  json


# def get_tankhah_budget_info(request):
#     tankhah_id = request.GET.get('tankhah_id')
#     if not tankhah_id:
#         logger.error("No tankhah_id provided in get_tankhah_budget_info")
#         return JsonResponse({'error': 'Tankhah ID is required'}, status=400)
#
#     try:
#         tankhah = Tankhah.objects.get(id=tankhah_id)
#         project = tankhah.project
#         budget_info = {
#             'project_name': project.name,
#             'project_budget': str(get_project_total_budget(project)),
#             'project_consumed': str(get_project_used_budget(project)),
#             'project_returned': str(
#                 BudgetTransaction.objects.filter(
#                     allocation__project_allocations__project=project,
#                     transaction_type='RETURN'
#                 ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#             ),
#             'project_remaining': str(get_project_remaining_budget(project)),
#             'tankhah_budget': str(get_tankhah_total_budget(tankhah)),
#             'tankhah_consumed': str(get_tankhah_used_budget(tankhah)),
#             'tankhah_remaining': str(get_tankhah_remaining_budget(tankhah)),
#             }
#         logger.info(f"Budget info retrieved for tankhah {tankhah.number}: {budget_info}")
#         return JsonResponse(budget_info)
#     except Tankhah.DoesNotExist:
#         logger.error(f"Tankhah with ID {tankhah_id} not found")
#         return JsonResponse({'error': 'Tankhah not found'}, status=404)
#     except Exception as e:
#         logger.error(f"Error in get_tankhah_budget_info: {e}")
#         return JsonResponse({'error': str(e)}, status=500)

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

class FactorCreateView(CreateView):
    model = Factor
    form_class = FactorForm
    success_url = reverse_lazy('factor_list')
    template_name = 'tankhah/factor_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.request.GET.get('tankhah') or self.request.POST.get('tankhah')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.get(pk=tankhah_id)
            except Tankhah.DoesNotExist:
                logger.warning(f"Tankhah {tankhah_id} not found")
        kwargs['formset'] = FactorItemFormSet(
            self.request.POST or None,
            instance=self.object,
            prefix='items'
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form_kwargs = self.get_form_kwargs()
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='factor_docs')

        tankhah = form_kwargs.get('tankhah')
        context['budget_info'] = {'tankhah_remaining': 0, 'project_total': 0, 'project_consumed': 0}
        if tankhah:
            try:
                context['budget_info'] = {
                    'tankhah_remaining': get_tankhah_remaining_budget(tankhah),
                    'project_total': get_project_total_budget(tankhah.project) if tankhah.project else Decimal('0'),
                    'project_consumed': (
                            get_project_total_budget(tankhah.project) - get_tankhah_remaining_budget(tankhah)
                    ) if tankhah.project else Decimal('0'),
                    'tankhah_initial': tankhah.budget_allocation.allocated_amount if tankhah.budget_allocation else Decimal(
                        '0'),
                }
            except Exception as e:
                logger.error(f"Budget info error: {str(e)}")

        context['title'] = 'ایجاد فاکتور'
        return context

    def form_valid(self, form):
        item_formset = form.formset
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')

        if not (form.is_valid() and item_formset.is_valid() and document_form.is_valid()):
            logger.error(
                f"Form errors: form={form.errors}, item_formset={item_formset.errors}, document_form={document_form.errors}")
            return self.form_invalid(form)

        tankhah = form.cleaned_data['tankhah']
        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'تنخواه انتخاب‌شده در وضعیت مجاز نیست.')
            return self.form_invalid(form)

        total_items_amount = Decimal('0')
        valid_items = 0
        for item_form in item_formset:
            if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                total_items_amount += item_form.cleaned_data['amount']
                valid_items += 1

        if valid_items == 0:
            messages.error(self.request, 'حداقل یک آیتم معتبر باید وجود داشته باشد.')
            return self.form_invalid(form)

        form_amount = form.cleaned_data['amount']
        if abs(total_items_amount - form_amount) > 0.01:
            messages.error(self.request,
                           f'مبلغ کل فاکتور ({form_amount}) با مجموع آیتم‌ها ({total_items_amount}) مطابقت ندارد.')
            return self.form_invalid(form)

        remaining_budget = get_tankhah_remaining_budget(tankhah)
        if total_items_amount > remaining_budget:
            messages.error(self.request,
                           f'مبلغ فاکتور ({total_items_amount}) بیشتر از بودجه باقی‌مانده تنخواه ({remaining_budget}) است.')
            return self.form_invalid(form)

        allocation = tankhah.budget_allocation
        if allocation.get_remaining_amount() < total_items_amount:
            messages.error(
                self.request,
                f'بودجه باقی‌مانده تخصیص ({allocation.get_remaining_amount()}) کمتر از مبلغ فاکتور ({total_items_amount}) است.'
            )
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                factor = form.save(commit=False)
                factor.created_by = self.request.user
                factor.status = 'DRAFT'
                factor.amount = total_items_amount
                factor.save()

                item_formset.instance = factor
                item_formset.save()

                files = self.request.FILES.getlist('factor_docs-files')
                for file in files:
                    FactorDocument.objects.create(factor=factor, file=file)

                create_budget_transaction(
                    allocation=allocation,
                    transaction_type='CONSUMPTION',
                    amount=total_items_amount,
                    related_obj=factor,
                    created_by=self.request.user,
                    description=f"مصرف بودجه توسط فاکتور {factor.number}",
                    transaction_id=f"TX-FAC-{factor.number}"
                )

                messages.success(self.request, 'فاکتور با موفقیت ایجاد شد.')
                return super().form_valid(form)

        except Exception as e:
            logger.error(f"Error saving factor: {str(e)}", exc_info=True)
            messages.error(self.request, 'خطایی در ذخیره فاکتور رخ داد. لطفاً دوباره تلاش کنید.')
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid: form={form.errors}, item_formset={form.formset.errors}")
        return self.render_to_response(
            self.get_context_data(form=form, item_formset=form.formset)
        )

    def handle_no_permission(self):
        messages.error(self.request, 'شما مجوز لازم برای ایجاد فاکتور را ندارید.')
        return redirect('home')

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



