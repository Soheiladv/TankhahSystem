import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
import logging
import os
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import DecimalField
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, View, UpdateView

from budgets.budget_calculations import get_project_total_budget, get_tankhah_remaining_budget, \
    get_actual_project_remaining_budget
from tankhah.Factor.forms_Factor import WizardTankhahSelectionForm, WizardFactorDetailsForm, WizardFactorItemFormSet, \
    WizardFactorDocumentForm, WizardTankhahDocumentForm, WizardConfirmationForm
from tankhah.forms import FactorForm, get_factor_item_formset
from tankhah.models import Factor, TankhahDocument, FactorDocument, FactorItem
from tankhah.models import Tankhah
from tankhah.forms import FactorDocumentForm, TankhahDocumentForm


from django.conf import settings
from django.core.files.storage import FileSystemStorage
from formtools.wizard.views import SessionWizardView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect # Import get_object_or_404
from django.contrib import messages
from django.db import transaction, models, IntegrityError
from django.db.models import Q, Sum, F, Value, DecimalField, Max
from django.db.models.functions import Coalesce
from decimal import Decimal, InvalidOperation
import logging
from django.utils import timezone # Import timezone

from budgets.models import BudgetTransaction, ProjectBudgetAllocation, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from core.models import WorkflowStage


logger = logging.getLogger('tankhah') # Use your app's logger name
#----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Assuming PermissionBaseView and utils exist
# from core.PermissionBase import PermissionBaseView
# from core.utils import restrict_to_user_organization
# from tankhah.fun_can_edit_approval import can_edit_factor # Example permission check function

# ================== Placeholders ==================

def can_edit_factor(user, factor): # Placeholder permission check
     # Implement your logic here, e.g., check status, stage, user role/level
     logger.debug(f"[PermCheck-Placeholder] Checking edit permission for user {user} on factor {factor.pk}")
     # Example: Allow edit only in DRAFT or PENDING by creator
     # if factor.status in ['DRAFT', 'PENDING'] and factor.created_by == user:
     #    return True
     # Allow staff always?
     if user.is_staff: return True
     return False # Default deny
# ================================================

logger = logging.getLogger('factor_update') # Specific logger for update view


class FactorWizardUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm # Main form for Factor details
    template_name = 'tankhah/Factors/wizard/factor_update_form.html' # Specific template for update
    # permission_codenames = ['tankhah.factor_update'] # Or use permission_required
    permission_required = 'tankhah.factor_update'
    permission_denied_message = _('شما دسترسی لازم برای ویرایش این فاکتور را ندارید.')
    context_object_name = 'factor'

    def get_success_url(self):
        # Redirect to factor detail or list after successful update
        # return reverse_lazy('factor_detail', kwargs={'pk': self.object.pk})
        return reverse_lazy('tankhah_factor_list') # Redirect to list for simplicity

    def dispatch(self, request, *args, **kwargs):
        """Check edit permissions before proceeding."""
        # Get object first to check permission against the specific factor
        self.object = self.get_object()
        if not can_edit_factor(request.user, self.object):
             logger.warning(f"[FactorUpdate] کاربر {request.user} دسترسی ویرایش فاکتور {self.object.pk} را ندارد.")
             messages.error(request, self.permission_denied_message)
             # Redirect to detail view or list view if no permission
             # return redirect(reverse('factor_detail', kwargs={'pk': self.object.pk}))
             return redirect(self.get_success_url()) # Redirect to list view

        # Also check object-level permissions if PermissionBaseView supports it
        # has_perm = super().has_permission() # Call standard permission check
        # if not has_perm:
        #     return self.handle_no_permission()

        logger.debug(f"[FactorUpdate] دسترسی ویرایش برای کاربر {request.user} روی فاکتور {self.object.pk} تایید شد.")
        return super().dispatch(request, *args, **kwargs)


    def get_form_kwargs(self):
        """Pass user and tankhah to the main FactorForm."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        # Pass the existing tankhah instance to the form
        kwargs['tankhah'] = self.object.tankhah
        logger.debug(f"[FactorUpdate] Kwargs برای FactorForm: user={kwargs['user']}, tankhah={kwargs['tankhah']}")
        return kwargs

    def get_context_data(self, **kwargs):
        """Add formsets and document forms to the context."""
        context = super().get_context_data(**kwargs)
        logger.info(f"[FactorUpdate] شروع get_context_data برای ویرایش فاکتور {self.object.pk}")
        context['title'] = _('ویرایش فاکتور') + f' #{self.object.number}'

        # Get the inline formset factory
        FactorItemFormSet = get_factor_item_formset()

        if self.request.POST:
            # If form submitted, bind formsets/forms to POST data and files
            logger.debug("[FactorUpdate] درخواست POST دریافت شد، اتصال فرم‌ست‌ها و فرم‌های فایل...")
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES, prefix='tankhah_docs')
        else:
            # If GET request, initialize unbound forms
            logger.debug("[FactorUpdate] درخواست GET دریافت شد، ایجاد فرم‌ست‌ها و فرم‌های فایل خالی...")
            context['item_formset'] = FactorItemFormSet(instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(prefix='tankhah_docs')

        # Add existing documents for display/deletion
        context['existing_factor_documents'] = self.object.documents.all()
        context['existing_tankhah_documents'] = self.object.tankhah.documents.all()

        logger.debug(f"[FactorUpdate] تعداد فرم‌های آیتم: {len(context['item_formset'].forms)}")
        logger.debug(f"[FactorUpdate] تعداد اسناد فاکتور موجود: {context['existing_factor_documents'].count()}")
        logger.debug(f"[FactorUpdate] تعداد اسناد تنخواه موجود: {context['existing_tankhah_documents'].count()}")
        logger.info(f"[FactorUpdate] پایان get_context_data")
        return context

    def form_valid(self, form):
        """Process the main form and all related formsets/forms."""
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_form = context['document_form'] # Factor docs
        tankhah_document_form = context['tankhah_document_form'] # Tankhah docs
        factor = self.object # The factor being edited

        logger.info(f"[FactorUpdate] شروع form_valid برای فاکتور {factor.pk}")
        logger.debug(f"[FactorUpdate] اعتبار فرم اصلی (FactorForm): {form.is_valid()}")
        logger.debug(f"[FactorUpdate] اعتبار فرم‌ست آیتم‌ها: {item_formset.is_valid()}")
        logger.debug(f"[FactorUpdate] اعتبار فرم اسناد فاکتور: {document_form.is_valid()}")
        logger.debug(f"[FactorUpdate] اعتبار فرم اسناد تنخواه: {tankhah_document_form.is_valid()}")

        # Validate all forms together
        if form.is_valid() and item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            logger.info("[FactorUpdate] تمام فرم‌ها معتبر هستند. شروع تراکنش...")
            try:
                with transaction.atomic():
                    # 1. Save the main Factor instance (UpdateView does this implicitly via super().form_valid)
                    # We call it explicitly here before saving formsets to ensure factor PK exists
                    # UpdateView's default form_valid saves the main form.
                    # self.object = form.save() # No need to call form.save() directly if using UpdateView default

                    logger.debug(f"[FactorUpdate] ذخیره فرم اصلی فاکتور...")
                    response = super().form_valid(form) # Let UpdateView save the main form
                    factor = self.object # Get the saved object
                    logger.info(f"[FactorUpdate] فرم اصلی فاکتور ذخیره شد (ID: {factor.pk}).")


                    # 2. Save the FactorItem formset
                    logger.debug(f"[FactorUpdate] ذخیره فرم‌ست آیتم‌ها...")
                    item_formset.instance = factor # Ensure instance is set
                    item_formset.save() # Handles additions, updates, and deletions
                    logger.info(f"[FactorUpdate] فرم‌ست آیتم‌ها ذخیره شد.")


                    # 3. Handle FactorDocument uploads/deletions
                    logger.debug(f"[FactorUpdate] پردازش اسناد فاکتور...")
                    # Handle deletions (assuming a checkbox like 'delete_doc_ID' is submitted)
                    for doc in factor.documents.all():
                        if f'delete_factor_doc_{doc.pk}' in self.request.POST:
                             logger.info(f"[FactorUpdate] حذف سند فاکتور: {doc.pk} - {doc.document.name}")
                             # Optionally delete the file from storage too
                             # doc.document.delete(save=False) # Delete file without saving model yet
                             doc.delete()


                    # Handle new uploads
                    new_factor_files = document_form.cleaned_data.get('files', [])
                    if new_factor_files:
                         factor_docs_to_create = [
                              FactorDocument(factor=factor, document=f, uploaded_by=self.request.user)
                              for f in new_factor_files if f
                         ]
                         if factor_docs_to_create:
                              FactorDocument.objects.bulk_create(factor_docs_to_create)
                              logger.info(f"[FactorUpdate] تعداد {len(factor_docs_to_create)} سند جدید فاکتور ذخیره شد.")


                    # 4. Handle TankhahDocument uploads/deletions
                    logger.debug(f"[FactorUpdate] پردازش اسناد تنخواه...")
                    tankhah = factor.tankhah # Get the related tankhah
                    # Handle deletions
                    for doc in tankhah.documents.all():
                         if f'delete_tankhah_doc_{doc.pk}' in self.request.POST:
                              logger.info(f"[FactorUpdate] حذف سند تنخواه: {doc.pk} - {doc.document.name}")
                              # doc.document.delete(save=False)
                              doc.delete()

                    # Handle new uploads
                    new_tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
                    if new_tankhah_files:
                         tankhah_docs_to_create = [
                              TankhahDocument(tankhah=tankhah, document=f, uploaded_by=self.request.user)
                              for f in new_tankhah_files if f
                         ]
                         if tankhah_docs_to_create:
                              TankhahDocument.objects.bulk_create(tankhah_docs_to_create)
                              logger.info(f"[FactorUpdate] تعداد {len(tankhah_docs_to_create)} سند جدید تنخواه ذخیره شد.")


                    # 5. Recalculate factor amount based on saved items (Important!)
                    factor.refresh_from_db() # Get latest data after item save
                    new_total_amount = factor.items.aggregate(
                         total=Coalesce(Sum(F('amount') * F('quantity')), Decimal('0.00'), output_field=DecimalField())
                    )['total']

                    if factor.amount != new_total_amount:
                         logger.info(f"[FactorUpdate] بروزرسانی مبلغ کل فاکتور از {factor.amount} به {new_total_amount}")
                         factor.amount = new_total_amount
                         factor.save(update_fields=['amount']) # Save only the amount field


                # --- Transaction Success ---
                logger.info(f"[FactorUpdate] تراکنش با موفقیت کامل شد. فاکتور {factor.number} بروزرسانی شد.")
                messages.success(self.request, _("فاکتور با موفقیت ویرایش شد."))
                return response # Return the response from super().form_valid() which is the redirect

            except Exception as e:
                 # Log error and display message
                 logger.error(f"[FactorUpdate] خطا در حین تراکنش ذخیره‌سازی: {e}", exc_info=True)
                 messages.error(self.request, _("خطایی هنگام ذخیره تغییرات رخ داد. لطفاً دوباره تلاش کنید."))
                 # Return form_invalid to re-render the page with forms containing errors
                 return self.form_invalid(form)

        else:
            # If any form is invalid, re-render the page
            logger.warning("[FactorUpdate] یک یا چند فرم نامعتبر است.")
            logger.debug(f"FactorForm Errors: {form.errors.as_json(escape_html=True)}")
            logger.debug(f"ItemFormSet Errors: {item_formset.errors}")
            logger.debug(f"ItemFormSet Non-Form Errors: {item_formset.non_form_errors()}")
            logger.debug(f"FactorDocForm Errors: {document_form.errors.as_json(escape_html=True)}")
            logger.debug(f"TankhahDocForm Errors: {tankhah_document_form.errors.as_json(escape_html=True)}")
            messages.error(self.request, _("لطفاً خطاهای موجود در فرم را اصلاح کنید."))
            # UpdateView's default behavior when form is invalid handles re-rendering
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid forms by re-rendering the template with errors."""
        logger.warning("[FactorUpdate] form_invalid فراخوانی شد.")
        # The context already contains the invalid forms bound to POST data
        # UpdateView's default form_invalid calls render_to_response with get_context_data
        return super().form_invalid(form)