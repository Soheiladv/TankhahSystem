# import logging
# from decimal import Decimal
# from django.db import models, transaction
# from django.urls import reverse_lazy
# from django.shortcuts import redirect
# from django.contrib import messages
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _
# from django.views.generic import CreateView
# from django.forms import inlineformset_factory
#
# from accounts.AccessRule.check_user_access import check_user_factor_access
# from core.views import PermissionBaseView  # Your permission checking base view
# from notificationApp.utils import send_notification
# from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm, FactorDocumentForm, TankhahDocumentForm
# from tankhah.models import ItemCategory, Tankhah, Factor, FactorItem, FactorDocument, TankhahDocument, \
#     create_budget_transaction, FactorHistory, ApprovalLog
# from core.models import   AccessRule, Post
#
# # --- End Assumptions ---
# logger = logging.getLogger('New_FactorCreateView')
# # Define the inline formset factory (can be defined globally or inside the view methods)
#
#
# # FactorItemFormSet = inlineformset_factory(
# #     Factor,           # مدل والد
# #     FactorItem,       # مدل فرزند (ردیف‌ها)
# #     form=FactorItemForm, # فرمی که برای هر ردیف استفاده می‌شود
# #     extra=1,          # همیشه یک فرم خالی اضافی برای ورود ردیف جدید نمایش بده
# #     can_delete=True,  # اجازه حذف ردیف‌های موجود را بده
# #     # min_num=1,        # حداقل یک ردیف باید وجود داشته باشد
# #     validate_min=True # این حداقل را در سمت سرور اعتبارسنجی کن
# # )
#
#
# ##############################################################################################
#
# FactorItemFormSet = inlineformset_factory(
#     Factor, FactorItem, form=FactorItemForm,
#     extra=1, can_delete=True,  validate_min=True
# )
#
#
# ##############################################################################################
# class New_FactorCreateView(PermissionBaseView, CreateView):
#     model = Factor
#     form_class = FactorForm
#     template_name = 'tankhah/Factors/NF/new_factor_form.html'
#     permission_codenames = ['tankhah.factor_add']
#     permission_denied_message = _('متاسفانه دسترسی لازم برای افزودن فاکتور را ندارید.')
#
#     def get_success_url(self):
#         return reverse_lazy('factor_list')
#
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
#         if tankhah_id:
#             try:
#                 kwargs['tankhah'] = Tankhah.objects.select_related(
#                     'project', 'organization', 'project_budget_allocation__budget_period'
#                 ).get(id=tankhah_id)
#                 if kwargs['tankhah'].due_date and kwargs['tankhah'].due_date < timezone.now():
#                     messages.error(self.request, _('تنخواه منقضی شده است. لطفاً تنخواه جدیدی انتخاب کنید.'))
#                     kwargs['tankhah'] = None
#             except (Tankhah.DoesNotExist, ValueError):
#                 messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
#         return kwargs
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         if self.object and self.object.pk:
#             can_delete = False
#             user = self.request.user
#             factor = self.object
#             tankhah = factor.tankhah
#
#             # بررسی دسترسی حذف
#             access_info = check_user_factor_access(user.username, tankhah=tankhah, action_type='DELETE', entity_type='FACTOR')
#             can_delete = access_info['has_access'] and factor.status in ['DRAFT', 'PENDING', 'PENDING_APPROVAL'] and not factor.is_locked and not tankhah.is_locked and not tankhah.is_archived
#
#             context['can_delete'] = can_delete
#
#         if self.request.POST:
#             context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
#             context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
#             context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
#         else:
#             context['formset'] = FactorItemFormSet()
#             context['document_form'] = FactorDocumentForm()
#             context['tankhah_document_form'] = TankhahDocumentForm()
#
#         form_kwargs = self.get_form_kwargs()
#         if 'tankhah' in form_kwargs:
#             context['tankhah'] = form_kwargs['tankhah']
#
#         return context
#
#     def form_valid(self, form):
#         context = self.get_context_data()
#         item_formset = context['formset']
#         document_form = context['document_form']
#         tankhah_document_form = context['tankhah_document_form']
#
#         if not item_formset.is_valid():
#             messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
#             return self.form_invalid(form)
#
#         valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
#         if not valid_item_forms:
#             logger.warning("No valid items submitted in the formset.")
#             messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
#             return self.render_to_response(
#                 self.get_context_data(
#                     form=form,
#                     formset=item_formset,
#                     document_form=document_form,
#                     tankhah_document_form=tankhah_document_form
#                 )
#             )
#
#         total_items_amount = sum(
#             (f.cleaned_data.get('unit_price', Decimal('0')) * f.cleaned_data.get('quantity', Decimal('0'))).quantize(
#                 Decimal('0.01'))
#             for f in valid_item_forms
#         )
#
#         if abs(total_items_amount - form.cleaned_data['amount']) > Decimal('0.01'):
#             msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
#                 form.cleaned_data['amount'], total_items_amount
#             )
#             form.add_error('amount', msg)
#             return self.form_invalid(form)
#
#         try:
#             with transaction.atomic():
#                 self.object = form.save(commit=False)
#                 self.object.created_by = self.request.user
#                 self.object.status = 'PENDING_APPROVAL'
#                 self.object._request_user = self.request.user  # اضافه کردن کاربر برای سیگنال
#                 self.object.current_stage = AccessRule.objects.filter(
#                     entity_type='FACTOR',
#                     stage_order=1,
#                     is_active=True
#                 ).first()  # تنظیم مرحله اولیه فاکتور
#                 self.object.save()
#                 logger.info(f"Factor saved: PK={self.object.pk}, Number={self.object.number}")
#
#                 item_formset.instance = self.object
#                 item_formset.save()
#
#                 if document_form.is_valid():
#                     for file in document_form.cleaned_data.get('files', []):
#                         FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)
#
#                 if tankhah_document_form.is_valid():
#                     for file in tankhah_document_form.cleaned_data.get('documents', []):
#                         TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file,
#                                                        uploaded_by=self.request.user)
#
#                 create_budget_transaction(
#                     allocation=self.object.tankhah.project_budget_allocation,
#                     transaction_type='CONSUMPTION',
#                     amount=self.object.amount,
#                     related_obj=self.object,
#                     created_by=self.request.user,
#                     description=f"ایجاد فاکتور به شماره {self.object.number}",
#                     transaction_id=f"TX-FACTOR-NEW-{self.object.id}-{timezone.now().timestamp()}"
#                 )
#
#                 FactorHistory.objects.create(
#                     factor=self.object,
#                     change_type=FactorHistory.ChangeType.CREATION,
#                     changed_by=self.request.user,
#                     description=f"فاکتور به شماره {self.object.number} توسط {self.request.user.username} ایجاد شد."
#                 )
#
#         except Exception as e:
#             logger.error(f"Error during atomic transaction for Factor creation: {e}", exc_info=True)
#             messages.error(self.request,
#                            _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد. لطفاً دوباره تلاش کنید.'))
#             return self.form_invalid(form)
#
#         messages.success(self.request, _('فاکتور با موفقیت ثبت و برای تایید ارسال شد.'))
#         return super().form_valid(form)
#
#     def form_invalid(self, form):
#         messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
#         return super().form_invalid(form)

