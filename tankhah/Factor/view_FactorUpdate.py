import logging
from django.forms import inlineformset_factory

# فرض می‌کنیم این‌ها از قبل تعریف شده‌اند
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, Update_FactorForm
from tankhah.models import Factor, FactorItem
from budgets.budget_calculations import create_budget_transaction

# تنظیم لاگر برای ثبت رویدادها
logger = logging.getLogger(__name__)
# tankhah/views.py
# وارد کردن ماژول‌های مورد نیاز
import logging  # برای ثبت لاگ‌ها
from decimal import Decimal  # برای محاسبات دقیق اعشاری
from django.core.exceptions import ValidationError, PermissionDenied  # برای مدیریت خطاها
from django.db import models, transaction  # برای مدل‌ها و تراکنش‌های اتمی
from django.urls import reverse_lazy  # برای تعریف URL مقصد
from django.shortcuts import redirect, render, get_object_or_404  # برای ریدایرکت و رندر
from django.contrib import messages  # برای نمایش پیام به کاربر
from django.utils import timezone  # برای کار با زمان
from django.utils.translation import gettext_lazy as _  # برای ترجمه
from django.views.generic import UpdateView  # ویوی پایه برای ویرایش
from django.forms import inlineformset_factory  # برای فرم‌ست
from django.db.models import Sum  # برای جمع‌بندی کوئری‌ها

# وارد کردن ویوی پایه برای مدیریت مجوزها
from core.views import PermissionBaseView
# وارد کردن فرم‌ها
from tankhah.Factor.NF.form_Nfactor import FactorItemForm, FactorForm, FactorDocumentForm, TankhahDocumentForm
# وارد کردن مدل‌ها
from tankhah.models import  Factor, FactorItem, FactorDocument, TankhahDocument, FactorHistory

from core.models import Status, PostAction
from budgets.models import BudgetTransaction, BudgetAllocation
# وارد کردن توابع محاسبات بودجه
from budgets.budget_calculations import (
    get_project_total_budget, get_project_used_budget, get_project_remaining_budget,
    get_tankhah_total_budget, get_tankhah_remaining_budget, get_tankhah_used_budget,
)
# تعریف فرم‌ست برای آیتم‌ها
# تعریف فرم‌ست برای آیتم‌های فاکتور
FactorItemFormSet = inlineformset_factory(
    Factor,  # مدل والد
    FactorItem,  # مدل فرزند
    form=FactorItemForm,  # فرم آیتم
    extra=1,  # تعداد فرم‌های خالی اضافی
    can_delete=True,  # امکان حذف آیتم‌ها
)

