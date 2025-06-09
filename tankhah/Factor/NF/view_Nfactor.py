import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect, render # Import render
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.forms import inlineformset_factory
from django.db.models import Sum
# Assuming these base classes, models, forms, and functions exist
from core.views import PermissionBaseView # Your permission checking base view
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm, FactorDocumentForm, TankhahDocumentForm
from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem, FactorDocument, TankhahDocument, \
    create_budget_transaction, FactorHistory
from accounts.models import CustomUser # Your user model
from core.models import WorkflowStage # Your workflow stage model
from budgets.models import BudgetTransaction, BudgetAllocation
from budgets.budget_calculations import (
    get_project_total_budget, get_project_used_budget, get_project_remaining_budget,
    get_tankhah_total_budget, get_tankhah_remaining_budget, get_tankhah_used_budget,
    # Your budget transaction helper
)


# --- End Assumptions ---

logger = logging.getLogger(__name__)

# Define the inline formset factory (can be defined globally or inside the view methods)
FactorItemFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemForm,
    extra=1,          # Start with one extra form
    can_delete=True,
    # min_num=1,        # Enforce at least one item
    # validate_min=True # Validate the minimum number
)

class New_FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'  # Your template path
    success_url = reverse_lazy('factor_list') # Use your URL namespace and name
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_add'] # Use your actual permission codename
    permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')
    check_organization = True # Assuming your PermissionBaseView uses this

    def get_form_kwargs(self):
        """Pass user and pre-selected tankhah (if any) to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id') or self.request.POST.get('tankhah')

        if tankhah_id:
            try:
                # Fetch tankhah with related objects needed later
                tankhah = Tankhah.objects.select_related('project', 'organization', 'current_stage').get(id=tankhah_id)
                kwargs['tankhah'] = tankhah # Pass the instance
                logger.info(f"Tankhah {tankhah_id} ({tankhah.number}) passed to form kwargs.")
            except (Tankhah.DoesNotExist, ValueError):
                logger.error(f"Invalid or non-existent tankhah_id '{tankhah_id}' provided in request.", exc_info=True)
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        """Prepare context: forms, formset, budget info."""
        context = super().get_context_data(**kwargs)
        form = context.get('form')
        tankhah = None

        # Determine the current Tankhah object
        if form and hasattr(form, 'cleaned_data') and form.cleaned_data.get('tankhah'):
             tankhah = form.cleaned_data['tankhah'] # From POST data after clean
        elif form and hasattr(form, 'initial') and form.initial.get('tankhah'):
            tankhah = form.initial['tankhah'] # From initial data (e.g., passed in kwargs)
        elif form and hasattr(form, 'instance') and form.instance.tankhah_id:
             # If editing an existing instance (though this is CreateView)
             try:
                 tankhah = Tankhah.objects.select_related('project').get(pk=form.instance.tankhah_id)
             except Tankhah.DoesNotExist:
                 pass
        else: # Fallback for initial GET request with ID in URL/GET params
             tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
             if tankhah_id:
                 tankhah = Tankhah.objects.select_related('project').filter(id=tankhah_id).first()

        # Initialize formset and document forms
        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES, prefix='tankhah_docs')
        else:
            # Pass tankhah instance to formset if editing? Not applicable for CreateView usually.
            # instance = context.get('object') # Usually None in CreateView initial GET
            context['formset'] = FactorItemFormSet(prefix='items') # No instance for new factor
            context['document_form'] = FactorDocumentForm(prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(prefix='tankhah_docs')

        # Calculate Budget Info
        budget_info = None
        tankhah_remaining_budget = Decimal('0')
        # ... (rest of budget calculation logic from your preferred version - using helpers) ...
        if tankhah:
            try:
                project = tankhah.project
                budget_info = {
                    'project_name': project.name,
                    'project_budget': get_project_total_budget(project),
                    'project_consumed': get_project_used_budget(project),
                    'project_returned': BudgetTransaction.objects.filter(
                        allocation__project_allocations__project=project,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
                    'project_remaining': get_project_remaining_budget(project),
                    'tankhah_budget': get_tankhah_total_budget(tankhah),
                    'tankhah_consumed': get_tankhah_used_budget(tankhah),
                    'tankhah_remaining': get_tankhah_remaining_budget(tankhah),
                }
                tankhah_remaining_budget = budget_info.get('tankhah_remaining', Decimal('0')) # Use .get()
                logger.info(f"Budget info calculated for Tankhah {tankhah.number}: Remaining={tankhah_remaining_budget}")
            except Exception as e:
                logger.error(f"Error calculating budget info for Tankhah {tankhah.number}: {e}", exc_info=True)
                messages.error(self.request, _("خطا در محاسبه اطلاعات بودجه."))
                budget_info = None

        context.update({
            'title': _('ایجاد فاکتور جدید'),
            'tankhah': tankhah,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'budget_info': budget_info,
            'tankhah_remaining_budget': tankhah_remaining_budget,
        })
        # logger.debug(f"Final context data prepared: {context}")
        return context

    def form_valid(self, form):
        """Process valid forms: validate all, check budget, save atomically."""
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']
        tankhah = form.cleaned_data['tankhah']
        is_draft = 'save_draft' in self.request.POST

        logger.info(f"Processing form_valid for Factor creation linked to Tankhah {tankhah.number}")

        save_incomplete = 'save_draft_incomplete' in self.request.POST
        save_final = 'save_final_draft' in self.request.POST or not save_incomplete
        logger.info(f"Form submission type: {'Incomplete Draft' if save_incomplete else 'Final Draft'}")

        # چک اولیه تنخواه
        try:
            initial_stage = WorkflowStage.objects.order_by('order').first()
            initial_stage_order = initial_stage.order if initial_stage else 0
            if not tankhah.current_stage or tankhah.current_stage.order != initial_stage_order:
                stage_name = tankhah.current_stage.name if tankhah.current_stage else _("نامشخص")
                initial_name = initial_stage.name if initial_stage else _("تعریف نشده")
                msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ثبت کنید. مرحله فعلی تنخواه: {}').format(
                    initial_name, stage_name
                )
                messages.error(self.request, msg)
                logger.warning(f"Invalid stage order for tankhah {tankhah.number}: current_stage={stage_name}")
                return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Error checking workflow stage for tankhah {tankhah.number}: {e}", exc_info=True)
            messages.error(self.request, _('خطا در بررسی مرحله گردش کار تنخواه.'))
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request,
                           _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))
            logger.warning(f"Invalid status for tankhah {tankhah.number}: {tankhah.status}")
            return self.form_invalid(form)

        # چک تخصیص بودجه تنخواه
        if not tankhah.project_budget_allocation:
            messages.error(self.request, _('تنخواه انتخاب‌شده تخصیص بودجه معتبر ندارد.'))
            logger.error(f"No project_budget_allocation for tankhah {tankhah.number}")
            return self.form_invalid(form)

        # اعتبارسنجی فرم‌ها
        is_item_formset_valid = item_formset.is_valid()
        is_doc_form_valid = document_form.is_valid()
        is_tankhah_doc_form_valid = tankhah_document_form.is_valid()

        if not (is_item_formset_valid and is_doc_form_valid and is_tankhah_doc_form_valid):
            logger.error("Validation failed for formset or document forms.")
            if not is_item_formset_valid:
                logger.error(f"Item formset errors: {item_formset.errors} {item_formset.non_form_errors()}")
            if not is_doc_form_valid:
                logger.error(f"Factor document form errors: {document_form.errors}")
            if not is_tankhah_doc_form_valid:
                logger.error(f"Tankhah document form errors: {tankhah_document_form.errors}")
            messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم ردیف‌ها یا اسناد را بررسی و اصلاح کنید.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if not valid_item_forms:
            logger.warning("No valid items submitted in the formset.")
            messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # محاسبه مبلغ و چک بودجه
        total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
        factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))
        tolerance = Decimal('0.01')

        logger.info(f"Calculated total items amount: {total_items_amount}, Factor form amount: {factor_form_amount}")
        if abs(total_items_amount - factor_form_amount) > tolerance:
            msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
                factor_form_amount, total_items_amount
            )
            messages.error(self.request, msg)
            logger.error(f"Amount mismatch: Factor={factor_form_amount}, Items={total_items_amount}")
            form.add_error('amount', msg)
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        try:
            tankhah_remaining = get_tankhah_remaining_budget(tankhah)
            logger.debug(
                f"Checking budget for tankhah {tankhah.number}: Remaining={tankhah_remaining}, Requested={total_items_amount}")
            if tankhah_remaining == Decimal('0') and tankhah.project_budget_allocation:
                logger.warning(f"Zero remaining budget for tankhah {tankhah.number}, possible calculation error")
                messages.error(self.request, _('بودجه باقی‌مانده تنخواه صفر است. لطفاً تخصیص بودجه را بررسی کنید.'))
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        formset=item_formset,
                        document_form=document_form,
                        tankhah_document_form=tankhah_document_form
                    )
                )
            if total_items_amount > tankhah_remaining:
                msg = _('مبلغ فاکتور ({:,}) از بودجه باقی‌مانده تنخواه ({:,}) بیشتر است.').format(
                    total_items_amount, tankhah_remaining
                )
                messages.error(self.request, msg)
                logger.error(
                    f"Budget Exceeded: Factor Amount={total_items_amount}, Tankhah Remaining={tankhah_remaining}")
                form.add_error(None, msg)
                return self.render_to_response(
                    self.get_context_data(
                        form=form,
                        formset=item_formset,
                        document_form=document_form,
                        tankhah_document_form=tankhah_document_form
                    )
                )
        except Exception as e:
            logger.error(f"Error getting remaining tankhah budget in view: {e}", exc_info=True)
            messages.error(self.request, _('خطا در بررسی بودجه تنخواه.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # پیدا کردن تخصیص بودجه
        try:
            budget_allocation_instance = tankhah.project_budget_allocation
            if not budget_allocation_instance:
                raise BudgetAllocation.DoesNotExist("تخصیص بودجه معتبر یافت نشد.")
        except BudgetAllocation.DoesNotExist:
            logger.error(f"No valid BudgetAllocation found for tankhah {tankhah.number}")
            messages.error(self.request, _('تخصیص بودجه معتبر برای این تنخواه یافت نشد.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # چک قفل بودن دوره بودجه
        budget_period = budget_allocation_instance.budget_period
        is_locked, lock_message = budget_period.is_period_locked
        if is_locked:
            messages.error(self.request, _("امکان ثبت هزینه وجود ندارد: {}").format(lock_message))
            logger.error(f"Budget period locked for tankhah {tankhah.number}: {lock_message}")
            raise ValidationError(_("عملیات به دلیل قفل بودن دوره بودجه مجاز نیست."))

        # ذخیره اتمی
        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.status = 'DRAFT' if is_draft else 'PENDING'
                self.object.created_by = self.request.user
                self.object.amount = total_items_amount if save_final else factor_form_amount
                self.object.save()
                logger.info(
                    f"Factor object saved (pk={self.object.pk}, number={self.object.number}, type={'Final' if save_final else 'Incomplete'})")

                # ذخیره تاریخچه فاکتور
                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=self.request.user,
                    new_data={
                        'amount': str(self.object.amount),
                        'status': self.object.status,
                        'items': [
                            {
                                'id': item.id,
                                'description': item.description,
                                'quantity': str(item.quantity),
                                'unit_price': str(item.unit_price),
                                'amount': str(item.amount),
                            } for item in self.object.items.all()
                        ],
                        'documents': [
                            {'id': doc.id, 'file': str(doc.file)} for doc in self.object.documents.all()
                        ],
                    },
                    description=f"ایجاد فاکتور {self.object.number} توسط {self.request.user.username}."
                )
                logger.info(f"Factor history recorded for creation of Factor pk={self.object.pk}.")

                # ذخیره آیتم‌ها
                items_saved_count = 0
                for item_form in valid_item_forms:
                    item = item_form.save(commit=False)
                    item.factor = self.object
                    item.save()
                    items_saved_count += 1
                logger.info(f"Saved {items_saved_count} factor items for Factor pk={self.object.pk}.")

                # ذخیره اسناد فاکتور
                factor_files = document_form.cleaned_data.get('files', [])
                docs_saved_count = 0
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)
                    docs_saved_count += 1
                if docs_saved_count:
                    logger.info(f"Saved {docs_saved_count} factor documents.")

                # ذخیره اسناد تنخواه
                tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
                tdocs_saved_count = 0
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
                    tdocs_saved_count += 1
                if tdocs_saved_count:
                    logger.info(f"Saved {tdocs_saved_count} tankhah documents.")

                # ایجاد تراکنش بودجه برای ذخیره نهایی
                if save_final:
                    logger.info("Creating budget transaction for final draft save.")
                    create_budget_transaction(
                        allocation=budget_allocation_instance,
                        transaction_type='CONSUMPTION',
                        amount=total_items_amount,
                        related_obj=self.object,
                        created_by=self.request.user,
                        description=f"ایجاد فاکتور {self.object.number}",
                        transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
                    )
                    logger.info(
                        f"Budget transaction created for Factor pk={self.object.pk}, amount={total_items_amount}.")

        except ValidationError as ve:
            logger.error(f"Validation Error during atomic save: {ve}", exc_info=True)
            messages.error(self.request, _('خطای اعتبارسنجی هنگام ذخیره: {}').format(ve))
            if hasattr(ve, 'error_dict'):
                for field, errors in ve.error_dict.items():
                    if field == '__all__':
                        form.add_error(None, errors)
                    else:
                        if field in form.fields:
                            form.add_error(field, errors)
                        else:
                            item_formset.add_error(None, f"{field}: {errors}")
            else:
                form.add_error(None, str(ve))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        except Exception as e:
            logger.error(f"Unexpected error during atomic transaction for saving factor: {e}", exc_info=True)
            messages.error(self.request, _('خطای پیش‌بینی نشده‌ای هنگام ذخیره اطلاعات رخ داد.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # موفقیت
        success_message = _('فاکتور با موفقیت ذخیره شد.') if save_final else _(
            'فاکتور به‌صورت موقت ذخیره شد. لطفاً بعداً آن را تکمیل و نهایی کنید.'
        )
        messages.success(self.request, success_message)
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """Handle cases where the main FactorForm is invalid."""
        logger.warning(f"Main FactorForm is invalid. Errors: {form.errors}")
        # Get context again to ensure formset/doc forms are included, potentially with POST data
        context = self.get_context_data(form=form)
        item_formset = context['formset'] # Should be bound if it was a POST request
        if item_formset.is_bound:
             logger.warning(f"Item formset errors (in form_invalid): {item_formset.errors}")
        messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم اصلی فاکتور را اصلاح کنید.'))
        return self.render_to_response(context)

    def handle_no_permission(self):
        """Handle permission denied cases."""
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Permission denied for user {self.request.user} trying to add factor.")
        # Redirect to a safe page
        # default_url = reverse_lazy('dashboard') # Or your app's index
        # referer = self.request.META.get('HTTP_REFERER')
        # return redirect(referer or default_url)
        return super().handle_no_permission() # Or use base class handling

   # def form_valid(self, form):
    #     """Process valid forms: validate all, check budget, save atomically."""
    #     context = self.get_context_data()
    #     item_formset = context['formset']
    #     document_form = context['document_form']
    #     tankhah_document_form = context['tankhah_document_form']
    #     tankhah = form.cleaned_data['tankhah']
    #     is_draft = 'save_draft' in self.request.POST
    #
    #     logger.info(f"Processing form_valid for Factor creation linked to Tankhah {tankhah.number}")
    #
    #     save_incomplete = 'save_draft_incomplete' in self.request.POST
    #     save_final = 'save_final_draft' in self.request.POST or not save_incomplete
    #     logger.info(f"Form submission type: {'Incomplete Draft' if save_incomplete else 'Final Draft'}")
    #
    #     # چک اولیه تنخواه
    #     try:
    #         initial_stage = WorkflowStage.objects.order_by('order').first()
    #         initial_stage_order = initial_stage.order if initial_stage else 0
    #         if not tankhah.current_stage or tankhah.current_stage.order != initial_stage_order:
    #             stage_name = tankhah.current_stage.name if tankhah.current_stage else _("نامشخص")
    #             initial_name = initial_stage.name if initial_stage else _("تعریف نشده")
    #             msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ثبت کنید. مرحله فعلی تنخواه: {}').format(
    #                 initial_name, stage_name
    #             )
    #             messages.error(self.request, msg)
    #             logger.warning(f"Invalid stage order for tankhah {tankhah.number}: current_stage={stage_name}")
    #             return self.form_invalid(form)
    #     except Exception as e:
    #         logger.error(f"Error checking workflow stage for tankhah {tankhah.number}: {e}", exc_info=True)
    #         messages.error(self.request, _('خطا در بررسی مرحله گردش کار تنخواه.'))
    #         return self.form_invalid(form)
    #
    #     if tankhah.status not in ['DRAFT', 'PENDING']:
    #         messages.error(self.request,
    #                        _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))
    #         logger.warning(f"Invalid status for tankhah {tankhah.number}: {tankhah.status}")
    #         return self.form_invalid(form)
    #
    #     # چک تخصیص بودجه تنخواه
    #     if not tankhah.project_budget_allocation:
    #         messages.error(self.request, _('تنخواه انتخاب‌شده تخصیص بودجه معتبر ندارد.'))
    #         logger.error(f"No project_budget_allocation for tankhah {tankhah.number}")
    #         return self.form_invalid(form)
    #
    #     # اعتبارسنجی فرم‌ها
    #     is_item_formset_valid = item_formset.is_valid()
    #     is_doc_form_valid = document_form.is_valid()
    #     is_tankhah_doc_form_valid = tankhah_document_form.is_valid()
    #
    #     if not (is_item_formset_valid and is_doc_form_valid and is_tankhah_doc_form_valid):
    #         logger.error("Validation failed for formset or document forms.")
    #         if not is_item_formset_valid:
    #             logger.error(f"Item formset errors: {item_formset.errors} {item_formset.non_form_errors()}")
    #         if not is_doc_form_valid:
    #             logger.error(f"Factor document form errors: {document_form.errors}")
    #         if not is_tankhah_doc_form_valid:
    #             logger.error(f"Tankhah document form errors: {tankhah_document_form.errors}")
    #         messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم ردیف‌ها یا اسناد را بررسی و اصلاح کنید.'))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
    #     if not valid_item_forms:
    #         logger.warning("No valid items submitted in the formset.")
    #         messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     # محاسبه مبلغ و چک بودجه
    #     total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
    #     factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))
    #     tolerance = Decimal('0.01')
    #
    #     logger.info(f"Calculated total items amount: {total_items_amount}, Factor form amount: {factor_form_amount}")
    #     if abs(total_items_amount - factor_form_amount) > tolerance:
    #         msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
    #             factor_form_amount, total_items_amount
    #         )
    #         messages.error(self.request, msg)
    #         logger.error(f"Amount mismatch: Factor={factor_form_amount}, Items={total_items_amount}")
    #         form.add_error('amount', msg)
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     try:
    #         tankhah_remaining = get_tankhah_remaining_budget(tankhah)
    #         if total_items_amount > tankhah_remaining:
    #             msg = _('مبلغ فاکتور ({:,}) از بودجه باقی‌مانده تنخواه ({:,}) بیشتر است.').format(
    #                 total_items_amount, tankhah_remaining
    #             )
    #             messages.error(self.request, msg)
    #             logger.error(
    #                 f"Budget Exceeded: Factor Amount={total_items_amount}, Tankhah Remaining={tankhah_remaining}")
    #             form.add_error(None, msg)
    #             return self.render_to_response(
    #                 self.get_context_data(
    #                     form=form,
    #                     formset=item_formset,
    #                     document_form=document_form,
    #                     tankhah_document_form=tankhah_document_form
    #                 )
    #             )
    #     except Exception as e:
    #         logger.error(f"Error getting remaining tankhah budget in view: {e}", exc_info=True)
    #         messages.error(self.request, _('خطا در بررسی بودجه تنخواه.'))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     # پیدا کردن تخصیص بودجه
    #     try:
    #         budget_allocation_instance = tankhah.project_budget_allocation
    #         if not budget_allocation_instance:
    #             raise BudgetAllocation.DoesNotExist("تخصیص بودجه معتبر یافت نشد.")
    #     except BudgetAllocation.DoesNotExist:
    #         logger.error(f"No valid BudgetAllocation found for tankhah {tankhah.number}")
    #         messages.error(self.request, _('تخصیص بودجه معتبر برای این تنخواه یافت نشد.'))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     # چک قفل بودن دوره بودجه
    #     budget_period = budget_allocation_instance.budget_period
    #     is_locked, lock_message = budget_period.is_period_locked
    #     if is_locked:
    #         messages.error(self.request, _("امکان ثبت هزینه وجود ندارد: {}").format(lock_message))
    #         logger.error(f"Budget period locked for tankhah {tankhah.number}: {lock_message}")
    #         raise ValidationError(_("عملیات به دلیل قفل بودن دوره بودجه مجاز نیست."))
    #
    #     # ذخیره اتمی
    #     try:
    #         with transaction.atomic():
    #             self.object = form.save(commit=False)
    #             self.object.status = 'DRAFT' if is_draft else 'PENDING'
    #             self.object.created_by = self.request.user
    #             self.object.amount = total_items_amount if save_final else factor_form_amount
    #             self.object.save()
    #             logger.info(
    #                 f"Factor object saved (pk={self.object.pk}, number={self.object.number}, type={'Final' if save_final else 'Incomplete'})"
    #             )
    #
    #             # ذخیره تاریخچه فاکتور
    #             FactorHistory.objects.create(
    #                 factor=self.object,
    #                 change_type=FactorHistory.ChangeType.CREATION,
    #                 changed_by=self.request.user,
    #                 new_data={
    #                     'amount': str(self.object.amount),
    #                     'status': self.object.status,
    #                     'items': [
    #                         {
    #                             'id': item.id,
    #                             'description': item.description,
    #                             'quantity': str(item.quantity),
    #                             'unit_price': str(item.unit_price),
    #                             'amount': str(item.amount),
    #                         } for item in self.object.items.all()
    #                     ],
    #                     'documents': [
    #                         {'id': doc.id, 'file': str(doc.file)} for doc in self.object.documents.all()
    #                     ],
    #                 },
    #                 description=f"ایجاد فاکتور {self.object.number} توسط {self.request.user.username}."
    #             )
    #             logger.info(f"Factor history recorded for creation of Factor pk={self.object.pk}.")
    #
    #             # ذخیره آیتم‌ها
    #             items_saved_count = 0
    #             for item_form in valid_item_forms:
    #                 item = item_form.save(commit=False)
    #                 item.factor = self.object
    #                 item.save()
    #                 items_saved_count += 1
    #             logger.info(f"Saved {items_saved_count} factor items for Factor pk={self.object.pk}.")
    #
    #             # ذخیره اسناد فاکتور
    #             factor_files = document_form.cleaned_data.get('files', [])
    #             docs_saved_count = 0
    #             for file in factor_files:
    #                 FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)
    #                 docs_saved_count += 1
    #             if docs_saved_count:
    #                 logger.info(f"Saved {docs_saved_count} factor documents.")
    #
    #             # ذخیره اسناد تنخواه
    #             tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
    #             tdocs_saved_count = 0
    #             for file in tankhah_files:
    #                 TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
    #                 tdocs_saved_count += 1
    #             if tdocs_saved_count:
    #                 logger.info(f"Saved {tdocs_saved_count} tankhah documents.")
    #
    #             # ایجاد تراکنش بودجه برای ذخیره نهایی
    #             if save_final:
    #                 logger.info("Creating budget transaction for final draft save.")
    #                 create_budget_transaction(
    #                     allocation=budget_allocation_instance,
    #                     transaction_type='CONSUMPTION',
    #                     amount=total_items_amount,
    #                     related_obj=self.object,
    #                     created_by=self.request.user,
    #                     description=f"ایجاد فاکتور {self.object.number}",
    #                     transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
    #                 )
    #                 logger.info(
    #                     f"Budget transaction created for Factor pk={self.object.pk}, amount={total_items_amount}.")
    #
    #     except ValidationError as ve:
    #         logger.error(f"Validation Error during atomic save: {ve}", exc_info=True)
    #         messages.error(self.request, _('خطای اعتبارسنجی هنگام ذخیره: {}').format(ve))
    #         if hasattr(ve, 'error_dict'):
    #             for field, errors in ve.error_dict.items():
    #                 if field == '__all__':
    #                     form.add_error(None, errors)
    #                 else:
    #                     if field in form.fields:
    #                         form.add_error(field, errors)
    #                     else:
    #                         item_formset.add_error(None, f"{field}: {errors}")
    #         else:
    #             form.add_error(None, str(ve))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     except Exception as e:
    #         logger.error(f"Unexpected error during atomic transaction for saving factor: {e}", exc_info=True)
    #         messages.error(self.request, _('خطای پیش‌بینی نشده‌ای هنگام ذخیره اطلاعات رخ داد.'))
    #         return self.render_to_response(
    #             self.get_context_data(
    #                 form=form,
    #                 formset=item_formset,
    #                 document_form=document_form,
    #                 tankhah_document_form=tankhah_document_form
    #             )
    #         )
    #
    #     # موفقیت
    #     success_message = _('فاکتور با موفقیت ذخیره شد.') if save_final else _(
    #         'فاکتور به‌صورت موقت ذخیره شد. لطفاً بعداً آن را تکمیل و نهایی کنید.'
    #     )
    #     messages.success(self.request, success_message)
    #     return redirect(self.get_success_url())
    #
# class _FactorCreateView(PermissionBaseView, CreateView):
#     model = Factor
#     form_class = FactorForm
#     template_name = 'tankhah/Factors/NF/new_factor_form.html'
#     success_url = reverse_lazy('factor_list')
#     context_object_name = 'factor'
#
#     permission_codenames = ['tankhah.factor_add']
#     permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')
#     check_organization = True
#
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id') or self.request.POST.get('tankhah')
#
#         if tankhah_id:
#             try:
#                 tankhah = Tankhah.objects.select_related('project', 'organization', 'current_stage').get(id=tankhah_id)
#                 kwargs['tankhah'] = tankhah
#                 logger.info(f"Tankhah {tankhah_id} ({tankhah.number}) passed to form kwargs.")
#             except (Tankhah.DoesNotExist, ValueError):
#                 logger.error(f"Invalid or non-existent tankhah_id '{tankhah_id}' provided in request.", exc_info=True)
#                 messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
#         return kwargs
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         form = context.get('form')
#         tankhah = None
#
#         if form and hasattr(form, 'cleaned_data') and form.cleaned_data.get('tankhah'):
#             tankhah = form.cleaned_data['tankhah']
#             logger.debug(f"Tankhah from cleaned_data: {tankhah.id}")
#         elif form and hasattr(form, 'initial') and form.initial.get('tankhah'):
#             tankhah = form.initial['tankhah']
#             logger.debug(f"Tankhah from initial: {tankhah.id}")
#         elif form and hasattr(form, 'instance') and form.instance.tankhah_id:
#             try:
#                 tankhah = Tankhah.objects.select_related('project').get(pk=form.instance.tankhah_id)
#                 logger.debug(f"Tankhah from instance: {tankhah.id}")
#             except Tankhah.DoesNotExist:
#                 logger.warning("Tankhah not found in instance")
#                 pass
#         else:
#             tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
#             if tankhah_id:
#                 tankhah = Tankhah.objects.select_related('project').filter(id=tankhah_id).first()
#                 if tankhah:
#                     logger.debug(f"Tankhah from URL/GET params: {tankhah.id}")
#                 else:
#                     logger.warning(f"Tankhah not found for ID: {tankhah_id}")
#
#         if self.request.POST:
#             context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='items')
#             context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
#             context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES, prefix='tankhah_docs')
#         else:
#             context['formset'] = FactorItemFormSet(prefix='items')
#             context['document_form'] = FactorDocumentForm(prefix='factor_docs')
#             context['tankhah_document_form'] = TankhahDocumentForm(prefix='tankhah_docs')
#
#         budget_info = None
#         tankhah_remaining_budget = Decimal('0')
#         if tankhah:
#             try:
#                 project = tankhah.project
#                 if not project:
#                     raise ValueError("Tankhah does not have an associated project")
#                 logger.debug(f"Project for Tankhah {tankhah.id}: {project.id}")
#                 budget_info = {
#                     'project_name': project.name,
#                     'project_budget': get_project_total_budget(project),
#                     'project_consumed': get_project_used_budget(project),
#                     'project_returned': BudgetTransaction.objects.filter(
#                         allocation__project_allocations__project=project,
#                         transaction_type='RETURN'
#                     ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
#                     'project_remaining': get_project_remaining_budget(project),
#                     'tankhah_budget': get_tankhah_total_budget(tankhah),
#                     'tankhah_consumed': get_tankhah_used_budget(tankhah),
#                     'tankhah_remaining': get_tankhah_remaining_budget(tankhah),
#                 }
#                 tankhah_remaining_budget = budget_info.get('tankhah_remaining', Decimal('0'))
#                 logger.info(f"Budget info calculated for Tankhah {tankhah.number}: Remaining={tankhah_remaining_budget}")
#             except Exception as e:
#                 logger.error(f"Error calculating budget info for Tankhah {tankhah.number if tankhah else 'None'}: {str(e)}", exc_info=True)
#                 messages.error(self.request, _("خطا در محاسبه اطلاعات بودجه."))
#                 budget_info = None
#         else:
#             logger.warning("No Tankhah provided for budget calculations")
#
#         context.update({
#             'title': _('ایجاد فاکتور جدید'),
#             'tankhah': tankhah,
#             'tankhah_documents': tankhah.documents.all() if tankhah else [],
#             'budget_info': budget_info,
#             'tankhah_remaining_budget': tankhah_remaining_budget,
#         })
#         return context
#
#     def form_valid(self, form):
#         context = self.get_context_data()
#         item_formset = context['formset']
#         document_form = context['document_form']
#         tankhah_document_form = context['tankhah_document_form']
#         tankhah = form.cleaned_data['tankhah']
#         is_draft = 'save_draft' in self.request.POST
#
#         logger.info(f"Processing form_valid for Factor creation linked to Tankhah {tankhah.number}")
#
#         save_incomplete = 'save_draft_incomplete' in self.request.POST
#         save_final = 'save_final_draft' in self.request.POST or not save_incomplete
#         logger.info(f"Form submission type: {'Incomplete Draft' if save_incomplete else 'Final Draft'}")
#
#         try:
#             initial_stage = WorkflowStage.objects.order_by('order').first()
#             initial_stage_order = initial_stage.order if initial_stage else 0
#             if not tankhah.current_stage or tankhah.current_stage.order != initial_stage_order:
#                 stage_name = tankhah.current_stage.name if tankhah.current_stage else _("نامشخص")
#                 initial_name = initial_stage.name if initial_stage else _("تعریف نشده")
#                 msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ثبت کنید. مرحله فعلی تنخواه: {}').format(initial_name, stage_name)
#                 messages.error(self.request, msg)
#                 logger.warning(f"Invalid stage order for tankhah {tankhah.number}: current_stage={stage_name}")
#                 return self.form_invalid(form)
#         except Exception as e:
#             logger.error(f"Error checking workflow stage for tankhah {tankhah.number}: {e}", exc_info=True)
#             messages.error(self.request, _('خطا در بررسی مرحله گردش کار تنخواه.'))
#             return self.form_invalid(form)
#
#         if tankhah.status not in ['DRAFT', 'PENDING']:
#             messages.error(self.request, _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.'))
#             logger.warning(f"Invalid status for tankhah {tankhah.number}: {tankhah.status}")
#             return self.form_invalid(form)
#
#         is_item_formset_valid = item_formset.is_valid()
#         is_doc_form_valid = document_form.is_valid()
#         is_tankhah_doc_form_valid = tankhah_document_form.is_valid()
#
#         if not (is_item_formset_valid and is_doc_form_valid and is_tankhah_doc_form_valid):
#             logger.error("Validation failed for formset or document forms.")
#             if not is_item_formset_valid: logger.error(f"Item formset errors: {item_formset.errors} {item_formset.non_form_errors()}")
#             if not is_doc_form_valid: logger.error(f"Factor document form errors: {document_form.errors}")
#             if not is_tankhah_doc_form_valid: logger.error(f"Tankhah document form errors: {tankhah_document_form.errors}")
#             messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم ردیف‌ها یا اسناد را بررسی و اصلاح کنید.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
#
#         if not valid_item_forms:
#             logger.warning("No valid items submitted in the formset.")
#             messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
#         factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))
#         tolerance = Decimal('0.01')
#
#         logger.info(f"Calculated total items amount: {total_items_amount}, Factor form amount: {factor_form_amount}")
#
#         if abs(total_items_amount - factor_form_amount) > tolerance:
#             msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
#                 factor_form_amount, total_items_amount
#             )
#             messages.error(self.request, msg)
#             logger.error(f"Amount mismatch: Factor={factor_form_amount}, Items={total_items_amount}")
#             form.add_error('amount', msg)
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         try:
#             tankhah_remaining = get_tankhah_remaining_budget(tankhah)
#             if total_items_amount > tankhah_remaining:
#                 msg = _('مبلغ فاکتور ({:,}) از بودجه باقی‌مانده تنخواه ({:,}) بیشتر است.').format(
#                     total_items_amount, tankhah_remaining
#                 )
#                 messages.error(self.request, msg)
#                 logger.error(f"Budget Exceeded: Factor Amount={total_items_amount}, Tankhah Remaining={tankhah_remaining}")
#                 form.add_error(None, msg)
#                 return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#         except Exception as e:
#             logger.error(f"Error getting remaining tankhah budget in view: {e}", exc_info=True)
#             messages.error(self.request, _('خطا در بررسی بودجه تنخواه.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         try:
#             project_allocation = ProjectBudgetAllocation.objects.select_related('budget_allocation').filter(project=tankhah.project).first()
#             if not project_allocation:
#                 raise ProjectBudgetAllocation.DoesNotExist("No ProjectBudgetAllocation found for this project.")
#             if not project_allocation.budget_allocation:
#                 raise ProjectBudgetAllocation.DoesNotExist("خطای عدم تخصیص بودجه در ثبت فاکتور👎😒💵 Associated BudgetAllocation missing.")
#             budget_allocation_instance = project_allocation.budget_allocation
#         except ProjectBudgetAllocation.DoesNotExist as e:
#             logger.error(f"No valid ProjectBudgetAllocation/BudgetAllocation found for project {tankhah.project.name}: {str(e)}")
#             messages.error(self.request, _('تخصیص بودجه معتبر برای پروژه این تنخواه یافت نشد.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#         except Exception as e:
#             logger.error(f"Error fetching project allocation: {e}", exc_info=True)
#             messages.error(self.request, _('خطا در یافتن تخصیص بودجه پروژه.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         budget_allocation_instance = project_allocation.budget_allocation
#         budget_period = budget_allocation_instance.budget_period
#         is_locked, lock_message = budget_period.is_period_locked
#         if is_locked:
#             messages.error(self.request, _("امکان ثبت هزینه وجود ندارد: {}").format(lock_message))
#             raise ValidationError(_("عملیات به دلیل قفل بودن دوره بودجه مجاز نیست."))
#
#         try:
#             with transaction.atomic():
#                 self.object = form.save(commit=False)
#                 self.object.status = 'DRAFT' if is_draft else 'PENDING'
#                 self.object.created_by = self.request.user
#                 self.object.amount = total_items_amount if save_final else factor_form_amount
#                 self.object.save()
#                 logger.info(
#                     f"Factor object saved (pk={self.object.pk}, number={self.object.number}, type={'Final' if save_final else 'Incomplete'})"
#                 )
#
#                 items_saved_count = 0
#                 for item_form in valid_item_forms:
#                     item = item_form.save(commit=False)
#                     item.factor = self.object
#                     item.save()
#                     items_saved_count += 1
#                 logger.info(f"Saved {items_saved_count} factor items for Factor pk={self.object.pk}.")
#
#                 factor_files = document_form.cleaned_data.get('files', [])
#                 docs_saved_count = 0
#                 for file in factor_files:
#                     FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)
#                     docs_saved_count += 1
#                 if docs_saved_count: logger.info(f"Saved {docs_saved_count} factor documents.")
#
#                 tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
#                 tdocs_saved_count = 0
#                 for file in tankhah_files:
#                     TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
#                     tdocs_saved_count += 1
#                 if tdocs_saved_count: logger.info(f"Saved {tdocs_saved_count} tankhah documents.")
#
#                 if save_final:
#                     logger.info("Creating budget transaction for final draft save.")
#                     create_budget_transaction(
#                         allocation=budget_allocation_instance,
#                         transaction_type='CONSUMPTION',
#                         amount=total_items_amount,
#                         related_obj=self.object,
#                         created_by=self.request.user,
#                         description=f"ایجاد فاکتور {self.object.number}",
#                         transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
#                     )
#                     logger.info(
#                         f"Budget transaction created for Factor pk={self.object.pk}, amount={total_items_amount}."
#                     )
#                 else:
#                     logger.info("Skipping budget transaction for incomplete draft save.")
#
#         except ValidationError as ve:
#             logger.error(f"Validation Error during atomic save: {ve.message_dict if hasattr(ve, 'message_dict') else ve}", exc_info=True)
#             messages.error(self.request, _('خطای اعتبارسنجی هنگام ذخیره: {}').format(ve))
#             if hasattr(ve, 'error_dict'):
#                 for field, errors in ve.error_dict.items():
#                     if field == '__all__':
#                         form.add_error(None, errors)
#                     else:
#                         if field in form.fields:
#                             form.add_error(field, errors)
#                         else:
#                             item_formset.add_error(None, f"{field}: {errors}")
#             else:
#                 form.add_error(None, str(ve))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         except Exception as e:
#             logger.error(f"Unexpected error during atomic transaction for saving factor: {e}", exc_info=True)
#             messages.error(self.request, _('خطای پیش‌بینی نشده‌ای هنگام ذخیره اطلاعات رخ داد.'))
#             return self.render_to_response(self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form))
#
#         success_message = _('فاکتور با موفقیت ذخیره شد.') if save_final else _(
#             'فاکتور به‌صورت موقت ذخیره شد. لطفاً بعداً آن را تکمیل و نهایی کنید.'
#         )
#         messages.success(self.request, success_message)
#         return redirect(self.get_success_url())
#
#     def form_invalid(self, form):
#         logger.warning(f"Main FactorForm is invalid. Errors: {form.errors}")
#         context = self.get_context_data(form=form)
#         item_formset = context['formset']
#         if item_formset.is_bound:
#             logger.warning(f"Item formset errors (in form_invalid): {item_formset.errors}")
#         messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم اصلی فاکتور را اصلاح کنید.'))
#         return self.render_to_response(context)
#
#     def handle_no_permission(self):
#         messages.error(self.request, self.permission_denied_message)
#         logger.warning(f"Permission denied for user {self.request.user} trying to add factor.")
#         return super().handle_no_permission()
