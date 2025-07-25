import logging
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect, render  # Import render
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.forms import inlineformset_factory
from django.db.models import Sum, Max

from accounts.AccessRule.check_user_access import check_user_factor_access
# Assuming these base classes, models, forms, and functions exist
from core.views import PermissionBaseView  # Your permission checking base view
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm, FactorDocumentForm, TankhahDocumentForm
from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem, FactorDocument, TankhahDocument, \
    create_budget_transaction, FactorHistory, ApprovalLog
from accounts.models import CustomUser  # Your user model
from core.models import WorkflowStage, Organization, AccessRule  # Your workflow stage model
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
    extra=1,  # Start with one extra form
    can_delete=True,
    # min_num=1,  # Enforce at least one item
    # validate_min=True # Validate the minimum number
)

###############################################################################################
###############################################################################################


class New_FactorCreateView__(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')

    def get_success_url(self):
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.select_related(
                    'project', 'organization', 'project_budget_allocation__budget_period'
                ).get(id=tankhah_id)
                if kwargs['tankhah'].due_date and kwargs['tankhah'].due_date < timezone.now():
                    messages.error(self.request, _('تنخواه منقضی شده است. لطفاً تنخواه جدیدی انتخاب کنید.'))
                    kwargs['tankhah'] = None
            except (Tankhah.DoesNotExist, ValueError):
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and self.object.pk:
            can_delete = False
            user = self.request.user
            factor = self.object
            tankhah = factor.tankhah

            # بررسی دسترسی حذف
            access_info = check_user_factor_access(user.username, tankhah=tankhah, action_type='DELETE', entity_type='FACTOR')
            can_delete = access_info['has_access'] and factor.status in ['DRAFT', 'PENDING', 'PENDING_APPROVAL'] and not factor.is_locked and not tankhah.is_locked and not tankhah.is_archived

            context['can_delete'] = can_delete

        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()

        form_kwargs = self.get_form_kwargs()
        if 'tankhah' in form_kwargs:
            context['tankhah'] = form_kwargs['tankhah']

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        if not item_formset.is_valid():
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

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

        total_items_amount = sum(
            (f.cleaned_data.get('unit_price', Decimal('0')) * f.cleaned_data.get('quantity', Decimal('0'))).quantize(
                Decimal('0.01'))
            for f in valid_item_forms
        )

        if abs(total_items_amount - form.cleaned_data['amount']) > Decimal('0.01'):
            msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
                form.cleaned_data['amount'], total_items_amount
            )
            form.add_error('amount', msg)
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                self.object.status = 'PENDING'
                self.object._request_user = self.request.user  # اضافه کردن کاربر برای سیگنال
                self.object.current_stage = AccessRule.objects.filter(
                    entity_type='FACTOR',
                    stage_order=1,
                    is_active=True
                ).first()  # تنظیم مرحله اولیه فاکتور
                self.object.save()
                logger.info(f"Factor saved: PK={self.object.pk}, Number={self.object.number}")

                item_formset.instance = self.object
                item_formset.save()

                if document_form.is_valid():
                    for file in document_form.cleaned_data.get('files', []):
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)

                if tankhah_document_form.is_valid():
                    for file in tankhah_document_form.cleaned_data.get('documents', []):
                        TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file,
                                                       uploaded_by=self.request.user)

                create_budget_transaction(
                    allocation=self.object.tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=self.object.amount,
                    related_obj=self.object,
                    created_by=self.request.user,
                    description=f"ایجاد فاکتور به شماره {self.object.number}",
                    transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
                )

                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=self.request.user,
                    description=f"فاکتور به شماره {self.object.number} توسط {self.request.user.username} ایجاد شد."
                )

        except Exception as e:
            logger.error(f"Error during atomic transaction for Factor creation: {e}", exc_info=True)
            messages.error(self.request,
                           _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد. لطفاً دوباره تلاش کنید.'))
            return self.form_invalid(form)

        messages.success(self.request, _('فاکتور با موفقیت ثبت و برای تایید ارسال شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return super().form_invalid(form)

class New_FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')

    def get_success_url(self):
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.select_related(
                    'project', 'organization', 'project_budget_allocation__budget_period'
                ).get(id=tankhah_id)
                if kwargs['tankhah'].due_date and kwargs['tankhah'].due_date < timezone.now():
                    messages.error(self.request, _('تنخواه منقضی شده است. لطفاً تنخواه جدیدی انتخاب کنید.'))
                    kwargs['tankhah'] = None
            except (Tankhah.DoesNotExist, ValueError):
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object and self.object.pk:
            access_info = check_user_factor_access(
                self.request.user.username,
                tankhah=self.object.tankhah,
                action_type='DELETE',
                entity_type='FACTOR'
            )
            context['can_delete'] = (
                access_info['has_access'] and
                self.object.status in ['DRAFT', 'PENDING', 'PENDING_APPROVAL'] and
                not self.object.is_locked and
                not self.object.tankhah.is_locked and
                not self.object.tankhah.is_archived
            )

        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()

        form_kwargs = self.get_form_kwargs()
        if 'tankhah' in form_kwargs and form_kwargs['tankhah']:
            context['tankhah'] = form_kwargs['tankhah']
            # اضافه کردن اطلاعات بودجه به context
            try:
                budget_allocation = form_kwargs['tankhah'].project_budget_allocation
                if budget_allocation:
                    context['budget_info'] = {
                        'tankhah_budget': get_tankhah_total_budget(form_kwargs['tankhah']),
                        'tankhah_remaining': get_tankhah_remaining_budget(form_kwargs['tankhah']),
                        'project_budget': budget_allocation.total_amount,
                        'project_remaining': budget_allocation.get_remaining_amount()
                    }
            except Exception as e:
                logger.error(f"Error fetching budget info for tankhah {form_kwargs['tankhah'].number}: {e}")
                messages.error(self.request, _('خطا در بارگذاری اطلاعات بودجه.'))

        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        if not item_formset.is_valid():
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

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

        total_items_amount = sum(
            (f.cleaned_data.get('unit_price', Decimal('0')) * f.cleaned_data.get('quantity', Decimal('0'))).quantize(
                Decimal('0.01'))
            for f in valid_item_forms
        )

        if abs(total_items_amount - form.cleaned_data['amount']) > Decimal('0.01'):
            msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
                form.cleaned_data['amount'], total_items_amount
            )
            form.add_error('amount', msg)
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                self.object._request_user = self.request.user
                # تنظیم مرحله اولیه
                current_stage = AccessRule.objects.filter(
                    entity_type='FACTOR',
                    stage_order=1,
                    is_active=True
                ).first()
                if not current_stage:
                    raise ValueError(_('هیچ قانون دسترسی فعالی برای مرحله اولیه فاکتور یافت نشد.'))

                # بررسی سطح کاربر
                user_level =  AccessRule.min_level  # فرض می‌کنیم فیلد level در مدل User وجود دارد
                logger.info(f'userlevel: {user_level} , current_stage: {current_stage}')
                if user_level > current_stage.min_level:
                    raise ValueError(
                        _('سطح شما ({}) برای ثبت فاکتور در این مرحله ({}) کافی نیست.').format(
                            user_level, current_stage.min_level
                        )
                    )

                self.object.current_stage = current_stage
                self.object.status = 'PENDING_APPROVAL'
                self.object.save()
                logger.info(f"Factor saved: PK={self.object.pk}, Number={self.object.number}")

                item_formset.instance = self.object
                item_formset.save()

                if document_form.is_valid():
                    for file in document_form.cleaned_data.get('files', []):
                        FactorDocument.objects.create(
                            factor=self.object,
                            file=file,
                            uploaded_by=self.request.user
                        )

                if tankhah_document_form.is_valid():
                    for file in tankhah_document_form.cleaned_data.get('documents', []):
                        TankhahDocument.objects.create(
                            tankhah=self.object.tankhah,
                            document=file,
                            uploaded_by=self.request.user
                        )

                # ثبت در ApprovalLog
                ApprovalLog.objects.create(
                    tankhah=self.object.tankhah,
                    user=self.request.user,
                    action="CREATED",
                    stage=current_stage.stage_order,  # استفاده از stage_order
                    object_id=self.object.pk,
                    content_type=ContentType.objects.get_for_model(Factor),
                    description=f"فاکتور {self.object.number} توسط {self.request.user.username} ایجاد شد."
                )

                create_budget_transaction(
                    allocation=self.object.tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=self.object.amount,
                    related_obj=self.object,
                    created_by=self.request.user,
                    description=f"Factor {self.object.number} for tankhah {self.object.tankhah.number}",
                    transaction_id=f"TX-FAC-{self.object.number}-{int(timezone.now().timestamp())}"
                )

                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=self.request.user,
                    description=f"فاکتور به شماره {self.object.number} توسط {self.request.user.username} ایجاد شد."
                )

                budget_allocation = self.object.tankhah.project_budget_allocation
                if budget_allocation:
                    budget_allocation.budget_period.update_lock_status()
                    status, message = budget_allocation.budget_period.check_budget_status_no_save()
                    if status in ['warning', 'locked', 'completed']:
                        budget_allocation.budget_period.send_notification(status, message)

        except Exception as e:
            logger.error(f"Error during atomic transaction for Factor creation: {e}", exc_info=True)
            messages.error(self.request,
                           _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد: {}').format(str(e)))
            return self.form_invalid(form)

        messages.success(self.request, _('فاکتور با موفقیت ثبت و برای تأیید ارسال شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return super().form_invalid(form)


###############################################################################################
