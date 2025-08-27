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
from core.models import AccessRule, Post, Status, Transition, Project, Organization
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
# ===== CONFIGURATION & CONSTANTS =====
# FactorItemFormSet = inlineformset_factory(
#     Factor,
#     FactorItem,
#     fields=['quantity', 'unit_price', 'description'],
#     extra=1,
#     can_delete=True,
#     min_num=1,
#     validate_min=True
# )
FactorItemFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemForm,
    extra=1,
    can_delete=True,
    min_num=1,  # حداقل یک ردیف الزامی است
    validate_min=True
)

# ===== UTILITY FUNCTIONS =====
def calculate_total_from_formset(item_formset):
    total_amount = Decimal('0')
    for item_form in item_formset:
        if item_form.is_valid() and item_form.has_changed() and not item_form.cleaned_data.get('DELETE'):
            quantity = item_form.cleaned_data.get('quantity', 0)
            unit_price = item_form.cleaned_data.get('unit_price', 0)
            total_amount += (quantity * unit_price)
    return total_amount

def has_permission_to_create(self, user, tankhah):
    logger.debug(f"بررسی مجوزهای ایجاد برای کاربر '{user.username}' در تنخواه '{tankhah.number}'")
    if not user.has_perm('tankhah.factor_add'):
        logger.warning("کاربر فاقد مجوز 'tankhah.factor_add' است")
        messages.error(self.request, _('شما مجوز اولیه برای افزودن فاکتور را ندارید.'))
        return False

    user_post_qs = user.userpost_set.filter(is_active=True)
    if not user_post_qs.exists():
        logger.warning("کاربر پست فعال ندارد")
        messages.error(self.request, _("شما برای ثبت فاکتور باید یک پست سازمانی فعال داشته باشید."))
        return False

    if user.is_superuser:
        logger.debug("کاربر سوپریوزر است")
        return True

    target_org = tankhah.organization
    target_project_orgs = set(tankhah.project.organizations.filter(is_core=False, is_holding=False)) if tankhah.project else set()
    user_orgs = set()
    for up in user_post_qs.select_related('post__organization'):
        org = up.post.organization
        if org and isinstance(org, Organization) and not org.is_core and not org.is_holding:
            user_orgs.add(org)
            logger.debug(f"[has_permission_to_create] سازمان شعبه‌ای اضافه شد: {org.name} (کد: {org.code})")

    if not user_orgs:
        logger.warning(f"هیچ سازمان شعبه‌ای برای کاربر '{user.username}' یافت نشد")
        messages.error(self.request, _("شما به هیچ شعبه‌ای دسترسی ندارید. لطفاً با مدیر سیستم تماس بگیرید."))
        return False

    if target_org not in user_orgs or (target_project_orgs and not target_project_orgs.issubset(user_orgs)):
        logger.warning(f"کاربر به سازمان '{target_org.name}' یا سازمان‌های پروژه '{[org.name for org in target_project_orgs]}' دسترسی ندارد")
        messages.error(self.request, _('شما به سازمان این تنخواه یا سازمان‌های پروژه آن دسترسی ندارید.'))
        return False

    logger.debug("مجوز ایجاد تأیید شد")
    return True

def create_related_objects_and_notify(factor, user, tankhah, initial_stage, document_form):
    logger.debug("ایجاد اشیاء مرتبط و ارسال اعلان‌ها")
    if document_form.is_valid():
        files = document_form.cleaned_data.get('files', [])
        for file in files:
            FactorDocument.objects.create(factor=factor, file=file, uploaded_by=user)
        logger.info(f"{len(files)} فایل برای فاکتور {factor.pk} ذخیره شد")

    user_post = user.userpost_set.filter(is_active=True).first()
    ApprovalLog.objects.create(
        factor=factor,
        user=user,
        post=user_post.post if user_post else None,
        action="CREATED",
        stage_rule=initial_stage,
        comment=f"فاکتور {factor.number} توسط {user.username} ایجاد شد."
    )
    FactorHistory.objects.create(
        factor=factor,
        change_type=FactorHistory.ChangeType.CREATION,
        changed_by=user,
        description=f"فاکتور ایجاد شد."
    )
    logger.info(f"ApprovalLog و FactorHistory برای فاکتور {factor.pk} ایجاد شد")

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
        logger.info(f"اعلان به {len(approver_posts_ids)} پست برای تأیید اولیه فاکتور {factor.pk} ارسال شد")

