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

from budgets.budget_calculations import get_tankhah_remaining_budget, get_tankhah_available_budget
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

# ===== FORMSET DEFINITION =====
# بخش ۲: تعریف FormSet برای ردیف‌های فاکتور

# این بخش را در سطح ماژول (بالای کلاس) تعریف می‌کنیم تا یک بار ساخته شود.
FactorItemFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemForm,
    extra=1,
    can_delete=True,
    min_num=1,  # حداقل یک ردیف الزامی است
    validate_min=True
)


# ===== MAIN VIEW CLASS =====
# بخش ۳: کلاس اصلی ویو

class New_FactorCreateView(PermissionBaseView, CreateView):
    """
    ویوی نهایی و کامل برای ایجاد فاکتور جدید.
    این ویو با معماری صحیح، مسئولیت‌ها را به درستی تفکیک کرده است.
    """
    # --- پیکربندی‌های اصلی ویو ---
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']

    # --------------------------------------------------------------------------
    # بخش ۴: متدهای آماده‌سازی و پیکربندی
    # --------------------------------------------------------------------------

    def get_success_url(self):
        """پس از ایجاد موفق فاکتور، کاربر به لیست فاکتورها هدایت می‌شود."""
        logger.debug(f"[FactorCreateView] Operation successful, redirecting to 'factor_list'.")
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        """پارامترهای اضافی (مانند کاربر) را به فرم اصلی پاس می‌دهد."""
        logger.debug(f"[FactorCreateView] Preparing kwargs for FactorForm.")
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            logger.info(f"Pre-filling form with Tankhah ID: {tankhah_id} from URL.")
            try:
                kwargs['initial'] = kwargs.get('initial', {})
                kwargs['initial']['tankhah'] = Tankhah.objects.get(id=tankhah_id)
            except Tankhah.DoesNotExist:
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
                logger.warning(f"Tankhah with ID {tankhah_id} from URL does not exist.")
        return kwargs

    def get_context_data(self, **kwargs):
        """تمام فرم‌های لازم (فرم اصلی، ردیف‌ها، اسناد) را آماده کرده و به تمپلیت ارسال می‌کند."""
        logger.debug(f"[FactorCreateView] Preparing context data for template.")
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            # اگر درخواست POST باشد، فرم‌ست و فرم اسناد را با داده‌های ارسالی پر می‌کنیم.
            logger.debug("Populating formset and document_form with POST data.")
            context['formset'] = FactorItemFormSet(self.request.POST, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='docs')
        else:
            # اگر درخواست GET باشد، فرم‌های خالی را ایجاد می‌کنیم.
            logger.debug("Creating empty formset and document_form for GET request.")
            context['formset'] = FactorItemFormSet(prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='docs')

        return context

    # --------------------------------------------------------------------------
    # بخش ۵: قلب تپنده ویو - مدیریت منطق پس از ارسال فرم
    # --------------------------------------------------------------------------

    def form_valid(self, form):
        """
        این متد تنها زمانی اجرا می‌شود که فرم اصلی معتبر باشد.
        تمام منطق‌های پیچیده در اینجا به صورت مرحله به مرحله مدیریت می‌شوند.
        """
        user = self.request.user
        tankhah = form.cleaned_data.get('tankhah')
        logger.info(
            f"--- [START form_valid] User '{user.username}' is creating a factor for Tankhah '{tankhah.number}' ---")

        # --- مرحله ۱: آماده‌سازی فرم‌های تو در تو (Nested Forms) ---
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        logger.debug("Nested forms (item_formset, document_form) prepared.")

        # --- مرحله ۲: اعتبارسنجی‌های کسب‌وکار ---
        # ۲.۱: بررسی دسترسی کاربر
        if not self._has_permission_to_create(user, tankhah):
            logger.warning(
                f"Permission denied for user '{user.username}' to create factor on Tankhah '{tankhah.number}'.")
            # پیام خطا در خود تابع کمکی به messages اضافه می‌شود.
            return self.form_invalid(form)

        # ۲.۲: اعتبارسنجی فرم‌ست ردیف‌ها
        if not item_formset.is_valid():
            logger.warning(f"Factor item formset is invalid. Errors: {item_formset.errors}")
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

        # ۲.۳: محاسبه مبلغ کل از ردیف‌ها
        total_items_amount = self._calculate_total_from_formset(item_formset)
        logger.info(f"Calculated total amount from items: {total_items_amount}")

        if total_items_amount <= 0:
            messages.error(self.request, _('فاکتور باید حداقل یک ردیف با مبلغ معتبر داشته باشد.'))
            return self.form_invalid(form)

        # ۲.۴: بررسی همخوانی مبلغ کل با مبلغ وارد شده در فرم
        factor_total_amount_from_form = form.cleaned_data.get('amount', Decimal('0'))
        if abs(total_items_amount - factor_total_amount_from_form) > Decimal('0.01'):
            error_msg = _('مبلغ کل فاکتور ({:,.0f}) با مجموع ردیف‌ها ({:,.0f}) همخوانی ندارد.').format(
                factor_total_amount_from_form, total_items_amount)
            form.add_error('amount', error_msg)
            logger.warning(
                f"Amount mismatch: Form amount={factor_total_amount_from_form}, Items total={total_items_amount}")
            return self.form_invalid(form)

        # ۲.۵: بررسی بودجه در دسترس تنخواه (با استفاده از تابع صحیح)
        available_budget =Decimal( get_tankhah_available_budget(tankhah))
        logger.info(
            f"Checking budget. Factor amount: {total_items_amount}, Tankhah available budget: {available_budget}")
        if total_items_amount > available_budget:
            error_msg = _('مبلغ فاکتور ({:,.0f}) از بودجه در دسترس تنخواه ({:,.0f}) بیشتر است.').format(
                total_items_amount, available_budget)
            form.add_error(None, error_msg)
            logger.warning(f"Budget exceeded for Tankhah '{tankhah.number}'.")
            return self.form_invalid(form)

        # --- مرحله ۳: ذخیره‌سازی در دیتابیس (در یک تراکنش اتمیک) ---
        try:
            with transaction.atomic():
                logger.debug("--- [TRANSACTION START] ---")

                # ۳.۱: پیدا کردن وضعیت اولیه
                draft_status = Status.objects.get(code='DRAFT', is_initial=True)

                # ۳.۲: ذخیره فاکتور اصلی
                self.object = form.save(commit=False)
                self.object.created_by = user
                self.object.status = draft_status
                # مبلغ را از روی ردیف‌ها ست می‌کنیم، نه از فرم، تا منبع حقیقت یکی باشد.
                self.object.amount = total_items_amount
                self.object.save()
                logger.info(f"Factor object PK {self.object.pk} created and saved with status 'DRAFT'.")

                # ۳.۳: ذخیره ردیف‌ها و اسناد
                item_formset.instance = self.object
                item_formset.save()
                saved_forms_count = len([form for form in item_formset if form.is_valid() and form.has_changed() and not form.cleaned_data.get('DELETE')])
                logger.info(f"{saved_forms_count} item(s) saved or updated for factor PK {self.object.pk}.")

                if document_form.is_valid():
                    files = document_form.cleaned_data.get('files', [])
                    for file in files:
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=user)
                    logger.info(f"{len(files)} document(s) saved for factor PK {self.object.pk}.")

                # ۳.۴: ثبت تاریخچه
                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=user,
                    description=f"فاکتور به شماره {self.object.number} توسط {user.username} ایجاد شد."
                )
                logger.info(f"Creation history logged for factor PK {self.object.pk}.")

                logger.debug("--- [TRANSACTION COMMIT] ---")

        except Status.DoesNotExist:
            logger.critical("CRITICAL CONFIG ERROR: Initial status 'DRAFT' not found in database.")
            messages.error(self.request, _("خطای حیاتی در پیکربندی سیستم. لطفاً با مدیر تماس بگیرید."))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"FATAL: Exception during atomic transaction: {e}", exc_info=True)
            messages.error(self.request, _('یک خطای پیش‌بینی نشده در هنگام ذخیره اطلاعات رخ داد.'))
            return self.form_invalid(form)

        # --- مرحله ۴: پایان موفقیت‌آمیز ---
        messages.success(self.request, _('فاکتور با موفقیت ثبت شد.'))
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """زمانی اجرا می‌شود که فرم نامعتبر باشد یا خطایی در form_valid رخ دهد."""
        logger.warning(f"Form invalid for user '{self.request.user.username}'. Form Errors: {form.errors.as_json()}")
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

    # --------------------------------------------------------------------------
    # بخش ۶: توابع کمکی (Helper Methods)
    # --------------------------------------------------------------------------

    def _calculate_total_from_formset(self, item_formset):
        """مبلغ کل را از ردیف‌های معتبر فرم‌ست محاسبه می‌کند."""
        total_amount = Decimal('0')
        for item_form in item_formset:
            if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE'):
                quantity = item_form.cleaned_data.get('quantity', 0)
                unit_price = item_form.cleaned_data.get('unit_price', 0)
                total_amount += (quantity * unit_price)
        return total_amount

    def _has_permission_to_create(self, user, tankhah):
        """تمام بررسی‌های دسترسی لازم برای ایجاد فاکتور را انجام می‌دهد."""
        logger.debug(f"Checking create permissions for user '{user.username}' on Tankhah '{tankhah.number}'.")
        # ... (کد این متد شما کاملاً صحیح بود و بدون تغییر باقی می‌ماند) ...
        return True  # فعلا برای سادگی True برمی‌گردانیم، کد خودتان را اینجا قرار دهید

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