class ool_FactorUpdateView(PermissionBaseView, UpdateView):
    """
    ویو برای ویرایش فاکتور با مدیریت بودجه، ثبت تاریخچه، و بررسی گردش کار.
    """
    # تنظیمات پایه ویو
    model = Factor  # مدل اصلی که ویرایش می‌شود
    form_class = FactorForm  # فرم اصلی برای ویرایش فاکتور
    template_name = 'tankhah/Factors/edit_factor_form.html'  # مسیر قالب
    success_url = reverse_lazy('factor_list')  # URL مقصد پس از موفقیت
    context_object_name = 'factor'  # نام آبجکت در کنتکست
    permission_codenames = ['tankhah.factor_update']  # پرمیشن مورد نیاز
    permission_denied_message = _('متاسفانه دسترسی لازم برای ویرایش فاکتور را ندارید.')  # پیام خطای عدم دسترسی
    check_organization = True  # بررسی سازمان در PermissionBaseView

    def get_object(self, queryset=None):
        """
        دریافت فاکتور و بررسی شرایط ویرایش.
        """
        # دریافت فاکتور با pk ارسالی در URL
        factor = get_object_or_404(Factor, pk=self.kwargs['pk'])
        # بررسی وضعیت فاکتور برای ویرایش
        if factor.status not in ['DRAFT', 'PENDING']:
            # ثبت پیام خطا برای کاربر
            messages.error(self.request, _('فقط فاکتورهای در وضعیت پیش‌نویس یا در انتظار قابل ویرایش هستند.'))
            # ثبت لاگ هشدار
            logger.warning(f"تلاش برای ویرایش فاکتور {factor.number} با وضعیت غیرمجاز: {factor.status}")
            # ریدایرکت به لیست فاکتورها
            return redirect(self.success_url)
        # بازگشت فاکتور
        return factor

    def get_form_kwargs(self):
        """
        پاس دادن کاربر و تنخواه به فرم.
        """
        # دریافت kwargs پایه
        kwargs = super().get_form_kwargs()
        # افزودن کاربر فعلی
        kwargs['user'] = self.request.user
        # افزودن تنخواه اگر فاکتور وجود داشته باشد
        if self.object and self.object.tankhah:
            kwargs['tankhah'] = self.object.tankhah
            logger.info(f"تنخواه {self.object.tankhah.number} به فرم فاکتور {self.object.number} پاس داده شد.")
        return kwargs

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی کنتکست برای قالب: فرم‌ها، اطلاعات بودجه، و غیره.
        """
        # دریافت کنتکست پایه
        context = super().get_context_data(**kwargs)
        # دریافت تنخواه
        tankhah = self.object.tankhah

        # تنظیم فرم‌ست و فرم‌های اسناد
        if self.request.POST:
            # فرم‌ست آیتم‌ها با داده‌های POST
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='items')
            # فرم اسناد فاکتور
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
            # فرم اسناد تنخواه
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES, prefix='tankhah_docs')
        else:
            # فرم‌ست اولیه برای GET
            context['formset'] = FactorItemFormSet(instance=self.object, prefix='items')
            # فرم‌های اولیه اسناد
            context['document_form'] = FactorDocumentForm(prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(prefix='tankhah_docs')

        # محاسبه اطلاعات بودجه
        budget_info = None
        tankhah_remaining_budget = Decimal('0')
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
                tankhah_remaining_budget = budget_info.get('tankhah_remaining', Decimal('0'))
                logger.info(f"اطلاعات بودجه برای تنخواه {tankhah.number}: باقی‌مانده={tankhah_remaining_budget}")
            except Exception as e:
                logger.error(f"خطا در محاسبه اطلاعات بودجه برای تنخواه {tankhah.number}: {e}", exc_info=True)
                messages.error(self.request, _("خطا در محاسبه اطلاعات بودجه."))
                budget_info = None

        # افزودن داده‌ها به کنتکست
        context.update({
            'title': _('ویرایش فاکتور'),
            'tankhah': tankhah,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'budget_info': budget_info,
            'tankhah_remaining_budget': tankhah_remaining_budget,
        })
        return context

    def form_valid(self, form):
        """
        پردازش فرم‌های معتبر: اعتبارسنجی، ذخیره، و مدیریت بودجه.
        """
        # دریافت کنتکست
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']
        tankhah = self.object.tankhah
        is_draft = 'save_draft' in self.request.POST

        logger.info(f"پردازش form_valid برای ویرایش فاکتور (pk={self.object.pk}, number={self.object.number})")

        # تشخیص نوع ذخیره
        save_incomplete = 'save_draft_incomplete' in self.request.POST
        save_final = 'save_final_draft' in self.request.POST or not save_incomplete
        logger.info(f"نوع ارسال فرم: {'پیش‌نویس ناقص' if save_incomplete else 'پیش‌نویس نهایی'}")

        # بررسی مرحله و وضعیت تنخواه
        try:
            initial_status = Status.objects.filter(is_initial=True).first()
            if initial_status and (not tankhah.current_stage or tankhah.current_stage_id != initial_status.id):
                stage_name = tankhah.current_stage.name if tankhah.current_stage else _("نامشخص")
                initial_name = initial_status.name
                msg = _('فقط در مرحله اولیه ({}) می‌توانید فاکتور ویرایش کنید. مرحله فعلی تنخواه: {}').format(
                    initial_name, stage_name)
                messages.error(self.request, msg)
                logger.warning(f"مرحله غیرمجاز برای تنخواه {tankhah.number}: مرحله فعلی={stage_name}")
                return self.form_invalid(form)
        except Exception as e:
            logger.error(f"خطا در بررسی مرحله گردش کار برای تنخواه {tankhah.number}: {e}", exc_info=True)
            messages.error(self.request, _('خطا در بررسی مرحله گردش کار تنخواه.'))
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, _('فقط برای تنخواه‌های در وضعیت پیش‌نویس یا در انتظار می‌توانید فاکتور ویرایش کنید.'))
            logger.warning(f"وضعیت غیرمجاز برای تنخواه {tankhah.number}: {tankhah.status}")
            return self.form_invalid(form)

        # اعتبارسنجی فرم‌ها
        is_item_formset_valid = item_formset.is_valid()
        is_doc_form_valid = document_form.is_valid()
        is_tankhah_doc_form_valid = tankhah_document_form.is_valid()

        if not (is_item_formset_valid and is_doc_form_valid and is_tankhah_doc_form_valid):
            logger.error("اعتبارسنجی فرم‌ست یا فرم‌های اسناد ناموفق بود.")
            if not is_item_formset_valid:
                logger.error(f"خطاهای فرم‌ست آیتم‌ها: {item_formset.errors} {item_formset.non_form_errors()}")
            if not is_doc_form_valid:
                logger.error(f"خطاهای فرم اسناد فاکتور: {document_form.errors}")
            if not is_tankhah_doc_form_valid:
                logger.error(f"خطاهای فرم اسناد تنخواه: {tankhah_document_form.errors}")
            messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم ردیف‌ها یا اسناد را بررسی و اصلاح کنید.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # بررسی آیتم‌های معتبر
        valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if not valid_item_forms:
            logger.warning("هیچ آیتم معتبری در فرم‌ست ارائه نشده است.")
            messages.error(self.request, _('حداقل یک ردیف معتبر باید برای فاکتور وارد شود.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # محاسبه مجموع آیتم‌ها
        total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
        factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))
        tolerance = Decimal('0.01')

        logger.info(f"مجموع مبلغ آیتم‌ها: {total_items_amount}، مبلغ فرم فاکتور: {factor_form_amount}")

        # بررسی تطابق مبالغ برای ذخیره نهایی
        if save_final and abs(total_items_amount - factor_form_amount) > tolerance:
            msg = _('مبلغ کل فاکتور ({}) با مجموع مبلغ ردیف‌ها ({}) همخوانی ندارد.').format(
                factor_form_amount, total_items_amount
            )
            messages.error(self.request, msg)
            logger.error(f"عدم تطابق مبلغ: فاکتور={factor_form_amount}، آیتم‌ها={total_items_amount}")
            form.add_error('amount', msg)
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # بررسی مجوز تغییر مرحله
        try:
            from core.models import Post
            user_post = self.request.user.userpost_set.filter(
                post__organization=tankhah.organization,
                is_active=True
            ).first()
            if not user_post:
                msg = _("شما پست فعالی در این سازمان ندارید.")
                messages.error(self.request, msg)
                logger.error(f"کاربر {self.request.user.username} پست فعالی در سازمان {tankhah.organization} ندارد.")
                return self.form_invalid(form)

            # بررسی مجوز STAGE_CHANGE
            current_stage = tankhah.current_stage or self.object.locked_by_stage
            if current_stage and hasattr(current_stage, 'has_permission'):
                if not current_stage.has_permission(user_post.post, action='STAGE_CHANGE'):
                    msg = _(f"پست شما ({user_post.post}) مجاز به تغییر مرحله در این مرحله نیست.")
                    messages.error(self.request, msg)
                    logger.error(f"پست {user_post.post} مجاز به STAGE_CHANGE در مرحله {current_stage} نیست.")
                    return self.form_invalid(form)
        except Exception as e:
            logger.error(f"خطا در بررسی مجوز تغییر مرحله برای فاکتور {self.object.number}: {e}", exc_info=True)
            messages.error(self.request, _("خطا در بررسی مجوزها. لطفاً با مدیر سیستم تماس بگیرید."))
            return self.form_invalid(form)

        # بررسی بودجه تنخواه
        try:
            tankhah_remaining = get_tankhah_remaining_budget(tankhah)
            # اصلاح خطای related_obj
            previous_transaction = BudgetTransaction.objects.filter(
                related_tankhah=tankhah,
                transaction_type='CONSUMPTION',
                description__contains=f"مصرف بودجه توسط فاکتور {self.object.number}"
            ).first()
            previous_amount = previous_transaction.amount if previous_transaction else Decimal('0')
            adjusted_remaining = tankhah_remaining + previous_amount
            if save_final and total_items_amount > adjusted_remaining:
                msg = _('مبلغ فاکتور ({:,}) از بودجه باقی‌مانده تنخواه ({:,}) بیشتر است.').format(
                    total_items_amount, adjusted_remaining
                )
                messages.error(self.request, msg)
                logger.error(f"تجاوز از بودجه: مبلغ فاکتور={total_items_amount}، بودجه باقی‌مانده={adjusted_remaining}")
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
            logger.error(f"خطا در بررسی بودجه تنخواه برای فاکتور {self.object.number}: {e}", exc_info=True)
            messages.error(self.request, _('خطا در بررسی بودجه تنخواه.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # یافتن تخصیص بودجه
        try:
            project_allocation = BudgetAllocation.objects.select_related('budget_allocation').filter(
                project=tankhah.project
            ).first()
            if not project_allocation or not project_allocation.budget_allocation:
                raise BudgetAllocation.DoesNotExist("خطای عدم تخصیص بودجه.")
            budget_allocation_instance = project_allocation.budget_allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"تخصیص بودجه معتبر برای پروژه {tankhah.project.name} یافت نشد.")
            messages.error(self.request, _('تخصیص بودجه معتبر برای پروژه این تنخواه یافت نشد.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )
        except Exception as e:
            logger.error(f"خطا در یافتن تخصیص بودجه پروژه: {e}", exc_info=True)
            messages.error(self.request, _('خطا در یافتن تخصیص بودجه پروژه.'))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                )
            )

        # بررسی قفل دوره بودجه
        budget_period = budget_allocation_instance.budget_period
        is_locked, lock_message = budget_period.is_period_locked
        if is_locked:
            messages.error(self.request, _("امکان ویرایش هزینه وجود ندارد: {}").format(lock_message))
            logger.error(f"دوره بودجه قفل شده است: {lock_message}")
            return self.form_invalid(form)

        # ذخیره اتمی
        try:
            with transaction.atomic():
                # جمع‌آوری داده‌های قدیمی
                old_factor_data = {
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
                }

                # ذخیره فاکتور
                self.object = form.save(commit=False)
                self.object.status = 'DRAFT' if is_draft else 'PENDING'
                self.object.amount = total_items_amount if save_final else factor_form_amount
                self.object.save()
                logger.info(f"فاکتور ذخیره شد (pk={self.object.pk}, number={self.object.number}, نوع={'نهایی' if save_final else 'ناقص'})")

                # ذخیره آیتم‌ها
                item_formset.instance = self.object
                items_saved_count = 0
                for item_form in valid_item_forms:
                    item = item_form.save(commit=False)
                    item.factor = self.object
                    item.save()
                    items_saved_count += 1
                logger.info(f"{items_saved_count} آیتم فاکتور ذخیره شد.")

                # ذخیره اسناد فاکتور
                factor_files = document_form.cleaned_data.get('files', [])
                docs_saved_count = 0
                for file in factor_files:
                    FactorDocument.objects.create(
                        factor=self.object,
                        file=file,
                        uploaded_by=self.request.user
                    )
                    docs_saved_count += 1
                if docs_saved_count:
                    logger.info(f"{docs_saved_count} سند فاکتور ذخیره شد.")

                # ذخیره اسناد تنخواه
                tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
                tdocs_saved_count = 0
                for file in tankhah_files:
                    TankhahDocument.objects.create(
                        tankhah=tankhah,
                        document=file,
                        uploaded_by=self.request.user
                    )
                    tdocs_saved_count += 1
                if tdocs_saved_count:
                    logger.info(f"{tdocs_saved_count} سند تنخواه ذخیره شد.")

                # حذف اسناد
                docs_deleted_count = 0
                tdocs_deleted_count = 0
                for key in self.request.POST:
                    if key.startswith('delete_factor_doc_'):
                        doc_id = key.replace('delete_factor_doc_', '')
                        FactorDocument.objects.filter(id=doc_id, factor=self.object).delete()
                        docs_deleted_count += 1
                    elif key.startswith('delete_tankhah_doc_'):
                        doc_id = key.replace('delete_tankhah_doc_', '')
                        TankhahDocument.objects.filter(id=doc_id, tankhah=tankhah).delete()
                        tdocs_deleted_count += 1
                if docs_deleted_count:
                    logger.info(f"{docs_deleted_count} سند فاکتور حذف شد.")
                if tdocs_deleted_count:
                    logger.info(f"{tdocs_deleted_count} سند تنخواه حذف شد.")

                # جمع‌آوری داده‌های جدید
                new_factor_data = {
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
                }

                # ثبت تاریخچه
                try:
                    FactorHistory.objects.create(
                        factor=self.object,
                        change_type=FactorHistory.ChangeType.UPDATE,
                        changed_by=self.request.user,
                        old_data=old_factor_data,
                        new_data=new_factor_data,
                        description=f"فاکتور {self.object.number} توسط {self.request.user.username} ویرایش شد."
                    )
                    logger.info(f"تاریخچه فاکتور برای فاکتور pk={self.object.pk} ثبت شد.")
                except PermissionDenied as e:
                    logger.error(f"خطا در ثبت تاریخچه فاکتور {self.object.number}: {e}")
                    messages.error(self.request, _("شما مجاز به ویرایش این فاکتور در مرحله فعلی نیستید."))
                    return self.form_invalid(form)

                # به‌روزرسانی تراکنش بودجه
                if save_final:
                    # حذف تراکنش قبلی
                    BudgetTransaction.objects.filter(
                        related_tankhah=tankhah,
                        transaction_type='CONSUMPTION',
                        description__contains=f"مصرف بودجه توسط فاکتور {self.object.number}"
                    ).delete()
                    logger.info(f"تراکنش بودجه قبلی برای فاکتور pk={self.object.pk} حذف شد.")
                    # ایجاد تراکنش جدید
                    BudgetTransaction.objects.create(
                        allocation=budget_allocation_instance,
                        transaction_type='CONSUMPTION',
                        amount=total_items_amount,
                        related_tankhah=tankhah,
                        created_by=self.request.user,
                        description=f"مصرف بودجه توسط فاکتور {self.object.number}",
                        transaction_id=f"TX-FACTOR-UPDATE-{self.object.id}-{timezone.now().timestamp()}"
                    )
                    logger.info(f"تراکنش بودجه برای فاکتور pk={self.object.pk} با مبلغ {total_items_amount} ایجاد شد.")
                else:
                    logger.info("تراکنش بودجه برای ذخیره پیش‌نویس ناقص تغییر نکرد.")

        except ValidationError as ve:
            logger.error(f"خطای اعتبارسنجی در ذخیره اتمی: {ve}", exc_info=True)
            messages.error(self.request, _('خطای اعتبارسنجی هنگام ذخیره: {}').format(ve))
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
            logger.error(f"خطای غیرمنتظره در تراکنش اتمی برای فاکتور {self.object.number}: {e}", exc_info=True)
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
        success_message = (
            _('فاکتور با موفقیت ویرایش شد.') if save_final
            else _('فاکتور به‌صورت موقت ویرایش شد.')
        )
        messages.success(self.request, success_message)
        return redirect(self.success_url)

    def form_invalid(self, form):
        """
        مدیریت فرم نامعتبر.
        """
        logger.warning(f"فرم اصلی فاکتور نامعتبر است. خطاها: {form.errors}")
        context = self.get_context_data(form=form)
        item_formset = context['formset']
        if item_formset.is_bound:
            logger.warning(f"خطاهای فرم‌ست آیتم‌ها: {item_formset.errors}")
        messages.error(self.request, _('لطفاً خطاهای مشخص شده در فرم اصلی فاکتور را اصلاح کنید.'))
        return self.render_to_response(context)

    def handle_no_permission(self):
        """
        مدیریت عدم دسترسی.
        """
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"عدم دسترسی برای کاربر {self.request.user} در تلاش برای ویرایش فاکتور.")
        return super().handle_no_permission()

class FactorUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/edit_factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_update']
    permission_denied_message = 'شما دسترسی لازم برای ویرایش فاکتور را ندارید.'
    check_organization = True

    def get_object(self, queryset=None):
        factor = get_object_or_404(Factor, pk=self.kwargs['pk'])
        # جایگزینی WorkflowStage با Status اولیه سیستم
        initial_stage = Status.objects.filter(is_initial=True).first()

        # بررسی وضعیت فاکتور
        if factor.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط فاکتورهای در وضعیت پیش‌نویس یا در انتظار قابل ویرایش هستند.')
            logger.warning(f"تلاش برای ویرایش فاکتور {factor.number} با وضعیت غیرمجاز: {factor.status}")
            return redirect(self.success_url)

        # بررسی وضعیت و مرحله تنخواه
        if factor.tankhah.status not in ['DRAFT', 'PENDING', 'REJECTED']:
            messages.error(self.request, 'تنخواه باید در وضعیت پیش‌نویس، در انتظار یا رد شده باشد.')
            logger.warning(f"وضعیت غیرمجاز تنخواه {factor.tankhah.number}: {factor.tankhah.status}")
            return redirect(self.success_url)

        # اگر تنخواه رد شده، باید در مرحله اولیه باشد
        if factor.tankhah.status == 'REJECTED' and (initial_stage and factor.tankhah.current_stage_id != initial_stage.id):
            messages.error(self.request, 'تنخواه رد شده فقط در مرحله اولیه قابل ویرایش است.')
            logger.warning(
                f"تنخواه {factor.tankhah.number} رد شده اما در مرحله غیراولیه: {factor.tankhah.current_stage}")
            return redirect(self.success_url)

        # بررسی قفل بودن فاکتور
        if factor.is_finalized or factor.locked:
            messages.error(self.request, 'فاکتور قفل شده و قابل ویرایش نیست.')
            logger.warning(
                f"فاکتور {factor.number} قفل شده است: is_finalized={factor.is_finalized}, locked={factor.locked}")
            return redirect(self.success_url)

        return factor


    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.object and self.object.tankhah:
            kwargs['tankhah'] = self.object.tankhah
            logger.info(f"تنخواه {self.object.tankhah.number} به فرم فاکتور {self.object.number} پاس داده شد.")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object.tankhah

        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES, prefix='tankhah_docs')
        else:
            context['formset'] = FactorItemFormSet(instance=self.object, prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='factor_docs')
            context['tankhah_document_form'] = TankhahDocumentForm(prefix='tankhah_docs')

        budget_info = None
        tankhah_remaining_budget = Decimal('0')
        if tankhah:
            try:
                project = tankhah.project
                budget_info = {
                    'project_name': project.name if project else 'بدون پروژه',
                    'project_budget': get_project_total_budget(project) if project else Decimal('0'),
                    'project_consumed': get_project_used_budget(project) if project else Decimal('0'),
                    'project_returned': BudgetTransaction.objects.filter(
                        allocation__project_allocations__project=project,
                        transaction_type='RETURN'
                    ).aggregate(total=Sum('amount'))['total'] or Decimal('0'),
                    'project_remaining': get_project_remaining_budget(project) if project else Decimal('0'),
                    'tankhah_budget': get_tankhah_total_budget(tankhah),
                    'tankhah_consumed': get_tankhah_used_budget(tankhah),
                    'tankhah_remaining': get_tankhah_remaining_budget(tankhah),
                }
                tankhah_remaining_budget = budget_info['tankhah_remaining']
                logger.info(f"اطلاعات بودجه برای تنخواه {tankhah.number}: باقی‌مانده={tankhah_remaining_budget}")
            except Exception as e:
                logger.error(f"خطا در محاسبه بودجه تنخواه {tankhah.number}: {e}", exc_info=True)
                messages.error(self.request, 'خطا در محاسبه اطلاعات بودجه.')
                budget_info = None

        context.update({
            'title': 'ویرایش فاکتور',
            'tankhah': tankhah,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'budget_info': budget_info,
            'tankhah_remaining_budget': tankhah_remaining_budget,
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']
        tankhah_document_form = context['tankhah_document_form']
        tankhah = self.object.tankhah
        is_draft = 'save_draft' in self.request.POST
        save_incomplete = 'save_draft_incomplete' in self.request.POST
        save_final = 'save_final_draft' in self.request.POST or not save_incomplete

        logger.info(f"پردازش form_valid برای فاکتور (pk={self.object.pk}, number={self.object.number})")
        logger.info(f"نوع ذخیره: {'پیش‌نویس ناقص' if save_incomplete else 'نهایی'}")

        # بررسی مرحله اولیه تنخواه
        try:
            initial_stage = Status.objects.filter(is_initial=True).first()
            if initial_stage and (not tankhah.current_stage or tankhah.current_stage_id != initial_stage.id):
                stage_name = tankhah.current_stage.name if tankhah.current_stage else 'نامشخص'
                initial_name = initial_stage.name
                messages.error(self.request, f'فقط در مرحله اولیه ({initial_name}) می‌توانید فاکتور ویرایش کنید. مرحله فعلی: {stage_name}')
                logger.warning(f"مرحله غیرمجاز برای تنخواه {tankhah.number}: {stage_name}")
                return self.form_invalid(form)
        except Exception as e:
            logger.error(f"خطا در بررسی مرحله تنخواه {tankhah.number}: {e}", exc_info=True)
            messages.error(self.request, 'خطا در بررسی مرحله گردش کار تنخواه.')
            return self.form_invalid(form)

        # بررسی وضعیت تنخواه
        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'تنخواه باید در وضعیت پیش‌نویس یا در انتظار باشد.')
            logger.warning(f"وضعیت غیرمجاز تنخواه {tankhah.number}: {tankhah.status}")
            return self.form_invalid(form)

        # اعتبارسنجی فرم‌ها
        if not (item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid()):
            logger.error("خطا در اعتبارسنجی فرم‌ها")
            if not item_formset.is_valid():
                logger.error(f"خطاهای فرم‌ست آیتم‌ها: {item_formset.errors}")
            if not document_form.is_valid():
                logger.error(f"خطاهای فرم اسناد فاکتور: {document_form.errors}")
            if not tankhah_document_form.is_valid():
                logger.error(f"خطاهای فرم اسناد تنخواه: {tankhah_document_form.errors}")
            messages.error(self.request, 'لطفاً خطاهای فرم را اصلاح کنید.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        # بررسی آیتم‌ها
        valid_item_forms = [f for f in item_formset.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if not valid_item_forms and save_final:
            messages.error(self.request, 'حداقل یک ردیف معتبر برای فاکتور لازم است.')
            logger.warning(f"هیچ آیتم معتبری برای فاکتور {self.object.number} ارائه نشد.")
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        # محاسبه مجموع آیتم‌ها
        total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
        factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))
        tolerance = Decimal('0.01')
        logger.info(f"مجموع آیتم‌ها: {total_items_amount}, مبلغ فاکتور: {factor_form_amount}")

        if save_final and abs(total_items_amount - factor_form_amount) > tolerance:
            messages.error(self.request, f'مبلغ فاکتور ({factor_form_amount}) با مجموع آیتم‌ها ({total_items_amount}) همخوانی ندارد.')
            logger.error(f"عدم تطابق مبلغ فاکتور {self.object.number}: فاکتور={factor_form_amount}, آیتم‌ها={total_items_amount}")
            form.add_error('amount', 'مبلغ فاکتور با مجموع آیتم‌ها همخوانی ندارد.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        # بررسی مجوز کاربر
        try:
            user_post = self.request.user.userpost_set.filter(
                post__organization=tankhah.organization,
                is_active=True
            ).first()
            if not user_post:
                messages.error(self.request, 'شما پست فعالی در این سازمان ندارید.')
                logger.error(f"کاربر {self.request.user.username} پست فعالی در سازمان {tankhah.organization} ندارد.")
                return self.form_invalid(form)

            # کاربران HQ (دفتر مرکزی) دسترسی کامل دارند
            if not tankhah.organization.is_core:
                current_stage = tankhah.current_stage
                if current_stage and not PostAction.objects.filter(
                    post=user_post.post,
                    stage=current_stage,
                    action_type='STAGE_CHANGE',
                    entity_type='FACTOR',
                    is_active=True
                ).exists():
                    messages.error(self.request, f'پست شما ({user_post.post}) مجاز به تغییر مرحله فاکتور نیست.')
                    logger.error(f"پست {user_post.post} مجاز به STAGE_CHANGE در مرحله {current_stage} برای فاکتور نیست.")
                    return self.form_invalid(form)
        except Exception as e:
            logger.error(f"خطا در بررسی مجوز برای فاکتور {self.object.number}: {e}", exc_info=True)
            messages.error(self.request, 'خطا در بررسی مجوزها. با مدیر سیستم تماس بگیرید.')
            return self.form_invalid(form)

        # بررسی بودجه
        try:
            tankhah_remaining = get_tankhah_remaining_budget(tankhah)
            previous_transaction = BudgetTransaction.objects.filter(
                related_tankhah=tankhah,
                transaction_type='CONSUMPTION',
                description__contains=f"مصرف بودجه توسط فاکتور {self.object.number}"
            ).first()
            previous_amount = previous_transaction.amount if previous_transaction else Decimal('0')
            adjusted_remaining = tankhah_remaining + previous_amount
            if save_final and total_items_amount > adjusted_remaining:
                messages.error(self.request, f'مبلغ فاکتور ({total_items_amount:,}) از بودجه باقی‌مانده ({adjusted_remaining:,}) بیشتر است.')
                logger.error(f"تجاوز از بودجه فاکتور {self.object.number}: مبلغ={total_items_amount}, بودجه={adjusted_remaining}")
                form.add_error(None, 'مبلغ فاکتور از بودجه باقی‌مانده بیشتر است.')
                return self.render_to_response(self.get_context_data(
                    form=form,
                    formset=item_formset,
                    document_form=document_form,
                    tankhah_document_form=tankhah_document_form
                ))
        except Exception as e:
            logger.error(f"خطا در بررسی بودجه فاکتور {self.object.number}: {e}", exc_info=True)
            messages.error(self.request, 'خطا در بررسی بودجه تنخواه.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        # بررسی تخصیص بودجه
        try:
            project_allocation = tankhah.project_budget_allocation or BudgetAllocation.objects.filter(
                budget_allocation=tankhah.budget_allocation,
                project=tankhah.project,
                subproject=tankhah.subproject
            ).first()
            if not project_allocation or not project_allocation.budget_allocation:
                raise BudgetAllocation.DoesNotExist
            budget_allocation = project_allocation.budget_allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"تخصیص بودجه برای پروژه {tankhah.project.name if tankhah.project else 'نامشخص'} یافت نشد.")
            messages.error(self.request, 'تخصیص بودجه برای پروژه یافت نشد.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))
        except Exception as e:
            logger.error(f"خطا در یافتن تخصیص بودجه: {e}", exc_info=True)
            messages.error(self.request, 'خطا در یافتن تخصیص بودجه.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        # بررسی قفل بودن دوره بودجه
        budget_period = budget_allocation.budget_period
        is_locked, lock_message = budget_period.is_period_locked
        if is_locked:
            messages.error(self.request, f'امکان ویرایش وجود ندارد: {lock_message}')
            logger.error(f"دوره بودجه قفل شده برای فاکتور {self.object.number}: {lock_message}")
            return self.form_invalid(form)

        # ذخیره فاکتور
        try:
            with transaction.atomic():
                old_factor_data = {
                    'amount': str(self.object.amount),
                    'status': self.object.status,
                    'items': [{
                        'id': item.id,
                        'description': item.description,
                        'quantity': str(item.quantity),
                        'unit_price': str(item.unit_price),
                        'amount': str(item.amount),
                    } for item in self.object.items.all()],
                    'documents': [{'id': doc.id, 'file': str(doc.file)} for doc in self.object.documents.all()],
                }

                factor = form.save(commit=False)
                factor.status = 'DRAFT' if is_draft or save_incomplete else 'PENDING'
                factor.amount = total_items_amount if save_final else factor_form_amount
                factor.save()
                logger.info(f"فاکتور {factor.number} ذخیره شد (نوع={'نهایی' if save_final else 'ناقص'})")

                # ذخیره آیتم‌ها
                item_formset.instance = factor
                items_saved = sum(1 for f in valid_item_forms if f.save(commit=False).save())
                logger.info(f"{items_saved} آیتم فاکتور ذخیره شد.")

                # ذخیره اسناد فاکتور
                factor_files = document_form.cleaned_data.get('files', [])
                docs_saved = sum(1 for file in factor_files if FactorDocument.objects.create(
                    factor=factor,
                    file=file,
                    uploaded_by=self.request.user
                ))
                if docs_saved:
                    logger.info(f"{docs_saved} سند فاکتور ذخیره شد.")

                # ذخیره اسناد تنخواه
                tankhah_files = tankhah_document_form.cleaned_data.get('documents', [])
                tdocs_saved = sum(1 for file in tankhah_files if TankhahDocument.objects.create(
                    tankhah=tankhah,
                    document=file,
                    uploaded_by=self.request.user
                ))
                if tdocs_saved:
                    logger.info(f"{tdocs_saved} سند تنخواه ذخیره شد.")

                # حذف اسناد
                docs_deleted = 0
                tdocs_deleted = 0
                for key in self.request.POST:
                    if key.startswith('delete_factor_doc_'):
                        doc_id = key.replace('delete_factor_doc_', '')
                        FactorDocument.objects.filter(id=doc_id, factor=factor).delete()
                        docs_deleted += 1
                    elif key.startswith('delete_tankhah_doc_'):
                        doc_id = key.replace('delete_tankhah_doc_', '')
                        TankhahDocument.objects.filter(id=doc_id, tankhah=tankhah).delete()
                        tdocs_deleted += 1
                if docs_deleted:
                    logger.info(f"{docs_deleted} سند فاکتور حذف شد.")
                if tdocs_deleted:
                    logger.info(f"{tdocs_deleted} سند تنخواه حذف شد.")

                # ثبت تاریخچه
                new_factor_data = {
                    'amount': str(factor.amount),
                    'status': factor.status,
                    'items': [{
                        'id': item.id,
                        'description': item.description,
                        'quantity': str(item.quantity),
                        'unit_price': str(item.unit_price),
                        'amount': str(item.amount),
                    } for item in factor.items.all()],
                    'documents': [{'id': doc.id, 'file': str(doc.file)} for doc in factor.documents.all()],
                }

                try:
                    FactorHistory.objects.create(
                        factor=factor,
                        change_type=FactorHistory.ChangeType.UPDATE,
                        changed_by=self.request.user,
                        old_data=old_factor_data,
                        new_data=new_factor_data,
                        description=f"فاکتور {factor.number} توسط {self.request.user.username} ویرایش شد."
                    )
                    logger.info(f"تاریخچه فاکتور برای فاکتور {factor.number} ثبت شد.")
                except PermissionDenied as e:
                    logger.error(f"خطا در ثبت تاریخچه فاکتور {factor.number}: {e}")
                    messages.error(self.request, 'شما مجاز به ویرایش این فاکتور در مرحله فعلی نیستید.')
                    return self.form_invalid(form)

                # ثبت تراکنش بودجه برای ذخیره نهایی
                if save_final and factor.status == 'PENDING':
                    BudgetTransaction.objects.filter(
                        related_tankhah=tankhah,
                        transaction_type='CONSUMPTION',
                        description__contains=f"مصرف بودجه توسط فاکتور {factor.number}"
                    ).delete()
                    logger.info(f"تراکنش بودجه قبلی برای فاکتور {factor.number} حذف شد.")
                    create_budget_transaction(
                        allocation=budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=total_items_amount,
                        related_obj=factor,
                        created_by=self.request.user,
                        description=f"مصرف بودجه توسط فاکتور {factor.number}",
                        transaction_id=f"TX-FAC-UPDATE-{factor.id}-{timezone.now().timestamp()}"
                    )
                    logger.info(f"تراکنش بودجه برای فاکتور {factor.number} با مبلغ {total_items_amount} ایجاد شد.")
                else:
                    logger.info("تراکنش بودجه برای پیش‌نویس ناقص تغییر نکرد.")

        except ValueError as ve:
            logger.error(f"خطای اعتبارسنجی فاکتور {self.object.number}: {ve}", exc_info=True)
            messages.error(self.request, f'خطا در ذخیره فاکتور: {ve}')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))
        except Exception as e:
            logger.error(f"خطای غیرمنتظره در فاکتور {self.object.number}: {e}", exc_info=True)
            messages.error(self.request, 'خطای غیرمنتظره‌ای رخ داد. با مدیر سیستم تماس بگیرید.')
            return self.render_to_response(self.get_context_data(
                form=form,
                formset=item_formset,
                document_form=document_form,
                tankhah_document_form=tankhah_document_form
            ))

        messages.success(self.request, 'فاکتور با موفقیت ویرایش شد.' if save_final else 'فاکتور به‌صورت موقت ویرایش شد.')
        return redirect(self.success_url)

    def form_invalid(self, form):
        logger.warning(f"فرم فاکتور نامعتبر: {form.errors}")
        context = self.get_context_data(form=form)
        if context['formset'].is_bound:
            logger.warning(f"خطاهای فرم‌ست آیتم‌ها: {context['formset'].errors}")
        messages.error(self.request, 'لطفاً خطاهای فرم را اصلاح کنید.')
        return self.render_to_response(context)

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"عدم دسترسی برای کاربر {self.request.user} در فاکتور.")
        return super().handle_no_permission()