##############################################################################################
#
# فایل نهایی: views/factor_views.py (یا هر فایلی که ویو در آن قرار دارد)
#
import logging
from decimal import Decimal
from django.db import transaction, models
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.forms import inlineformset_factory

from budgets.budget_calculations import get_tankhah_remaining_budget
# --- Import های لازم ---
# مطمئن شوید تمام این مدل‌ها و فرم‌ها به درستی import شده‌اند
from core.PermissionBase import PermissionBaseView
from core.models import AccessRule, Post, Status
from notificationApp.utils import send_notification
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm
from tankhah.models import Factor, Tankhah, FactorItem, FactorDocument, ApprovalLog, FactorHistory
# مسیر فرم‌های خود را بر اساس ساختار پروژه تنظیم کنید
from tankhah.forms import  FactorDocumentForm

# --- تنظیمات اولیه ---
logger = logging.getLogger('FactorCreateLogger')

# تعریف نهایی و صحیح FactorItemFormSet در سطح ماژول
FactorItemFormSet = inlineformset_factory(
    Factor,  # مدل والد
    FactorItem,  # مدل فرزند (ردیف‌ها)
    form=FactorItemForm,  # فرمی که برای هر ردیف استفاده می‌شود
    extra=1,  # همیشه یک فرم خالی اضافی برای ورود ردیف جدید نمایش بده
    can_delete=True,  # اجازه حذف ردیف‌های موجود را بده (برای حالت ویرایش مفید است)
    # min_num=1,  # حداقل یک ردیف باید در فرم وجود داشته باشد
    validate_min=True  # این حداقل را در سمت سرور اعتبارسنجی کن
)


