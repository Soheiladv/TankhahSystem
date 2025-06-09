from django.utils.translation import gettext_lazy as _
import logging
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum, Q
from django.db.models.functions.comparison import Coalesce
from django.forms import DecimalField
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

from budgets.models import ProjectBudgetAllocation, BudgetTransaction
from core.models import WorkflowStage

from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, View
from core.PermissionBase import PermissionBaseView
from django.contrib import messages

from tankhah.Factor import forms_Factor
from tankhah.Factor.forms_Factor import FactorWizardStep1Form, FactorItemWizardFormSet
from tankhah.forms import FactorForm, get_factor_item_formset, FactorItemForm
from tankhah.models import Factor, TankhahDocument, FactorDocument, FactorItem, create_budget_transaction
from tankhah.models import Tankhah
from tankhah.forms import get_factor_item_formset
from tankhah.models import Tankhah
from tankhah.forms import FactorDocumentForm, TankhahDocumentForm
logger = logging.getLogger('tankhah')
from formtools.wizard.views import SessionWizardView

from budgets.budget_calculations import get_project_total_budget, get_project_used_budget,get_project_remaining_budget, get_tankhah_total_budget,get_tankhah_remaining_budget,get_tankhah_used_budget
# فقط لاگ‌های سطح INFO و بالاتر
logging.basicConfig(level=logging.INFO)

