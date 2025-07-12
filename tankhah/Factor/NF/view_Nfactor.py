import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect, render  # Import render
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.forms import inlineformset_factory
from django.db.models import Sum
# Assuming these base classes, models, forms, and functions exist
from core.views import PermissionBaseView  # Your permission checking base view
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm, FactorDocumentForm, TankhahDocumentForm
from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem, FactorDocument, TankhahDocument, \
    create_budget_transaction, FactorHistory
from accounts.models import CustomUser  # Your user model
from core.models import WorkflowStage  # Your workflow stage model
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
class old__ok___New_FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')

    def get_success_url(self):
        # پس از ایجاد موفق، به لیست فاکتورها یا جزئیات فاکتور جدید بروید
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.select_related(
                    'project', 'organization', 'current_stage', 'project_budget_allocation__budget_period'
                ).get(id=tankhah_id)
                # انقضای تاریخ تنخواه
                if kwargs['tankhah'].due_date and kwargs['tankhah'].due_date.date() < timezone.now().date():
                    messages.error(self.request, _('تنخواه منقضی شده است. لطفاً تنخواه جدیدی انتخاب کنید.'))
                    kwargs['tankhah'] = None

            except (Tankhah.DoesNotExist, ValueError):
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()

        # ارسال تنخواه به context برای نمایش اطلاعات در تمپلیت
        form_kwargs = self.get_form_kwargs()
        if 'tankhah' in form_kwargs:
            context['tankhah'] = form_kwargs['tankhah']
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        # اعتبارسنجی فرم‌ست‌ها
        if not item_formset.is_valid():
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

        # بررسی وجود حداقل یک ردیف
        # valid_items = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
        # if not valid_items:
        #     messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
        #     return self.form_invalid(form)
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

        # بررسی همخوانی مبلغ کل با مجموع ردیف‌ها
        # total_items_amount = sum(item.cleaned_data['total_price'] for item in valid_items)
        # محاسبه مبلغ
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
            # تمام عملیات دیتابیس در یک تراکنش اتمیک انجام می‌شود
            with transaction.atomic():
                # ۱. ذخیره فاکتور اصلی
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                self.object.status = 'PENDING'  # یا هر وضعیت پیش‌فرض دیگری
                self.object.save()
                logger.info(f"Factor saved: PK={self.object.pk}, Number={self.object.number}")

                # ۲. ذخیره ردیف‌های فاکتور
                item_formset.instance = self.object
                item_formset.save()

                # ۳. ذخیره اسناد فاکتور
                if document_form.is_valid():
                    for file in document_form.cleaned_data.get('files', []):
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)

                # ۴. ذخیره اسناد تنخواه (در صورت وجود)
                if tankhah_document_form.is_valid():
                    for file in tankhah_document_form.cleaned_data.get('documents', []):
                        TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file,
                                                       uploaded_by=self.request.user)

                # ۵. ایجاد تراکنش بودجه برای کسر از اعتبار
                create_budget_transaction(
                    allocation=self.object.tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=self.object.amount,
                    related_obj=self.object,
                    created_by=self.request.user,
                    description=f"ایجاد فاکتور به شماره {self.object.number}",
                    transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
                )


                # ۶. ثبت تاریخچه برای فاکتور
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
        # چون خطاها در clean فرم مدیریت شده و به صورت non_field_error اضافه می‌شوند،
        # دیگر نیازی به نمایش پیام جداگانه نیست. جنگو خودکار آنها را نمایش می‌دهد.
        # فقط یک پیام کلی برای راهنمایی بهتر به کاربر نشان می‌دهیم.
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return super().form_invalid(form)
###############################################################################################
class New_FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')

    def get_success_url(self):
        # پس از ایجاد موفق، به لیست فاکتورها یا جزئیات فاکتور جدید بروید
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.select_related(
                    'project', 'organization', 'current_stage', 'project_budget_allocation__budget_period'
                ).get(id=tankhah_id)
                # انقضای تاریخ تنخواه
                if kwargs['tankhah'].due_date and kwargs['tankhah'].due_date.date() < timezone.now().date():
                    messages.error(self.request, _('تنخواه منقضی شده است. لطفاً تنخواه جدیدی انتخاب کنید.'))
                    kwargs['tankhah'] = None

            except (Tankhah.DoesNotExist, ValueError):
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['formset'] = FactorItemFormSet()
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()

        # ارسال تنخواه به context برای نمایش اطلاعات در تمپلیت
        form_kwargs = self.get_form_kwargs()
        if 'tankhah' in form_kwargs:
            context['tankhah'] = form_kwargs['tankhah']
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']

        # اعتبارسنجی فرم‌ست‌ها
        if not item_formset.is_valid():
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

        # بررسی وجود حداقل یک ردیف
        # valid_items = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
        # if not valid_items:
        #     messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
        #     return self.form_invalid(form)
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

        # بررسی همخوانی مبلغ کل با مجموع ردیف‌ها
        # total_items_amount = sum(item.cleaned_data['total_price'] for item in valid_items)
        # محاسبه مبلغ
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
            # تمام عملیات دیتابیس در یک تراکنش اتمیک انجام می‌شود
            with transaction.atomic():
                # ۱. ذخیره فاکتور اصلی
                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                self.object.status = 'PENDING'  # یا هر وضعیت پیش‌فرض دیگری
                self.object.save()
                logger.info(f"Factor saved: PK={self.object.pk}, Number={self.object.number}")

                # ۲. ذخیره ردیف‌های فاکتور
                item_formset.instance = self.object
                item_formset.save()

                # ۳. ذخیره اسناد فاکتور
                if document_form.is_valid():
                    for file in document_form.cleaned_data.get('files', []):
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)

                # ۴. ذخیره اسناد تنخواه (در صورت وجود)
                if tankhah_document_form.is_valid():
                    for file in tankhah_document_form.cleaned_data.get('documents', []):
                        TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file,
                                                       uploaded_by=self.request.user)

                # ۵. ایجاد تراکنش بودجه برای کسر از اعتبار
                create_budget_transaction(
                    allocation=self.object.tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=self.object.amount,
                    related_obj=self.object,
                    created_by=self.request.user,
                    description=f"ایجاد فاکتور به شماره {self.object.number}",
                    transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
                )


                # ۶. ثبت تاریخچه برای فاکتور
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
        # چون خطاها در clean فرم مدیریت شده و به صورت non_field_error اضافه می‌شوند،
        # دیگر نیازی به نمایش پیام جداگانه نیست. جنگو خودکار آنها را نمایش می‌دهد.
        # فقط یک پیام کلی برای راهنمایی بهتر به کاربر نشان می‌دهیم.
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return super().form_invalid(form)

###############################################################################################