class New_FactorCreateView(PermissionBaseView, CreateView):
    """
    ویوی نهایی، کامل و بهینه برای ایجاد فاکتور جدید به همراه ردیف‌ها و اسناد.
    این ویو تمام منطق‌های دسترسی، اعتبارسنجی، ذخیره‌سازی و شروع گردش کار را مدیریت می‌کند.
    """
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    check_organization = False  # بررسی دسترسی سازمان به صورت دستی و شفاف در داخل ویو انجام می‌شود

    def get_success_url(self):
        """پس از ایجاد موفق فاکتور، کاربر به لیست فاکتورها هدایت می‌شود."""
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        """
        پارامترهای لازم مانند کاربر و تنخواه را به فرم اصلی (FactorForm) پاس می‌دهد.
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        # تلاش برای خواندن تنخواه از URL یا پارامترهای GET
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            try:
                # مقدار اولیه تنخواه را برای فرم ست می‌کنیم
                kwargs['initial'] = kwargs.get('initial', {})
                kwargs['initial']['tankhah'] = Tankhah.objects.get(id=tankhah_id)
            except Tankhah.DoesNotExist:
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
        return kwargs

    def get_context_data(self, **kwargs):
        """
        تمام فرم‌های لازم (فرم اصلی، فرم‌ست ردیف‌ها، فرم اسناد) را آماده کرده و به تمپلیت ارسال می‌کند.
        این متد هم برای درخواست GET (نمایش فرم خالی) و هم برای POST (نمایش مجدد فرم با خطاها) کار می‌کند.
        """
        context = super().get_context_data(**kwargs)

        # ساخت فرم‌ست‌ها
        if self.request.POST:
            # اگر درخواست POST باشد، فرم‌ها را با داده‌های ارسالی پر می‌کنیم تا خطاها نمایش داده شوند
            context['formset'] = FactorItemFormSet(self.request.POST, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='docs')
        else:
            # اگر درخواست GET باشد، فرم‌های خالی را ایجاد می‌کنیم
            # FactorItemFormSet به خاطر extra=1 به صورت خودکار یک ردیف خالی خواهد داشت
            context['formset'] = FactorItemFormSet(prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='docs')

        return context

    # def form_valid(self, form):
    #     """
    #     این متد قلب تپنده ویو است. تنها زمانی اجرا می‌شود که فرم اصلی (FactorForm) معتبر باشد.
    #     تمام منطق‌های پیچیده در این متد مدیریت می‌شوند.
    #     """
    #     user = self.request.user
    #     tankhah = form.cleaned_data.get('tankhah')
    #     context = self.get_context_data()
    #     item_formset = context['formset']
    #     document_form = context['document_form']
    #
    #     logger.info(
    #         f"--- [START form_valid] User '{user.username}' is creating a factor for Tankhah '{tankhah.number}' ---")
    #
    #     # --- مرحله ۱: بررسی جامع دسترسی‌ها ---
    #     if not self._has_permission_to_create(user, tankhah):
    #         # پیغام خطا در خود تابع کمکی به messages اضافه می‌شود
    #         return self.form_invalid(form)
    #
    #     # --- مرحله ۲: اعتبارسنجی فرم‌ست ردیف‌ها ---
    #     if not item_formset.is_valid():
    #         logger.warning(f"Item formset is invalid. Errors: {item_formset.errors}")
    #         messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
    #         return self.form_invalid(form)
    #
    #     # --- ۳. محاسبه مبلغ کل و بررسی بودجه ---
    #     total_items_amount = Decimal('0')
    #     for item_form in item_formset:
    #         if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE'):
    #             quantity = item_form.cleaned_data.get('quantity', 0)
    #             unit_price = item_form.cleaned_data.get('unit_price', 0)
    #             total_items_amount += (quantity * unit_price)
    #
    #     factor_total_amount  = form.cleaned_data.get('amount', Decimal('0'))
    #     total_amount= factor_total_amount
    #     tankhah = form.cleaned_data.get('tankhah')
    #     remaining_budget = get_tankhah_remaining_budget(tankhah)
    #     if factor_total_amount > remaining_budget:
    #         form.add_error(None, _('مجموع مبلغ ردیف‌ها از بودجه باقی‌مانده تنخواه بیشتر است.'))
    #         return self.form_invalid(form)
    #
    #     # یک تلورانس کوچک برای جلوگیری از خطاهای اعشاری در نظر می‌گیریم
    #     if abs(total_items_amount - factor_total_amount) > Decimal('0.01'):
    #         error_msg = _('مبلغ کل فاکتور ({:,.0f}) با مجموع ردیف‌ها ({:,.0f}) همخوانی ندارد.').format(
    #             factor_total_amount, total_items_amount)
    #         messages.error(self.request, error_msg)
    #         # می‌توانیم خطا را به فیلد amount اضافه کنیم تا در فرم نمایش داده شود
    #         form.add_error('amount', error_msg)
    #         return self.form_invalid(form)
    #     # ----  ذخیره سازی
    #     try:
    #         # --- مرحله ۳: شروع تراکنش اتمیک برای تضمین یکپارچگی داده‌ها ---
    #         with transaction.atomic():
    #             logger.debug("--- [TRANSACTION START] ---")
    #             # ذخیره فاکتور اصلی برای گرفتن ID
    #             try:
    #                 initial_factor_status = Status.objects.get(code='DRAFT', is_initial=True)
    #                 logger.info(f'initial_factor_status: {initial_factor_status}')
    #             except Status.DoesNotExist:
    #                 messages.error(self.request, _("وضعیت اولیه 'DRAFT' در سیستم تعریف نشده است!"))
    #                 messages.error(self.request,
    #                                _("هیچ وضعیت اولیه‌ای در سیستم تعریف نشده است! لطفاً با مدیر سیستم تماس بگیرید."))
    #                 raise transaction.TransactionManagementError('Initial DRAFT status not found.')
    #             except Status.MultipleObjectsReturned:
    #                 messages.error(self.request,
    #                                _("بیش از یک وضعیت اولیه در سیستم تعریف شده است! لطفاً با مدیر سیستم تماس بگیرید."))
    #                 raise transaction.TransactionManagementError('Multiple initial statuses found.')
    #
    #             # --- ذخیره فاکتور با وضعیت صحیح ---
    #             self.object = form.save(commit=False)
    #             self.object.created_by = self.request.user
    #             self.object.status = initial_factor_status   # <-- **اصلاح کلیدی**
    #             # self.object.amount = total_amount # <-- مبلغ محاسبه شده
    #             logger.warning(f'After Save Method :self.object.amount: {self.object.amount} - self.object.created_by: {self.object.created_by} - self.object.status: {initial_factor_status}')
    #             self.object.save()
    #             logger.info(f"Factor object PK {self.object.pk} created and saved.")
    #
    #             # اتصال ردیف‌ها به فاکتور و ذخیره آن‌ها
    #             item_formset.instance = self.object
    #             item_formset.save()
    #             logger.info(f"{item_formset.total_form_count()} item(s) saved for factor PK {self.object.pk}.")
    #             self.object.update_total_amount() # از متد مدل استفاده می‌کنیم
    #
    #             # -----
    #             # --- ذخیره اسناد ---
    #             if document_form.is_valid():
    #                 for file in document_form.cleaned_data.get('files', []):
    #                     FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)
    #
    #             logger.info(f"Factor PK {self.object.pk} and its items created successfully.")
    #
    #     except Exception as e:
    #         logger.error(f"FATAL: Exception during atomic transaction: {e}", exc_info=True)
    #         messages.error(self.request, _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد.'))
    #         return self.form_invalid(form)
    #
    #     messages.success(self.request, _('فاکتور با موفقیت ثبت و برای تأیید ارسال شد.'))
    #     return redirect(self.get_success_url())
    def form_valid(self, form):
        user = self.request.user
        tankhah = form.cleaned_data.get('tankhah')
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']

        logger.info(
            f"--- [START form_valid] User '{user.username}' is creating a factor for Tankhah '{tankhah.number}' ---")

        if not self._has_permission_to_create(user, tankhah):
            return self.form_invalid(form)

        if not item_formset.is_valid():
            logger.warning(f"Item formset is invalid. Errors: {item_formset.errors}")
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

        total_items_amount = Decimal('0')
        for item_form in item_formset:
            if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE'):
                quantity = item_form.cleaned_data.get('quantity', 0)
                unit_price = item_form.cleaned_data.get('unit_price', 0)
                total_items_amount += (quantity * unit_price)

        factor_total_amount = form.cleaned_data.get('amount', Decimal('0'))
        remaining_budget = get_tankhah_remaining_budget(tankhah)
        if factor_total_amount > remaining_budget:
            form.add_error(None, _('مجموع مبلغ ردیف‌ها از بودجه باقی‌مانده تنخواه بیشتر است.'))
            return self.form_invalid(form)

        if abs(total_items_amount - factor_total_amount) > Decimal('0.01'):
            error_msg = _('مبلغ کل فاکتور ({:,.0f}) با مجموع ردیف‌ها ({:,.0f}) همخوانی ندارد.').format(
                factor_total_amount, total_items_amount)
            messages.error(self.request, error_msg)
            form.add_error('amount', error_msg)
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                try:
                    draft_status = Status.objects.get(code='DRAFT', is_initial=True)
                except Status.DoesNotExist:
                    messages.error(self.request, _("وضعیت اولیه 'DRAFT' در سیستم تعریف نشده است!"))
                    return self.form_invalid(form)
                except Status.MultipleObjectsReturned:
                    messages.error(self.request, _("بیش از یک وضعیت اولیه در سیستم تعریف شده است!"))
                    return self.form_invalid(form)

                self.object = form.save(commit=False)
                self.object.created_by = self.request.user
                self.object.status = draft_status  # اطمینان از مقداردهی
                logger.debug(f"Before save: Factor status set to {draft_status}")
                self.object.save()
                logger.info(f"Factor object PK {self.object.pk} created and saved.")

                item_formset.instance = self.object
                item_formset.save()
                logger.info(f"{item_formset.total_form_count()} item(s) saved for factor PK {self.object.pk}.")
                self.object.update_total_amount()

                if document_form.is_valid():
                    for file in document_form.cleaned_data.get('files', []):
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)

                logger.info(f"Factor PK {self.object.pk} and its items created successfully.")
                from tankhah.models import create_budget_transaction
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
            logger.error(f"FATAL: Exception during atomic transaction: {e}", exc_info=True)
            messages.error(self.request, _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد.'))
            return self.form_invalid(form)

        messages.success(self.request, _('فاکتور با موفقیت ثبت و برای تأیید ارسال شد.'))
        return redirect(self.get_success_url())
    def form_invalid(self, form):
        """
        این متد در صورت نامعتبر بودن فرم اصلی یا بروز هر خطای دیگر فراخوانی می‌شود.
        """
        context = self.get_context_data(form=form)
        # لاگ کردن خطاهای فرم اصلی و فرم‌ست
        logger.warning(
            f"Form invalid for user '{self.request.user.username}'. Form Errors: {form.errors}. ItemFormset Errors: {context['formset'].errors}")
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        # صفحه را با فرم‌های پر شده و خطاهایشان دوباره نمایش می‌دهد
        return self.render_to_response(context)

    # --------------------------------------------------------------------------
    # بخش توابع کمکی (Helper Methods)
    # --------------------------------------------------------------------------

    def _has_permission_to_create(self, user, tankhah):
        """
        تابع کمکی برای تجمیع تمام بررسی‌های دسترسی لازم برای ایجاد فاکتور.
        """
        logger.debug(f"--- Checking create permissions for user '{user.username}' on Tankhah '{tankhah.number}' ---")

        # 1. پرمیشن پایه جنگو
        if not user.has_perm('tankhah.factor_add'):
            logger.warning("Permission check FAILED: User lacks 'tankhah.factor_add' permission.")
            messages.error(self.request, _('شما مجوز اولیه برای افزودن فاکتور را ندارید.'))
            return False

        # 2. داشتن پست فعال
        user_post_qs = user.userpost_set.filter(is_active=True)
        if not user_post_qs.exists():
            logger.warning("Permission check FAILED: User has no active post.")
            messages.error(self.request, _("شما برای ثبت فاکتور باید یک پست سازمانی فعال داشته باشید."))
            return False

        # 3. دسترسی به سازمان تنخواه (با در نظر گرفتن سلسله مراتب)
        if user.is_superuser:
            logger.debug("Permission check PASSED: User is a superuser.")
            return True

        target_org = tankhah.organization
        user_orgs_with_parents = {up.post.organization for up in user_post_qs.select_related('post__organization')}
        for org in list(user_orgs_with_parents):
            parent = org.parent_organization
            while parent:
                user_orgs_with_parents.add(parent)
                parent = parent.parent_organization

        if target_org not in user_orgs_with_parents:
            logger.warning(
                f"Permission check FAILED: User's organizations do not include target org '{target_org.name}'.")
            messages.error(self.request, _('شما به سازمان این تنخواه دسترسی ندارید.'))
            return False

        logger.debug("Permission check PASSED.")
        return True

    def _create_related_objects_and_notify(self, factor, user, tankhah, initial_stage, document_form):
        """
        لاگ‌ها، تاریخچه، اسناد و نوتیفیکیشن‌های مربوطه را ایجاد می‌کند.
        """
        logger.debug("--- Creating related objects and sending notifications ---")

        # ذخیره اسناد
        if document_form.is_valid():
            files = document_form.cleaned_data.get('files', [])
            for file in files:
                FactorDocument.objects.create(factor=factor, file=file, uploaded_by=user)
            logger.info(f"Saved {len(files)} document(s) for factor {factor.pk}.")

        # ثبت لاگ و تاریخچه
        logger.debug(f"--- Creating Log for factor {factor.pk} in stage '{initial_stage.stage}' ---")
        user_post = user.userpost_set.filter(is_active=True).first()
        ApprovalLog.objects.create(
            factor=factor,
            user=user,
            post=user_post.post if user_post else None,
            action="CREATED",
            stage_rule=initial_stage,  # <--- **اصلاح اصلی و حیاتی**
            comment=f"فاکتور {factor.number} توسط {user.username} ایجاد شد."
        )

        # ApprovalLog.objects.create(
        #     factor=factor, user=user, post=user_post.post if user_post else None,
        #     action="CREATED",
        #     stage_rule=initial_stage,
        #     comment=f"فاکتور {factor.number} توسط {user.username} ایجاد شد."
        # )
        FactorHistory.objects.create(
            factor=factor, change_type=FactorHistory.ChangeType.CREATION,
            changed_by=user, description=f"فاکتور ایجاد شد."
        )
        logger.info(f"ApprovalLog and FactorHistory created for factor {factor.pk}.")

        # ارسال نوتیفیکیشن به تأییدکنندگان مرحله اول
        approver_posts_ids = AccessRule.objects.filter(
            organization=tankhah.organization,
            entity_type='FACTORITEM',
            stage_order=initial_stage.stage_order
        ).values_list('post_id', flat=True).distinct()

        if approver_posts_ids:
            send_notification(
                sender=user,
                posts=Post.objects.filter(id__in=approver_posts_ids),
                verb=_("برای تأیید ارسال شد"),
                target=factor,
                description=_(f"فاکتور جدید #{factor.number} برای تأیید ارسال شد."),
                entity_type='FACTOR'
            )
            logger.info(
                f"Notification sent to {len(approver_posts_ids)} post(s) for initial approval of factor {factor.pk}.")
        else:
            logger.warning(f"No approver posts found for stage order {initial_stage.stage_order} to send notification.")