class FactorCreateView(CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
        if tankhah_id:
            try:
                kwargs['tankhah'] = Tankhah.objects.get(id=tankhah_id)
                logger.info(f"Tankhah {tankhah_id} retrieved for form")
            except Tankhah.DoesNotExist:
                logger.error(f"Tankhah with ID {tankhah_id} not found")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah_id = self.kwargs.get('tankhah_id') or self.request.POST.get('tankhah') or self.request.GET.get('tankhah')
        tankhah = Tankhah.objects.filter(id=tankhah_id).first() if tankhah_id else None
        from django.forms import inlineformset_factory
        FactorItemFormSet = inlineformset_factory(Factor, FactorItem, form=FactorItemForm, extra=1, can_delete=True)

        if self.request.POST:
            form = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah)
            item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='items')
            document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
            tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            form = self.form_class(user=self.request.user, tankhah=tankhah)
            item_formset = FactorItemFormSet(prefix='items')
            document_form = FactorDocumentForm()
            tankhah_document_form = TankhahDocumentForm()

        budget_info = None
        tankhah_remaining_budget = Decimal('0')
        project_remaining_budget = Decimal('0')
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
                tankhah_remaining_budget = budget_info['tankhah_remaining']
                project_remaining_budget = budget_info['project_remaining']
                logger.info(f"Budget info calculated: {budget_info}")
            except Exception as e:
                logger.error(f"Error accessing budget info for tankhah {tankhah.number}: {e}")
                budget_info = None

        context.update({
            'form': form,
            'formset': item_formset,
            'document_form': document_form,
            'tankhah_document_form': tankhah_document_form,
            'title': 'ایجاد فاکتور جدید',
            'tankhah': tankhah,
            'tankhah_documents': tankhah.documents.all() if tankhah else [],
            'budget_info': budget_info,
            'tankhah_remaining_budget': tankhah_remaining_budget,
            'project_remaining_budget': project_remaining_budget,
        })
        logger.debug(f"Context data: {context}")
        return context

    def form_valid(self, form):
        tankhah = form.cleaned_data['tankhah']
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order
        from django.forms import inlineformset_factory
        FactorItemFormSet = inlineformset_factory(Factor, FactorItem, form=FactorItemForm, extra=1, can_delete=True)

        # ... (بررسی‌های اولیه stage و status تنخواه) ...

        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='items')
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
        tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)

        # بررسی اعتبار فرم‌ها قبل از محاسبات
        # مهم: is_valid() را اینجا فراخوانی کنید تا cleaned_data فرم‌ها پر شود
        is_main_form_valid = form.is_valid() # این باید True باشد چون به form_valid رسیدیم
        is_item_formset_valid = item_formset.is_valid()
        is_doc_form_valid = document_form.is_valid()
        is_tankhah_doc_form_valid = tankhah_document_form.is_valid()

        logger.info(f"Main form valid? {is_main_form_valid}")
        logger.info(f"Item formset valid? {is_item_formset_valid}")
        logger.info(f"Document form valid? {is_doc_form_valid}")
        logger.info(f"Tankhah document form valid? {is_tankhah_doc_form_valid}")


        # اگر فرم‌ست آیتم‌ها نامعتبر بود، مستقیم به form_invalid بروید
        if not is_item_formset_valid:
             logger.error(f"Item formset is invalid. Errors: {item_formset.errors}")
             messages.error(self.request, 'خطا در ردیف‌های فاکتور. لطفاً بررسی کنید.')
             # از self.form_invalid استفاده کنید تا context مناسب ساخته شود
             return self.form_invalid(form)


        # استخراج آیتم‌های معتبر (آنهایی که حذف نشده‌اند و cleaned_data دارند)
        # cleaned_data در فرم‌های معتبر فرم‌ست وجود خواهد داشت
        valid_item_forms = [f for f in item_formset.forms if hasattr(f, 'cleaned_data') and f.cleaned_data and not f.cleaned_data.get('DELETE')]

        if not valid_item_forms:
            logger.error("No valid (non-deleted) items found in formset after validation.")
            messages.error(self.request, 'حداقل یک ردیف معتبر باید وارد کنید.')
            # context را برای نمایش مجدد فرم با خطاها بسازید
            context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
            return self.render_to_response(context)

        # محاسبه مجموع amount آیتم‌ها از cleaned_data فرم‌ها
        # حالا باید f.cleaned_data['amount'] وجود داشته باشد چون فرم آیتم آن را محاسبه می‌کند
        total_items_amount = sum(f.cleaned_data.get('amount', Decimal('0')) for f in valid_item_forms)
        factor_form_amount = form.cleaned_data.get('amount', Decimal('0'))

        logger.info(f"Calculated total_items_amount from forms: {total_items_amount}")
        logger.info(f"Amount from main factor form: {factor_form_amount}")

        # مقایسه مجموع آیتم‌ها با مبلغ فاکتور اصلی
        if abs(total_items_amount - factor_form_amount) > Decimal('0.01'):
            logger.error(
                f"Total items amount ({total_items_amount}) does not match factor amount ({factor_form_amount})")
            messages.error(self.request, 'مبلغ فاکتور با مجموع مبلغ ردیف‌ها همخوانی ندارد.')
            context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
            return self.render_to_response(context)

        # بررسی بودجه تنخواه با مجموع مبلغ آیتم‌ها
        try:
            tankhah_remaining = get_tankhah_remaining_budget(tankhah)
            if total_items_amount > tankhah_remaining:
                logger.error(f"Total items amount ({total_items_amount}) exceeds remaining tankhah budget ({tankhah_remaining})")
                messages.error(self.request, f'مجموع مبلغ ردیف‌ها از بودجه باقی‌مانده تنخواه بیشتر است.')
                context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
                return self.render_to_response(context)
        except Exception as e:
             logger.error(f"Error getting remaining tankhah budget in view: {e}", exc_info=True)
             messages.error(self.request, 'خطا در بررسی بودجه تنخواه.')
             context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
             return self.render_to_response(context)


        # بررسی وجود تخصیص بودجه پروژه
        project_allocation = ProjectBudgetAllocation.objects.filter(project=tankhah.project).first()
        if not project_allocation:
            logger.error(f"No ProjectBudgetAllocation found for project {tankhah.project.name}")
            messages.error(self.request, 'تخصیص بودجه برای پروژه این تنخواه یافت نشد.')
            context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
            return self.render_to_response(context)

        # اگر همه چیز معتبر بود، ذخیره در دیتابیس
        if is_doc_form_valid and is_tankhah_doc_form_valid: # فرم اصلی و فرم‌ست قبلا چک شدند
            try:
                with transaction.atomic():
                    self.object = form.save(commit=False)
                    self.object.status = 'DRAFT' # یا وضعیت مناسب دیگر
                    self.object.created_by = self.request.user
                    # مبلغ فاکتور اصلی را برابر با مجموع آیتم‌ها قرار دهید (برای اطمینان)
                    self.object.amount = total_items_amount
                    self.object.save() # ذخیره فاکتور اصلی

                    # ذخیره آیتم‌های فرم‌ست
                    # دیگر نیازی به item_formset.save() نیست چون جداگانه ذخیره می‌کنیم
                    items_saved = []
                    for item_form in valid_item_forms:
                         item = item_form.save(commit=False)
                         item.factor = self.object # اتصال آیتم به فاکتور ذخیره شده
                         # مقدار amount باید توسط save مدل محاسبه شود، نیازی به تنظیم دوباره نیست
                         # item.amount = item_form.cleaned_data['amount']
                         item.save() # ذخیره آیتم (که save مدل amount را محاسبه می‌کند)
                         items_saved.append(item)
                    logger.info(f"Saved {len(items_saved)} factor items.")


                    # ذخیره اسناد فاکتور
                    factor_files = self.request.FILES.getlist('files')
                    for file in factor_files:
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=self.request.user)

                    # ذخیره اسناد تنخواه
                    tankhah_files = self.request.FILES.getlist('documents')
                    for file in tankhah_files:
                        TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)

                    # حذف اسناد علامت‌گذاری شده
                    for key in self.request.POST:
                        if key.startswith('delete_factor_doc_'):
                            doc_id = key.replace('delete_factor_doc_', '')
                            FactorDocument.objects.filter(pk=doc_id, factor=self.object).delete()
                        elif key.startswith('delete_tankhah_doc_'):
                            doc_id = key.replace('delete_tankhah_doc_', '')
                            TankhahDocument.objects.filter(pk=doc_id, tankhah=tankhah).delete()

                    # ایجاد تراکنش بودجه برای کل فاکتور (نه برای تنخواه)
                    # اطمینان از وجود allocation صحیح
                    if project_allocation.budget_allocation:
                         create_budget_transaction(
                             allocation=project_allocation.budget_allocation,
                             transaction_type='CONSUMPTION', # نوع تراکنش مصرف
                             amount=total_items_amount, # مبلغ کل آیتم‌ها
                             related_obj=self.object, # اتصال به خود فاکتور
                             created_by=self.request.user,
                             description=f"مصرف بودجه برای فاکتور {self.object.number}",
                             transaction_id=f"TX-FACTOR-{self.object.id}-{timezone.now().timestamp()}"
                         )
                    else:
                         logger.error(f"Project allocation {project_allocation.id} has no associated budget allocation.")
                         # شاید بخواهید در این حالت خطا ایجاد کنید یا فقط لاگ بگیرید

                    logger.info(f"Factor {self.object.number} and items saved successfully as DRAFT.")
                    messages.success(self.request, 'فاکتور به‌صورت پیش‌نویس ذخیره شد.')

            except Exception as e:
                # خطای کلی در هنگام ذخیره‌سازی
                logger.error(f"Error during atomic transaction for saving factor: {e}", exc_info=True)
                messages.error(self.request, 'خطایی در هنگام ذخیره فاکتور رخ داد. لطفاً دوباره تلاش کنید.')
                context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
                return self.render_to_response(context)

        else:
            # اگر فرم‌های اسناد نامعتبر بودند
            logger.error(f"Document forms invalid. Factor doc errors: {document_form.errors}. Tankhah doc errors: {tankhah_document_form.errors}")
            messages.error(self.request, 'خطا در فایل‌های پیوست شده. لطفاً بررسی کنید.')
            context = self.get_context_data(form=form, formset=item_formset, document_form=document_form, tankhah_document_form=tankhah_document_form)
            return self.render_to_response(context)

        return redirect(self.get_success_url())

    def form_invalid(self, form):
        from django.forms import inlineformset_factory

        FactorItemFormSet = inlineformset_factory(Factor, FactorItem, form=FactorItemForm, extra=1, can_delete=True)
        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='items')
        logger.error(f"Main form errors: {form.errors}, Item formset errors: {item_formset.errors}")
        messages.error(self.request, 'لطفاً خطاهای فرم را بررسی و اصلاح کنید.')
        return self.render_to_response(self.get_context_data(form=form, formset=item_formset))

