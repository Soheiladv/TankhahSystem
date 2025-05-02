from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import logging
import os
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import DecimalField
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, View

from budgets.budget_calculations import get_project_total_budget, get_tankhah_remaining_budget, \
    get_actual_project_remaining_budget
from tankhah.Factor.forms_Factor import WizardTankhahSelectionForm, WizardFactorDetailsForm, WizardFactorItemFormSet, \
    WizardFactorDocumentForm, WizardTankhahDocumentForm, WizardConfirmationForm
from tankhah.forms import FactorForm, get_factor_item_formset
from tankhah.models import Factor, TankhahDocument, FactorDocument
from tankhah.models import Tankhah
from tankhah.forms import FactorDocumentForm, TankhahDocumentForm
logger = logging.getLogger('tankhah')
#----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from formtools.wizard.views import SessionWizardView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect # Import get_object_or_404
from django.contrib import messages
from django.db import transaction, models
from django.db.models import Q, Sum, F, Value, DecimalField, Max
from django.db.models.functions import Coalesce
from decimal import Decimal
import logging
from django.utils import timezone # Import timezone

from budgets.models import BudgetTransaction, ProjectBudgetAllocation, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import WorkflowStage

class FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.get(id=tankhah_id)
            except Tankhah.DoesNotExist:
                logger.error(f"Tankhah with ID {tankhah_id} not found")
        logger.debug(f"Form kwargs: {kwargs}")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
        tankhah = Tankhah.objects.filter(id=tankhah_id).first() if tankhah_id else None
        FactorItemFormSet = get_factor_item_formset()

        if self.request.POST:
            form = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah)
            item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
            document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
            tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            form = self.form_class(user=self.request.user, tankhah=tankhah)
            item_formset = FactorItemFormSet(prefix='form')
            document_form = FactorDocumentForm()
            tankhah_document_form = TankhahDocumentForm()

        # اضافه کردن اطلاعات بودجه
        budget_info = None
        if tankhah:
            try:
                project = tankhah.project
                project_allocation = ProjectBudgetAllocation.objects.filter(project=project).first()
                if not project_allocation:
                    logger.warning(f"No ProjectBudgetAllocation found for project {project.name}")
                    budget_info = None
                else:
                    budget_allocation = project_allocation.budget_allocation
                    project_budget = project_allocation.allocated_amount
                    consumed = BudgetTransaction.objects.filter(
                        allocation=budget_allocation,
                        transaction_type='CONSUMPTION'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    returned = BudgetTransaction.objects.filter(
                        allocation=budget_allocation,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    tankhah_remaining = project_budget - consumed + returned

                    budget_info = {
                        'project_name': project.name,
                        'project_budget': project_budget,
                        'tankhah_budget': project_budget,
                        'tankhah_remaining': tankhah_remaining,
                    }
            except Exception as e:
                logger.error(f"Error accessing budget info for tankhah {tankhah.number}: {e}")
                budget_info = None

        context.update({
            'form': form,
            'item_formset': item_formset,
            'document_form': document_form,
            'tankhah_document_form': tankhah_document_form,
            'title': 'ایجاد فاکتور جدید',
            'tankhah': tankhah,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'budget_info': budget_info,
        })
        logger.debug(f"Context data: {context}")
        return context

    def form_valid(self, form):
        tankhah = form.cleaned_data['tankhah']
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order
        FactorItemFormSet = get_factor_item_formset()

        logger.debug(f"Tankhah status: {tankhah.status}, stage order: {tankhah.current_stage.order}, initial stage: {initial_stage_order}")

        if tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            logger.warning(f"Invalid stage order for tankhah {tankhah.number}: {tankhah.current_stage.order}")
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
            logger.warning(f"Invalid status for tankhah {tankhah.number}: {tankhah.status}")
            return self.form_invalid(form)

        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
        tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)

        logger.info(f"Main form valid? {form.is_valid()}")
        logger.info(f"Item formset valid? {item_formset.is_valid()}")
        logger.info(f"Document form valid? {document_form.is_valid()}")
        logger.info(f"Tankhah document form valid? {tankhah_document_form.is_valid()}")
        logger.debug(f"POST data: {self.request.POST}")
        logger.debug(f"Files: {self.request.FILES}")

        if not form.is_valid():
            logger.error(f"Main form errors: {form.errors}")
        if not item_formset.is_valid():
            logger.error(f"Item formset errors: {item_formset.errors}")
            logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")

        valid_items = [f for f in item_formset if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if not valid_items:
            logger.error("No valid items in formset.")
            messages.error(self.request, 'حداقل یک ردیف معتبر باید وارد کنید.')
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        # بررسی بودجه باقی‌مانده تنخواه
        total_amount = sum(f.cleaned_data.get('amount', 0) for f in valid_items)
        project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
        if not project_allocation:
            logger.error(f"No ProjectBudgetAllocation found for project {tankhah.project.name}")
            messages.error(self.request, 'تخصیص بودجه برای پروژه این تنخواه یافت نشد.')
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        budget_allocation = project_allocation.budget_allocation
        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        tankhah_remaining = project_allocation.allocated_amount - consumed + returned

        if total_amount > tankhah_remaining:
            logger.error(f"Factor amount ({total_amount}) exceeds remaining tankhah budget ({tankhah_remaining}).")
            messages.error(self.request, f'مبلغ فاکتور از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,} تومان) بیشتر است.')
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.status = 'DRAFT'
                self.object.save()

                item_formset.instance = self.object
                for form in item_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                        form.save()

                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=tankhah, document=file)

                # ثبت تراکنش مصرف بودجه
                BudgetTransaction.objects.create(
                    allocation=budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=total_amount,
                    related_tankhah=tankhah,
                    created_by=self.request.user,
                    description=f"مصرف برای فاکتور {self.object.number}",
                    transaction_id=f"TX-FACTOR-{self.object.id}-{timezone.now().timestamp()}"
                )

                logger.info(f"Factor {self.object.number} saved as DRAFT.")
                messages.success(self.request, 'فاکتور به‌صورت پیش‌نویس ذخیره شد. می‌توانید بعداً آن را تکمیل کنید.')
        else:
            logger.error(f"Form errors: {form.errors}")
            logger.error(f"Item formset errors: {item_formset.errors}")
            logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")
            logger.error(f"Document form errors: {document_form.errors}")
            logger.error(f"Tankhah document form errors: {tankhah_document_form.errors}")
            messages.error(self.request, 'لطفاً خطاهای فرم را بررسی و اصلاح کنید.')
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        FactorItemFormSet = get_factor_item_formset()
        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
        logger.error(f"Main form errors: {form.errors}")
        logger.error(f"Item formset errors: {item_formset.errors}")
        logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")
        messages.error(self.request, 'لطفاً خطاهای فرم را بررسی و اصلاح کنید.')
        return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Permission denied for user {self.request.user}")
        return super().handle_no_permission()

class FactorCreateWizard(PermissionBaseView, SessionWizardView):
    template_name = 'tankhah/Factors/factor_wizard.html'
    FactorItemFormSet = get_factor_item_formset()
    form_list = [
        ('tankhah', FactorForm),  # مرحله انتخاب تنخواه
        ('factor', FactorForm),   # مرحله اطلاعات فاکتور
        ('items', FactorItemFormSet),  # مرحله آیتم‌ها
        ('documents', FactorDocumentForm),  # مرحله اسناد
        ('confirmation', WizardConfirmationForm),
    ]
    # form_class =  forms_Factor.W_FactorForm

    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True
    file_storage = FileSystemStorage(location=os.path.join(BASE_DIR, 'tmp'))  # ذخیره در پوشه tmp پروژه


    def get_form_kwargs(self, step):
        kwargs = super().get_form_kwargs(step)
        kwargs['user'] = self.request.user

        if step == 'tankhah':
            # فقط برای انتخاب تنخواه
            kwargs['tankhah'] = None
        elif step in ['factor', 'items', 'documents']:
            # دریافت تنخواه انتخاب‌شده از مرحله اول
            tankhah_data = self.get_cleaned_data_for_step('tankhah') or {}
            tankhah_id = tankhah_data.get('tankhah')
            if tankhah_id:
                try:
                    kwargs['tankhah'] = Tankhah.objects.get(id=tankhah_id)
                except Tankhah.DoesNotExist:
                    logger.error(f"Tankhah with ID {tankhah_id} not found")
        logger.debug(f"Form kwargs for step {step}: {kwargs}")
        return kwargs

    def get_form(self, step=None, data=None, files=None):
        FactorItemFormSet = get_factor_item_formset()
        form = super().get_form(step, data, files)
        if step == 'items':
            # فرمست آیتم‌ها
            form = FactorItemFormSet(data, files, prefix='form')
        elif step == 'documents':
            # فرم اسناد
            form = FactorDocumentForm(data, files)
            self.tankhah_document_form = TankhahDocumentForm(data, files)
        return form

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        # context['wizard_steps'] = ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد']
        context['wizard_steps'] = ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد', 'تأیید نهایی']

        context['wizard_step'] = self.steps.current
        current_step =self.steps.current
        tankhah = None
        budget_info = None

        # دریافت تنخواه از داده‌های ذخیره‌شده یا URL
        tankhah_data = self.get_cleaned_data_for_step('tankhah') or {}
        tankhah_id = tankhah_data.get('tankhah') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
        if tankhah_id:
            tankhah = Tankhah.objects.filter(id=tankhah_id).first()

        if tankhah:
            try:
                project = tankhah.project
                project_allocation = ProjectBudgetAllocation.objects.filter(project=project).first()
                if project_allocation:
                    budget_allocation = project_allocation.budget_allocation
                    project_budget = project_allocation.allocated_amount
                    consumed = BudgetTransaction.objects.filter(
                        allocation=budget_allocation,
                        transaction_type='CONSUMPTION'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    returned = BudgetTransaction.objects.filter(
                        allocation=budget_allocation,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                    tankhah_remaining = project_budget - consumed + returned

                    budget_info = {
                        'project_name': project.name,
                        'project_budget': project_budget,
                        'tankhah_budget': tankhah.amount,
                        'tankhah_remaining': tankhah_remaining,
                    }
            except Exception as e:
                logger.error(f"Error accessing budget info for tankhah {tankhah.number}: {e}")

        context.update({
            'title': 'ایجاد فاکتور جدید',
            'tankhah': tankhah,
            'budget_info': budget_info,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'wizard_step': current_step,
            'wizard_steps': ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد', 'تأیید نهایی'],
        })
        if current_step == 'documents':
            context['tankhah_document_form'] = getattr(self, 'tankhah_document_form', TankhahDocumentForm())
        logger.debug(f"Context data: {context}")

        print('Storage data:', self.storage.data)
        print('Step files (factor_docs):', self.storage.get_step_files('factor_docs'))
        step4_files = self.storage.get_step_files('factor_docs')
        context['step4_files'] = [f.name for f in step4_files.get('factor_docs-files', []) if f] if step4_files else []

        # بررسی فایل‌های مرحله factor_docs
        step4_files = self.storage.get_step_files('factor_docs')
        if step4_files and 'factor_docs-files' in step4_files:
            context['step4_files'] = [f.name for f in step4_files['factor_docs-files'] if f]

        return context

    def done(self, form_list, **kwargs):
        # جمع‌آوری داده‌ها
        tankhah_form = form_list['tankhah']
        factor_form = form_list['factor']
        item_formset = form_list['items']
        document_form = form_list['documents']
        tankhah_document_form = self.tankhah_document_form

        tankhah = tankhah_form.cleaned_data['tankhah']
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order

        # اعتبارسنجی وضعیت تنخواه
        if tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            logger.warning(f"Invalid stage order for tankhah {tankhah.number}")
            return self.render_to_response(self.get_context_data(form=factor_form))

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
            logger.warning(f"Invalid status for tankhah {tankhah.number}")
            return self.render_to_response(self.get_context_data(form=factor_form))

        # اعتبارسنجی آیتم‌ها
        valid_items = [f for f in item_formset if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if not valid_items:
            messages.error(self.request, 'حداقل یک ردیف معتبر باید وارد کنید.')
            logger.error("No valid items in formset.")
            return self.render_to_response(self.get_context_data(form=item_formset))

        # محاسبه مبلغ کل آیتم‌ها
        total_amount = sum(f.cleaned_data.get('amount', 0) * f.cleaned_data.get('quantity', 1) for f in valid_items)

        # اعتبارسنجی بودجه
        project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
        if not project_allocation:
            messages.error(self.request, 'تخصیص بودجه برای پروژه این تنخواه یافت نشد.')
            logger.error(f"No ProjectBudgetAllocation found for project {tankhah.project.name}")
            return self.render_to_response(self.get_context_data(form=factor_form))

        budget_allocation = project_allocation.budget_allocation
        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        tankhah_remaining = project_allocation.allocated_amount - consumed + returned

        if total_amount > tankhah_remaining:
            messages.error(self.request, f'مبلغ فاکتور از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,} تومان) بیشتر است.')
            logger.error(f"Factor amount ({total_amount}) exceeds remaining tankhah budget ({tankhah_remaining}).")
            return self.render_to_response(self.get_context_data(form=factor_form))

        # ثبت فاکتور
        with transaction.atomic():
            factor = factor_form.save(commit=False)
            factor.status = 'DRAFT' if self.request.POST.get('save_draft') else 'PENDING'
            factor.tankhah = tankhah
            factor.save()

            item_formset.instance = factor
            for form in item_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    form.save()

            factor_files = self.request.FILES.getlist('files')
            for file in factor_files:
                FactorDocument.objects.create(factor=factor, file=file)

            tankhah_files = self.request.FILES.getlist('documents')
            for file in tankhah_files:
                TankhahDocument.objects.create(tankhah=tankhah, document=file)

            if factor.status == 'PENDING':
                BudgetTransaction.objects.create(
                    allocation=budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=total_amount,
                    related_tankhah=tankhah,
                    created_by=self.request.user,
                    description=f"مصرف برای فاکتور {factor.number}",
                    transaction_id=f"TX-FACTOR-{factor.id}-{timezone.now().timestamp()}"
                )

            logger.info(f"Factor {factor.number} saved as {factor.status}.")
            messages.success(self.request, f'فاکتور به‌صورت {"پیش‌نویس" if factor.status == "DRAFT" else "در انتظار"} ذخیره شد.')

        return redirect(reverse_lazy('factor_list'))

    def post(self, *args, **kwargs):
        # مدیریت ذخیره پیش‌نویس
        if self.request.POST.get('save_draft'):
            return self.done(self.get_all_cleaned_data(), **kwargs)
        return super().post(*args, **kwargs)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Permission denied for user {self.request.user}")
        return super().handle_no_permission()
#---------------- این ویو مسئول دریافت ID تنخواه و برگرداندن اطلاعات بودجه مرتبط است.

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
                logger.debug(f"Using ProjectBudgetAllocation {tankhah.project_budget_allocation.id} linked to BudgetAllocation {target_allocation_instance.id}")
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
#------- Main View
FACTOR_TEMPLATES = {
    "step1": 'tankhah/Factors/wizard/factor_wizard_step1.html',
    "step2": 'tankhah/Factors/wizard/factor_wizard_step2_formset.html',
    "step3_docs": 'tankah/Factors/wizard/factor_wizard_step3_docs.html',
    "step3_tankhah_docs": 'tankah/Factors/wizard/factor_wizard_step3_tankhah_docs.html',
    "step4_review": 'tankhah/Factors/wizard/factor_wizard_step4_review.html',
}
wizard_file_storage_location = os.path.join(settings.MEDIA_ROOT, 'temp_wizard_files')
if not os.path.exists(wizard_file_storage_location):
    try:
        os.makedirs(wizard_file_storage_location)
    except OSError as e:
        logger.error(f"Could not create wizard file storage directory: {wizard_file_storage_location}. Error: {e}")
        # Handle error appropriately, maybe raise ImproperlyConfigured
# Use FileSystemStorage for handling file uploads in the wizard
wizard_file_storage = FileSystemStorage(location=wizard_file_storage_location)


logger = logging.getLogger('tankhah')

# Configure File Storage
wizard_file_storage_location = os.path.join(settings.MEDIA_ROOT, 'temp_wizard_files')
# ... (os.makedirs logic remains the same) ...
if not os.path.exists(wizard_file_storage_location):
    try:
        os.makedirs(wizard_file_storage_location)
    except OSError as e:
        logger.error(f"Could not create directory: {wizard_file_storage_location}. Error: {e}")
wizard_file_storage = FileSystemStorage(location=wizard_file_storage_location)

# from .forms_Factor import FactorStepOneForm # فرض کنید فرم مرحله اول این است
class OK_NEW_FactorCreateWizardView(PermissionBaseView, SessionWizardView): # Renamed class
    model = Factor
    form_class = FactorForm
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_codenames = ['tankhah.a_factor_add']
    # permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

    # --- Corrected form_list using NEW forms ---
    form_list = [
        ("select_tankhah", WizardTankhahSelectionForm),
        ("factor_details", WizardFactorDetailsForm),
        ("factor_items", WizardFactorItemFormSet), # The inline formset factory result
        ("factor_docs", WizardFactorDocumentForm),
        ("tankhah_docs", WizardTankhahDocumentForm),
        ("confirmation", WizardConfirmationForm), # Empty form for the review step
    ]

    template_name = "tankhah/Factors/wizard/factor_wizard_base.html" # Base template
    file_storage = wizard_file_storage

    def post(self, *args, **kwargs):
        # دریافت فرم مرحله فعلی
        form = self.get_form(data=self.request.POST, files=self.request.FILES)

        # لاگ کردن وضعیت اعتبار و خطاها
        logger.info(f"Processing POST for step: {self.steps.current}")
        if form.is_valid():
            logger.info(f"Form for step {self.steps.current} IS VALID.")
        else:
            logger.error(f"Form for step {self.steps.current} IS INVALID.")
            # logger.error(f"Form errors: {form.errors.as_json()}") # نمایش خطاها به صورت JSON

        # اجرای منطق پیش فرض post
        return super().post(*args, **kwargs)

    def get_step_titles(self):
        return {
            "select_tankhah": _("۱. انتخاب تنخواه"),
            "factor_details": _("۲. اطلاعات فاکتور"),
            "factor_items": _("۳. ردیف‌های فاکتور"),
            "factor_docs": _("۴. اسناد فاکتور"),
            "tankhah_docs": _("۵. اسناد تنخواه"),
            "confirmation": _("۶. تأیید نهایی"),
        }

    def get_template_names(self):
        FACTOR_TEMPLATES = {
            "select_tankhah": "tankhah/Factors/wizard/step_select_tankhah.html",
            "factor_details": "tankhah/Factors/wizard/step_factor_details.html",
            "factor_items": "tankhah/Factors/wizard/step_factor_items.html",
            "factor_docs": "tankhah/Factors/wizard/step_factor_docs.html",
            "tankhah_docs": "tankhah/Factors/wizard/step_tankhah_docs.html",
            "confirmation": "tankhah/Factors/wizard/step_confirmation.html",  # Review/Confirmation step
        }
        # Get template based on current step key
        return [FACTOR_TEMPLATES.get(self.steps.current, self.template_name)]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        # بررسی کنید که آیا مرحله فعلی، مرحله ای است که فرمش به user نیاز دارد
        # step معمولا یک رشته عددی است '0', '1', ...
        # یا اگر از نام برای مراحل استفاده می کنید، نام مرحله خواهد بود.
        # فرض می کنیم فرم مرحله اول (step '0') به user نیاز دارد.
        print(f'Step is {step}') #Step is select_tankhah
        # if step == 'select_tankhah': # استفاده از نام مرحله برای خوانایی
        if step == self.steps.first: #step == '0':  # یا step == self.steps.first یا مقایسه با نام مرحله
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                kwargs['user'] = self.request.user
            else:
                # مدیریت حالتی که کاربر لاگین نیست (اگر ممکن است)
                kwargs['user'] = None  # یا raise Exception

        # برای مراحل دیگر، 'user' به kwargs اضافه نمی شود
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        total_steps = len(self.form_list) # Total steps including confirmation
        context['step_titles'] = self.get_step_titles()  # Add titles to context
        context['wizard_title'] = _('ایجاد فاکتور جدید (مرحله {} از {})').format(self.steps.step1, total_steps)
        context['step_name'] = self.steps.current

        # --- Get Tankhah instance from previous step's data ---
        # --- دریافت Tankhah و Project ---
        tankhah = None
        tankhah_id = None
        if self.steps.prev: # If not the first step
            cleaned_data_prev = self.get_cleaned_data_for_step(self.steps.prev)
            if cleaned_data_prev and 'tankhah' in cleaned_data_prev:
                 tankhah = cleaned_data_prev['tankhah'] # Get the instance directly
                 if tankhah: tankhah_id = tankhah.id
            # Fallback: try getting from storage directly if cleaned_data not available yet
            if not tankhah:
                step1_storage_data = self.storage.get_step_data('select_tankhah')
                if step1_storage_data and 'select_tankhah-tankhah' in step1_storage_data:
                    tankhah_id = step1_storage_data.get('select_tankhah-tankhah')
                    tankhah = Tankhah.objects.filter(pk=tankhah_id).first()
        project = None
        # سعی کنید از cleaned_data مراحل قبلی بگیرید
        cleaned_data_step1 = self.get_cleaned_data_for_step('select_tankhah')
        if cleaned_data_step1:
            tankhah = cleaned_data_step1.get('tankhah')
            if tankhah:
                project = tankhah.project  # یا tankhah.subproject.project اگر از زیرپروژه استفاده می شود

                # اگر هنوز پیدا نشده، از storage بگیرید (مثلاً هنگام بارگذاری مجدد صفحه)
        if not tankhah:
            step1_storage_data = self.storage.get_step_data('select_tankhah')
            if step1_storage_data and 'select_tankhah-tankhah' in step1_storage_data:
                tankhah_id = step1_storage_data.get('select_tankhah-tankhah')
                tankhah = Tankhah.objects.filter(pk=tankhah_id).select_related(
                    'project').first()  # select_related برای بهینه سازی
                if tankhah:
                    project = tankhah.project


        context['selected_tankhah'] = tankhah # Pass to all steps for potential display

        # --- Add Budget Info ---
        # --- اضافه کردن اطلاعات برای مرحله آیتم ها ---
        if self.steps.current == 'factor_items':
            context['formset'] = form  # فرم ست را به کانتکست اضافه کنید

            # دریافت مبلغ اولیه فاکتور از مرحله قبل
            initial_factor_amount = Decimal('0.0')
            cleaned_data_step2 = self.get_cleaned_data_for_step('factor_details')
            if cleaned_data_step2:
                initial_factor_amount = cleaned_data_step2.get('amount', Decimal('0.0'))
            context['initial_factor_amount'] = initial_factor_amount

            # محاسبه و اضافه کردن بودجه در دسترس
            context['available_budget'] = Decimal('0.0')
            if project:  # اگر پروژه مشخص است
                try:
                    # <<<--- استفاده از تابع دقیق محاسبه بودجه ---<<<
                    context['available_budget'] = get_actual_project_remaining_budget(project)
                    # get_tankhah_remaining_budget
                    """ محاسبه بودجه باقی‌مانده تنخواه  """



                    logger.info(
                        f"Wizard Context: Available budget for project {project.id}: {context['available_budget']}")
                except Exception as e:
                    logger.error(f"Wizard Context: Error calculating available budget for project {project.id}: {e}")
            else:
                logger.warning("Wizard Context: Project not found for budget calculation.")

        elif self.steps.current == 'confirmation':
            context['step1_data'] = self.get_cleaned_data_for_step('select_tankhah')
            context['step2_data'] = self.get_cleaned_data_for_step('factor_details')
            # پردازش داده های فرم ست برای نمایش بهتر
            item_formset_data = self.get_cleaned_data_for_step('factor_items') or []
            context['item_data_list'] = [item for item in item_formset_data if item and not item.get('DELETE')]
            context['summary_total'] = self.get_summary_total()
            # ... (داده های مراحل دیگر را هم اضافه کنید) ...

        return context

    # --- محاسبه مجموع کل آیتم ها ---
    def get_summary_total(self):
        item_formset_data = self.get_cleaned_data_for_step('factor_items') or []
        total = Decimal('0.0')
        for item_data in item_formset_data:
            # مطمئن شوید آیتم معتبر است و حذف نشده
            if item_data and not item_data.get('DELETE', False):
                amount = item_data.get('amount', Decimal('0.0'))
                quantity = item_data.get('quantity', 1)  # مقدار پیش فرض ۱
                if isinstance(quantity, (int, float, Decimal)) and quantity > 0:
                    total += (amount * Decimal(quantity))  # ضرب Decimal
                elif isinstance(quantity, str) and quantity.isdigit() and int(quantity) > 0:
                    total += (amount * Decimal(quantity))
        return total.quantize(Decimal('0'))  # گرد کردن به ریال

    # # get_summary_total method (calculates from 'factor_items' step data)
    # def get_summary_total(self):
    #     item_formset_data = self.get_cleaned_data_for_step('factor_items') or []  # Use correct step name
    #     total = Decimal('0.0')
    #     # item_formset_data is a list of dicts here
    #     for item_data in item_formset_data:
    #         if item_data and not item_data.get('DELETE', False):
    #             amount = item_data.get('amount', Decimal('0.0'))
    #             quantity = item_data.get('quantity', 1)
    #             total += (amount * quantity)
    #     return total

        # --- ذخیره نهایی ---
    def done(self, form_list, form_dict, **kwargs):
            logger.info("Wizard 'done' method started.")
            # ... (استخراج داده ها از form_dict مانند قبل) ...
            tankhah_data = form_dict['select_tankhah'].cleaned_data
            factor_details_data = form_dict['factor_details'].cleaned_data
            item_formset_instance = form_dict['factor_items']  # نمونه فرم ست
            factor_doc_data = form_dict['factor_docs'].cleaned_data
            tankhah_doc_data = form_dict['tankhah_docs'].cleaned_data

            tankhah = tankhah_data.get('tankhah')
            if not tankhah:
                messages.error(self.request, _("خطای داخلی: تنخواه یافت نشد."))
                logger.error("Wizard Done: Tankhah object not found in step 1 data.")
                return redirect(reverse('factor_wizard'))

            project = tankhah.project  # یا منطق زیرپروژه
            total_amount = self.get_summary_total()  # محاسبه مجدد مجموع
            logger.info(f"Wizard Done: Calculated total amount: {total_amount}")

            # --- اعتبارسنجی نهایی بودجه در سمت سرور ---
            if project:
                try:
                    # <<<--- محاسبه مجدد بودجه در دسترس قبل از ذخیره ---<<<
                    current_available_budget = get_actual_project_remaining_budget(project)
                    logger.info(
                        f"Wizard Done: Server-side available budget check for project {project.id}: {current_available_budget}")

                    if total_amount > current_available_budget:
                        messages.error(self.request,
                                       _("خطای بودجه: مبلغ نهایی فاکتور ({amount} ریال) از بودجه باقیمانده پروژه ({budget} ریال) بیشتر است. لطفاً آیتم‌ها را اصلاح کنید.").format(
                                           amount=f"{total_amount:,.0f}", budget=f"{current_available_budget:,.0f}"))
                        logger.warning(
                            f"Wizard Done: Budget exceeded. Factor Amount: {total_amount}, Available Budget: {current_available_budget}")
                        # بازگشت به مرحله آیتم‌ها
                        # نکته: render_goto_step ممکن است با SessionWizardView پیچیده باشد، redirect ساده تر است
                        # return self.render_goto_step('factor_items')
                        # ذخیره داده های فعلی برای پر کردن مجدد فرم ها (اگر WizardView خودش این کار را نکند)
                        self.storage.set_step_data('factor_items', self.request.POST)
                        return redirect(
                            self.request.path_info + '?step=factor_items')  # ریدایرکت به همین صفحه با پارامتر step

                except Exception as e:
                    messages.error(self.request, _("خطا در بررسی بودجه."))
                    logger.error(f"Wizard Done: Exception during server-side budget check: {e}", exc_info=True)
                    return redirect(reverse('factor_wizard'))
            else:
                messages.error(self.request, _("خطا: پروژه مرتبط با تنخواه یافت نشد."))
                logger.error(f"Wizard Done: Project not found for Tankhah {tankhah.id}")
                return redirect(reverse('factor_wizard'))

            # --- ذخیره اتمی ---
            try:
                with transaction.atomic():
                    # 1. ایجاد فاکتور
                    factor = Factor.objects.create(  # استفاده از create برای سادگی
                        tankhah=tankhah,
                        date=factor_details_data['date'],
                        description=factor_details_data.get('description', ''),
                        created_by=self.request.user,
                        amount=total_amount,  # مبلغ کل محاسبه شده
                        status='PENDING'  # وضعیت اولیه
                    )
                    logger.info(f"Wizard Done: Factor created: ID={factor.pk}")

                    # 2. ذخیره آیتم ها
                    item_formset_instance.instance = factor
                    item_formset_instance.save()
                    logger.info(
                        f"Wizard Done: Factor items saved for Factor ID={factor.pk}. Count: {item_formset_instance.total_form_count()}")

                    # 3. ذخیره اسناد فاکتور (از storage)
                    factor_files_storage = self.storage.get_step_files('factor_docs')
                    saved_factor_docs = 0
                    if factor_files_storage and 'factor_docs-files' in factor_files_storage:
                        for file in factor_files_storage['factor_docs-files']:
                            if file:
                                FactorDocument.objects.create(factor=factor, file=file, uploaded_by=self.request.user)
                                saved_factor_docs += 1
                    logger.info(f"Wizard Done: Saved {saved_factor_docs} factor documents.")

                    # 4. ذخیره اسناد تنخواه (از storage)
                    tankhah_files_storage = self.storage.get_step_files('tankhah_docs')
                    saved_tankhah_docs = 0
                    if tankhah_files_storage and 'tankhah_docs-documents' in tankhah_files_storage:
                        for file in tankhah_files_storage['tankhah_docs-documents']:
                            if file:
                                # اطمینان از عدم ثبت فایل تکراری (اگر نیاز است)
                                TankhahDocument.objects.create(tankhah=tankhah, document=file,
                                                               uploaded_by=self.request.user)
                                saved_tankhah_docs += 1
                    logger.info(f"Wizard Done: Saved {saved_tankhah_docs} tankhah documents.")

                    # 5. ایجاد تراکنش بودجه (مهم)
                    # یافتن BudgetAllocation مناسب برای ثبت تراکنش مصرف
                    # این بخش نیاز به منطق دقیق دارد: کدام BudgetAllocation؟
                    # معمولاً آخرین تخصیص فعال به پروژه یا سازمان مربوطه
                    budget_allocation_to_consume = ProjectBudgetAllocation.objects.filter(
                        project=project,
                        # budget_allocation__is_active=True # شاید فقط از تخصیص های فعال کسر شود؟
                        # budget_allocation__budget_period__is_active=True
                    ).order_by('-allocation_date').first()  # یا منطق دیگر

                    if budget_allocation_to_consume:
                        budget_transaction = BudgetTransaction.objects.create(
                            allocation=budget_allocation_to_consume.budget_allocation,
                            # <--- اتصال به BudgetAllocation اصلی
                            transaction_type='CONSUMPTION',
                            amount=total_amount,
                            related_tankhah=tankhah,  # لینک به تنخواه
                            # related_factor=factor ? # اگر میخواهید مستقیم به فاکتور هم لینک دهید
                            created_by=self.request.user,
                            description=f"مصرف بودجه برای فاکتور شماره {factor.number} تنخواه {tankhah.number}",
                            # transaction_id خودکار ایجاد می شود؟ (بر اساس مدل شما)
                        )
                        logger.info(
                            f"Wizard Done: BudgetTransaction {budget_transaction.id} created against BudgetAllocation {budget_allocation_to_consume.budget_allocation.id}.")
                        # به‌روزرسانی remaining_amount در BudgetAllocation (مدل BudgetTransaction باید این کار را بکند)
                        # budget_allocation_to_consume.budget_allocation.save() # <-- Ensure save triggers update if needed
                    else:
                        logger.error(
                            f"Wizard Done: Could not find a suitable ProjectBudgetAllocation to record consumption for Project {project.id}.")
                        # در این حالت چه باید کرد؟ شاید خطا داد؟
                        raise Exception(
                            f"No suitable budget allocation found for project {project.name} to record consumption.")

                # پاک کردن storage و نمایش پیام موفقیت
                self.storage.reset()
                messages.success(self.request, _("فاکتور با شماره {} با موفقیت ثبت شد.").format(factor.number))
                logger.info(f"Wizard Done: Successfully completed for Factor {factor.number}")
                return redirect(self.get_success_url())

            except Exception as e:
                # ... (مدیریت خطا مانند قبل) ...
                messages.error(self.request, _("خطا در ذخیره‌سازی نهایی فاکتور."))
                logger.error(f"Wizard Done: Exception during final save transaction: {e}", exc_info=True)
                return redirect(reverse('factor_wizard'))  # بازگشت به شروع
    # done method (called after confirmation step)
    def ____done(self, form_list, form_dict, **kwargs):
        # form_list is now a list of form instances in order
        # form_dict maps step_name to form instance

        # Extract cleaned data using form_dict and CORRECT step names
        tankhah_data = form_dict['select_tankhah'].cleaned_data
        factor_details_data = form_dict['factor_details'].cleaned_data
        item_formset_instance = form_dict['factor_items'] # This is the formset INSTANCE
        factor_doc_data = form_dict['factor_docs'].cleaned_data
        tankhah_doc_data = form_dict['tankhah_docs'].cleaned_data

        tankhah = tankhah_data['tankhah']
        total_amount = self.get_summary_total() # Use helper

        # --- Re-validate Tankhah Status/Stage and Budget ---
        initial_stage = WorkflowStage.objects.order_by('order').first()
        if tankhah.status not in ['DRAFT', 'PENDING'] or (initial_stage and tankhah.current_stage.order != initial_stage.order):
            messages.error(self.request, _("وضعیت تنخواه در حین ثبت تغییر کرده است. لطفاً دوباره تلاش کنید."))
            return redirect(reverse('factor_wizard')) # Redirect to start

        # ...(Budget checking logic using tankhah and total_amount - same as before)...
        project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
        if not project_allocation:
             messages.error(self.request, "تخصیص بودجه پروژه یافت نشد.")
             return self.render_goto_step('select_tankhah') # Go back
        #... rest of budget check ...
        budget_allocation = project_allocation.budget_allocation
        consumed = BudgetTransaction.objects.filter(allocation=budget_allocation, transaction_type='CONSUMPTION').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(allocation=budget_allocation, transaction_type='RETURN').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        current_remaining_budget = project_allocation.allocated_amount - consumed + returned
        if total_amount > current_remaining_budget:
            messages.error(self.request, f"مبلغ فاکتور ({total_amount:,.0f}) از بودجه باقیمانده ({current_remaining_budget:,.0f}) بیشتر است.")
            return self.render_goto_step('factor_items') # Go back to items

        # --- Save Everything Atomically ---
        try:
            with transaction.atomic():
                # 1. Create Factor
                factor = Factor(
                    tankhah=tankhah,
                    date=factor_details_data['date'],
                    description=factor_details_data.get('description', ''),
                    created_by=self.request.user,
                    amount=total_amount,
                    status='PENDING' # Final status
                )
                factor.save()
                logger.info(f"Wizard Done: Factor saved: ID={factor.pk}")

                # 2. Save Items using the validated formset instance
                item_formset_instance.instance = factor
                item_formset_instance.save() # Saves valid, non-deleted items
                logger.info(f"Wizard Done: Factor items saved.")

                # 3. Save Factor Documents
                # Access files from storage for the specific step
                factor_files_storage = self.storage.get_step_files('factor_docs')
                saved_factor_docs = 0
                if factor_files_storage and 'factor_docs-files' in factor_files_storage:
                     for file in factor_files_storage['factor_docs-files']:
                         if file:
                             FactorDocument.objects.create(factor=factor, file=file, uploaded_by=self.request.user)
                             saved_factor_docs += 1
                logger.info(f"Wizard Done: Saved {saved_factor_docs} factor documents.")

                # 4. Save Tankhah Documents
                tankhah_files_storage = self.storage.get_step_files('tankhah_docs')
                saved_tankhah_docs = 0
                if tankhah_files_storage and 'tankhah_docs-documents' in tankhah_files_storage:
                     for file in tankhah_files_storage['tankhah_docs-documents']:
                         if file:
                             TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
                             saved_tankhah_docs += 1
                logger.info(f"Wizard Done: Saved {saved_tankhah_docs} tankhah documents.")

                # 5. Create Budget Transaction
                # ...(Budget transaction creation logic remains the same)...
                budget_transaction = BudgetTransaction.objects.create(
                     allocation=budget_allocation,
                     transaction_type='CONSUMPTION',
                     amount=total_amount,
                     related_tankhah=tankhah,
                     created_by=self.request.user,
                     description=f"مصرف بودجه فاکتور {factor.number}",
                 )
                logger.info(f"Wizard Done: BudgetTransaction {budget_transaction.id} created.")


            self.storage.reset() # Clear storage on success
            messages.success(self.request, _("فاکتور با شماره {} با موفقیت ثبت شد.").format(factor.number))
            logger.info(f"Wizard Done: Successfully created Factor {factor.number}")
            return redirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, _("خطا در ذخیره‌سازی نهایی فاکتور."))
            logger.error(f"Wizard Done: Exception during final save transaction: {e}", exc_info=True)
            # Don't reset storage, maybe go back to confirmation?
            # return self.render_goto_step('confirmation') # Might need manual re-render
            return redirect(reverse('factor_wizard')) # Safest: redirect to start

    def get_success_url(self):
        # به لیست فاکتورها یا صفحه جزئیات فاکتور جدید بروید
        return reverse_lazy('factor_list')

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Wizard Permission denied for user {self.request.user}")
        return redirect(reverse_lazy('dashboard')) # Or appropriate page
 

#-------------------
# # views.py (یا فایل مربوط به ویوهای Factor)
#
# --- Import توابع محاسبه بودجه ---
from budgets.budget_calculations import (
    get_actual_project_remaining_budget, # <<<--- تابع مهم
    get_tankhah_remaining_budget,      # <<<--- تابع مهم
    get_project_total_budget           # <<<--- تابع کمکی (اگر در done لازم شد)
)
from tankhah.utils import restrict_to_user_organization

logger = logging.getLogger('tankhah')

# --- تنظیمات Storage (مانند قبل) ---
wizard_file_storage_location = os.path.join(settings.MEDIA_ROOT, 'temp_wizard_files')
if not os.path.exists(wizard_file_storage_location):
    try: os.makedirs(wizard_file_storage_location)
    except OSError as e: logger.error(f"Could not create wizard storage dir: {e}")
wizard_file_storage = FileSystemStorage(location=wizard_file_storage_location)

# --- کلاس WizardView ---
class FactorCreateWizardView(PermissionBaseView, SessionWizardView):
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('متاسفانه شما دسترسی لازم برای ایجاد فاکتور را ندارید.')
    check_organization = True # Ensure this works as expected in PermissionBaseView
    models = Factor
    form_list = [
        ("select_tankhah", WizardTankhahSelectionForm),
        ("factor_details", WizardFactorDetailsForm),
        ("factor_items", WizardFactorItemFormSet),
        ("factor_docs", WizardFactorDocumentForm),
        ("tankhah_docs", WizardTankhahDocumentForm),
        ("confirmation", WizardConfirmationForm),
    ]

    template_name = "tankhah/Factors/wizard/factor_wizard_base.html"
    file_storage = wizard_file_storage

    FACTOR_TEMPLATES = {
        "select_tankhah": "tankhah/Factors/wizard/step_select_tankhah.html",
        "factor_details": "tankhah/Factors/wizard/step_factor_details.html",
        "factor_items":   "tankhah/Factors/wizard/step_factor_items.html",
        "factor_docs":    "tankhah/Factors/wizard/step_factor_docs.html",
        "tankhah_docs":   "tankhah/Factors/wizard/step_tankhah_docs.html",
        "confirmation":   "tankhah/Factors/wizard/step_confirmation.html",
    }

    STEP_TITLES = {
        "select_tankhah": _("۱. انتخاب تنخواه"),
        "factor_details": _("۲. اطلاعات فاکتور"),
        "factor_items": _("۳. ردیف‌های فاکتور"),
        "factor_docs": _("۴. اسناد فاکتور"),
        "tankhah_docs": _("۵. اسناد تنخواه"),
        "confirmation": _("۶. تأیید نهایی"),
    }

    def get_step_titles(self):
        return self.STEP_TITLES

    def get_template_names(self):
        return [self.FACTOR_TEMPLATES.get(self.steps.current, self.template_name)]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == 'select_tankhah':
            if hasattr(self.request, 'user') and self.request.user.is_authenticated:
                kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        total_steps = len(self.form_list)
        context['step_titles'] = self.get_step_titles()
        context['wizard_title'] = _('ایجاد فاکتور جدید (مرحله {} از {})').format(self.steps.step1, total_steps)
        context['step_name'] = self.steps.current

        # --- پیدا کردن Tankhah و Project ---
        tankhah = None
        project = None
        cleaned_data_step1 = self.get_cleaned_data_for_step('select_tankhah')
        if cleaned_data_step1:
            tankhah = cleaned_data_step1.get('tankhah')
        if not tankhah:
            step1_storage_data = self.storage.get_step_data('select_tankhah')
            if step1_storage_data and 'select_tankhah-tankhah' in step1_storage_data:
                tankhah_id = step1_storage_data.get('select_tankhah-tankhah')
                tankhah = Tankhah.objects.select_related('project', 'subproject__project').filter(pk=tankhah_id).first()

        if tankhah:
            logger.info(
                f"Wizard Context: Found Tankhah ID: {tankhah.id}, Number: {tankhah.number}, Amount: {tankhah.amount}")  # لاگ مشخصات تنخواه
            project = tankhah.project or (tankhah.subproject and tankhah.subproject.project)
            context['selected_tankhah'] = tankhah
            logger.info(f"Wizard Context: Found Tankhah {tankhah.id}, Project {project.id if project else 'None'}")
        else:
             if self.steps.prev: logger.warning(f"Wizard Context: Tankhah not found for step {self.steps.current}.")

        # --- کانتکست مخصوص مرحله آیتم ها ---
        if self.steps.current == 'factor_items':
            context['formset'] = form

            initial_factor_amount = Decimal('0.0')
            cleaned_data_step2 = self.get_cleaned_data_for_step('factor_details')
            if cleaned_data_step2:
                initial_factor_amount = cleaned_data_step2.get('amount', Decimal('0.0'))
            context['initial_factor_amount'] = initial_factor_amount
            logger.info(f"Wizard Context: Initial factor amount from step 2: {initial_factor_amount}")

            # --- محاسبه و ارسال بودجه ها ---
            context['available_project_budget'] = Decimal('0.0')
            context['available_tankhah_budget'] = Decimal('0.0')
            context['budget_warning_threshold'] = Decimal('10.0') # Default
            context['budget_locked_percentage'] = Decimal('0.0')  # Default
            context['budget_warning_action'] = 'NOTIFY'      # Default

            if tankhah:
                # محاسبه مانده تنخواه
                try:
                    context['available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah)
                    logger.info(f"Wizard Context: Tankhah {tankhah.id} remaining budget: {context['available_tankhah_budget']}")
                except Exception as e:
                    logger.error(f"Wizard Context: Error calculating Tankhah {tankhah.id} remaining budget: {e}", exc_info=True)

                # محاسبه مانده پروژه و خواندن آستانه ها
                if project:
                    logger.info(f"Wizard Context: Found Project ID: {project.id}, Name: {project.name}")
                    try:
                        context['available_project_budget'] = get_actual_project_remaining_budget(project)
                        logger.info(f"Wizard Context: Project {project.id} actual remaining budget: {context['available_project_budget']}")

                        proj_alloc = ProjectBudgetAllocation.objects.filter(
                            project=project
                        ).select_related('budget_allocation').order_by('-allocation_date').first()

                        if proj_alloc and proj_alloc.budget_allocation:
                            budget_alloc = proj_alloc.budget_allocation
                            context['budget_warning_threshold'] = budget_alloc.warning_threshold
                            context['budget_locked_percentage'] = budget_alloc.locked_percentage
                            context['budget_warning_action'] = budget_alloc.warning_action
                            logger.info(
                                f"Wizard Context: Budget thresholds read - Warn:{context['budget_warning_threshold']}, Lock:{context['budget_locked_percentage']}, Act:{context['budget_warning_action']}")
                        else:
                            logger.warning(
                                f"Wizard Context: No ProjectBudgetAllocation found to read thresholds for project {project.id}.")

                    except Exception as e:
                        logger.error(
                            f"Wizard Context: ERROR calculating project budget/thresholds for project {project.id}: {e}",
                            exc_info=True)
                    else:
                        logger.warning("Wizard Context: Project is None, skipping project budget calculation.")
                else:
                 logger.warning("Wizard Context: Tankhah is None, skipping all budget calculations.")


        # --- کانتکست مخصوص مرحله تایید نهایی ---
        elif self.steps.current == 'confirmation':
            # بازیابی تمام داده های تمیز شده
            context['step1_data'] = self.get_cleaned_data_for_step('select_tankhah')
            context['step2_data'] = self.get_cleaned_data_for_step('factor_details')
            item_formset_data = self.get_cleaned_data_for_step('factor_items') or []
            context['item_data_list'] = [item for item in item_formset_data if item and not item.get('DELETE')]
            context['summary_total'] = self.get_summary_total()
            # بازیابی فایل ها برای نمایش (نام فایل ها)
            step4_files = self.storage.get_step_files('factor_docs')
            if not step4_files:
                context['step4_files'] = []
                context['warning'] = 'هیچ فایلی در مرحله آپلود یافت نشد.'
            else:
                context['step4_files'] = [f.name for f in step4_files.get('factor_docs-files', []) if f]

            # context['step4_files'] = [f.name for f in step4_files.get('factor_docs-files', []) if
            #                           f] if step4_files else []
            # context['step4_files'] = [f.name for f in self.storage.get_step_files('factor_docs').get('factor_docs-files', []) if f]
            context['step5_files'] = [f.name for f in self.storage.get_step_files('tankhah_docs').get('tankhah_docs-documents', []) if f]

            # محاسبه مجدد بودجه ها برای نمایش نهایی
            context['final_available_project_budget'] = Decimal('0.0')
            context['final_remaining_project_budget'] = Decimal('0.0')
            context['final_available_tankhah_budget'] = Decimal('0.0')
            context['final_remaining_tankhah_budget'] = Decimal('0.0')

            if tankhah:
                # --- لاگ بودجه تنخواه ---
                try:
                    logger.debug(f"Wizard Context: Calling get_tankhah_remaining_budget for Tankhah ID: {tankhah.id}")
                    remaining_tankhah_budget = get_tankhah_remaining_budget(tankhah)
                    context['available_tankhah_budget'] = remaining_tankhah_budget
                    logger.info(
                        f"Wizard Context: SUCCESS - Tankhah {tankhah.id} remaining budget: {remaining_tankhah_budget}")
                except Exception as e:
                    logger.error(f"Wizard Context: ERROR calculating Tankhah {tankhah.id} remaining budget: {e}",
                                 exc_info=True)  # لاگ خطا با جزئیات
            # --- لاگ بودجه پروژه ---
            # if project:
            #     try:
            #         logger.debug( f"Wizard Context: Calling get_actual_project_remaining_budget for Project ID: {project.id}")
            #         remaining_project_budget = get_actual_project_remaining_budget(project)
            #         context['available_project_budget'] = remaining_project_budget
            #         logger.info( f"Wizard Context: SUCCESS - Project {project.id} actual remaining budget: {remaining_project_budget} ")
            #     except Exception as e:
            #         logger.error(f"Confirmation Context Error (Project Budget): {e}")
            if project:
                try:
                    logger.debug( f"Wizard Context: Calling get_actual_project_remaining_budget for Project ID: {project.id}")
                    context['final_available_project_budget'] = get_actual_project_remaining_budget(project)
                    context['final_remaining_project_budget'] = context['final_available_project_budget'] - context['summary_total']

                except Exception as e:
                    logger.error(f"Confirmation Context Error (Project Budget): {e}")
        return context

    def get_summary_total(self):
        # ... (مانند قبل، با دقت بیشتر) ...
        item_formset_data = self.get_cleaned_data_for_step('factor_items') or []
        total = Decimal('0.0')
        for item_data in item_formset_data:
            if item_data and not item_data.get('DELETE', False):
                from decimal import InvalidOperation
                try:
                    # اطمینان از اینکه مقادیر None یا خالی به صفر تبدیل می شوند
                    amount_str = item_data.get('amount', '0') or '0'
                    quantity_str = item_data.get('quantity', '1') or '1'
                    amount = Decimal(amount_str)
                    quantity = Decimal(quantity_str)
                    if quantity <= 0: quantity = Decimal('1') # حداقل تعداد ۱
                    total += (amount * quantity)
                except (TypeError, ValueError, InvalidOperation) as e:
                     logger.warning(f"Wizard Summary: Could not parse amount/quantity in item data: {item_data}. Error: {e}")
                     continue
        return total.quantize(Decimal('0'))

    def done(self, form_list, form_dict, **kwargs):
        logger.info("Wizard 'done' method started.")
        # --- استخراج داده ها ---
        try:
            tankhah_data = form_dict.get('select_tankhah').cleaned_data
            factor_details_data = form_dict.get('factor_details').cleaned_data
            item_formset_instance = form_dict.get('factor_items') # نمونه فرم ست
            tankhah = tankhah_data.get('tankhah')
            project = tankhah.project or (tankhah.subproject and tankhah.subproject.project) if tankhah else None
            total_amount = self.get_summary_total()
        except Exception as e:
            messages.error(self.request, _("خطا در پردازش داده‌های فرم."))
            logger.error(f"Wizard Done: Error extracting data from forms: {e}", exc_info=True)
            return redirect(reverse('factor_wizard'))

        if not tankhah:
            messages.error(self.request, _("خطای داخلی: تنخواه یافت نشد."))
            logger.error("Wizard Done: Tankhah object is None after extraction.")
            return redirect(reverse('factor_wizard'))

        logger.info(f"Wizard Done: Processing Factor for Tankhah {tankhah.id}, Project {project.id if project else 'None'}, Amount {total_amount}")

        # --- اعتبارسنجی نهایی بودجه و وضعیت تنخواه ---
        # 1. بررسی وضعیت تنخواه (استفاده از وضعیت های مجاز)
        allowed_statuses = ['APPROVED', 'ACTIVE', 'PENDING'] # <<<--- وضعیت های مجاز خود را اینجا تعریف کنید
        if tankhah.status not in allowed_statuses:
             messages.error(self.request, _("وضعیت تنخواه ({status}) اجازه ثبت فاکتور جدید را نمی‌دهد.").format(status=tankhah.get_status_display()))
             logger.warning(f"Wizard Done: Tankhah {tankhah.id} status '{tankhah.status}' not allowed.")
             return redirect(reverse('factor_wizard'))

        # 2. بررسی بودجه پروژه و تنخواه
        if not project:
             messages.error(self.request, _("خطا: پروژه مرتبط با تنخواه یافت نشد."))
             logger.error(f"Wizard Done: Project is None for Tankhah {tankhah.id}")
             return redirect(reverse('factor_wizard'))

        try:
            current_available_project_budget = get_actual_project_remaining_budget(project)
            current_available_tankhah_budget = get_tankhah_remaining_budget(tankhah)
            logger.info(f"Wizard Done: Server Budget Check - Project Avail: {current_available_project_budget}, Tankhah Avail: {current_available_tankhah_budget}")

            # بررسی بودجه تنخواه
            if total_amount > current_available_tankhah_budget:
                error_msg = _("خطای اعتبار تنخواه: مبلغ فاکتور ({amount} ریال) از اعتبار باقیمانده تنخواه ({budget} ریال) بیشتر است.").format(amount=f"{total_amount:,.0f}", budget=f"{current_available_tankhah_budget:,.0f}")
                messages.error(self.request, error_msg)
                logger.warning(f"Wizard Done: Tankhah budget exceeded. Factor: {total_amount}, Avail: {current_available_tankhah_budget}")
                self.storage.current_step = 'factor_items'
                return self.render(self.get_form(step='factor_items'), **self.get_context_data(form=self.get_form(step='factor_items')))

            # بررسی بودجه پروژه
            if total_amount > current_available_project_budget:
                error_msg = _("خطای بودجه پروژه: مبلغ فاکتور ({amount} ریال) از بودجه باقیمانده پروژه ({budget} ریال) بیشتر است.").format(amount=f"{total_amount:,.0f}", budget=f"{current_available_project_budget:,.0f}")
                messages.error(self.request, error_msg)
                logger.warning(f"Wizard Done: Project budget exceeded. Factor: {total_amount}, Avail: {current_available_project_budget}")
                self.storage.current_step = 'factor_items'
                return self.render(self.get_form(step='factor_items'), **self.get_context_data(form=self.get_form(step='factor_items')))

            # بررسی قفل بودجه پروژه (اگر نیاز است)
            proj_alloc = ProjectBudgetAllocation.objects.filter(project=project).select_related('budget_allocation').order_by('-allocation_date').first()
            if proj_alloc and proj_alloc.budget_allocation:
                budget_alloc = proj_alloc.budget_allocation
                locked_percentage = budget_alloc.locked_percentage
                if locked_percentage > 0:
                     total_project_allocation = get_project_total_budget(project)
                     locked_amount_threshold = (total_project_allocation * locked_percentage / Decimal(100)).quantize(Decimal('0'))
                     remaining_after_factor = current_available_project_budget - total_amount
                     if remaining_after_factor < locked_amount_threshold:
                          messages.error(self.request, _("خطای بودجه پروژه: ثبت این فاکتور باعث عبور از حد قفل بودجه ({lock_percent}%) می‌شود. مانده محاسبه شده: {remaining} ریال، حد قفل: {threshold} ریال").format(lock_percent=locked_percentage, remaining=f"{remaining_after_factor:,.0f}", threshold=f"{locked_amount_threshold:,.0f}"))
                          logger.warning(f"Wizard Done: Project budget lock threshold exceeded for project {project.id}. Remaining after factor: {remaining_after_factor}, Threshold: {locked_amount_threshold}")
                          self.storage.current_step = 'factor_items'
                          return self.render(self.get_form(step='factor_items'), **self.get_context_data(form=self.get_form(step='factor_items')))

        except Exception as e:
             messages.error(self.request, _("خطا در بررسی بودجه نهایی."))
             logger.error(f"Wizard Done: Exception during final server-side budget check: {e}", exc_info=True)
             return redirect(reverse('factor_wizard'))

        # --- ذخیره اتمی ---
        try:
            with transaction.atomic():
                # 1. ایجاد فاکتور
                factor = Factor.objects.create(
                    tankhah=tankhah,
                    date=factor_details_data['date'],
                    description=factor_details_data.get('description', ''),
                    created_by=self.request.user,
                    amount=total_amount,
                    status='PENDING' # وضعیت اولیه بعد از ثبت
                )
                logger.info(f"Wizard Done: Factor created: ID={factor.pk}, Number={factor.number}")

                # 2. ذخیره آیتم ها
                if item_formset_instance:
                    item_formset_instance.instance = factor
                    item_formset_instance.save()
                    saved_item_count = factor.items.count()
                    logger.info(f"Wizard Done: Factor items saved for Factor ID={factor.pk}. Count: {saved_item_count}")
                else:
                    logger.error("Wizard Done: item_formset_instance is None, cannot save items.")
                    raise ValueError("Formset instance not found.")


                # 3. ذخیره اسناد فاکتور
                factor_files_storage = self.storage.get_step_files('factor_docs')
                saved_factor_docs = 0
                if factor_files_storage and 'factor_docs-files' in factor_files_storage:
                     for file in factor_files_storage.getlist('factor_docs-files'): # Use getlist for multiple files
                         if file:
                             if self.storage.exists(file.name):
                                FactorDocument.objects.create(factor=factor, file=file, uploaded_by=self.request.user)
                                saved_factor_docs += 1
                             else: logger.warning(f"Wizard Done: Factor doc file not found: {file.name}")
                logger.info(f"Wizard Done: Saved {saved_factor_docs} factor documents.")

                # 4. ذخیره اسناد تنخواه
                tankhah_files_storage = self.storage.get_step_files('tankhah_docs')
                saved_tankhah_docs = 0
                if tankhah_files_storage and 'tankhah_docs-documents' in tankhah_files_storage:
                     for file in tankhah_files_storage.getlist('tankhah_docs-documents'): # Use getlist
                         if file:
                             if self.storage.exists(file.name):
                                TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
                                saved_tankhah_docs += 1
                             else: logger.warning(f"Wizard Done: Tankhah doc file not found: {file.name}")
                logger.info(f"Wizard Done: Saved {saved_tankhah_docs} tankhah documents.")

                # 5. ایجاد تراکنش مصرف بودجه (مهم)
                budget_allocation_to_consume = ProjectBudgetAllocation.objects.filter(
                    project=project,
                    budget_allocation__is_active=True,
                    budget_allocation__budget_period__is_active=True
                ).select_related('budget_allocation').order_by('-allocation_date').first()

                if budget_allocation_to_consume:
                    main_budget_allocation = budget_allocation_to_consume.budget_allocation
                    # تولید شناسه تراکنش اگر لازم است
                    # transaction_id = f"FCTR-CONSUME-{factor.id}-{timezone.now().timestamp()}"
                    budget_transaction = BudgetTransaction.objects.create(
                         allocation=main_budget_allocation,
                         transaction_type='CONSUMPTION',
                         amount=total_amount,
                         related_tankhah=tankhah,
                         created_by=self.request.user,
                         description=f"مصرف بودجه فاکتور شماره {factor.number} تنخواه {tankhah.number}",
                         # transaction_id=transaction_id # اگر نیاز به تنظیم دستی دارد
                     )
                    logger.info(f"Wizard Done: BudgetTransaction {budget_transaction.id} created against BA {main_budget_allocation.id}.")
                    # اطمینان از آپدیت remaining_amount در BudgetAllocation
                    # (متد save تراکنش باید این کار را بکند)
                else:
                    logger.error(f"Wizard Done: CRITICAL - Could not find active PBA for Project {project.id} to record consumption.")
                    raise ValidationError(_("خطای سیستمی: تخصیص بودجه معتبری برای ثبت مصرف یافت نشد."))

            # --- موفقیت ---
            self.storage.reset()
            messages.success(self.request, _("فاکتور با شماره {} با موفقیت ثبت شد.").format(factor.number))
            logger.info(f"Wizard Done: Successfully completed for Factor {factor.number}")
            # ریدایرکت به صفحه جزئیات فاکتور جدید
            return redirect(reverse('factor_detail', kwargs={'pk': factor.pk})) # <<<--- URL جزئیات فاکتور

        except ValidationError as ve:
            messages.error(self.request, _("خطا در ذخیره‌سازی: {}").format(ve))
            logger.error(f"Wizard Done: Validation error during final save: {ve}", exc_info=True)
            # بازگشت به مرحله تایید یا شروع؟
            # self.storage.current_step = 'confirmation' # Try going back to confirmation
            # return self.render(self.get_form(step='confirmation'), **self.get_context_data(form=self.get_form(step='confirmation')))
            return redirect(reverse('factor_wizard')) # Safer: back to start
        except Exception as e:
            messages.error(self.request, _("خطای غیرمنتظره در ذخیره‌سازی نهایی فاکتور."))
            logger.error(f"Wizard Done: Unexpected exception during final save transaction: {e}", exc_info=True)
            return redirect(reverse('factor_wizard'))

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Wizard Permission denied for user {self.request.user}")
        return redirect(reverse_lazy('factor_list')) # یا داشبورد