# ===== CORE BUSINESS LOGIC =====
class New_FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/Factors/NF/new_factor_form.html'
    permission_codenames = ['tankhah.factor_add']
    permission_denied_message = _('شما دسترسی لازم برای ویرایش فاکتورها را ندارید.')
    check_organization = True

    def get_success_url(self):
        logger.debug("عملیات موفق، هدایت به factor_list")
        return reverse_lazy('factor_list')

    def get_form_kwargs(self):
        logger.debug("آماده‌سازی kwargs برای FactorForm")
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user

        tankhah_id = self.kwargs.get('tankhah_id') or self.request.GET.get('tankhah_id')
        if tankhah_id:
            logger.info(f"پر کردن فرم با تنخواه ID: {tankhah_id}")
            try:
                tankhah = Tankhah.objects.get(id=tankhah_id)
                if not isinstance(tankhah.project, Project):
                    logger.error(f"پروژه نامعتبر برای تنخواه {tankhah_id}: {tankhah.project}")
                    messages.error(self.request, _("پروژه مرتبط با تنخواه نامعتبر است. لطفاً با مدیر سیستم تماس بگیرید."))
                    return kwargs
                if tankhah.due_date < timezone.now():
                    logger.warning(f"تنخواه {tankhah_id} منقضی شده است")
                    messages.error(self.request, _("تنخواه انتخاب شده منقضی شده است و نمی‌توان برای آن فاکتور ثبت کرد."))
                else:
                    kwargs['initial'] = kwargs.get('initial', {})
                    kwargs['initial']['tankhah'] = tankhah
            except Tankhah.DoesNotExist:
                messages.error(self.request, _("تنخواه انتخاب شده معتبر نیست."))
                logger.warning(f"تنخواه با ID {tankhah_id} یافت نشد")
        return kwargs

    def get_context_data(self, **kwargs):
        logger.debug("آماده‌سازی داده‌های context برای قالب")
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = FactorItemFormSet(self.request.POST, prefix='items')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES, prefix='docs')
        else:
            context['formset'] = FactorItemFormSet(prefix='items')
            context['document_form'] = FactorDocumentForm(prefix='docs')
        return context

    def form_valid(self, form):
        user = self.request.user
        tankhah = form.cleaned_data.get('tankhah')
        logger.info(f"شروع form_valid برای کاربر '{user.username}' و تنخواه '{tankhah.number}'")

        if not isinstance(tankhah.project, Project):
            logger.error(f"پروژه نامعتبر برای تنخواه {tankhah.number}: {tankhah.project}")
            messages.error(self.request, _("پروژه مرتبط با تنخواه نامعتبر است. لطفاً با مدیر سیستم تماس بگیرید."))
            return self.form_invalid(form)

        if tankhah.due_date < timezone.now():
            logger.warning(f"تنخواه {tankhah.number} منقضی شده است: {tankhah.due_date}")
            messages.error(self.request, _("تنخواه انتخاب شده منقضی شده است و نمی‌توان برای آن فاکتور ثبت کرد."))
            return self.form_invalid(form)

        context = self.get_context_data()
        item_formset = context['formset']
        document_form = context['document_form']

        if not has_permission_to_create(self, user, tankhah):
            logger.warning(f"کاربر '{user.username}' مجوز ایجاد فاکتور را ندارد")
            return self.form_invalid(form)

        if not item_formset.is_valid():
            logger.warning(f"فرم‌ست آیتم‌ها نامعتبر است. خطاها: {item_formset.errors}")
            messages.error(self.request, _('لطفاً خطاهای ردیف‌های فاکتور را اصلاح کنید.'))
            return self.form_invalid(form)

        total_items_amount = calculate_total_from_formset(item_formset)
        logger.info(f"مجموع مبلغ آیتم‌ها: {total_items_amount}")

        if total_items_amount <= 0:
            messages.error(self.request, _('فاکتور باید حداقل یک ردیف با مبلغ معتبر داشته باشد.'))
            return self.form_invalid(form)

        available_budget = Decimal(get_tankhah_available_budget(tankhah))
        logger.info(f"مبلغ فاکتور: {total_items_amount}, بودجه در دسترس تنخواه: {available_budget}")
        if total_items_amount > available_budget:
            error_msg = _('مبلغ فاکتور ({:,.0f} ریال) از بودجه در دسترس تنخواه ({:,.0f} ریال) بیشتر است.').format(
                total_items_amount, available_budget)
            messages.error(self.request, error_msg)
            logger.warning(f"خطای اعتبارسنجی: {error_msg}")
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                logger.debug("شروع تراکنش")
                draft_status = Status.objects.get(code='DRAFT', is_initial=True)

                self.object = form.save(commit=False)
                self.object.created_by = user
                self.object.status = draft_status
                self.object.amount = total_items_amount
                self.object.save()
                logger.info(f"فاکتور {self.object.pk} با وضعیت DRAFT ذخیره شد")

                item_formset.instance = self.object
                item_formset.save()
                logger.info(f"{len([f for f in item_formset if f.is_valid() and f.has_changed() and not f.cleaned_data.get('DELETE')])} آیتم ذخیره شد")

                if document_form.is_valid():
                    files = document_form.cleaned_data.get('files', [])
                    for file in files:
                        FactorDocument.objects.create(factor=self.object, file=file, uploaded_by=user)
                    logger.info(f"{len(files)} فایل ذخیره شد")

                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.CREATION,
                    changed_by=user,
                    description=f"فاکتور به شماره {self.object.number} توسط {user.username} ایجاد شد."
                )

                logger.debug("اتمام تراکنش")
                messages.success(self.request, _('فاکتور با موفقیت ثبت شد.'))
                return redirect(self.get_success_url())

        except Status.DoesNotExist:
            logger.critical("خطای تنظیمات: وضعیت اولیه DRAFT یافت نشد")
            messages.error(self.request, _("خطای حیاتی در پیکربندی سیستم. لطفاً با مدیر تماس بگیرید."))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"خطا در تراکنش: {str(e)}", exc_info=True)
            messages.error(self.request, _('خطای پیش‌بینی نشده در ذخیره اطلاعات.'))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.warning(f"فرم نامعتبر برای کاربر '{self.request.user.username}'. خطاها: {form.errors.as_json()}")
        messages.error(self.request, _('ثبت فاکتور با خطا مواجه شد. لطفاً موارد مشخص شده را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))