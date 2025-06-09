# import datetime
# import json
#
# from django import forms
# from django.core.exceptions import ValidationError
# from django.template.response import TemplateResponse
# from django.utils.translation import gettext_lazy as _
# import logging
# import os
# from django.core.serializers.json import DjangoJSONEncoder
# from django.forms import DecimalField
# from django.http import JsonResponse
# from django.urls import reverse_lazy
# from django.views.generic import CreateView, View
#
# from budgets.budget_calculations import get_project_total_budget, get_tankhah_remaining_budget, \
#     get_actual_project_remaining_budget
# from tankhah.Factor.forms_Factor import WizardTankhahSelectionForm, WizardFactorDetailsForm, WizardFactorItemFormSet, \
#     WizardFactorDocumentForm, WizardTankhahDocumentForm, WizardConfirmationForm
# from tankhah.forms import FactorForm, get_factor_item_formset
# from tankhah.models import Factor, TankhahDocument, FactorDocument, FactorItem
# from tankhah.models import Tankhah
# from tankhah.forms import FactorDocumentForm, TankhahDocumentForm
#
#
# from django.conf import settings
# from django.core.files.storage import FileSystemStorage
# from formtools.wizard.views import SessionWizardView
# from django.urls import reverse_lazy, reverse
# from django.shortcuts import get_object_or_404, redirect # Import get_object_or_404
# from django.contrib import messages
# from django.db import transaction, models, IntegrityError
# from django.db.models import Q, Sum, F, Value, DecimalField, Max
# from django.db.models.functions import Coalesce
# from decimal import Decimal, InvalidOperation
# import logging
# from django.utils import timezone # Import timezone
#
# from budgets.models import BudgetTransaction, ProjectBudgetAllocation, BudgetAllocation, TransactionType
# from core.PermissionBase import PermissionBaseView
# from core.models import WorkflowStage
#
#
# logger = logging.getLogger('tankhah') # Use your app's logger name
# #----------
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#
# class FactorCreateView(PermissionBaseView, CreateView):
#     model = Factor
#     form_class = FactorForm
#     template_name = 'tankhah/factor_form.html'
#     success_url = reverse_lazy('factor_list')
#     context_object_name = 'factor'
#     permission_codenames = ['tankhah.factor_add']
#     permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
#     check_organization = True
#
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
#         if tankhah_id:
#             try:
#                 kwargs['tankhah'] = Tankhah.objects.get(id=tankhah_id)
#             except Tankhah.DoesNotExist:
#                 logger.error(f"Tankhah with ID {tankhah_id} not found")
#         logger.debug(f"Form kwargs: {kwargs}")
#         return kwargs
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
#         tankhah = Tankhah.objects.filter(id=tankhah_id).first() if tankhah_id else None
#         FactorItemFormSet = get_factor_item_formset()
#
#         if self.request.POST:
#             form = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah)
#             item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
#             document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
#             tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)
#         else:
#             form = self.form_class(user=self.request.user, tankhah=tankhah)
#             item_formset = FactorItemFormSet(prefix='form')
#             document_form = FactorDocumentForm()
#             tankhah_document_form = TankhahDocumentForm()
#
#         # اضافه کردن اطلاعات بودجه
#         budget_info = None
#         if tankhah:
#             try:
#                 project = tankhah.project
#                 project_allocation = ProjectBudgetAllocation.objects.filter(project=project).first()
#                 if not project_allocation:
#                     logger.warning(f"No ProjectBudgetAllocation found for project {project.name}")
#                     budget_info = None
#                 else:
#                     budget_allocation = project_allocation.budget_allocation
#                     project_budget = project_allocation.allocated_amount
#                     consumed = BudgetTransaction.objects.filter(
#                         allocation=budget_allocation,
#                         transaction_type='CONSUMPTION'
#                     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#                     returned = BudgetTransaction.objects.filter(
#                         allocation=budget_allocation,
#                         transaction_type='RETURN'
#                     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#                     tankhah_remaining = project_budget - consumed + returned
#
#                     budget_info = {
#                         'project_name': project.name,
#                         'project_budget': project_budget,
#                         'tankhah_budget': project_budget,
#                         'tankhah_remaining': tankhah_remaining,
#                     }
#             except Exception as e:
#                 logger.error(f"Error accessing budget info for tankhah {tankhah.number}: {e}")
#                 budget_info = None
#
#         context.update({
#             'form': form,
#             'item_formset': item_formset,
#             'document_form': document_form,
#             'tankhah_document_form': tankhah_document_form,
#             'title': 'ایجاد فاکتور جدید',
#             'tankhah': tankhah,
#             'tankhah_documents': tankhah.documents.all() if tankhah else [],
#             'budget_info': budget_info,
#         })
#         logger.debug(f"Context data: {context}")
#         return context
#
#     def form_valid(self, form):
#         tankhah = form.cleaned_data['tankhah']
#         initial_stage_order = WorkflowStage.objects.order_by('order').first().order
#         FactorItemFormSet = get_factor_item_formset()
#
#         logger.debug(f"Tankhah status: {tankhah.status}, stage order: {tankhah.current_stage.order}, initial stage: {initial_stage_order}")
#
#         if tankhah.current_stage.order != initial_stage_order:
#             messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
#             logger.warning(f"Invalid stage order for tankhah {tankhah.number}: {tankhah.current_stage.order}")
#             return self.form_invalid(form)
#
#         if tankhah.status not in ['DRAFT', 'PENDING']:
#             messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
#             logger.warning(f"Invalid status for tankhah {tankhah.number}: {tankhah.status}")
#             return self.form_invalid(form)
#
#         item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
#         document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
#         tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)
#
#         logger.info(f"Main form valid? {form.is_valid()}")
#         logger.info(f"Item formset valid? {item_formset.is_valid()}")
#         logger.info(f"Document form valid? {document_form.is_valid()}")
#         logger.info(f"Tankhah document form valid? {tankhah_document_form.is_valid()}")
#         logger.debug(f"POST data: {self.request.POST}")
#         logger.debug(f"Files: {self.request.FILES}")
#
#         if not form.is_valid():
#             logger.error(f"Main form errors: {form.errors}")
#         if not item_formset.is_valid():
#             logger.error(f"Item formset errors: {item_formset.errors}")
#             logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")
#
#         valid_items = [f for f in item_formset if f.cleaned_data and not f.cleaned_data.get('DELETE')]
#         if not valid_items:
#             logger.error("No valid items in formset.")
#             messages.error(self.request, 'حداقل یک ردیف معتبر باید وارد کنید.')
#             return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))
#
#         # بررسی بودجه باقی‌مانده تنخواه
#         total_amount = sum(f.cleaned_data.get('amount', 0) for f in valid_items)
#         project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
#         if not project_allocation:
#             logger.error(f"No ProjectBudgetAllocation found for project {tankhah.project.name}")
#             messages.error(self.request, 'تخصیص بودجه برای پروژه این تنخواه یافت نشد.')
#             return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))
#
#         budget_allocation = project_allocation.budget_allocation
#         consumed = BudgetTransaction.objects.filter(
#             allocation=budget_allocation,
#             transaction_type='CONSUMPTION'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         returned = BudgetTransaction.objects.filter(
#             allocation=budget_allocation,
#             transaction_type='RETURN'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         tankhah_remaining = project_allocation.allocated_amount - consumed + returned
#
#         if total_amount > tankhah_remaining:
#             logger.error(f"Factor amount ({total_amount}) exceeds remaining tankhah budget ({tankhah_remaining}).")
#             messages.error(self.request, f'مبلغ فاکتور از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,} تومان) بیشتر است.')
#             return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))
#
#         if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
#             with transaction.atomic():
#                 self.object = form.save(commit=False)
#                 self.object.status = 'DRAFT'
#                 self.object.save()
#
#                 item_formset.instance = self.object
#                 for form in item_formset:
#                     if form.cleaned_data and not form.cleaned_data.get('DELETE'):
#                         form.save()
#
#                 factor_files = self.request.FILES.getlist('files')
#                 for file in factor_files:
#                     FactorDocument.objects.create(factor=self.object, file=file)
#
#                 tankhah_files = self.request.FILES.getlist('documents')
#                 for file in tankhah_files:
#                     TankhahDocument.objects.create(tankhah=tankhah, document=file)
#
#                 # ثبت تراکنش مصرف بودجه
#                 BudgetTransaction.objects.create(
#                     allocation=budget_allocation,
#                     transaction_type='CONSUMPTION',
#                     amount=total_amount,
#                     related_tankhah=tankhah,
#                     created_by=self.request.user,
#                     description=f"مصرف برای فاکتور {self.object.number}",
#                     transaction_id=f"TX-FACTOR-{self.object.id}-{timezone.now().timestamp()}"
#                 )
#
#                 logger.info(f"Factor {self.object.number} saved as DRAFT.")
#                 messages.success(self.request, 'فاکتور به‌صورت پیش‌نویس ذخیره شد. می‌توانید بعداً آن را تکمیل کنید.')
#         else:
#             logger.error(f"Form errors: {form.errors}")
#             logger.error(f"Item formset errors: {item_formset.errors}")
#             logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")
#             logger.error(f"Document form errors: {document_form.errors}")
#             logger.error(f"Tankhah document form errors: {tankhah_document_form.errors}")
#             messages.error(self.request, 'لطفاً خطاهای فرم را بررسی و اصلاح کنید.')
#             return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))
#
#         return redirect(self.get_success_url())
#
#     def form_invalid(self, form):
#         FactorItemFormSet = get_factor_item_formset()
#         item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
#         logger.error(f"Main form errors: {form.errors}")
#         logger.error(f"Item formset errors: {item_formset.errors}")
#         logger.error(f"Item formset non-form errors: {item_formset.non_form_errors()}")
#         messages.error(self.request, 'لطفاً خطاهای فرم را بررسی و اصلاح کنید.')
#         return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))
#
#     def handle_no_permission(self):
#         messages.error(self.request, self.permission_denied_message)
#         logger.warning(f"Permission denied for user {self.request.user}")
#         return super().handle_no_permission()
#
# class FactorCreateWizard(PermissionBaseView, SessionWizardView):
#     template_name = 'tankhah/Factors/factor_wizard.html'
#     FactorItemFormSet = get_factor_item_formset()
#     form_list = [
#
#         ('factor_docs', FactorDocument ),
#         ('tankhah_docs', TankhahDocumentForm ),  # مرحله آپلود اسناد تنخواه
#         ('tankhah', FactorForm),  # مرحله انتخاب تنخواه
#         ('factor', FactorForm),   # مرحله اطلاعات فاکتور
#         ('items', FactorItemFormSet),  # مرحله آیتم‌ها
#         ('documents', FactorDocumentForm),  # مرحله اسناد
#         ('confirmation', WizardConfirmationForm), # مرحله تأیید نهایی
#     ]
#     # form_class =  forms_Factor.W_FactorForm
#
#     permission_codenames = ['tankhah.factor_add']
#     permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
#     check_organization = True
#     file_storage = FileSystemStorage(location=os.path.join(BASE_DIR, 'tmp'))  # ذخیره در پوشه tmp پروژه
#
#
#     def get_form_kwargs(self, step):
#         kwargs = super().get_form_kwargs(step)
#         kwargs['user'] = self.request.user
#
#         if step == 'tankhah':
#             # فقط برای انتخاب تنخواه
#             kwargs['tankhah'] = None
#         elif step in ['factor', 'items', 'documents']:
#             # دریافت تنخواه انتخاب‌شده از مرحله اول
#             tankhah_data = self.get_cleaned_data_for_step('tankhah') or {}
#             tankhah_id = tankhah_data.get('tankhah')
#             if tankhah_id:
#                 try:
#                     kwargs['tankhah'] = Tankhah.objects.get(id=tankhah_id)
#                 except Tankhah.DoesNotExist:
#                     logger.error(f"Tankhah with ID {tankhah_id} not found")
#         logger.debug(f"Form kwargs for step {step}: {kwargs}")
#         return kwargs
#
#     def get_form(self, step=None, data=None, files=None):
#         FactorItemFormSet = get_factor_item_formset()
#         form = super().get_form(step, data, files)
#         if step == 'items':
#             # فرمست آیتم‌ها
#             form = FactorItemFormSet(data, files, prefix='form')
#         elif step == 'documents':
#             # فرم اسناد
#             form = FactorDocumentForm(data, files)
#             self.tankhah_document_form = TankhahDocumentForm(data, files)
#         return form
#
#     def get_context_data(self, form, **kwargs):
#         context = super().get_context_data(form, **kwargs)
#         # context['wizard_steps'] = ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد']
#         context['wizard_steps'] = ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد', 'تأیید نهایی']
#         context['wizard_step'] = self.steps.current
#         current_step =self.steps.current
#         tankhah = None
#         budget_info = None
#
#         # دریافت تنخواه از داده‌های ذخیره‌شده یا URL
#         tankhah_data = self.get_cleaned_data_for_step('tankhah') or {}
#         tankhah_id = tankhah_data.get('tankhah') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
#         if tankhah_id:
#             tankhah = Tankhah.objects.filter(id=tankhah_id).first()
#
#         if tankhah:
#             try:
#                 project = tankhah.project
#                 project_allocation = ProjectBudgetAllocation.objects.filter(project=project).first()
#                 if project_allocation:
#                     budget_allocation = project_allocation.budget_allocation
#                     project_budget = project_allocation.allocated_amount
#                     consumed = BudgetTransaction.objects.filter(
#                         allocation=budget_allocation,
#                         transaction_type='CONSUMPTION'
#                     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#                     returned = BudgetTransaction.objects.filter(
#                         allocation=budget_allocation,
#                         transaction_type='RETURN'
#                     ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#                     tankhah_remaining = project_budget - consumed + returned
#
#                     budget_info = {
#                         'project_name': project.name,
#                         'project_budget': project_budget,
#                         'tankhah_budget': tankhah.amount,
#                         'tankhah_remaining': tankhah_remaining,
#                     }
#             except Exception as e:
#                 logger.error(f"Error accessing budget info for tankhah {tankhah.number}: {e}")
#
#         context.update({
#             'title': 'ایجاد فاکتور جدید',
#             'tankhah': tankhah,
#             'budget_info': budget_info,
#             'tankhah_documents': tankhah.documents.all() if tankhah else [],
#             'wizard_step': current_step,
#             'wizard_steps': ['انتخاب تنخواه', 'اطلاعات فاکتور', 'آیتم‌ها', 'اسناد', 'تأیید نهایی'],
#         })
#         if current_step == 'documents':
#             context['tankhah_document_form'] = getattr(self, 'tankhah_document_form', TankhahDocumentForm())
#         logger.debug(f"Context data: {context}")
#
#         print('Storage data:', self.storage.data)
#         print('Step files (factor_docs):', self.storage.get_step_files('factor_docs'))
#         step4_files = self.storage.get_step_files('factor_docs')
#         context['step4_files'] = [f.name for f in step4_files.get('factor_docs-files', []) if f] if step4_files else []
#
#         # بررسی فایل‌های مرحله factor_docs
#         step4_files = self.storage.get_step_files('factor_docs')
#         if step4_files and 'factor_docs-files' in step4_files:
#             context['step4_files'] = [f.name for f in step4_files['factor_docs-files'] if f]
#
#         return context
#
#     def done(self, form_list, **kwargs):
#         # جمع‌آوری داده‌ها
#         tankhah_form = form_list['tankhah']
#         factor_form = form_list['factor']
#         item_formset = form_list['items']
#         document_form = form_list['documents']
#         tankhah_document_form = self.tankhah_document_form
#
#         tankhah = tankhah_form.cleaned_data['tankhah']
#         initial_stage_order = WorkflowStage.objects.order_by('order').first().order
#
#         # اعتبارسنجی وضعیت تنخواه
#         if tankhah.current_stage.order != initial_stage_order:
#             messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
#             logger.warning(f"Invalid stage order for tankhah {tankhah.number}")
#             return self.render_to_response(self.get_context_data(form=factor_form))
#
#         if tankhah.status not in ['DRAFT', 'PENDING']:
#             messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
#             logger.warning(f"Invalid status for tankhah {tankhah.number}")
#             return self.render_to_response(self.get_context_data(form=factor_form))
#
#         # اعتبارسنجی آیتم‌ها
#         valid_items = [f for f in item_formset if f.cleaned_data and not f.cleaned_data.get('DELETE')]
#         if not valid_items:
#             messages.error(self.request, 'حداقل یک ردیف معتبر باید وارد کنید.')
#             logger.error("No valid items in formset.")
#             return self.render_to_response(self.get_context_data(form=item_formset))
#
#         # محاسبه مبلغ کل آیتم‌ها
#         total_amount = sum(f.cleaned_data.get('amount', 0) * f.cleaned_data.get('quantity', 1) for f in valid_items)
#
#         # اعتبارسنجی بودجه
#         project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
#         if not project_allocation:
#             messages.error(self.request, 'تخصیص بودجه برای پروژه این تنخواه یافت نشد.')
#             logger.error(f"No ProjectBudgetAllocation found for project {tankhah.project.name}")
#             return self.render_to_response(self.get_context_data(form=factor_form))
#
#         budget_allocation = project_allocation.budget_allocation
#         consumed = BudgetTransaction.objects.filter(
#             allocation=budget_allocation,
#             transaction_type='CONSUMPTION'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         returned = BudgetTransaction.objects.filter(
#             allocation=budget_allocation,
#             transaction_type='RETURN'
#         ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
#         tankhah_remaining = project_allocation.allocated_amount - consumed + returned
#
#         if total_amount > tankhah_remaining:
#             messages.error(self.request, f'مبلغ فاکتور از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,} تومان) بیشتر است.')
#             logger.error(f"Factor amount ({total_amount}) exceeds remaining tankhah budget ({tankhah_remaining}).")
#             return self.render_to_response(self.get_context_data(form=factor_form))
#
#         # ثبت فاکتور
#         with transaction.atomic():
#             factor = factor_form.save(commit=False)
#             factor.status = 'DRAFT' if self.request.POST.get('save_draft') else 'PENDING'
#             factor.tankhah = tankhah
#             factor.save()
#
#             item_formset.instance = factor
#             for form in item_formset:
#                 if form.cleaned_data and not form.cleaned_data.get('DELETE'):
#                     form.save()
#
#             factor_files = self.request.FILES.getlist('files')
#             for file in factor_files:
#                 FactorDocument.objects.create(factor=factor, file=file)
#
#             tankhah_files = self.request.FILES.getlist('documents')
#             for file in tankhah_files:
#                 TankhahDocument.objects.create(tankhah=tankhah, document=file)
#
#             if factor.status == 'PENDING':
#                 BudgetTransaction.objects.create(
#                     allocation=budget_allocation,
#                     transaction_type='CONSUMPTION',
#                     amount=total_amount,
#                     related_tankhah=tankhah,
#                     created_by=self.request.user,
#                     description=f"مصرف برای فاکتور {factor.number}",
#                     transaction_id=f"TX-FACTOR-{factor.id}-{timezone.now().timestamp()}"
#                 )
#
#             logger.info(f"Factor {factor.number} saved as {factor.status}.")
#             messages.success(self.request, f'فاکتور به‌صورت {"پیش‌نویس" if factor.status == "DRAFT" else "در انتظار"} ذخیره شد.')
#
#         return redirect(reverse_lazy('factor_list'))
#
#     def post(self, *args, **kwargs):
#         # مدیریت ذخیره پیش‌نویس
#         if self.request.POST.get('save_draft'):
#             return self.done(self.get_all_cleaned_data(), **kwargs)
#         return super().post(*args, **kwargs)
#
#     def handle_no_permission(self):
#         messages.error(self.request, self.permission_denied_message)
#         logger.warning(f"Permission denied for user {self.request.user}")
#         return super().handle_no_permission()
# #---------------- این ویو مسئول دریافت ID تنخواه و برگرداندن اطلاعات بودجه مرتبط است.
#
# class TankhahBudgetInfoAjaxView(PermissionBaseView, View):
#     http_method_names = ['get']
#     permission_codenames = ['tankhah.factor_add'] # User needs factor add permission to see budget?
#
#     def get(self, request, tankhah_id, *args, **kwargs):
#         # Basic permission check first
#         # if not self.has_permission(): # Assuming has_permission checks request.user
#         #     return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
#
#         from django.http import Http404
#         try:
#             # Get Tankhah with related fields needed for budget calculation
#             from django.shortcuts import get_object_or_404
#             tankhah = get_object_or_404(
#                 Tankhah.objects.select_related(
#                     'project',
#                     'subproject',
#                     'project_budget_allocation', # Direct link if available
#                     'budget_allocation', # Fallback link
#                     'project_budget_allocation__budget_allocation', # Get parent allocation
#                 ),
#                 pk=tankhah_id
#             )
#
#             # --- Determine the relevant BudgetAllocation ---
#             target_allocation_instance = None
#             if tankhah.project_budget_allocation:
#                 target_allocation_instance = tankhah.project_budget_allocation.budget_allocation
#                 project_allocation_amount = tankhah.project_budget_allocation.allocated_amount
#                 logger.debug(f"Using ProjectBudgetAllocation {tankhah.project_budget_allocation.id} linked to BudgetAllocation {target_allocation_instance.id}")
#             elif tankhah.budget_allocation:
#                  # Less ideal, assumes Tankhah directly uses a main allocation
#                  target_allocation_instance = tankhah.budget_allocation
#                  project_allocation_amount = target_allocation_instance.allocated_amount # Use the whole allocation amount? Risky.
#                  logger.warning(f"Tankhah {tankhah.id} using direct BudgetAllocation {target_allocation_instance.id}. Budget calculation might be less precise.")
#             else:
#                  logger.error(f"Tankhah {tankhah.id} has no link to ProjectBudgetAllocation or BudgetAllocation.")
#                  return JsonResponse({'success': False, 'error': 'تنخواه به هیچ تخصیص بودجه‌ای متصل نیست.'}, status=400)
#
#             if not target_allocation_instance:
#                  logger.error(f"Could not determine target BudgetAllocation for Tankhah {tankhah.id}")
#                  return JsonResponse({'success': False, 'error': 'تخصیص بودجه مبنا برای تنخواه یافت نشد.'}, status=400)
#
#
#             # --- Calculate Project/Subproject Budget Remaining ---
#             # This uses the BudgetTransaction model linked to the target_allocation_instance
#             consumed_q = Q(allocation=target_allocation_instance, transaction_type='CONSUMPTION')
#             returned_q = Q(allocation=target_allocation_instance, transaction_type='RETURN')
#
#             consumption_total = BudgetTransaction.objects.filter(consumed_q).aggregate(
#                 total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
#             )['total']
#
#             return_total = BudgetTransaction.objects.filter(returned_q).aggregate(
#                 total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
#             )['total']
#
#             # Remaining = Original Allocation - Consumed + Returned
#             # What is the "Original Allocation" amount here? It should be the amount from ProjectBudgetAllocation
#             base_amount_for_remaining = project_allocation_amount if tankhah.project_budget_allocation else target_allocation_instance.allocated_amount
#             project_remaining_budget = base_amount_for_remaining - consumption_total + return_total
#             logger.debug(f"Budget for Allocation {target_allocation_instance.id}: Base={base_amount_for_remaining}, Consumed={consumption_total}, Returned={return_total}, Remaining={project_remaining_budget}")
#
#
#             # --- Calculate Tankhah Specific Remaining ---
#             # Sum of *approved* factors for this *specific* Tankhah
#             # Note: This requires factors to have a status indicating approval/payment
#             factors_approved_sum = Factor.objects.filter(
#                 tankhah=tankhah,
#                 status__in=['APPROVED', 'PAID'] # Adjust statuses as needed
#             ).aggregate(
#                 total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
#             )['total']
#
#             tankhah_remaining_budget = tankhah.amount - factors_approved_sum
#             logger.debug(f"Tankhah {tankhah.id} Budget: Amount={tankhah.amount}, ApprovedFactorsSum={factors_approved_sum}, Remaining={tankhah_remaining_budget}")
#
#
#             data = {
#                 'success': True,
#                 'project_name': tankhah.project.name if tankhah.project else '-',
#                 'subproject_name': tankhah.subproject.name if tankhah.subproject else None,
#                 # Use the calculated project/subproject remaining from transactions
#                 'project_remaining_budget': project_remaining_budget,
#                 # Use the tankhah's own amount and approved factors sum
#                 'tankhah_amount': tankhah.amount,
#                 'tankhah_consumed_approved': factors_approved_sum, # Sum of approved factors
#                 'tankhah_remaining': tankhah_remaining_budget, # Tankhah amount - approved factors
#             }
#             return JsonResponse(data, encoder=DjangoJSONEncoder)
#
#         except Http404:
#             logger.warning(f"Tankhah not found: ID={tankhah_id}")
#             return JsonResponse({'success': False, 'error': 'تنخواه یافت نشد.'}, status=404)
#         except Exception as e:
#             logger.error(f"Error fetching budget info for Tankhah {tankhah_id}: {e}", exc_info=True)
#             return JsonResponse({'success': False, 'error': 'خطای داخلی در دریافت اطلاعات بودجه.'}, status=500)
# #------- Main View
#
# FACTOR_TEMPLATES = {
#     "step1": 'tankhah/Factors/wizard/factor_wizard_step1.html',
#     "step2": 'tankhah/Factors/wizard/factor_wizard_step2_formset.html',
#     "step3_docs": 'tankah/Factors/wizard/factor_wizard_step3_docs.html',
#     "step3_tankhah_docs": 'tankah/Factors/wizard/factor_wizard_step3_tankhah_docs.html',
#     "step4_review": 'tankhah/Factors/wizard/factor_wizard_step4_review.html',
# }
#
# ##########################################3
#
# # تنظیم مسیر ذخیره‌سازی فایل‌های موقت
# wizard_file_storage_location = os.path.join(settings.MEDIA_ROOT, 'temp_wizard_files')
# try:
#     os.makedirs(wizard_file_storage_location, exist_ok=True)
#     logger.info(f"[ویزارد] مسیر ذخیره‌سازی فایل ایجاد شد: {wizard_file_storage_location}")
# except Exception as e:
#     logger.error(f"[ویزارد] خطا در ایجاد مسیر ذخیره‌سازی: {e}")
#
# wizard_file_storage = FileSystemStorage(location=wizard_file_storage_location)
#
# class خنی__FactorCreateWizardView(PermissionBaseView, SessionWizardView):
#     permission_codenames = ['tankhah.factor_add']
#     permission_denied_message = _('متاسفانه شما دسترسی لازم برای ایجاد فاکتور را ندارید.')
#     check_organization = True
#
#     form_list = [
#         ("select_tankhah", WizardTankhahSelectionForm),
#         ("factor_details", WizardFactorDetailsForm),
#         ("factor_items", WizardFactorItemFormSet),
#         ("factor_docs", WizardFactorDocumentForm),
#         ("tankhah_docs", WizardTankhahDocumentForm),
#         ("confirmation", WizardConfirmationForm),
#     ]
#
#     template_name = "tankhah/Factors/wizard/factor_wizard_base.html"
#     file_storage = wizard_file_storage
#
#     FACTOR_TEMPLATES = {
#         "select_tankhah": "tankhah/Factors/wizard/step_select_tankhah.html",
#         "factor_details": "tankhah/Factors/wizard/step_factor_details.html",
#         "factor_items":   "tankhah/Factors/wizard/step_factor_items.html",
#         "factor_docs":    "tankhah/Factors/wizard/step_factor_docs.html",
#         "tankhah_docs":   "tankhah/Factors/wizard/step_tankhah_docs.html",
#         "confirmation":   "tankhah/Factors/wizard/step_confirmation.html",
#     }
#
#     STEP_TITLES = {
#         "select_tankhah": _("۱. انتخاب تنخواه"),
#         "factor_details": _("۲. اطلاعات فاکتور"),
#         "factor_items": _("۳. ردیف‌های فاکتور"),
#         "factor_docs": _("۴. اسناد فاکتور"),
#         "tankhah_docs": _("۵. اسناد تنخواه"),
#         "confirmation": _("۶. تأیید نهایی"),
#     }
#
#     # نام فیلدها
#     TANKHAH_FIELD_NAME_STEP1 = 'tankhah'
#     DATE_FIELD_NAME_STEP2 = 'date'
#     FACTOR_DOCS_FIELD_NAME_STEP4 = 'files'
#     TANKHAH_DOCS_FIELD_NAME_STEP5 = 'documents'
#
#     # متدهای کمکی
#     def _get_selected_tankhah(self):
#         logger.debug("[ویزارد] شروع متد _get_selected_tankhah")
#         tankhah = None
#         cleaned_data_step1 = self.get_cleaned_data_for_step('select_tankhah')
#         logger.debug(f"[ویزارد] داده‌های تمیز شده مرحله ۱: {cleaned_data_step1}")
#         if cleaned_data_step1:
#             tankhah = cleaned_data_step1.get(self.TANKHAH_FIELD_NAME_STEP1)
#             logger.debug(f"[ویزارد] تنخواه از داده‌های تمیز شده: {tankhah}")
#             if tankhah:
#                 logger.info(f"[ویزارد] تنخواه یافت شد: {tankhah}")
#                 return tankhah
#         step1_storage_data = self.storage.get_step_data('select_tankhah')
#         logger.debug(f"[ویزارد] داده‌های ذخیره‌سازی مرحله ۱: {step1_storage_data}")
#         if step1_storage_data:
#             storage_key = f'select_tankhah-{self.TANKHAH_FIELD_NAME_STEP1}'
#             tankhah_id = step1_storage_data.get(storage_key)
#             logger.debug(f"[ویزارد] شناسه تنخواه از ذخیره‌سازی: {tankhah_id}")
#             if tankhah_id:
#                 try:
#                     tankhah = Tankhah.objects.select_related('project', 'subproject__project', 'organization').get(pk=tankhah_id)
#                     logger.info(f"[ویزارد] تنخواه از دیتابیس: {tankhah}")
#                     return tankhah
#                 except (Tankhah.DoesNotExist, ValueError) as e:
#                     logger.error(f"[ویزارد] خطا در دریافت تنخواه از دیتابیس: {e}")
#         logger.warning("[ویزارد] هیچ تنخواهی یافت نشد")
#         return None
#
#     def _get_decimal_from_data(self, data_dict, key, default='0.00'):
#         logger.debug(f"[ویزارد] شروع متد _get_decimal_from_data برای کلید: {key}")
#         value_str = str(data_dict.get(key, default) or default)
#         logger.debug(f"[ویزارد] مقدار خام: {value_str}")
#         try:
#             cleaned_value_str = value_str.replace(',', '').replace(' ', '')
#             result = Decimal(cleaned_value_str).quantize(Decimal('0.01'))
#             logger.debug(f"[ویزارد] مقدار تبدیل‌شده به Decimal: {result}")
#             return result
#         except (TypeError, ValueError, InvalidOperation) as e:
#             logger.error(f"[ویزارد] خطا در تبدیل مقدار به Decimal: {e}")
#             return Decimal(default).quantize(Decimal('0.01'))
#
#     def _get_summary_total(self, step_name='factor_items'):
#         logger.debug(f"[ویزارد] شروع متد _get_summary_total برای مرحله: {step_name}")
#         item_formset_data = self.get_cleaned_data_for_step(step_name) or []
#         logger.debug(f"[ویزارد] داده‌های فرم‌ست مرحله {step_name}: {item_formset_data}")
#         total = Decimal('0.00')
#         for i, item_data in enumerate(item_formset_data):
#             if item_data and isinstance(item_data, dict) and not item_data.get('DELETE', False):
#                 try:
#                     # --- محاسبه بر اساس unit_price ---
#                     unit_price = self._get_decimal_from_data(item_data, 'unit_price')  # <--- خواندن قیمت واحد
#                     quantity = self._get_decimal_from_data(item_data, 'quantity', '1')
#                     if quantity <= 0: quantity = Decimal('1.00')
#
#                     # فقط اگر قیمت واحد معتبر بود، محاسبه کن
#                     if unit_price > 0:
#                         row_total = (unit_price * quantity).quantize(Decimal('0.01'))
#                         total += row_total
#                         logger.debug(
#                             f"[ویزارد-کمکی] ردیف {i + 1}: تعداد={quantity}, قیمت واحد={unit_price}, جمع ردیف={row_total}")
#                     else:
#                         logger.warning(
#                             f"[ویزارد-کمکی] ردیف {i + 1}: قیمت واحد نامعتبر یا صفر ({unit_price})، در مجموع کل لحاظ نشد.")
#                 except Exception as e:
#                     logger.error(f"[ویزارد] خطا در محاسبه جمع آیتم: {e}")
#         result = total.quantize(Decimal('0.01'))
#         logger.info(f"[ویزارد] جمع کل محاسبه‌شده: {result}")
#         return result
#
#     # متدهای ویزارد
#     def get_step_titles(self):
#         logger.debug("[ویزارد] دریافت عناوین مراحل")
#         return self.STEP_TITLES
#
#     def get_template_names(self):
#         current_step = self.steps.current
#         template = self.FACTOR_TEMPLATES.get(current_step, self.template_name)
#         logger.debug(f"[ویزارد] قالب انتخاب‌شده برای مرحله {current_step}: {template}")
#         return [template]
#
#     def handle_no_permission(self):
#         logger.error(f"[ویزارد] عدم دسترسی کاربر: {self.request.user}")
#         messages.error(self.request, self.permission_denied_message)
#         return redirect(reverse_lazy('factor_list'))
#
#     def get_form_kwargs(self, step=None):
#         logger.debug(f"[ویزارد] دریافت kwargs فرم برای مرحله: {step}")
#         kwargs = super().get_form_kwargs(step)
#         if step == 'select_tankhah' and hasattr(self.request, 'user') and self.request.user.is_authenticated:
#             kwargs['user'] = self.request.user
#             logger.debug(f"[ویزارد] کاربر به kwargs اضافه شد: {self.request.user}")
#         return kwargs
#
#     def render_rerender_confirmation(self, form_dict):
#         logger.info("[ویزارد] رندر مجدد مرحله تأیید به دلیل خطا")
#         confirmation_form = form_dict.get('confirmation')
#         context = self.get_context_data(form=confirmation_form)
#         logger.debug(f"[ویزارد] کانتکست برای رندر مجدد: {context}")
#         return TemplateResponse(
#             request=self.request,
#             template=self.FACTOR_TEMPLATES['confirmation'],
#             context=context
#         )
#     # is old
#     # def get_context_data(self, form, **kwargs):
#     #     logger.info(f"[ویزارد] شروع متد get_context_data برای مرحله: {self.steps.current}")
#     #     context = super().get_context_data(form=form, **kwargs)
#     #     current_step_name = self.steps.current
#     #     logger.debug(f"[ویزارد] نام مرحله فعلی: {current_step_name}")
#     #
#     #     # لاگ محتوای خام storage
#     #     logger.debug(f"[ویزارد] محتوای خام storage: {self.storage.data}")
#     #
#     #     context['wizard_title'] = _('ایجاد فاکتور جدید ({})').format(self.STEP_TITLES.get(current_step_name, current_step_name))
#     #     context['step_name'] = current_step_name
#     #     context['step_number'] = self.steps.step1
#     #     context['total_steps'] = len(self.form_list)
#     #     context['step_titles_dict'] = self.STEP_TITLES
#     #     logger.debug(f"[ویزارد] تنظیمات اولیه کانتکست: عنوان={context['wizard_title']}, شماره مرحله={context['step_number']}")
#     #
#     #     tankhah = self._get_selected_tankhah()
#     #     project = tankhah.project if tankhah else None
#     #     if tankhah and not project:
#     #         project = tankhah.subproject.project if tankhah.subproject else None
#     #     context['selected_tankhah_for_display'] = tankhah
#     #     logger.debug(f"[ویزارد] تنخواه انتخاب‌شده: {tankhah}, پروژه: {project}")
#     #
#     #     if current_step_name == 'factor_items':
#     #         logger.info(f"[ویزارد] آماده‌سازی کانتکست برای مرحله ردیف‌های فاکتور")
#     #         context['formset'] = form
#     #         cleaned_data_step2 = self.get_cleaned_data_for_step('factor_details') or {}
#     #         context['initial_factor_amount'] = self._get_decimal_from_data(cleaned_data_step2, 'unit_price')
#     #         logger.debug(f"[ویزارد] داده‌های تمیز شده مرحله ۲: {cleaned_data_step2}")
#     #         logger.debug(f"[ویزارد] مبلغ اولیه فاکتور: {context['initial_factor_amount']}")
#     #
#     #         context['available_tankhah_budget'] = Decimal('0.00')
#     #         context['available_project_budget'] = Decimal('0.00')
#     #         context['budget_warning_threshold'] = Decimal('10.0')
#     #         context['budget_locked_percentage'] = Decimal('0.0')
#     #         context['budget_warning_action'] = 'NOTIFY'
#     #         if tankhah:
#     #             try:
#     #                 context['available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(Decimal('0.01'))
#     #                 logger.info(f"[بودجه] تنخواه {tankhah.id}: موجودی {context['available_tankhah_budget']}")
#     #             except Exception as e:
#     #                 logger.error(f"[بودجه] خطا در محاسبه بودجه تنخواه {tankhah.id}: {e}", exc_info=True)
#     #                 context['available_tankhah_budget'] = _("خطا")
#     #         if project:
#     #             try:
#     #                 context['available_project_budget'] = get_actual_project_remaining_budget(project).quantize(Decimal('0.01'))
#     #                 logger.info(f"[بودجه] پروژه {project.id}: موجودی {context['available_project_budget']}")
#     #             except Exception as e:
#     #                 logger.error(f"[بودجه] خطا در محاسبه بودجه پروژه {project.id}: {e}", exc_info=True)
#     #                 context['available_project_budget'] = _("خطا")
#     #
#     #     elif current_step_name == 'confirmation':
#     #         logger.info("[ویزارد] آماده‌سازی کانتکست برای مرحله تأیید نهایی")
#     #         all_data = self.get_all_cleaned_data()
#     #         step1_data = all_data # self.get_cleaned_data_for_step('select_tankhah') or {}
#     #         step2_data = all_data #self.get_cleaned_data_for_step('factor_details') or {}
#     #         # self.get_cleaned_data_for_step('factor_items') or []
#     #         step3_data =all_data.get('formset-factor_items', [])  # کلید صحیح برای فرم‌ست#
#     #         step4_files_data = self.storage.get_step_files('factor_docs') or {}
#     #         step5_files_data = self.storage.get_step_files('tankhah_docs') or {}
#     #
#     #         logger.debug(f"[ویزارد] داده‌های مرحله ۱ (تنخواه): {step1_data}")
#     #         logger.debug(f"[ویزارد] داده‌های مرحله ۲ (جزئیات): {step2_data}")
#     #         logger.debug(f"[ویزارد] داده‌های مرحله ۳ (آیتم‌ها): {step3_data}")
#     #         logger.debug(f"[ویزارد] داده‌های فایل مرحله ۴ (اسناد فاکتور): {step4_files_data}")
#     #         logger.debug(f"[ویزارد] داده‌های فایل مرحله ۵ (اسناد تنخواه): {step5_files_data}")
#     #
#     #         context['confirmation_tankhah'] = tankhah
#     #         context['confirmation_details'] = {
#     #             'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#     #             'description': step2_data.get('description', _('ندارد')),
#     #             'declared_amount': self._get_decimal_from_data(step2_data, 'amount')
#     #         }
#     #         if not context['confirmation_details']['date']:
#     #             logger.error(f"[ویزارد] تاریخ فاکتور در داده LGBTQ+ در مرحله تأیید یافت نشد!")
#     #         else:
#     #             logger.debug(f"[ویزارد] تاریخ فاکتور برای نمایش: {context['confirmation_details']['date']}")
#     #
#     #         context['confirmation_items'] = [
#     #             {
#     #                 'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#     #                 'description': item.get('description', ''),
#     #                 'quantity': self._get_decimal_from_data(item, 'quantity', '1'),
#     #                 'amount': self._get_decimal_from_data(item, 'amount'),
#     #                 'total': (self._get_decimal_from_data(item, 'quantity', '1') * self._get_decimal_from_data(item, 'amount')).quantize(Decimal('0.01'))
#     #             }
#     #             for item in step3_data if isinstance(item, dict) and not item.get('DELETE', False)
#     #         ]
#     #         context['confirmation_summary_total'] = self._get_summary_total('factor_items')
#     #         logger.info(f"[ویزارد] مجموع محاسبه‌شده آیتم‌ها: {context['confirmation_summary_total']}")
#     #
#     #         # بازیابی فایل‌های اسناد فاکتور
#     #         context['confirmation_factor_docs'] = []
#     #         storage_key_step4 = f'factor_docs-{self.FACTOR_DOCS_FIELD_NAME_STEP4}'
#     #         logger.debug(f"[ویزارد] بررسی فایل‌ها در storage با کلید: {storage_key_step4}")
#     #         if step4_files_data and storage_key_step4 in step4_files_data:
#     #             file_list = step4_files_data.get(storage_key_step4, [])
#     #             context['confirmation_factor_docs'] = [f for f in file_list if f and hasattr(f, 'name')]
#     #             logger.info(f"[ویزارد] تعداد {len(context['confirmation_factor_docs'])} فایل اسناد فاکتور یافت شد.")
#     #         else:
#     #             logger.warning(f"[ویزارد] کلید '{storage_key_step4}' در داده‌های فایل مرحله ۴ یافت نشد یا داده‌ای وجود نداشت. داده خام فایل مرحله ۴: {step4_files_data}")
#     #
#     #         # بازیابی فایل‌های اسناد تنخواه
#     #         context['confirmation_tankhah_docs'] = []
#     #         storage_key_step5 = f'tankhah_docs-{self.TANKHAH_DOCS_FIELD_NAME_STEP5}'
#     #         logger.debug(f"[ویزارد] بررسی فایل‌ها در storage با کلید: {storage_key_step5}")
#     #         if step5_files_data and storage_key_step5 in step5_files_data:
#     #             file_list = step5_files_data.get(storage_key_step5, [])
#     #             context['confirmation_tankhah_docs'] = [f for f in file_list if f and hasattr(f, 'name')]
#     #             logger.info(f"[ویزارد] تعداد {len(context['confirmation_tankhah_docs'])} فایل اسناد تنخواه یافت شد.")
#     #         else:
#     #             logger.warning(f"[ویزارد] کلید '{storage_key_step5}' در داده‌های فایل مرحله ۵ یافت نشد یا داده‌ای وجود نداشت. داده خام فایل مرحله ۵: {step5_files_data}")
#     #
#     #         # نمایش بودجه نهایی
#     #         context['final_available_tankhah_budget'] = Decimal('0.00')
#     #         context['final_remaining_tankhah_budget'] = Decimal('0.00')
#     #         context['final_available_project_budget'] = Decimal('0.00')
#     #         context['final_remaining_project_budget'] = Decimal('0.00')
#     #         if tankhah:
#     #             try:
#     #                 context['final_available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(Decimal('0.01'))
#     #                 logger.debug(f"[بودجه] بودجه موجود تنخواه: {context['final_available_tankhah_budget']}")
#     #             except Exception as e:
#     #                 logger.error(f"[بودجه] خطا در محاسبه بودجه تنخواه: {e}")
#     #         if project:
#     #             try:
#     #                 context['final_available_project_budget'] = get_actual_project_remaining_budget(project).quantize(Decimal('0.01'))
#     #                 logger.debug(f"[بودجه] بودجه موجود پروژه: {context['final_available_project_budget']}")
#     #             except Exception as e:
#     #                 logger.error(f"[بودجه] خطا در محاسبه بودجه پروژه: {e}")
#     #         summary_total = context['confirmation_summary_total']
#     #         context['final_remaining_tankhah_budget'] = context['final_available_tankhah_budget'] - summary_total
#     #         context['final_remaining_project_budget'] = context['final_available_project_budget'] - summary_total
#     #         logger.info(f"[ویزارد] مانده نهایی تنخواه: {context['final_remaining_tankhah_budget']}, مانده نهایی پروژه: {context['final_remaining_project_budget']}")
#     #
#     #     logger.debug(f"[ویزارد] کانتکست نهایی برای مرحله {current_step_name}: {context}")
#     #     return context
#     #
#     #     # --- بازنویسی post با لاگ‌گیری دقیق و اصلاح فراخوانی management_form ---
#
#     def get_context_data(self, form, **kwargs):
#         context = super().get_context_data(form=form, **kwargs)
#         current_step_name = self.steps.current
#         logger.info(f"[Wizard-Context] شروع get_context_data برای مرحله: {current_step_name}")
#
#         context['wizard_title'] = _('ایجاد فاکتور جدید ({})').format(
#             self.STEP_TITLES.get(current_step_name, current_step_name))
#         context['step_name'] = current_step_name
#         context['step_number'] = self.steps.step1
#         context['total_steps'] = len(self.form_list)
#         context['step_titles_dict'] = self.STEP_TITLES
#
#         tankhah = self._get_selected_tankhah()
#         project = tankhah.project if tankhah else None
#         if tankhah and not project:
#             project = tankhah.subproject.project if tankhah.subproject else None
#         context['selected_tankhah_for_display'] = tankhah
#         logger.info(f"[Wizard-Context] {current_step_name}: تنخواه={tankhah}, پروژه={project}")
#
#         if current_step_name == 'confirmation':
#             logger.info("[Wizard-Context] آماده‌سازی کانتکست تایید نهایی.")
#             all_data = self.get_all_cleaned_data()
#             logger.debug(f"[Wizard-Context-Confirm] تمام داده‌های تمیز شده: {all_data}")
#
#             step1_data = all_data
#             step2_data = all_data
#             step3_data = all_data.get('formset-factor_items', [])  # کلید صحیح برای فرم‌ست
#             step4_files_data = self.storage.get_step_files('factor_docs') or {}
#             step5_files_data = self.storage.get_step_files('tankhah_docs') or {}
#
#             context['confirmation_tankhah'] = tankhah
#             context['confirmation_details'] = {
#                 'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#                 'description': step2_data.get('description', _('ندارد')),
#                 'declared_amount': self._get_decimal_from_data(step2_data, 'amount')
#             }
#
#             # context['confirmation_details'] = {
#             #     'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#             #     'description': step2_data.get(self.DESC_FIELD_NAME_STEP2),
#             #     'declared_amount': self._get_decimal_from_data(step2_data, self.AMOUNT_FIELD_NAME_STEP2)
#             # }
#             # حذف شرط نادرست
#             # if not context['confirmation_details']['date']:
#             #     logger.error("[Wizard-Context-Confirm] تاریخ یافت نشد!")
#
#             context['confirmation_summary_total'] = self._calculate_summary_total(step3_data)
#             context['confirmation_items'] = []
#             logger.info(f"[Wizard-Context-Confirm] شروع آماده‌سازی آیتم‌ها برای نمایش. تعداد خام: {len(step3_data)}")
#             for item_data in step3_data:
#                 if isinstance(item_data, dict) and not item_data.get('DELETE', False):
#                     desc = item_data.get(self.ITEM_DESC_FIELD)
#                     qty = self._get_decimal_from_data(item_data, self.ITEM_QTY_FIELD, '1')
#                     price = self._get_decimal_from_data(item_data, self.ITEM_UNIT_PRICE_FIELD)
#                     if desc and qty > 0 and price > 0:
#                         context['confirmation_items'].append({
#                             'description': desc,
#                             'quantity': qty,
#                             'unit_price': price,
#                             'total': (qty * price).quantize(Decimal('0.01'))
#                         })
#
#             logger.info(
#                 f"[Wizard-Context-Confirm] تعداد آیتم‌های معتبر برای نمایش: {len(context['confirmation_items'])}")
#             logger.info(f"[Wizard-Context-Confirm] مجموع کل نهایی برای نمایش: {context['confirmation_summary_total']}")
#
#             key4 = f'factor_docs-{self.FACTOR_DOCS_FIELD_NAME_STEP4}'
#             context['confirmation_factor_docs'] = [f for f in step4_files_data.get(key4, []) if
#                                                    f and hasattr(f, 'name')]
#             key5 = f'tankhah_docs-{self.TANKHAH_DOCS_FIELD_NAME_STEP5}'
#             context['confirmation_tankhah_docs'] = [f for f in step5_files_data.get(key5, []) if
#                                                     f and hasattr(f, 'name')]
#             logger.debug(
#                 f"[Wizard-Context-Confirm] فایل‌های فاکتور: {len(context['confirmation_factor_docs'])}, فایل‌های تنخواه: {len(context['confirmation_tankhah_docs'])}")
#
#             context['final_available_tankhah_budget'] = Decimal('0.00')
#             context['final_remaining_tankhah_budget'] = Decimal('0.00')
#             context['final_available_project_budget'] = Decimal('0.00')
#             context['final_remaining_project_budget'] = Decimal('0.00')
#             if tankhah:
#                 try:
#                     context['final_available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(
#                         Decimal('0.01'))
#                 except Exception:
#                     pass
#             if project:
#                 try:
#                     context['final_available_project_budget'] = get_actual_project_remaining_budget(project).quantize(
#                         Decimal('0.01'))
#                 except Exception:
#                     pass
#             summary_total = context['confirmation_summary_total']
#             context['final_remaining_tankhah_budget'] = context['final_available_tankhah_budget'] - summary_total
#             context['final_remaining_project_budget'] = context['final_available_project_budget'] - summary_total
#             logger.info(
#                 f"[Wizard-Context-Confirm] بودجه نهایی: تنخواه={context['final_remaining_tankhah_budget']}, پروژه={context['final_remaining_project_budget']}")
#
#         logger.info(f"[Wizard-Context] پایان get_context_data برای مرحله: {current_step_name}")
#         return context
#
#     def post(self, *args, **kwargs):
#         logger.info(f"[ویزارد-POST] شروع اجرای متد post بازنویسی شده. مرحله فعلی از storage: {self.steps.current}")
#         logger.debug(f"[ویزارد-POST] داده‌های POST: {self.request.POST}")
#         logger.debug(f"[ویزارد-POST] فایل‌های FILES: {self.request.FILES}")
#
#         # --- 1. اعتبارسنجی ManagementForm ---
#         from formtools.wizard.forms import ManagementForm
#         management_form = ManagementForm(self.request.POST, prefix=self.prefix)
#
#         if not management_form.is_valid():
#             logger.error("[ویزارد-POST] management_form نامعتبر است! خطاها: %s", management_form.errors.as_json())
#             messages.error(self.request, _("خطای داخلی: اطلاعات کنترل مراحل ویزارد نامعتبر است."))
#             try:
#                  current_step_on_error = self.request.POST.get(self.management_form.add_prefix('current_step'), self.steps.first)
#                  form_on_error = self.get_form(step=current_step_on_error, data=self.request.POST, files=self.request.FILES)
#                  return self.render(form_on_error)
#             except Exception: return self.render_goto_step(self.steps.first)
#
#         current_step = management_form.cleaned_data["current_step"]
#         logger.info(f"[ویزارد-POST] مرحله شناسایی شده از management_form: '{current_step}'")
#
#         # --- 2. دریافت و اعتبارسنجی فرم مرحله فعلی ---
#         form = self.get_form(step=current_step, data=self.request.POST, files=self.request.FILES)
#
#         if not form.is_valid():
#              logger.warning(f"[ویزارد-POST] فرم مرحله '{current_step}' نامعتبر است. خطاها: {form.errors.as_json(escape_html=True)}")
#              # اجازه می‌دهیم render پیش‌فرض خطاها را نمایش دهد
#              # return self.render(form) # این خط نیاز نیست، super().post() این کار را می‌کند
#
#         # --- 3. لاگ‌گیری قبل از فراخوانی متد post والد ---
#         is_last_step = current_step == self.steps.last
#         if form.is_valid() and is_last_step:
#             logger.info("[ویزارد-POST] فرم مرحله آخر ('%s') معتبر است. انتظار اجرای done() توسط متد post والد می‌رود...", current_step)
#         elif form.is_valid():
#             logger.info("[ویزارد-POST] فرم مرحله ('%s') معتبر است. انتظار رفتن به مرحله بعد توسط متد post والد می‌رود...", current_step)
#
#         # --- 4. فراخوانی متد post اصلی WizardView ---
#         #    این متد خودش مسئول ذخیره داده در storage، رندر مرحله بعد یا فراخوانی done() است.
#         try:
#             response = super().post(*args, **kwargs)
#             # لاگ‌گیری نتیجه اجرای متد والد
#             logger.info(f"[ویزارد-POST] اجرای متد post والد تکمیل شد. کد وضعیت پاسخ: {response.status_code}")
#             if response.status_code in (301, 302, 307, 308):
#                  logger.info(f"[ویزارد-POST] ریدایرکت شناسایی شد (احتمالاً done() موفق بود). URL مقصد: {response.url}")
#             elif response.status_code == 200:
#                  # اگر ۲۰۰ بود یعنی یا خطا در فرم بوده و همان مرحله رندر شده، یا done خطا داده و به confirmation برگشته
#                  logger.debug("[ویزارد-POST] پاسخ ۲۰۰ OK دریافت شد (یا خطای فرم یا بازگشت از done با خطا).")
#             return response
#         except Exception as e:
#             logger.error(f"[ویزارد-POST] خطا در حین اجرای متد post والد: {e}", exc_info=True)
#             # اگر خطای غیرمنتظره‌ای در منطق داخلی ویزارد رخ دهد
#             messages.error(self.request, _("خطای پیش‌بینی نشده در پردازش مراحل ویزارد."))
#             # شاید بازگشت به مرحله اول امن‌ترین کار باشد
#             return self.render_goto_step(self.steps.first)
#
#     # --- done() Method (Final Version based on Model - No changes needed here) ---
#     # def done(self, form_list, form_dict, **kwargs):
#     #     logger.info("[ویزارد-DONE] ** شروع اجرای متد done() **")
#     #     # ... (Rest of the done method remains the same as the previous final version) ...
#     #     # ... (Includes data extraction, transaction, factor/item/doc creation, error handling, redirect) ...
#     #     cleaned_data_step1 = self.get_cleaned_data_for_step('select_tankhah') or {}
#     #     cleaned_data_step2 = self.get_cleaned_data_for_step('factor_details') or {}
#     #     cleaned_data_step3 = self.get_cleaned_data_for_step('factor_items') or []
#     #
#     #     logger.debug(f"[ویزارد-DONE] داده مرحله ۱: {cleaned_data_step1}")
#     #     logger.debug(f"[ویزارد-DONE] داده مرحله ۲: {cleaned_data_step2}")
#     #
#     #     # --- Extract & Validate Core Data ---
#     #     try:
#     #         tankhah = cleaned_data_step1.get(self.TANKHAH_FIELD_NAME_STEP1)
#     #         if not isinstance(tankhah, Tankhah): raise ValueError(f"آبجکت تنخواه معتبر نیست (نوع: {type(tankhah)}).")
#     #         logger.info(f"[ویزارد-DONE] تنخواه معتبر: ID={tankhah.id}")
#     #
#     #         factor_date = cleaned_data_step2.get(self.DATE_FIELD_NAME_STEP2)
#     #         if not isinstance(factor_date, (datetime.date, datetime.datetime)): raise ValueError(f"تاریخ فاکتور معتبر نیست (نوع: {type(factor_date)}).")
#     #         logger.info(f"[ویزارد-DONE] تاریخ فاکتور معتبر: {factor_date}")
#     #
#     #         description = cleaned_data_step2.get('description')
#     #         total_amount = self._get_summary_total('factor_items')
#     #         logger.info(f"[ویزارد-DONE] مبلغ کل محاسبه شده: {total_amount}")
#     #
#     #     except Exception as e:
#     #          logger.error(f"[ویزارد-DONE] خطا در استخراج/اعتبارسنجی داده اولیه: {e}", exc_info=True); messages.error(self.request, _("خطای داخلی داده اولیه.")); return self.render_rerender_confirmation(form_dict)
#     #
#     #     # --- Database Transaction ---
#     #     try:
#     #         with transaction.atomic():
#     #             logger.info(f"[ویزارد-DONE] شروع تراکنش...")
#     #             # 1. Create Factor
#     #             factor = Factor(tankhah=tankhah, date=factor_date, amount=total_amount, description=description, created_by=self.request.user, status='PENDING')
#     #             factor.save(); logger.info(f"[ویزارد-DONE] فاکتور ذخیره شد: ID={factor.id}, شماره={factor.number}")
#     #
#     #             # 2. Create Factor Items
#     #             if cleaned_data_step3:
#     #                 items_to_create = [ FactorItem(factor=factor, description=i.get('d',''), quantity=self._get_decimal_from_data(i,'q','1'), amount=self._get_decimal_from_data(i,'a'), status='PENDING')
#     #                                     for i in cleaned_data_step3 if isinstance(i,dict) and not i.get('DELETE',False) and i.get('description') and self._get_decimal_from_data(i,'a') > 0 ]
#     #                 if items_to_create: FactorItem.objects.bulk_create(items_to_create); logger.info(f"[ویزارد-DONE] {len(items_to_create)} ردیف ذخیره شد.")
#     #                 else: logger.warning("[ویزارد-DONE] ردیف معتبری یافت نشد.")
#     #             else: logger.warning("[ویزارد-DONE] داده ردیف‌ها خالی بود.")
#     #
#     #             # 3. Save Factor Documents
#     #             factor_docs_form = form_dict.get('factor_docs')
#     #             if factor_docs_form and factor_docs_form.is_valid():
#     #                 files_step4 = factor_docs_form.cleaned_data.get(self.FACTOR_DOCS_FIELD_NAME_STEP4, [])
#     #                 if files_step4:
#     #                     docs4 = [ FactorDocument(factor=factor, document=f, uploaded_by=self.request.user) for f in files_step4 if f ];
#     #                     if docs4: FactorDocument.objects.bulk_create(docs4); logger.info(f"[ویزارد-DONE] {len(docs4)} سند فاکتور ذخیره شد.")
#     #                 else: logger.info("[ویزارد-DONE] فایلی برای اسناد فاکتور نبود.")
#     #
#     #             # 4. Save Tankhah Documents
#     #             tankhah_docs_form = form_dict.get('tankhah_docs')
#     #             if tankhah_docs_form and tankhah_docs_form.is_valid():
#     #                 files_step5 = tankhah_docs_form.cleaned_data.get(self.TANKHAH_DOCS_FIELD_NAME_STEP5, [])
#     #                 if files_step5:
#     #                     docs5 = [ TankhahDocument(tankhah=tankhah, document=f, uploaded_by=self.request.user) for f in files_step5 if f ];
#     #                     if docs5: TankhahDocument.objects.bulk_create(docs5); logger.info(f"[ویزارد-DONE] {len(docs5)} سند تنخواه ذخیره شد.")
#     #                 else: logger.info("[ویزارد-DONE] فایلی برای اسناد تنخواه نبود.")
#     #
#     #         # --- Transaction Success ---
#     #         logger.info(f"[ویزارد-DONE] تراکنش موفق. فاکتور {factor.number} ایجاد شد.")
#     #         messages.success(self.request, _("فاکتور با کد رهگیری {} ایجاد شد.").format(factor.number)); self.storage.reset(); logger.info("[ویزارد] storage پاک شد.")
#     #         return redirect('factor_list')
#     #
#     #     # --- Exception Handling during DB Operations ---
#     #     except IntegrityError as e: logger.error(f"[ویزارد-DONE] خطای IntegrityError: {e}", exc_info=True); messages.error(self.request, _("خطا: شماره فاکتور تکراری."))
#     #     except ValueError as e:
#     #          if 'fromgregorian' in str(e): logger.error(f"[ویزارد-DONE] خطای jdatetime: {e}", exc_info=True); messages.error(self.request, _("خطای داخلی: پردازش تاریخ مدل."))
#     #          else: logger.error(f"[ویزارد-DONE] خطای ValueError: {e}", exc_info=True); messages.error(self.request, _("خطا در داده‌ها."))
#     #     except Exception as e: logger.error(f"[ویزارد-DONE] خطای ناشناخته دیتابیس: {e}", exc_info=True); messages.error(self.request, _("خطای ناشناخته ذخیره‌سازی."))
#     #
#     #     # --- Return to confirmation on error ---
#     #     return self.render_rerender_confirmation(form_dict)
#
#     # --- متد done() - اصلاح شده برای استفاده صحیح از formset ---
#     # --- متد done() - اصلاح شده برای استفاده صحیح از formset ---
#     # def done(self, form_list, form_dict, **kwargs):
#     #     logger.info("[ویزارد-DONE] **** شروع اجرای متد done() ****")
#     #
#     #     # --- بازیابی فرم‌های معتبر از form_dict ---
#     #     try:
#     #         logger.debug("[ویزارد-DONE] شروع بازیابی فرم‌های معتبر از form_dict...")
#     #         select_tankhah_form = form_dict.get('select_tankhah')
#     #         factor_details_form = form_dict.get('factor_details')
#     #         factor_items_formset = form_dict.get('factor_items')  # این نمونه formset است
#     #         factor_docs_form = form_dict.get('factor_docs')
#     #         tankhah_docs_form = form_dict.get('tankhah_docs')
#     #
#     #         # بررسی وجود فرم‌ها
#     #         if not all([select_tankhah_form, factor_details_form, factor_items_formset]):
#     #             raise ValueError("فرم‌های مراحل اصلی یافت نشدند.")
#     #
#     #         logger.debug(
#     #             f"[ویزارد-DONE] فرم تنخواه: {select_tankhah_form.cleaned_data if select_tankhah_form.is_valid() else 'نامعتبر'}")
#     #         logger.debug(
#     #             f"[ویزارد-DONE] فرم جزئیات: {factor_details_form.cleaned_data if factor_details_form.is_valid() else 'نامعتبر'}")
#     #         logger.debug(f"[ویزارد-DONE] فرم‌ست آیتم‌ها معتبر؟ {factor_items_formset.is_valid()}")
#     #         if not factor_items_formset.is_valid():
#     #             logger.error(f"[ویزارد-DONE] فرم‌ست آیتم‌ها نامعتبر است: {factor_items_formset.errors}")
#     #             logger.error(f"[ویزارد-DONE] خطاهای غیر فرم فرم‌ست: {factor_items_formset.non_form_errors()}")
#     #             messages.error(self.request, _("خطا در اطلاعات ردیف‌های فاکتور."))
#     #             return self.render_goto_step('factor_items')
#     #
#     #     except Exception as e:
#     #         logger.error(f"[ویزارد-DONE] خطا در بازیابی فرم‌ها از form_dict: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای داخلی: عدم امکان بازیابی فرم‌های مراحل."))
#     #         return redirect('tankhah_factor_list')
#     #
#     #     # --- استخراج داده‌های کلیدی از فرم‌های معتبر ---
#     #     try:
#     #         logger.info("[ویزارد-DONE] شروع استخراج داده کلیدی از فرم‌های معتبر...")
#     #         # ۱. تنخواه از فرم مرحله ۱
#     #         tankhah = select_tankhah_form.cleaned_data.get(self.TANKHAH_FIELD_NAME_STEP1)
#     #         if not tankhah:
#     #             raise ValueError("تنخواه در فرم مرحله ۱ یافت نشد.")
#     #         logger.info(f"[ویزارد-DONE] تنخواه: {tankhah}")
#     #
#     #         # ۲. تاریخ از فرم مرحله ۲
#     #         factor_date = factor_details_form.cleaned_data.get(self.DATE_FIELD_NAME_STEP2)
#     #         if not factor_date:
#     #             raise ValueError("تاریخ در فرم مرحله ۲ یافت نشد.")
#     #         factor_date_final = factor_date.date() if isinstance(factor_date, datetime.datetime) else factor_date
#     #         logger.info(f"[ویزارد-DONE] تاریخ نهایی: {factor_date_final}")
#     #
#     #         # ۳. توضیحات از فرم مرحله ۲
#     #         description = factor_details_form.cleaned_data.get('description')
#     #         logger.debug(f"[ویزارد-DONE] توضیحات: '{description}'")
#     #
#     #         # ۴. محاسبه مبلغ کل از فرم‌ست معتبر مرحله ۳
#     #         total_amount = Decimal('0.00')
#     #         for item_form in factor_items_formset:
#     #             if item_form.is_valid() and not item_form.cleaned_data.get('DELETE', False):
#     #                 amount = item_form.cleaned_data.get('amount', Decimal('0.00'))
#     #                 quantity = item_form.cleaned_data.get('quantity', Decimal('1.00'))
#     #                 if quantity <= 0:
#     #                     quantity = Decimal('1.00')
#     #                 total_amount += (amount * quantity)
#     #         total_amount = total_amount.quantize(Decimal('0.01'))
#     #         logger.info(f"[ویزارد-DONE] مبلغ کل محاسبه شده از فرم‌ست آیتم‌ها: {total_amount}")
#     #
#     #         # ۵. استخراج فایل‌ها از فرم‌های فایل
#     #         files_step4 = []
#     #         if factor_docs_form and factor_docs_form.is_valid():
#     #             files_step4 = factor_docs_form.cleaned_data.get(self.FACTOR_DOCS_FIELD_NAME_STEP4, [])
#     #         logger.debug(f"[ویزارد-DONE] فایل‌های معتبر اسناد فاکتور: {files_step4}")
#     #
#     #         files_step5 = []
#     #         if tankhah_docs_form and tankhah_docs_form.is_valid():
#     #             files_step5 = tankhah_docs_form.cleaned_data.get(self.TANKHAH_DOCS_FIELD_NAME_STEP5, [])
#     #         logger.debug(f"[ویزارد-DONE] فایل‌های معتبر اسناد تنخواه: {files_step5}")
#     #
#     #     except (ValueError, KeyError, TypeError, Exception) as e:
#     #         logger.error(f"[ویزارد-DONE] خطا در استخراج داده از فرم‌های معتبر: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای داخلی هنگام پردازش داده‌های معتبر."))
#     #         return self.render_rerender_confirmation(form_dict)
#     #
#     #     # --- عملیات دیتابیس ---
#     #     try:
#     #         with transaction.atomic():
#     #             logger.info(f"[ویزارد-DONE] شروع تراکنش دیتابیس...")
#     #             # 1. ایجاد Factor
#     #             factor = Factor(
#     #                 tankhah=tankhah,
#     #                 date=factor_date_final,
#     #                 amount=total_amount,
#     #                 description=description,
#     #                 created_by=self.request.user,
#     #                 status='PENDING'
#     #             )
#     #             factor.save()
#     #             logger.info(f"[ویزارد-DONE] فاکتور ذخیره شد: ID={factor.id}, شماره={factor.number}")
#     #
#     #             # --- 2. ایجاد FactorItem ها با استفاده از فرم‌ست ---
#     #             logger.info(f"[ویزارد-DONE] شروع ذخیره آیتم‌ها از فرم‌ست...")
#     #             items_to_create = []
#     #             for item_form in factor_items_formset:
#     #                 if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE',
#     #                                                                                                        False):
#     #                     cleaned_data = item_form.cleaned_data
#     #                     logger.debug(f"[ویزارد-DONE] آماده‌سازی آیتم از فرم: {cleaned_data}")
#     #
#     #                     # بررسی وجود unit_price و اعتبارسنجی آن
#     #                     unit_price = cleaned_data.get('unit_price', None)
#     #                     if unit_price is not None and unit_price <= 0:
#     #                         logger.warning(f"[ویزارد-DONE] قیمت واحد نامعتبر برای آیتم: {cleaned_data}")
#     #                         raise ValueError("قیمت واحد باید مثبت باشد.")
#     #
#     #                     # ایجاد نمونه FactorItem
#     #                     item_data = {
#     #                         'factor': factor,
#     #                         'description': cleaned_data.get('description', ''),
#     #                         'quantity': cleaned_data.get('quantity', Decimal('1.00')),
#     #                         'amount': cleaned_data.get('amount', Decimal('0.00')),
#     #                         'status': 'PENDING',
#     #                         # فیلدهای اضافی (اگر وجود دارند)
#     #                         'category': cleaned_data.get('category', None),
#     #                         'transaction_type': cleaned_data.get('transaction_type', None),
#     #                         'min_stage_order': cleaned_data.get('min_stage_order', 1)
#     #                     }
#     #                     if unit_price is not None:
#     #                         item_data['unit_price'] = unit_price
#     #
#     #                     items_to_create.append(FactorItem(**item_data))
#     #                     logger.debug(f"[ویزارد-DONE] آیتم آماده ذخیره: {item_data}")
#     #
#     #                 elif item_form.cleaned_data.get('DELETE'):
#     #                     logger.debug(f"[ویزارد-DONE] آیتم برای حذف علامت خورده: {item_form.cleaned_data}")
#     #
#     #             if items_to_create:
#     #                 logger.debug(f"[ویزارد-DONE] آماده bulk_create برای {len(items_to_create)} آیتم...")
#     #                 FactorItem.objects.bulk_create(items_to_create)
#     #                 logger.info(f"[ویزارد-DONE] تعداد {len(items_to_create)} ردیف فاکتور ذخیره شد.")
#     #             else:
#     #                 logger.warning("[ویزارد-DONE] هیچ آیتم جدید یا تغییر یافته‌ای برای ذخیره یافت نشد.")
#     #                 raise ValueError("حداقل یک ردیف فاکتور معتبر باید وجود داشته باشد.")
#     #
#     #             # 3. ذخیره اسناد فاکتور
#     #             if files_step4:
#     #                 docs4 = [FactorDocument(factor=factor, document=f, uploaded_by=self.request.user) for f in
#     #                          files_step4 if f]
#     #                 if docs4:
#     #                     FactorDocument.objects.bulk_create(docs4)
#     #                     logger.info(f"[ویزارد-DONE] {len(docs4)} سند فاکتور ذخیره شد.")
#     #             else:
#     #                 logger.info("[ویزارد-DONE] فایلی برای اسناد فاکتور نبود.")
#     #
#     #             # 4. ذخیره اسناد تنخواه
#     #             if files_step5:
#     #                 docs5 = [TankhahDocument(tankhah=tankhah, document=f, uploaded_by=self.request.user) for f in
#     #                          files_step5 if f]
#     #                 if docs5:
#     #                     TankhahDocument.objects.bulk_create(docs5)
#     #                     logger.info(f"[ویزارد-DONE] {len(docs5)} سند تنخواه ذخیره شد.")
#     #             else:
#     #                 logger.info("[ویزارد-DONE] فایلی برای اسناد تنخواه نبود.")
#     #
#     #             # --- Transaction Success ---
#     #             logger.info(
#     #                 f"[ویزارد-DONE] تراکنش موفق. فاکتور {factor.number} با {len(items_to_create)} ردیف ایجاد شد.")
#     #             messages.success(self.request, _("فاکتور با کد رهگیری {} با موفقیت ایجاد شد.").format(factor.number))
#     #             self.storage.reset()
#     #             logger.info("[ویزارد] storage پاک شد.")
#     #             return redirect('tankhah_factor_list')
#     #
#     #     # --- مدیریت خطاهای دیتابیس ---
#     #     except IntegrityError as e:
#     #         logger.error(f"[ویزارد-DONE] خطای IntegrityError: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطا: شماره فاکتور تکراری."))
#     #     except ValueError as e:
#     #         if 'fromgregorian' in str(e):
#     #             logger.error(f"[ویزارد-DONE] خطای jdatetime در مدل: {e}", exc_info=True)
#     #             messages.error(self.request, _("خطای داخلی: پردازش تاریخ مدل."))
#     #         else:
#     #             logger.error(f"[ویزارد-DONE] خطای ValueError: {e}", exc_info=True)
#     #             messages.error(self.request, _("خطا در داده‌ها: {}").format(str(e)))
#     #     except Exception as e:
#     #         logger.error(f"[ویزارد-DONE] خطای ناشناخته دیتابیس: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای ناشناخته ذخیره‌سازی."))
#     #
#     #     # --- بازگشت به تأیید نهایی در صورت خطا ---
#     #     return self.render_rerender_confirmation(form_dict)
#
#     print('dlkfhdskjfhkjdshf')
#
#     # def done(self, form_list, form_dict, **kwargs):
#     #     logger.info("[ویزارد-DONE] **** شروع اجرای متد done() ****")
#     #
#     #     # --- بازیابی فرم‌های معتبر از form_dict ---
#     #     try:
#     #         logger.debug("[ویزارد-DONE] شروع بازیابی فرم‌های معتبر از form_dict...")
#     #         select_tankhah_form = form_dict.get('select_tankhah')
#     #         factor_details_form = form_dict.get('factor_details')
#     #         factor_items_formset = form_dict.get('factor_items')  # این نمونه formset است
#     #         factor_docs_form = form_dict.get('factor_docs')
#     #         tankhah_docs_form = form_dict.get('tankhah_docs')
#     #
#     #         # بررسی وجود فرم‌ها
#     #         if not all([select_tankhah_form, factor_details_form, factor_items_formset]):
#     #             raise ValueError("فرم‌های مراحل اصلی یافت نشدند.")
#     #
#     #         logger.debug(
#     #             f"[ویزارد-DONE] فرم تنخواه: {select_tankhah_form.cleaned_data if select_tankhah_form.is_valid() else 'نامعتبر'}")
#     #         logger.debug(
#     #             f"[ویزارد-DONE] فرم جزئیات: {factor_details_form.cleaned_data if factor_details_form.is_valid() else 'نامعتبر'}")
#     #         logger.debug(f"[ویزارد-DONE] فرم‌ست آیتم‌ها معتبر؟ {factor_items_formset.is_valid()}")
#     #         if not factor_items_formset.is_valid():
#     #             logger.error(f"[ویزارد-DONE] فرم‌ست آیتم‌ها نامعتبر است: {factor_items_formset.errors}")
#     #             logger.error(f"[ویزارد-DONE] خطاهای غیر فرم فرم‌ست: {factor_items_formset.non_form_errors()}")
#     #             messages.error(self.request, _("خطا در اطلاعات ردیف‌های فاکتور."))
#     #             return self.render_goto_step('factor_items')
#     #
#     #     except Exception as e:
#     #         logger.error(f"[ویزارد-DONE] خطا در بازیابی فرم‌ها از form_dict: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای داخلی: عدم امکان بازیابی فرم‌های مراحل."))
#     #         return redirect('tankhah_factor_list')
#     #
#     #     # --- استخراج داده‌های کلیدی از فرم‌های معتبر ---
#     #     try:
#     #         logger.info("[ویزارد-DONE] شروع استخراج داده کلیدی از فرم‌های معتبر...")
#     #         # ۱. تنخواه از فرم مرحله ۱
#     #         tankhah = select_tankhah_form.cleaned_data.get(self.TANKHAH_FIELD_NAME_STEP1)
#     #         if not tankhah:
#     #             raise ValueError("تنخواه در فرم مرحله ۱ یافت نشد.")
#     #         logger.info(f"[ویزارد-DONE] تنخواه: {tankhah}")
#     #
#     #         # ۲. تاریخ از فرم مرحله ۲
#     #         factor_date = factor_details_form.cleaned_data.get(self.DATE_FIELD_NAME_STEP2)
#     #         if not factor_date:
#     #             raise ValueError("تاریخ در فرم مرحله ۲ یافت نشد.")
#     #         factor_date_final = factor_date.date() if isinstance(factor_date, datetime.datetime) else factor_date
#     #         logger.info(f"[ویزارد-DONE] تاریخ نهایی: {factor_date_final}")
#     #
#     #         # ۳. توضیحات از فرم مرحله ۲
#     #         description = factor_details_form.cleaned_data.get('description')
#     #         logger.debug(f"[ویزارد-DONE] توضیحات: '{description}'")
#     #
#     #         # ۴. محاسبه مبلغ کل از فرم‌ست معتبر مرحله ۳
#     #         total_amount = Decimal('0.00')
#     #         for item_form in factor_items_formset:
#     #             if item_form.is_valid() and not item_form.cleaned_data.get('DELETE', False):
#     #                 amount = item_form.cleaned_data.get('amount', Decimal('0.00'))
#     #                 quantity = item_form.cleaned_data.get('quantity', Decimal('1.00'))
#     #                 if quantity <= 0:
#     #                     quantity = Decimal('1.00')
#     #                 total_amount += (amount * quantity)
#     #         total_amount = total_amount.quantize(Decimal('0.01'))
#     #         logger.info(f"[ویزارد-DONE] مبلغ کل محاسبه شده از فرم‌ست آیتم‌ها: {total_amount}")
#     #
#     #         # ۵. استخراج فایل‌ها از فرم‌های فایل
#     #         files_step4 = []
#     #         if factor_docs_form and factor_docs_form.is_valid():
#     #             files_step4 = factor_docs_form.cleaned_data.get(self.FACTOR_DOCS_FIELD_NAME_STEP4, [])
#     #         logger.debug(f"[ویزارد-DONE] فایل‌های معتبر اسناد فاکتور: {files_step4}")
#     #
#     #         files_step5 = []
#     #         if tankhah_docs_form and tankhah_docs_form.is_valid():
#     #             files_step5 = tankhah_docs_form.cleaned_data.get(self.TANKHAH_DOCS_FIELD_NAME_STEP5, [])
#     #         logger.debug(f"[ویزارد-DONE] فایل‌های معتبر اسناد تنخواه: {files_step5}")
#     #
#     #     except (ValueError, KeyError, TypeError, Exception) as e:
#     #         logger.error(f"[ویزارد-DONE] خطا در استخراج داده از فرم‌های معتبر: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای داخلی هنگام پردازش داده‌های معتبر."))
#     #         return self.render_rerender_confirmation(form_dict)
#     #
#     #     # --- عملیات دیتابیس ---
#     #     try:
#     #         with transaction.atomic():
#     #             logger.info(f"[ویزارد-DONE] شروع تراکنش دیتابیس...")
#     #             # 1. ایجاد Factor
#     #             factor = Factor(
#     #                 tankhah=tankhah,
#     #                 date=factor_date_final,
#     #                 amount=total_amount,
#     #                 description=description,
#     #                 created_by=self.request.user,
#     #                 status='PENDING'
#     #             )
#     #             factor.save()
#     #             logger.info(f"[ویزارد-DONE] فاکتور ذخیره شد: ID={factor.id}, شماره={factor.number}")
#     #
#     #             # --- 2. ایجاد FactorItem ها با استفاده از فرم‌ست ---
#     #             logger.info(f"[ویزارد-DONE] شروع ذخیره آیتم‌ها از فرم‌ست...")
#     #             items_to_create = []
#     #             for item_form in factor_items_formset:
#     #                 if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE',
#     #                                                                                                        False):
#     #                     cleaned_data = item_form.cleaned_data
#     #                     logger.debug(f"[ویزارد-DONE] آماده‌سازی آیتم از فرم: {cleaned_data}")
#     #
#     #                     # بررسی وجود unit_price و اعتبارسنجی آن
#     #                     unit_price = cleaned_data.get('unit_price', None)
#     #                     if unit_price is not None and unit_price <= 0:
#     #                         logger.warning(f"[ویزارد-DONE] قیمت واحد نامعتبر برای آیتم: {cleaned_data}")
#     #                         raise ValueError("قیمت واحد باید مثبت باشد.")
#     #
#     #                     # ایجاد نمونه FactorItem
#     #                     item_data = {
#     #                         'factor': factor,
#     #                         'description': cleaned_data.get('description', ''),
#     #                         'quantity': cleaned_data.get('quantity', Decimal('1.00')),
#     #                         'amount': cleaned_data.get('amount', Decimal('0.00')),
#     #                         'status': 'PENDING',
#     #                         # فیلدهای اضافی (اگر وجود دارند)
#     #                         'category': cleaned_data.get('category', None),
#     #                         'transaction_type': cleaned_data.get('transaction_type', None),
#     #                         'min_stage_order': cleaned_data.get('min_stage_order', 1)
#     #                     }
#     #                     if unit_price is not None:
#     #                         item_data['unit_price'] = unit_price
#     #
#     #                     items_to_create.append(FactorItem(**item_data))
#     #                     logger.debug(f"[ویزارد-DONE] آیتم آماده ذخیره: {item_data}")
#     #
#     #                 elif item_form.cleaned_data.get('DELETE'):
#     #                     logger.debug(f"[ویزارد-DONE] آیتم برای حذف علامت خورده: {item_form.cleaned_data}")
#     #
#     #             if items_to_create:
#     #                 logger.debug(f"[ویزارد-DONE] آماده bulk_create برای {len(items_to_create)} آیتم...")
#     #                 FactorItem.objects.bulk_create(items_to_create)
#     #                 logger.info(f"[ویزارد-DONE] تعداد {len(items_to_create)} ردیف فاکتور ذخیره شد.")
#     #             else:
#     #                 logger.warning("[ویزارد-DONE] هیچ آیتم جدید یا تغییر یافته‌ای برای ذخیره یافت نشد.")
#     #                 raise ValueError("حداقل یک ردیف فاکتور معتبر باید وجود داشته باشد.")
#     #
#     #             # 3. ذخیره اسناد فاکتور
#     #             if files_step4:
#     #                 docs4 = [FactorDocument(factor=factor, document=f, uploaded_by=self.request.user) for f in
#     #                          files_step4 if f]
#     #                 if docs4:
#     #                     FactorDocument.objects.bulk_create(docs4)
#     #                     logger.info(f"[ویزارد-DONE] {len(docs4)} سند فاکتور ذخیره شد.")
#     #             else:
#     #                 logger.info("[ویزارد-DONE] فایلی برای اسناد فاکتور نبود.")
#     #
#     #             # 4. ذخیره اسناد تنخواه
#     #             if files_step5:
#     #                 docs5 = [TankhahDocument(tankhah=tankhah, document=f, uploaded_by=self.request.user) for f in
#     #                          files_step5 if f]
#     #                 if docs5:
#     #                     TankhahDocument.objects.bulk_create(docs5)
#     #                     logger.info(f"[ویزارد-DONE] {len(docs5)} سند تنخواه ذخیره شد.")
#     #             else:
#     #                 logger.info("[ویزارد-DONE] فایلی برای اسناد تنخواه نبود.")
#     #
#     #             # --- Transaction Success ---
#     #             logger.info(
#     #                 f"[ویزارد-DONE] تراکنش موفق. فاکتور {factor.number} با {len(items_to_create)} ردیف ایجاد شد.")
#     #             messages.success(self.request, _("فاکتور با کد رهگیری {} با موفقیت ایجاد شد.").format(factor.number))
#     #             self.storage.reset()
#     #             logger.info("[ویزارد] storage پاک شد.")
#     #             return redirect('tankhah_factor_list')
#     #
#     #     # --- مدیریت خطاهای دیتابیس ---
#     #     except IntegrityError as e:
#     #         logger.error(f"[ویزارد-DONE] خطای IntegrityError: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطا: شماره فاکتور تکراری."))
#     #     except ValueError as e:
#     #         if 'fromgregorian' in str(e):
#     #             logger.error(f"[ویزارد-DONE] خطای jdatetime در مدل: {e}", exc_info=True)
#     #             messages.error(self.request, _("خطای داخلی: پردازش تاریخ مدل."))
#     #         else:
#     #             logger.error(f"[ویزارد-DONE] خطای ValueError: {e}", exc_info=True)
#     #             messages.error(self.request, _("خطا در داده‌ها: {}").format(str(e)))
#     #     except Exception as e:
#     #         logger.error(f"[ویزارد-DONE] خطای ناشناخته دیتابیس: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای ناشناخته ذخیره‌سازی."))
#     #
#     #     # --- بازگشت به تأیید نهایی در صورت خطا ---
#     #     return self.render_rerender_confirmation(form_dict)
#     def done(self, form_list, form_dict, **kwargs):
#         logger.info("[Wizard-DONE] **** شروع اجرای متد done() ****")
#
#         try:
#             logger.debug("[Wizard-DONE] شروع بازیابی فرم‌ها از form_dict...")
#             select_tankhah_form = form_dict.get('select_tankhah')
#             factor_details_form = form_dict.get('factor_details')
#             factor_items_formset = form_dict.get('factor_items')
#             factor_docs_form = form_dict.get('factor_docs')
#             tankhah_docs_form = form_dict.get('tankhah_docs')
#
#             if not all([select_tankhah_form.is_valid(), factor_details_form.is_valid(),
#                         factor_items_formset.is_valid(), factor_docs_form.is_valid(),
#                         tankhah_docs_form.is_valid()]):
#                 raise ValueError("یکی از فرم‌ها نامعتبر است.")
#
#             logger.debug("[Wizard-DONE] تمام فرم‌های لازم معتبر هستند.")
#
#             logger.info("[Wizard-DONE] شروع استخراج داده کلیدی...")
#             tankhah = select_tankhah_form.cleaned_data.get(self.TANKHAH_FIELD_NAME_STEP1)
#             factor_date = factor_details_form.cleaned_data.get(self.DATE_FIELD_NAME_STEP2)
#             factor_date_final = factor_date.date() if isinstance(factor_date, datetime.datetime) else factor_date
#             description = factor_details_form.cleaned_data.get(self.DESC_FIELD_NAME_STEP2)
#
#             total_amount = Decimal('0.00')
#             items_to_create_data = []
#             logger.debug(f"[Wizard-DONE] پردازش {len(factor_items_formset.forms)} فرم در فرم‌ست آیتم‌ها...")
#             for item_form in factor_items_formset:
#                 if item_form.is_valid() and not item_form.cleaned_data.get('DELETE'):
#                     item_cleaned_data = item_form.cleaned_data
#                     logger.debug(f"[Wizard-DONE] داده تمیز شده آیتم {item_form.prefix}: {item_cleaned_data}")
#                     if item_cleaned_data.get(self.ITEM_DESC_FIELD):
#                         quantity = item_cleaned_data.get(self.ITEM_QTY_FIELD, Decimal('1.00'))
#                         unit_price = item_cleaned_data.get(self.ITEM_UNIT_PRICE_FIELD, Decimal('0.00'))
#                         if quantity > 0 and unit_price > 0:
#                             item_total = (quantity * unit_price).quantize(Decimal('0.01'))
#                             total_amount += item_total
#                             item_cleaned_data['calculated_amount'] = item_total
#                             items_to_create_data.append(item_cleaned_data)
#                         else:
#                             logger.warning(
#                                 f"[Wizard-DONE] آیتم {item_form.prefix} به دلیل تعداد یا قیمت واحد نامعتبر، در مجموع کل محاسبه نشد.")
#                     else:
#                         logger.warning(f"[Wizard-DONE] آیتم {item_form.prefix} فاقد شرح بود و نادیده گرفته شد.")
#             total_amount = total_amount.quantize(Decimal('0.01'))
#             logger.info(f"[Wizard-DONE] مبلغ کل نهایی محاسبه شده: {total_amount}")
#             logger.info(f"[Wizard-DONE] تعداد آیتم‌های معتبر برای ذخیره: {len(items_to_create_data)}")
#
#             files_step4 = factor_docs_form.cleaned_data.get(self.FACTOR_DOCS_FIELD_NAME_STEP4, [])
#             files_step5 = tankhah_docs_form.cleaned_data.get(self.TANKHAH_DOCS_FIELD_NAME_STEP5, [])
#             logger.debug(
#                 f"[Wizard-DONE] فایل‌های اسناد فاکتور: {len(files_step4)}, فایل‌های اسناد تنخواه: {len(files_step5)}")
#
#             with transaction.atomic():
#                 logger.info(f"[Wizard-DONE] شروع تراکنش دیتابیس...")
#                 factor = Factor(
#                     tankhah=tankhah,
#                     date=factor_date_final,
#                     amount=total_amount,
#                     description=description,
#                     created_by=self.request.user,
#                     status='PENDING'
#                 )
#                 factor.save()
#                 logger.info(f"[Wizard-DONE] فاکتور ذخیره شد: ID={factor.id}, شماره={factor.number}")
#
#                 if items_to_create_data:
#                     factor_items_to_create = [
#                         FactorItem(
#                             factor=factor,
#                             description=item_data.get(self.ITEM_DESC_FIELD, ''),
#                             quantity=item_data.get(self.ITEM_QTY_FIELD, Decimal('1.00')),
#                             unit_price=item_data.get(self.ITEM_UNIT_PRICE_FIELD, Decimal('0.00')),
#                             amount=item_data.get('calculated_amount', Decimal('0.00')),
#                             status='PENDING',
#                             transaction_type=item_data.get(self.ITEM_TRANS_TYPE_FIELD) or TransactionType.objects.get(
#                                 id=1),  # پیش‌فرض
#                             min_stage_order=item_data.get(self.ITEM_MIN_STAGE_FIELD, 1)
#                         ) for item_data in items_to_create_data
#                     ]
#                     if factor_items_to_create:
#                         logger.debug(f"[Wizard-DONE] آماده bulk_create برای آیتم‌ها: {factor_items_to_create}")
#                         FactorItem.objects.bulk_create(factor_items_to_create)
#                         logger.info(f"[Wizard-DONE] {len(factor_items_to_create)} ردیف فاکتور ذخیره شد.")
#                 else:
#                     logger.warning("[Wizard-DONE] هیچ آیتم معتبری برای ذخیره نبود.")
#
#                 if files_step4:
#                     docs4 = [FactorDocument(factor=factor, document=f, uploaded_by=self.request.user) for f in
#                              files_step4 if f]
#                     if docs4:
#                         FactorDocument.objects.bulk_create(docs4)
#                         logger.info(f"[Wizard-DONE] {len(docs4)} سند فاکتور ذخیره شد.")
#                 if files_step5:
#                     docs5 = [TankhahDocument(tankhah=tankhah, document=f, uploaded_by=self.request.user) for f in
#                              files_step5 if f]
#                     if docs5:
#                         TankhahDocument.objects.bulk_create(docs5)
#                         logger.info(f"[Wizard-DONE] {len(docs5)} سند تنخواه ذخیره شد.")
#
#                 logger.info(f"[Wizard-DONE] تراکنش موفق. فاکتور {factor.number} ایجاد شد.")
#                 messages.success(self.request, _("فاکتور با کد رهگیری {} ایجاد شد.").format(factor.number))
#                 self.storage.reset()
#                 logger.info("[Wizard] storage پاک شد.")
#                 return redirect('tankhah_factor_list')
#
#         except IntegrityError as e:
#             logger.error(f"[Wizard-DONE] خطای IntegrityError: {e}", exc_info=True)
#             messages.error(self.request, _("خطای ذخیره‌سازی: داده‌های نامعتبر یا نقض محدودیت‌های پایگاه داده."))
#         except ValueError as e:
#             logger.error(f"[Wizard-DONE] خطای ValueError: {e}", exc_info=True)
#             messages.error(self.request, _("خطا در پردازش داده‌ها."))
#         except Exception as e:
#             logger.error(f"[Wizard-DONE] خطای ناشناخته: {e}", exc_info=True)
#             messages.error(self.request, _("خطای ناشناخته در ذخیره‌سازی."))
#
#         return self.render_rerender_confirmation(form_dict)
#
# import jdatetime
#
# class FactorCreateWizardView(PermissionBaseView, SessionWizardView):
#     # --- Basic Wizard Configuration ---
#     permission_required = 'tankhah.factor_add'
#     login_url = reverse_lazy('login')
#     permission_denied_message = _('متاسفانه شما دسترسی لازم برای ایجاد فاکتور را ندارید.')
#
#     # --- Define form_list using form classes/factory ---
#     form_list = [
#         ("select_tankhah", WizardTankhahSelectionForm),
#         ("factor_details", WizardFactorDetailsForm),
#         ("factor_items", WizardFactorItemFormSet), # Use the imported FACTORY
#         ("factor_docs", WizardFactorDocumentForm),
#         ("tankhah_docs", WizardTankhahDocumentForm),
#         ("confirmation", WizardConfirmationForm),
#     ]
#
#     template_name = "tankhah/Factors/wizard/factor_wizard_base.html"
#     file_storage = wizard_file_storage
#
#     FACTOR_TEMPLATES = {
#         "select_tankhah": "tankhah/Factors/wizard/step_select_tankhah.html",
#         "factor_details": "tankhah/Factors/wizard/step_factor_details.html",
#         "factor_items":   "tankhah/Factors/wizard/step_factor_items.html",
#         "factor_docs":    "tankhah/Factors/wizard/step_factor_docs.html",
#         "tankhah_docs":   "tankhah/Factors/wizard/step_tankhah_docs.html",
#         "confirmation":   "tankhah/Factors/wizard/step_confirmation.html",
#     }
#
#     STEP_TITLES = {
#         "select_tankhah": _("۱. انتخاب تنخواه"),
#         "factor_details": _("۲. اطلاعات فاکتور"),
#         "factor_items": _("۳. ردیف‌های فاکتور"),
#         "factor_docs": _("۴. اسناد فاکتور"),
#         "tankhah_docs": _("۵. اسناد تنخواه"),
#         "confirmation": _("۶. تأیید نهایی"),
#     }
#
#     # --- Field Names (used for consistency) ---
#     TANKHAH_FIELD_NAME_STEP1 = 'tankhah'
#     DATE_FIELD_NAME_STEP2 = 'date'
#     AMOUNT_FIELD_NAME_STEP2 = 'amount' # Declared amount in step 2
#     DESC_FIELD_NAME_STEP2 = 'description'
#     FACTOR_DOCS_FIELD_NAME_STEP4 = 'files'
#     TANKHAH_DOCS_FIELD_NAME_STEP5 = 'documents'
#     # Item form field names (must match WizardFactorItemForm)
#     ITEM_DESC_FIELD = 'description'
#     ITEM_QTY_FIELD = 'quantity'
#     ITEM_UNIT_PRICE_FIELD = 'unit_price'
#     ITEM_AMOUNT_FIELD = 'amount' # This is calculated: quantity * unit_price
#     # Other optional item fields
#     ITEM_CATEGORY_FIELD = 'category'
#     ITEM_TRANS_TYPE_FIELD = 'transaction_type'
#     ITEM_MIN_STAGE_FIELD = 'min_stage_order'
#     # ---
#
#     # --- Helper Methods ---
#     def _get_selected_tankhah(self):
#         """بازیابی مطمئن آبجکت تنخواه انتخاب شده"""
#         tankhah = None
#         step_name = 'select_tankhah'
#         field_name = self.TANKHAH_FIELD_NAME_STEP1
#         cleaned_data = self.get_cleaned_data_for_step(step_name)
#         if cleaned_data:
#             tankhah = cleaned_data.get(field_name)
#             if tankhah: logger.debug(f"[Wizard-Helper] تنخواه ID {tankhah.id} از cleaned_data یافت شد."); return tankhah
#
#         storage_data = self.storage.get_step_data(step_name)
#         if storage_data:
#             key = f'{step_name}-{field_name}'
#             tankhah_id = storage_data.get(key)
#             if tankhah_id:
#                 try: return Tankhah.objects.select_related('project', 'subproject__project', 'organization').get(pk=int(tankhah_id))
#                 except (Tankhah.DoesNotExist, ValueError, TypeError): pass
#         logger.warning("[Wizard-Helper] تنخواه یافت نشد.")
#         return None
#
#     def _get_decimal_from_data(self, data_dict, key, default='0.00'):
#         """تبدیل امن مقدار به Decimal"""
#         value_str = str(data_dict.get(key, default) or default)
#         try: return Decimal(value_str.replace(',', '').replace(' ', '')).quantize(Decimal('0.01'))
#         except (TypeError, ValueError, InvalidOperation): return Decimal(default).quantize(Decimal('0.01'))
#
#     def _calculate_summary_total(self, items_data_list):
#         """محاسبه مجموع کل از لیست داده‌های آیتم (معمولا cleaned_data فرم‌ست)"""
#         total = Decimal('0.00')
#         if not isinstance(items_data_list, list): return total # Handle invalid input
#
#         logger.debug(f"[Wizard-Helper] محاسبه مجموع کل از {len(items_data_list)} آیتم...")
#         for i, item_data in enumerate(items_data_list):
#             if isinstance(item_data, dict) and not item_data.get('DELETE', False):
#                 # --- محاسبه بر اساس قیمت واحد و تعداد ---
#                 unit_price = self._get_decimal_from_data(item_data, self.ITEM_UNIT_PRICE_FIELD)
#                 quantity = self._get_decimal_from_data(item_data, self.ITEM_QTY_FIELD, '1')
#                 if quantity <= 0: quantity = Decimal('1.00')
#
#                 if item_data.get(self.ITEM_DESC_FIELD) and unit_price > 0 : # Only count valid items
#                     row_total = (unit_price * quantity).quantize(Decimal('0.01'))
#                     total += row_total
#                     # logger.debug(f"[Wizard-Helper] ردیف {i+1}: تعداد={quantity}, قیمت واحد={unit_price}, جمع={row_total}")
#                 # else: logger.warning(f"آیتم {i+1} نامعتبر یا حذف شده، نادیده گرفته شد: {item_data}")
#
#         logger.info(f"[Wizard-Helper] مجموع کل محاسبه شده: {total}")
#         return total.quantize(Decimal('0.01'))
#
#     # --- Wizard Overridden Methods ---
#     def get_step_titles(self): return self.STEP_TITLES
#     def get_template_names(self): return [self.FACTOR_TEMPLATES.get(self.steps.current, self.template_name)]
#
#     def get_form_kwargs(self, step=None):
#         kwargs = super().get_form_kwargs(step)
#         logger.debug(f"[Wizard-get_form_kwargs] دریافت kwargs برای مرحله: {step}")
#         if step == 'select_tankhah' and self.request.user.is_authenticated:
#             kwargs['user'] = self.request.user
#             logger.debug(f"[Wizard-get_form_kwargs] کاربر به kwargs اضافه شد.")
#         # Pass Tankhah instance to formset step if needed by forms within formset
#         # Note: inlineformset_factory handles parent instance binding automatically
#         # if step == 'factor_items':
#         #     kwargs['tankhah'] = self._get_selected_tankhah()
#         return kwargs
#
#     def get_form_initial(self, step):
#         initial = super().get_form_initial(step)
#         logger.debug(f"[Wizard-get_form_initial] دریافت initial برای مرحله: {step}. پیش‌فرض: {initial}")
#         # Add initial data if needed, e.g., default date
#         if step == 'factor_details':
#              if 'date' not in initial: # Set default date only if not already set
#                  try:
#                     # Set default to today's Jalali date string
#                     today_jalali = jdatetime.date.today().strftime('%Y/%m/%d')
#                     initial['date'] = today_jalali
#                     logger.debug(f"[Wizard-get_form_initial] تنظیم تاریخ پیش‌فرض برای '{step}': {today_jalali}")
#                  except Exception as e:
#                       logger.error(f"خطا در تنظیم تاریخ جلالی پیش‌فرض: {e}")
#         return initial
#
#     def get_form_instance(self, step):
#         """Ensure InlineFormset gets the parent instance correctly in `done`."""
#         # For steps *before* done(), the parent (Factor) doesn't exist yet.
#         # For the `factor_items` step, inlineformset_factory needs the PARENT instance.
#         # This instance is only available *after* the Factor is created in `done`.
#         # So, during the wizard steps, we return None for the formset step.
#         # In the `done` method, when we re-instantiate the formset for saving,
#         # we will pass the newly created `factor` object as the instance.
#         logger.debug(f"[Wizard-get_form_instance] دریافت instance برای مرحله: {step}")
#         if step == 'factor_items':
#              logger.debug(f"[Wizard-get_form_instance] مرحله '{step}' فرم‌ست است، instance=None برگردانده می‌شود.")
#              return None
#         # Let the default handle other steps (e.g., if using ModelForms for them)
#         return super().get_form_instance(step)
#     # --- متد کمکی برای رندر مجدد مرحله تایید ---
#     def render_rerender_confirmation(self, form_dict):
#         """Renders the confirmation step again, usually after a done() error."""
#         logger.warning("[Wizard] رندر مجدد مرحله تأیید به دلیل خطا در done()")
#         confirmation_form = form_dict.get('confirmation', self.get_form('confirmation')) # Get or create form
#         context = self.get_context_data(form=confirmation_form)
#         return TemplateResponse(request=self.request, template=self.FACTOR_TEMPLATES['confirmation'], context=context)
#
#     # --- متد post (فقط لاگ‌گیری، اعتماد به والد) ---
#     def post(self, *args, **kwargs):
#         logger.info(f"[ویزارد-POST] شروع اجرای متد post بازنویسی شده. مرحله فعلی از storage: {self.steps.current}")
#         logger.debug(f"[ویزارد-POST] داده‌های POST: {self.request.POST}")
#         logger.debug(f"[ویزارد-POST] فایل‌های FILES: {self.request.FILES}")
#
#         from formtools.wizard.forms import ManagementForm
#         management_form = ManagementForm(self.request.POST, prefix=self.prefix)
#
#         if not management_form.is_valid():
#             logger.error("[ویزارد-POST] management_form نامعتبر است! خطاها: %s", management_form.errors.as_json())
#             messages.error(self.request, _("خطای داخلی: اطلاعات کنترل مراحل ویزارد نامعتبر است."))
#             try:
#                 current_step_on_error = self.request.POST.get(self.management_form.add_prefix('current_step'),
#                                                               self.steps.first)
#                 form_on_error = self.get_form(step=current_step_on_error, data=self.request.POST,
#                                               files=self.request.FILES)
#                 return self.render(form_on_error)
#             except Exception:
#                 return self.render_goto_step(self.steps.first)
#
#         current_step = management_form.cleaned_data["current_step"]
#         logger.info(f"[ویزارد-POST] مرحله شناسایی شده از management_form: '{current_step}'")
#
#         form = self.get_form(step=current_step, data=self.request.POST, files=self.request.FILES)
#
#         from django.forms.formsets import BaseFormSet
#         if isinstance(form, BaseFormSet):
#             if form.is_valid():
#                 logger.info("[ویزارد-POST] فرم‌ست مرحله ('%s') معتبر است.", current_step)
#                 valid_forms = [f for f in form.forms if f.is_valid() and not f.cleaned_data.get('DELETE', False)]
#                 logger.debug(f"[ویزارد-POST] تعداد فرم‌های معتبر: {len(valid_forms)}")
#             else:
#                 formset_errors = []
#                 for i, subform in enumerate(form.forms):
#                     if subform.errors:
#                         formset_errors.append({f"فرم {i}": subform.errors})
#                 logger.warning("[ویزارد-POST] فرم‌ست مرحله ('%s') نامعتبر است. خطاها: %s", current_step,
#                                json.dumps(formset_errors, ensure_ascii=False))
#                 logger.debug("[ویزارد-POST] داده‌های فرم‌ست: %s",
#                              [f.cleaned_data for f in form.forms if f.cleaned_data])
#         else:
#             if form.is_valid():
#                 logger.info("[ویزارد-POST] فرم مرحله ('%s') معتبر است.", current_step)
#             else:
#                 logger.warning("[ویزارد-POST] فرم مرحله ('%s') نامعتبر است. خطاها: %s", current_step,
#                                form.errors.as_json())
#
#         is_last_step = current_step == self.steps.last
#         if form.is_valid() and is_last_step:
#             logger.info("[ویزارد-POST] فرم مرحله آخر ('%s') معتبر است. انتظار اجرای done()...", current_step)
#         elif form.is_valid():
#             logger.info("[ویزارد-POST] فرم مرحله ('%s') معتبر است. انتظار رفتن به مرحله بعد...", current_step)
#
#         try:
#             response = super().post(*args, **kwargs)
#             logger.info(f"[ویزارد-POST] اجرای متد post والد تکمیل شد. کد وضعیت پاسخ: {response.status_code}")
#             logger.debug(
#                 f"[ویزارد-POST] داده‌های ذخیره‌شده در storage برای مرحله {current_step}: {self.storage.get_step_data(current_step)}")
#             if response.status_code in (301, 302, 307, 308):
#                 logger.info(f"[ویزارد-POST] ریدایرکت شناسایی شد. URL مقصد: {response.url}")
#             elif response.status_code == 200:
#                 logger.debug("[ویزارد-POST] پاسخ ۲۰۰ OK دریافت شد (یا خطای فرم یا بازگشت از done با خطا).")
#             return response
#         except Exception as e:
#             logger.error(f"[ویزارد-POST] خطا در حین اجرای متد post والد: {e}", exc_info=True)
#             messages.error(self.request, _("خطای پیش‌بینی نشده در پردازش مراحل ویزارد."))
#             return self.render_goto_step(self.steps.first)
#
#     #
#     # def post(self, *args, **kwargs):
#     #     logger.info(f"[Wizard-POST] شروع اجرای متد post. مرحله فعلی از storage: {self.steps.current}")
#     #     logger.debug(f"[Wizard-POST] داده‌های POST: {self.request.POST}")
#     #     logger.debug(f"[Wizard-POST] فایل‌های FILES: {self.request.FILES}")
#     #
#     #     # --- اعتبارسنجی ManagementForm ---
#     #     from formtools.wizard.forms import ManagementForm
#     #     management_form = ManagementForm(self.request.POST, prefix=self.prefix)
#     #     if not management_form.is_valid():
#     #         logger.error("[Wizard-POST] management_form نامعتبر! خطاها: %s", management_form.errors.as_json())
#     #         messages.error(self.request, _("خطای داخلی: اطلاعات کنترل مراحل نامعتبر."))
#     #         # ... (Error handling) ...
#     #         try:
#     #              current_step_on_error = self.request.POST.get(self.management_form.add_prefix('current_step'), self.steps.first)
#     #              form_on_error = self.get_form(step=current_step_on_error, data=self.request.POST, files=self.request.FILES)
#     #              return self.render(form_on_error)
#     #         except Exception: return self.render_goto_step(self.steps.first)
#     #
#     #     current_step = management_form.cleaned_data["current_step"]
#     #     logger.info(f"[Wizard-POST] مرحله شناسایی شده: '{current_step}'")
#     #
#     #     # --- لاگ‌گیری قبل از فراخوانی super().post() ---
#     #     is_last_step = current_step == self.steps.last
#     #     # دریافت فرم فقط برای بررسی اعتبار (لاگ‌گیری)
#     #     form_for_check = self.get_form(step=current_step, data=self.request.POST, files=self.request.FILES)
#     #     is_form_valid_check = form_for_check.is_valid()
#     #     if is_form_valid_check and is_last_step: logger.info("[Wizard-POST] فرم مرحله آخر ('%s') معتبر است. انتظار اجرای done() توسط والد...", current_step)
#     #     elif is_form_valid_check: logger.info("[Wizard-POST] فرم مرحله ('%s') معتبر است. انتظار رفتن به مرحله بعد توسط والد...", current_step)
#     #     else: logger.warning(f"[Wizard-POST] فرم مرحله '{current_step}' نامعتبر (بررسی اولیه). خطاها: {form_for_check.errors.as_json(escape_html=True)}")
#     #
#     #     logger.debug(f"[Wizard-POST] Storage *قبل* از super().post() برای '{current_step}': {self.storage.data.get('step_data',{}).keys()}") # Log only keys
#     #
#     #     # --- فراخوانی متد post اصلی WizardView ---
#     #     try:
#     #         response = super().post(*args, **kwargs)
#     #         logger.info(f"[Wizard-POST] اجرای متد post والد تکمیل شد. کد وضعیت: {response.status_code}")
#     #         # logger.debug(f"[Wizard-POST] Storage *بعد* از super().post(): {self.storage.data}") # Can be verbose
#     #         if response.status_code in (301, 302, 307, 308): logger.info(f"[Wizard-POST] ریدایرکت شناسایی شد. URL: {response.url}")
#     #         elif response.status_code == 200: logger.debug("[Wizard-POST] پاسخ ۲۰۰ OK.")
#     #         return response
#     #     except Exception as e:
#     #         logger.error(f"[Wizard-POST] خطا در اجرای متد post والد: {e}", exc_info=True)
#     #         messages.error(self.request, _("خطای پیش‌بینی نشده در پردازش مراحل."))
#     #         return self.render_goto_step(self.steps.first)
#
#     # --- متد get_context_data ---
#
#     def get_context_data(self, form, **kwargs):
#         context = super().get_context_data(form=form, **kwargs)
#         current_step_name = self.steps.current
#         logger.info(f"[Wizard-Context] شروع get_context_data برای مرحله: {current_step_name}")
#
#         context['wizard_title'] = _('ایجاد فاکتور جدید ({})').format(
#             self.STEP_TITLES.get(current_step_name, current_step_name))
#         context['step_name'] = current_step_name
#         context['step_number'] = self.steps.step1
#         context['total_steps'] = len(self.form_list)
#         context['step_titles_dict'] = self.STEP_TITLES
#
#         tankhah = self._get_selected_tankhah()
#         project = tankhah.project if tankhah else None
#         if tankhah and not project:
#             project = tankhah.subproject.project if tankhah.subproject else None
#         context['selected_tankhah_for_display'] = tankhah
#         logger.info(f"[Wizard-Context] {current_step_name}: تنخواه={tankhah}, پروژه={project}")
#
#         if current_step_name == 'confirmation':
#             logger.info("[Wizard-Context] آماده‌سازی کانتکست تایید نهایی.")
#             all_data = self.get_all_cleaned_data()
#             logger.debug(f"[Wizard-Context-Confirm] تمام داده‌های تمیز شده: {all_data}")
#
#             step1_data = all_data
#             step2_data = all_data
#             step3_data = all_data.get('formset-factor_items', [])  # کلید صحیح برای فرم‌ست
#             step4_files_data = self.storage.get_step_files('factor_docs') or {}
#             step5_files_data = self.storage.get_step_files('tankhah_docs') or {}
#
#             context['confirmation_tankhah'] = tankhah
#             context['confirmation_details'] = {
#                 'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#                 'description': step2_data.get('description', _('ندارد')),
#                 'declared_amount': self._get_decimal_from_data(step2_data, 'amount')
#             }
#
#             # context['confirmation_details'] = {
#             #     'date': step2_data.get(self.DATE_FIELD_NAME_STEP2),
#             #     'description': step2_data.get(self.DESC_FIELD_NAME_STEP2),
#             #     'declared_amount': self._get_decimal_from_data(step2_data, self.AMOUNT_FIELD_NAME_STEP2)
#             # }
#             # حذف شرط نادرست
#             # if not context['confirmation_details']['date']:
#             #     logger.error("[Wizard-Context-Confirm] تاریخ یافت نشد!")
#
#             context['confirmation_summary_total'] = self._calculate_summary_total(step3_data)
#             context['confirmation_items'] = []
#             logger.info(f"[Wizard-Context-Confirm] شروع آماده‌سازی آیتم‌ها برای نمایش. تعداد خام: {len(step3_data)}")
#             for item_data in step3_data:
#                 if isinstance(item_data, dict) and not item_data.get('DELETE', False):
#                     desc = item_data.get(self.ITEM_DESC_FIELD)
#                     qty = self._get_decimal_from_data(item_data, self.ITEM_QTY_FIELD, '1')
#                     price = self._get_decimal_from_data(item_data, self.ITEM_UNIT_PRICE_FIELD)
#                     if desc and qty > 0 and price > 0:
#                         context['confirmation_items'].append({
#                             'description': desc,
#                             'quantity': qty,
#                             'unit_price': price,
#                             'total': (qty * price).quantize(Decimal('0.01'))
#                         })
#
#             logger.info(
#                 f"[Wizard-Context-Confirm] تعداد آیتم‌های معتبر برای نمایش: {len(context['confirmation_items'])}")
#             logger.info(f"[Wizard-Context-Confirm] مجموع کل نهایی برای نمایش: {context['confirmation_summary_total']}")
#
#             key4 = f'factor_docs-{self.FACTOR_DOCS_FIELD_NAME_STEP4}'
#             context['confirmation_factor_docs'] = [f for f in step4_files_data.get(key4, []) if
#                                                    f and hasattr(f, 'name')]
#             key5 = f'tankhah_docs-{self.TANKHAH_DOCS_FIELD_NAME_STEP5}'
#             context['confirmation_tankhah_docs'] = [f for f in step5_files_data.get(key5, []) if
#                                                     f and hasattr(f, 'name')]
#             logger.debug(
#                 f"[Wizard-Context-Confirm] فایل‌های فاکتور: {len(context['confirmation_factor_docs'])}, فایل‌های تنخواه: {len(context['confirmation_tankhah_docs'])}")
#
#             context['final_available_tankhah_budget'] = Decimal('0.00')
#             context['final_remaining_tankhah_budget'] = Decimal('0.00')
#             context['final_available_project_budget'] = Decimal('0.00')
#             context['final_remaining_project_budget'] = Decimal('0.00')
#             if tankhah:
#                 try:
#                     context['final_available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(
#                         Decimal('0.01'))
#                 except Exception:
#                     pass
#             if project:
#                 try:
#                     context['final_available_project_budget'] = get_actual_project_remaining_budget(project).quantize(
#                         Decimal('0.01'))
#                 except Exception:
#                     pass
#             summary_total = context['confirmation_summary_total']
#             context['final_remaining_tankhah_budget'] = context['final_available_tankhah_budget'] - summary_total
#             context['final_remaining_project_budget'] = context['final_available_project_budget'] - summary_total
#             logger.info(
#                 f"[Wizard-Context-Confirm] بودجه نهایی: تنخواه={context['final_remaining_tankhah_budget']}, پروژه={context['final_remaining_project_budget']}")
#
#         logger.info(f"[Wizard-Context] پایان get_context_data برای مرحله: {current_step_name}")
#         return context
#
#
#     def get_context_data(self, form, **kwargs):
#         context = super().get_context_data(form=form, **kwargs)
#         current_step_name = self.steps.current
#         logger.info(f"[Wizard-Context] شروع get_context_data برای مرحله: {current_step_name}")
#
#         context['wizard_title'] = _('ایجاد فاکتور جدید ({})').format(self.STEP_TITLES.get(current_step_name, current_step_name))
#         context['step_name'] = current_step_name
#         context['step_number'] = self.steps.step1
#         context['total_steps'] = len(self.form_list)
#         context['step_titles_dict'] = self.STEP_TITLES
#
#         tankhah = self._get_selected_tankhah()
#         project = tankhah.project if tankhah else None
#         if tankhah and not project: project = tankhah.subproject.project if tankhah.subproject else None
#         context['selected_tankhah_for_display'] = tankhah
#         logger.info(f"[Wizard-Context] {current_step_name}: تنخواه={tankhah}, پروژه={project}")
#
#         if current_step_name == 'factor_items':
#             logger.debug(f"[Wizard-Context] {current_step_name}: تنظیم formset.")
#             context['formset'] = form # The form IS the formset instance here
#             cleaned_data_step2 = self.get_cleaned_data_for_step('factor_details') or {}
#             context['initial_factor_amount'] = self._get_decimal_from_data(cleaned_data_step2, self.AMOUNT_FIELD_NAME_STEP2) # Use declared amount
#             logger.debug(f"[Wizard-Context] {current_step_name}: مبلغ اولیه (از مرحله ۲): {context['initial_factor_amount']}")
#             # Budget Calculation...
#             context['available_tankhah_budget'] = Decimal('0.00'); context['available_project_budget'] = Decimal('0.00')
#             context['budget_warning_threshold'] = Decimal('10.0'); context['budget_locked_percentage'] = Decimal('0.0'); context['budget_warning_action'] = 'NOTIFY' # Defaults
#             if tankhah:
#                 try: context['available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(Decimal('0.01'))
#                 except Exception: pass
#             if project:
#                  try:
#                       context['available_project_budget'] = get_actual_project_remaining_budget(project).quantize(Decimal('0.01'))
#                       # Get thresholds...
#                  except Exception: pass
#             logger.info(f"[Wizard-Context] {current_step_name}: بودجه تنخواه: {context['available_tankhah_budget']}, بودجه پروژه: {context['available_project_budget']}")
#
#
#         elif current_step_name == 'confirmation':
#             logger.info("[Wizard-Context] آماده‌سازی کانتکست تایید نهایی.")
#             all_data = self.get_all_cleaned_data()
#             logger.debug(f"[Wizard-Context-Confirm] تمام داده‌های تمیز شده: {all_data}") # Log all data once
#
#             step1_data = all_data.get('select_tankhah', {})
#             step2_data = all_data.get('factor_details', {})
#             step3_data = all_data.get('factor_items', [])
#             step4_files_data = self.storage.get_step_files('factor_docs') or {}
#             step5_files_data = self.storage.get_step_files('tankhah_docs') or {}
#
#             context['confirmation_tankhah'] = tankhah # Use already fetched tankhah object
#             context['confirmation_details'] = {
#                 'date': step2_data.get(self.DATE_FIELD_NAME_STEP2), # Should be date/datetime obj
#                 'description': step2_data.get(self.DESC_FIELD_NAME_STEP2),
#                 'declared_amount': self._get_decimal_from_data(step2_data, self.AMOUNT_FIELD_NAME_STEP2)
#             }
#             if not context['confirmation_details']['date']: logger.error("[Wizard-Context-Confirm] تاریخ یافت نشد!")
#
#             # Recalculate total and prepare items for display
#             context['confirmation_summary_total'] = self._calculate_summary_total(step3_data)
#             context['confirmation_items'] = []
#             logger.info(f"[Wizard-Context-Confirm] شروع آماده‌سازی آیتم‌ها برای نمایش. تعداد خام: {len(step3_data)}")
#             for item_data in step3_data:
#                  if isinstance(item_data, dict) and not item_data.get('DELETE', False):
#                       desc = item_data.get(self.ITEM_DESC_FIELD)
#                       qty = self._get_decimal_from_data(item_data, self.ITEM_QTY_FIELD, '1')
#                       price = self._get_decimal_from_data(item_data, self.ITEM_UNIT_PRICE_FIELD)
#                       if desc and qty > 0 and price > 0: # Only add valid items
#                            context['confirmation_items'].append({
#                                 'description': desc,
#                                 'quantity': qty,
#                                 'unit_price': price,
#                                 'total': (qty * price).quantize(Decimal('0.01'))
#                            })
#                       # else: logger.warning(f"آیتم نامعتبر در confirmation نادیده گرفته شد: {item_data}")
#
#             logger.info(f"[Wizard-Context-Confirm] تعداد آیتم‌های معتبر برای نمایش: {len(context['confirmation_items'])}")
#             logger.info(f"[Wizard-Context-Confirm] مجموع کل نهایی برای نمایش: {context['confirmation_summary_total']}")
#
#
#             # Files
#             key4 = f'factor_docs-{self.FACTOR_DOCS_FIELD_NAME_STEP4}'; context['confirmation_factor_docs'] = [f for f in step4_files_data.get(key4, []) if f and hasattr(f, 'name')]
#             key5 = f'tankhah_docs-{self.TANKHAH_DOCS_FIELD_NAME_STEP5}'; context['confirmation_tankhah_docs'] = [f for f in step5_files_data.get(key5, []) if f and hasattr(f, 'name')]
#             logger.debug(f"[Wizard-Context-Confirm] فایل‌های فاکتور: {len(context['confirmation_factor_docs'])}, فایل‌های تنخواه: {len(context['confirmation_tankhah_docs'])}")
#
#
#             # Final Budget
#             context['final_available_tankhah_budget'] = Decimal('0.00'); context['final_remaining_tankhah_budget'] = Decimal('0.00')
#             context['final_available_project_budget'] = Decimal('0.00'); context['final_remaining_project_budget'] = Decimal('0.00')
#             if tankhah:
#                 try: context['final_available_tankhah_budget'] = get_tankhah_remaining_budget(tankhah).quantize(Decimal('0.01'))
#                 except Exception: pass
#             if project:
#                 try: context['final_available_project_budget'] = get_actual_project_remaining_budget(project).quantize(Decimal('0.01'))
#                 except Exception: pass
#             summary_total = context['confirmation_summary_total']
#             context['final_remaining_tankhah_budget'] = context['final_available_tankhah_budget'] - summary_total
#             context['final_remaining_project_budget'] = context['final_available_project_budget'] - summary_total
#             logger.info(f"[Wizard-Context-Confirm] بودجه نهایی: تنخواه={context['final_remaining_tankhah_budget']}, پروژه={context['final_remaining_project_budget']}")
#
#         logger.info(f"[Wizard-Context] پایان get_context_data برای مرحله: {current_step_name}")
#         return context
#
#     # --- متد done() ---
#     def done(self, form_list, form_dict, **kwargs):
#         logger.info("[Wizard-DONE] **** شروع اجرای متد done() ****")
#
#         # --- بازیابی فرم‌های معتبر از form_dict ---
#         try:
#             # logger.debug("[Wizard-DONE] شروع بازیابی فرم‌ها از form_dict...")
#             # select_tankhah_form = form_dict.get('select_tankhah'); assert select_tankhah_form and select_tankhah_form.is_valid()
#             # factor_details_form = form_dict.get('factor_details'); assert factor_details_form and factor_details_form.is_valid()
#             # factor_items_formset = form_dict.get('factor_items'); assert factor_items_formset and factor_items_formset.is_valid()
#             # factor_docs_form = form_dict.get('factor_docs'); assert factor_docs_form and factor_docs_form.is_valid() # Files form should be valid
#             # tankhah_docs_form = form_dict.get('tankhah_docs'); assert tankhah_docs_form and tankhah_docs_form.is_valid()
#             logger.debug("[Wizard-DONE] شروع بازیابی فرم‌ها...")
#             select_tankhah_form = form_dict.get('select_tankhah');
#             assert select_tankhah_form and select_tankhah_form.is_valid()
#             factor_details_form = form_dict.get('factor_details');
#             assert factor_details_form and factor_details_form.is_valid()
#             factor_items_formset = form_dict.get('factor_items');
#             assert factor_items_formset and factor_items_formset.is_valid()
#             factor_docs_form = form_dict.get('factor_docs');
#             assert factor_docs_form and factor_docs_form.is_valid()
#             tankhah_docs_form = form_dict.get('tankhah_docs');
#             assert tankhah_docs_form and tankhah_docs_form.is_valid()
#             logger.debug("[Wizard-DONE] فرم‌های لازم بازیابی و معتبر هستند.")
#             logger.debug("[Wizard-DONE] تمام فرم‌های لازم از form_dict بازیابی و معتبر هستند.")
#
#         except AssertionError as e:
#             logger.error(f"[Wizard-DONE] خطا: یکی از فرم‌ها در form_dict یافت نشد یا نامعتبر بود: {e}", exc_info=True)
#             messages.error(self.request, _("خطای داخلی: عدم امکان پردازش اطلاعات فرم‌ها."))
#             # بازگشت به تایید نهایی برای نمایش خطا
#             return self.render_rerender_confirmation(form_dict)
#         except Exception as e:
#             logger.error(f"[Wizard-DONE] خطای ناشناخته در بازیابی فرم‌ها: {e}", exc_info=True)
#             messages.error(self.request, _("خطای داخلی."))
#             return self.render_rerender_confirmation(form_dict)
#
#
#         # --- استخراج داده‌های کلیدی از فرم‌های معتبر ---
#         try:
#             logger.info("[Wizard-DONE] شروع استخراج داده کلیدی...")
#             tankhah = select_tankhah_form.cleaned_data.get(self.TANKHAH_FIELD_NAME_STEP1);
#             assert tankhah
#             factor_date = factor_details_form.cleaned_data.get(self.DATE_FIELD_NAME_STEP2);
#             assert factor_date
#             factor_date_final = factor_date.date() if isinstance(factor_date, datetime.datetime) else factor_date
#             description = factor_details_form.cleaned_data.get(self.DESC_FIELD_NAME_STEP2)
#
#             # --- محاسبه مبلغ کل از فرم‌ست معتبر ---
#             total_amount = Decimal('0.00')
#             items_to_create_data = [] # لیست برای داده‌های تمیز شده آیتم‌های معتبر
#             logger.debug(f"[Wizard-DONE] پردازش {len(factor_items_formset.forms)} فرم در فرم‌ست آیتم‌ها...")
#             for item_form in factor_items_formset:
#                 # فقط فرم‌های معتبر و حذف نشده را پردازش کن
#                 if item_form.is_valid() and not item_form.cleaned_data.get('DELETE'):
#                     item_cleaned_data = item_form.cleaned_data
#                     logger.debug(f"[Wizard-DONE] داده تمیز شده آیتم {item_form.prefix}: {item_cleaned_data}")
#                     desc = item_cleaned_data.get(self.ITEM_DESC_FIELD)
#                     # --- خواندن از cleaned_data برای محاسبه ---
#                     quantity = item_cleaned_data.get(self.ITEM_QTY_FIELD, Decimal('1.00'))
#                     unit_price = item_cleaned_data.get(self.ITEM_UNIT_PRICE_FIELD, Decimal('0.00'))
#                     if quantity <= 0: quantity = Decimal('1.00')
#                     if desc and unit_price > 0:
#                         item_total = (quantity * unit_price).quantize(Decimal('0.01'))
#                         total_amount += item_total
#                         item_cleaned_data['calculated_amount'] = item_total  # ذخیره مبلغ محاسبه شده
#                         items_to_create_data.append(item_cleaned_data)  # اضافه کردن داده تمیز شده به لیست
#
#                     # اطمینان از وجود داده‌های اصلی آیتم
#                     if item_cleaned_data.get(self.ITEM_DESC_FIELD):
#                         quantity = item_cleaned_data.get(self.ITEM_QTY_FIELD, Decimal('1.00'))
#                         unit_price = item_cleaned_data.get(self.ITEM_UNIT_PRICE_FIELD, Decimal('0.00'))
#                         # فقط آیتم‌های با قیمت و تعداد معتبر را حساب کن
#                         if quantity > 0 and unit_price > 0:
#                             item_total = (quantity * unit_price).quantize(Decimal('0.01'))
#                             total_amount += item_total
#                             # اضافه کردن مبلغ محاسبه شده به داده‌های آیتم
#                             item_cleaned_data['calculated_amount'] = item_total
#                             items_to_create_data.append(item_cleaned_data)
#                         else:
#                              logger.warning(f"[Wizard-DONE] آیتم {item_form.prefix} به دلیل تعداد یا قیمت واحد نامعتبر، در مجموع کل محاسبه نشد.")
#                     else:
#                          logger.warning(f"[Wizard-DONE] آیتم {item_form.prefix} فاقد شرح بود و نادیده گرفته شد.")
#             total_amount = total_amount.quantize(Decimal('0.01'))
#             logger.info(f"[Wizard-DONE] مبلغ کل نهایی محاسبه شده: {total_amount}")
#             logger.info(f"[Wizard-DONE] تعداد آیتم‌های معتبر برای ذخیره: {len(items_to_create_data)}")
#
#
#             # استخراج فایل‌ها
#             files_step4 = factor_docs_form.cleaned_data.get(self.FACTOR_DOCS_FIELD_NAME_STEP4, [])
#             files_step5 = tankhah_docs_form.cleaned_data.get(self.TANKHAH_DOCS_FIELD_NAME_STEP5, [])
#             logger.debug(f"[Wizard-DONE] فایل‌های اسناد فاکتور: {len(files_step4)}, فایل‌های اسناد تنخواه: {len(files_step5)}")
#
#         except (AssertionError, ValueError, KeyError, TypeError, Exception) as e:
#              logger.error(f"[Wizard-DONE] خطا در استخراج داده معتبر: {e}", exc_info=True)
#              messages.error(self.request, _("خطای داخلی هنگام پردازش داده‌های فرم."))
#              return self.render_rerender_confirmation(form_dict)
#
#         # --- عملیات دیتابیس ---
#         try:
#             with transaction.atomic():
#                 logger.info(f"[Wizard-DONE] شروع تراکنش دیتابیس...")
#                 # 1. ایجاد Factor
#                 factor = Factor(tankhah=tankhah, date=factor_date_final, amount=total_amount, description=description, created_by=self.request.user, status='PENDING')
#                 factor.save(); logger.info(f"[Wizard-DONE] فاکتور ذخیره شد: ID={factor.id}, شماره={factor.number}")
#
#                 # 2. ایجاد FactorItems (از items_to_create_data)
#                 if items_to_create_data:
#                     factor_items_to_create = [
#                         FactorItem(
#                             factor=factor,
#                             description=item_data.get(self.ITEM_DESC_FIELD, ''),
#                             quantity=item_data.get(self.ITEM_QTY_FIELD, Decimal('1.00')),
#                             unit_price=item_data.get(self.ITEM_UNIT_PRICE_FIELD, Decimal('0.00')),
#                             amount=item_data.get('calculated_amount', Decimal('0.00')), # استفاده از مبلغ محاسبه شده
#                             status='PENDING',
#                             # ... (خواندن و تنظیم سایر فیلدهای اختیاری FactorItem) ...
#                             category=item_data.get(self.ITEM_CATEGORY_FIELD),
#                             transaction_type=item_data.get(self.ITEM_TRANS_TYPE_FIELD) or TransactionType.objects.get(id=1),  # پیش‌فرض
#                             min_stage_order=item_data.get(self.ITEM_MIN_STAGE_FIELD, 1),
#                             # transaction_type=item_data.get(self.ITEM_TRANS_TYPE_FIELD),
#                             # min_stage_order=item_data.get(self.ITEM_MIN_STAGE_FIELD, 1)
#                         ) for item_data in items_to_create_data # فقط آیتم‌های معتبر
#                     ]
#                     if factor_items_to_create:
#                         logger.debug(f"[Wizard-DONE] آماده bulk_create برای آیتم‌ها: {factor_items_to_create}")
#                         FactorItem.objects.bulk_create(factor_items_to_create);
#                         logger.info(f"[Wizard-DONE] {len(factor_items_to_create)} ردیف فاکتور ذخیره شد.")
#                 else: logger.warning("[Wizard-DONE] هیچ آیتم معتبری برای ذخیره نبود.")
#
#                 # 3. & 4. ذخیره اسناد (بدون تغییر)
#                 if files_step4: docs4 = [FactorDocument(factor=factor,document=f,uploaded_by=self.request.user) for f in files_step4 if f];
#                 if docs4: FactorDocument.objects.bulk_create(docs4); logger.info(f"[Wizard-DONE] {len(docs4)} سند فاکتور ذخیره شد.")
#                 if files_step5: docs5 = [TankhahDocument(tankhah=tankhah,document=f,uploaded_by=self.request.user) for f in files_step5 if f];
#                 if docs5: TankhahDocument.objects.bulk_create(docs5); logger.info(f"[Wizard-DONE] {len(docs5)} سند تنخواه ذخیره شد.")
#
#             # --- Transaction Success ---
#             logger.info(f"[Wizard-DONE] تراکنش موفق. فاکتور {factor.number} ایجاد شد.")
#             messages.success(self.request, _("فاکتور با کد رهگیری {} ایجاد شد.").format(factor.number)); self.storage.reset(); logger.info("[Wizard] storage پاک شد.")
#             return redirect('tankhah_factor_list') # <--- ADJUST URL NAME
#
#         # --- مدیریت خطاهای دیتابیس ---
#         # ... (except blocks remain the same) ...
#         except IntegrityError as e:
#              # بررسی خاص برای خطای unit_price
#              if 'unit_price' in str(e) and 'cannot be null' in str(e).lower():
#                   logger.error(f"[Wizard-DONE] خطای IntegrityError: unit_price نمی‌تواند null باشد!", exc_info=True)
#                   messages.error(self.request, _("خطای ذخیره‌سازی: قیمت واحد برای ردیف‌ها الزامی است."))
#              else:
#                   logger.error(f"[Wizard-DONE] خطای IntegrityError: {e}", exc_info=True); messages.error(self.request, _("خطا: شماره فاکتور تکراری یا داده نامعتبر."))
#         except ValueError as e:
#              if 'fromgregorian' in str(e): logger.error(f"[Wizard-DONE] خطای jdatetime در مدل: {e}", exc_info=True); messages.error(self.request, _("خطای داخلی: پردازش تاریخ مدل."))
#              else: logger.error(f"[Wizard-DONE] خطای ValueError: {e}", exc_info=True); messages.error(self.request, _("خطا در داده‌ها."))
#         except Exception as e: logger.error(f"[Wizard-DONE] خطای ناشناخته دیتابیس: {e}", exc_info=True); messages.error(self.request, _("خطای ناشناخته ذخیره‌سازی."))
#
#
#         # --- بازگشت به تایید نهایی در صورت خطا ---
#         return self.render_rerender_confirmation(form_dict)