from django.views.decorators.http import require_GET
@require_GET
def get_tankhah_budget_info(request):
    tankhah_id = request.GET.get('tankhah_id')
    if not tankhah_id:
        logger.error("No tankhah_id provided in get_tankhah_budget_info")
        return JsonResponse({'error': 'Tankhah ID is required'}, status=400)

    try:
        tankhah = Tankhah.objects.get(id=tankhah_id)
        project = tankhah.project
        budget_info = {
            'project_name': project.name,
            'project_budget': str(get_project_total_budget(project)),
            'project_consumed': str(get_project_used_budget(project)),
            'project_returned': str(
                BudgetTransaction.objects.filter(
                    allocation__project_allocations__project=project,
                    transaction_type='RETURN'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            ),
            'project_remaining': str(get_project_remaining_budget(project)),
            'tankhah_budget': str(get_tankhah_total_budget(tankhah)),
            'tankhah_consumed': str(get_tankhah_used_budget(tankhah)),
            'tankhah_remaining': str(get_tankhah_remaining_budget(tankhah)),
            }
        logger.info(f"Budget info retrieved for tankhah {tankhah.number}: {budget_info}")
        return JsonResponse(budget_info)
    except Tankhah.DoesNotExist:
        logger.error(f"Tankhah with ID {tankhah_id} not found")
        return JsonResponse({'error': 'Tankhah not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in get_tankhah_budget_info: {e}")
        return JsonResponse({'error': str(e)}, status=500)

#----------
class FactorCreateWizard(PermissionBaseView, SessionWizardView):
    template_name = 'tankhah/Factors/factor_wizard.html'
    FactorItemFormSet = get_factor_item_formset()
    form_list = [
        ('tankhah', FactorForm),  # مرحله انتخاب تنخواه
        ('factor', FactorForm),   # مرحله اطلاعات فاکتور
        ('items', FactorItemFormSet),  # مرحله آیتم‌ها
        ('documents', FactorDocumentForm),  # مرحله اسناد
    ]
    form_class =  forms_Factor.W_FactorForm

    permission_codenames = ['tankhah.a_factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

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
        current_step = self.steps.current
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
# views.py (Wizard View)

from core.PermissionBase import PermissionBaseView # Your permission mixin
from core.models import WorkflowStage # Import if needed for status checks

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from formtools.wizard.views import SessionWizardView

# --- Define Wizard Steps ---
FACTOR_FORMS = [
    ("step1", FactorWizardStep1Form),
    ("step2", FactorItemWizardFormSet),
    ("step3_docs", FactorDocumentForm),
    ("step3_tankhah_docs", TankhahDocumentForm), # Separate step for clarity or combine
    ("step4_review", None), # Optional review step without a form
]


FACTOR_TEMPLATES = {
    "step1": 'tankhah/Factors/wizard/factor_wizard_step1.html',
    "step2": 'tankhah/Factors/wizard/factor_wizard_step2_formset.html',
    "step3_docs": 'tankhah/Factors/Factorswizard/factor_wizard_step3_docs.html',
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

class FactorWizardView(PermissionBaseView, SessionWizardView):
    # Permission settings remain the same
    permission_codenames = ['tankhah.a_factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True

    form_list = FACTOR_FORMS
    template_name = "tankhah/wizard/factor_wizard_base.html" # Base template

    # --- *** ADD THIS LINE TO CONFIGURE FILE STORAGE *** ---
    file_storage = wizard_file_storage

    # get_template_names method remains the same
    def get_template_names(self):
        return [FACTOR_TEMPLATES.get(self.steps.current, self.template_name)] # Use .get for safety

    # get_form_kwargs method remains the same
    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        kwargs['user'] = self.request.user
        if step == 'step1':
            cleaned_data = self.get_cleaned_data_for_step('step1') or {}
            if 'tankhah' in cleaned_data:
                kwargs['initial'] = {'tankhah': cleaned_data['tankhah']}
        return kwargs

    # get_context_data method needs update for review step total
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        total_steps = len(self.form_list)
        # Check if review step exists (if named 'step4_review')
        # has_review_step = "step4_review" in FACTOR_TEMPLATES
        # if has_review_step:
        #     total_steps += 1 # Add 1 if review step is conceptual and not in form_list

        context['wizard_title'] = _('ایجاد فاکتور جدید (مرحله {} از {})').format(
            self.steps.step1, total_steps # Use calculated total steps
        )
        context['step_name'] = self.steps.current

        if self.steps.current == 'step1':
             context['tankhah_budget_info_url'] = reverse('tankhah_budget_info_ajax', args=[0]).replace('/0/', '/')

        elif self.steps.current == 'step2':
            cleaned_data_step1 = self.get_cleaned_data_for_step('step1') or {}
            context['selected_tankhah'] = cleaned_data_step1.get('tankhah')
            # Pass the formset explicitly if needed, though 'form' is the formset here
            context['formset'] = form

        elif self.steps.current == 'step3_tankhah_docs':
             cleaned_data_step1 = self.get_cleaned_data_for_step('step1') or {}
             tankhah = cleaned_data_step1.get('tankhah')
             if tankhah:
                  context['tankhah_documents'] = tankhah.documents.all()

        # Add context for the review step (assuming it's the step *after* the last form)
        # This requires a slightly different approach if review isn't a form step
        # Let's assume step4_review is the key for the review template
        if self.steps.current == 'step4_review':
             context['all_cleaned_data'] = self.get_all_cleaned_data()
             context['summary_total'] = self.get_summary_total()

        return context

    # Helper method to calculate total for review step
    def get_summary_total(self):
        item_formset_data = self.get_cleaned_data_for_step('step2') or []
        total = Decimal('0.0')
        for item_data in item_formset_data:
            if item_data and not item_data.get('DELETE', False):
                amount = item_data.get('amount', Decimal('0.0'))
                quantity = item_data.get('quantity', 1)
                total += (amount * quantity)
        return total

    # done method remains mostly the same, ensure it uses correct step keys
    def done(self, form_list, form_dict, **kwargs):
        step1_data = form_dict['step1'].cleaned_data
        item_formset = form_dict['step2']
        factor_doc_form = form_dict['step3_docs']
        tankhah_doc_form = form_dict['step3_tankhah_docs']
        tankhah = step1_data['tankhah']

        # --- Final Budget Check (Recalculate) ---
        total_amount = self.get_summary_total() # Use helper method

        if total_amount <= 0:
             messages.error(self.request, _("مبلغ کل فاکتور نمی‌تواند صفر یا منفی باشد. لطفاً ردیف‌ها را بررسی کنید."))
             logger.error("Wizard Done: Total amount is zero or negative.")
             return self.render_goto_step('step2')

        # --- (Rest of the budget checking logic remains the same) ---
        target_allocation_instance = None
        project_allocation_amount = Decimal('0.0')
        # ... (logic to find target_allocation_instance and project_allocation_amount) ...
        if tankhah.project_budget_allocation:
            target_allocation_instance = tankhah.project_budget_allocation.budget_allocation
            project_allocation_amount = tankhah.project_budget_allocation.allocated_amount
        elif tankhah.budget_allocation:
            target_allocation_instance = tankhah.budget_allocation
            project_allocation_amount = target_allocation_instance.allocated_amount # Re-evaluate if this is correct

        if not target_allocation_instance:
             messages.error(self.request, _("خطا: تخصیص بودجه مرتبط با تنخواه یافت نشد."))
             logger.error(f"Wizard Done: Could not find target allocation for Tankhah {tankhah.id} during final save.")
             return self.render_goto_step('step1')

        consumed_q = Q(allocation=target_allocation_instance, transaction_type='CONSUMPTION')
        returned_q = Q(allocation=target_allocation_instance, transaction_type='RETURN')
        consumption_total = BudgetTransaction.objects.filter(consumed_q).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField()))['total']
        return_total = BudgetTransaction.objects.filter(returned_q).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField()))['total']
        current_remaining_budget = project_allocation_amount - consumption_total + return_total

        if total_amount > current_remaining_budget:
            error_msg = _("مبلغ کل فاکتور ({amount1} ریال) از بودجه باقی‌مانده تخصیص ({amount2} ریال) بیشتر است.").format(
                amount1=f"{total_amount:,.0f}", amount2=f"{current_remaining_budget:,.0f}"
            )
            messages.error(self.request, error_msg)
            logger.error(f"Wizard Done: Final budget check failed. Required: {total_amount}, Available: {current_remaining_budget}")
            return self.render_goto_step('step2')

        # --- (Saving logic in transaction remains the same) ---
        try:
            with transaction.atomic():
                # 1. Create Factor
                factor = Factor(
                    tankhah=tankhah,
                    date=step1_data['date'],
                    description=step1_data.get('description', ''),
                    created_by=self.request.user,
                    amount=total_amount,
                    status='PENDING' # Final status
                )
                factor.save()
                logger.info(f"Wizard Done: Factor saved: ID={factor.pk}")

                # 2. Save Items
                item_formset.instance = factor
                item_formset.save()
                logger.info(f"Wizard Done: Factor items saved.")

                # 3. Save Factor Docs
                factor_files = factor_doc_form.cleaned_data.get('files', [])
                saved_factor_docs = 0
                for file in factor_files:
                    if file:
                        FactorDocument.objects.create(factor=factor, file=file, uploaded_by=self.request.user)
                        saved_factor_docs += 1
                logger.info(f"Wizard Done: Saved {saved_factor_docs} factor documents.")

                # 4. Save Tankhah Docs
                tankhah_files = tankhah_doc_form.cleaned_data.get('documents', [])
                saved_tankhah_docs = 0
                for file in tankhah_files:
                     if file:
                         TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
                         saved_tankhah_docs += 1
                logger.info(f"Wizard Done: Saved {saved_tankhah_docs} tankhah documents.")

                # 5. Create Budget Transaction
                transaction_description = f"مصرف بودجه فاکتور {factor.number} تنخواه {tankhah.number}"
                budget_transaction = BudgetTransaction.objects.create(
                    allocation=target_allocation_instance,
                    transaction_type='CONSUMPTION',
                    amount=total_amount,
                    related_tankhah=tankhah,
                    created_by=self.request.user,
                    description=transaction_description,
                )
                logger.info(f"Wizard Done: BudgetTransaction {budget_transaction.id} created.")

            messages.success(self.request, _("فاکتور با شماره {} با موفقیت ثبت شد.").format(factor.number))
            logger.info(f"Wizard Done: Successfully created Factor {factor.number}")
            return redirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, _("خطا در ذخیره‌سازی نهایی فاکتور."))
            logger.error(f"Wizard Done: Exception during final save: {e}", exc_info=True)
            # Redirect to a safe place, maybe the first step?
            return redirect(reverse('factor_wizard')) # Or self.render_goto_step('step1')

    # get_success_url method remains the same
    def get_success_url(self):
        return reverse_lazy('factor_list')

    # handle_no_permission method remains the same
    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Wizard Permission denied for user {self.request.user}")
        return redirect(reverse_lazy('dashboard'))


class old__FactorWizardView(PermissionBaseView, SessionWizardView):
    # Permission settings
    permission_codenames = ['tankhah.a_factor_add']
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    check_organization = True # Does your PermissionBaseView handle this?

    form_list = FACTOR_FORMS
    template_name = "tankhah/Factors/wizard/factor_wizard_base.html" # A base template for the wizard structure

    # --- File Storage for Wizard ---
    # Use SessionStorage temporarily, consider FileSystemStorage for large files
    # from formtools.wizard.storage import SessionStorage # Default
    # file_storage = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'temp_wizard_files'))

    def get_template_names(self):
        # Return specific template for the current step
        return [FACTOR_TEMPLATES[self.steps.current]]

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        kwargs['user'] = self.request.user
        # Pass tankhah instance from step 1 to step 1 form for editing checks
        if step == 'step1':
             cleaned_data = self.get_cleaned_data_for_step('step1') or {}
             if 'tankhah' in cleaned_data:
                  kwargs['initial'] = {'tankhah': cleaned_data['tankhah']} # Pass for __init__
        return kwargs

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context['wizard_title'] = _('ایجاد فاکتور جدید (مرحله {} از {})').format(
            self.steps.step1, len(self.form_list)
        )
        context['step_name'] = self.steps.current

        # Add specific context for steps
        if self.steps.current == 'step1':
            # Tankhah info for budget display (populated by JS)
             context['tankhah_budget_info_url'] = reverse('tankhah_budget_info_ajax', args=[0]).replace('/0/', '/') # URL template for JS

        elif self.steps.current == 'step2':
            cleaned_data_step1 = self.get_cleaned_data_for_step('step1') or {}
            context['selected_tankhah'] = cleaned_data_step1.get('tankhah')
            context['formset'] = form # The form here *is* the formset

        elif self.steps.current == 'step3_tankhah_docs':
             cleaned_data_step1 = self.get_cleaned_data_for_step('step1') or {}
             tankhah = cleaned_data_step1.get('tankhah')
             if tankhah:
                  context['tankhah_documents'] = tankhah.documents.all() # Show existing docs

        if self.steps.current == 'step4_review':  # Or whatever you name the review step
            context['all_cleaned_data'] = self.get_all_cleaned_data()
            context['summary_total'] = self.get_summary_total()  # Add total to context
        return context


    def done(self, form_list, form_dict, **kwargs):
        """
        This method is called when all steps are completed and valid.
        Save all data here within a transaction.
        """
        step1_data = form_dict['step1'].cleaned_data
        item_formset = form_dict['step2'] # This is the validated formset instance
        factor_doc_form = form_dict['step3_docs']
        tankhah_doc_form = form_dict['step3_tankhah_docs']

        tankhah = step1_data['tankhah']

        # --- Final Budget Check ---
        # Recalculate total amount from validated formset items
        total_amount = Decimal('0.0')
        valid_items_data = []
        for form in item_formset:
             if form.is_valid() and not form.cleaned_data.get('DELETE', False):
                  amount = form.cleaned_data.get('amount', Decimal('0.0'))
                  quantity = form.cleaned_data.get('quantity', 1)
                  total_amount += (amount * quantity)
                  valid_items_data.append(form.cleaned_data) # Store data if needed later

        if not valid_items_data:
             messages.error(self.request, _("خطا: هیچ ردیف معتبری برای ذخیره یافت نشد."))
             logger.error("Wizard Done: No valid items found in formset during final save.")
             # Redirect back to step 2?
             return self.render_goto_step('step2')


        # Get the relevant allocation again for the final check
        target_allocation_instance = None
        project_allocation_amount = Decimal('0.0')
        if tankhah.project_budget_allocation:
            target_allocation_instance = tankhah.project_budget_allocation.budget_allocation
            project_allocation_amount = tankhah.project_budget_allocation.allocated_amount
        elif tankhah.budget_allocation:
            target_allocation_instance = tankhah.budget_allocation
            project_allocation_amount = target_allocation_instance.allocated_amount

        if not target_allocation_instance:
             messages.error(self.request, _("خطا: تخصیص بودجه مرتبط با تنخواه یافت نشد."))
             logger.error(f"Wizard Done: Could not find target allocation for Tankhah {tankhah.id} during final save.")
             return self.render_goto_step('step1') # Go back to step 1

        # Calculate current remaining budget *now*
        consumed_q = Q(allocation=target_allocation_instance, transaction_type='CONSUMPTION')
        returned_q = Q(allocation=target_allocation_instance, transaction_type='RETURN')
        consumption_total = BudgetTransaction.objects.filter(consumed_q).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField()))['total']
        return_total = BudgetTransaction.objects.filter(returned_q).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField()))['total']
        current_remaining_budget = project_allocation_amount - consumption_total + return_total

        if total_amount > current_remaining_budget:
            error_msg = _("مبلغ کل فاکتور ({amount1} ریال) از بودجه باقی‌مانده تخصیص ({amount2} ریال) بیشتر است. لطفاً ردیف‌ها را اصلاح کنید یا بودجه را افزایش دهید.").format(
                amount1=f"{total_amount:,.0f}", amount2=f"{current_remaining_budget:,.0f}"
            )
            messages.error(self.request, error_msg)
            logger.error(f"Wizard Done: Final budget check failed for Tankhah {tankhah.id}. Required: {total_amount}, Available: {current_remaining_budget}")
            return self.render_goto_step('step2') # Go back to item step


        # --- Save Everything Atomically ---
        try:
            with transaction.atomic():
                # 1. Create Factor instance
                factor = Factor(
                    tankhah=tankhah,
                    date=step1_data['date'],
                    description=step1_data.get('description', ''),
                    created_by=self.request.user,
                    amount=total_amount, # Set the calculated total amount
                    status='PENDING' # Set initial status after successful save
                    # Add other necessary fields if any
                )
                factor.save() # Save to get PK
                logger.info(f"Wizard Done: Factor object created with ID: {factor.pk}, Total Amount: {total_amount}")

                # 2. Save Factor Items
                # Associate formset with the saved factor instance
                item_formset.instance = factor
                item_formset.save() # This saves new/changed items and handles deletions
                logger.info(f"Wizard Done: Factor items saved for Factor ID: {factor.pk}")

                # 3. Save Factor Documents
                factor_files = factor_doc_form.cleaned_data.get('files', [])
                for file in factor_files:
                    if file: # Ensure file exists
                        FactorDocument.objects.create(factor=factor, file=file, uploaded_by=self.request.user) # Assuming uploaded_by field exists
                logger.info(f"Wizard Done: Saved {len(factor_files)} factor documents for Factor ID: {factor.pk}")

                # 4. Save Tankhah Documents (linked to Tankhah, not Factor)
                tankhah_files = tankhah_doc_form.cleaned_data.get('documents', [])
                for file in tankhah_files:
                     if file:
                         TankhahDocument.objects.create(tankhah=tankhah, document=file, uploaded_by=self.request.user)
                logger.info(f"Wizard Done: Saved {len(tankhah_files)} tankhah documents for Tankhah ID: {tankhah.id}")

                # 5. Create Budget Transaction
                transaction_description = _("مصرف بودجه برای فاکتور شماره {} مربوط به تنخواه {}").format(factor.number, tankhah.number)
                budget_transaction = BudgetTransaction.objects.create(
                    allocation=target_allocation_instance, # Link to the correct BudgetAllocation
                    transaction_type='CONSUMPTION',
                    amount=total_amount,
                    related_tankhah=tankhah, # Link to the specific Tankhah
                    created_by=self.request.user,
                    description=transaction_description,
                    # transaction_id is generated automatically if set up in model save
                )
                logger.info(f"Wizard Done: BudgetTransaction {budget_transaction.id} created for {total_amount} consumption.")

                # 6. Optional: Update Tankhah status or remaining amount if needed
                # tankhah.spent_amount = F('spent_amount') + total_amount # Be careful with F expressions
                # tankhah.save(update_fields=['spent_amount'])

            # If transaction successful
            messages.success(self.request, _("فاکتور با شماره {} با موفقیت ثبت و برای بررسی ارسال شد.").format(factor.number))
            logger.info(f"Wizard Done: Successfully created Factor {factor.number} by user {self.request.user}")
            return redirect(self.get_success_url()) # Redirect to success page

        except Exception as e:
            # Transaction rolled back automatically
            messages.error(self.request, _("خطا در ذخیره‌سازی فاکتور. لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."))
            logger.error(f"Wizard Done: Exception during final save transaction: {e}", exc_info=True)
            # Stay on the last step or redirect to a specific error page?
            # For simplicity, let's redirect to the first step with an error message
            return redirect(reverse('factor_wizard')) # Redirect to the start of the wizard

    def get_success_url(self):
         # Redirect to the factor list or detail page
         return reverse_lazy('factor_list')

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        logger.warning(f"Wizard Permission denied for user {self.request.user}")
        # Redirect to a relevant page, e.g., dashboard or login
        return redirect(reverse_lazy('dashboard')) # Adjust as needed

    # In FactorWizardView
    def get_summary_total(self):
        cleaned_data = self.get_cleaned_data_for_step('step2') or []
        total = Decimal('0.0')
        for item_data in cleaned_data:
            if item_data and not item_data.get('DELETE', False):
                amount = item_data.get('amount', Decimal('0.0'))
                quantity = item_data.get('quantity', 1)
                total += (amount * quantity)
        return total

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

