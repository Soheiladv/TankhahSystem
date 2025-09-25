# budgets/forms.py
import logging
from decimal import Decimal

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Q, F
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from budgets.models import BudgetTransaction, BudgetAllocation, Tankhah, BudgetHistory, BudgetPeriod, \
    BudgetAllocation
from tankhah.models import Factor

logger = logging.getLogger(__name__) 

# یک تابع کمکی برای نمایش بهتر مبالغ در پیام‌های خطا
def __format_currency_for_display(value):
    try:
        # اگر از فیلتر to_persian_number_with_comma استفاده می‌کنید
        from core.templatetags.rcms_custom_filters import to_persian_number_with_comma
        return to_persian_number_with_comma(value)
    except (ImportError, TypeError, ValueError):
        # فال‌بک ساده
        try:
            return f"{Decimal(value):,.0f}"
        except:
            return str(value)

# =========================================================

class BudgetTransferForm(forms.Form):
    source_allocation = forms.ModelChoiceField(
        queryset=None,
        label=_("از تخصیص پروژه مبدأ"),
        widget=forms.Select(attrs={
            'class': 'form-select select2-ajax',
            'data-url': reverse_lazy('project_allocation_api_list')
        })
    )
    destination_allocation = forms.ModelChoiceField(
        queryset=None,
        label=_("به تخصیص پروژه مقصد"),
        widget=forms.Select(attrs={
            'class': 'form-select select2-ajax',
            'data-url': reverse_lazy('project_allocation_api_list')
        })
    )
    amount = forms.DecimalField(
        label=_("مبلغ جابجایی (ریال)"),
        min_value=Decimal('0.01'),
        decimal_places=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control ltr-input',
            'placeholder': _('مبلغ به ریال')
        })
    )
    description = forms.CharField(
        label=_("توضیحات جابجایی"),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 1,
            'placeholder': _('دلیل جابجایی بودجه...')
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        from budgets.models import BudgetAllocation

        # استفاده از فیلدهای واقعی برای فیلتر، چون is_locked در property است و نمی‌توان فیلتر روی آن انجام داد
        valid_project_allocations = BudgetAllocation.objects.filter(
            is_active=True,
            is_locked=False,
            budget_period__is_active=True,
            budget_period__is_completed=False,
        ).select_related(
            'project',
            'organization',
            'budget_period',
        ).distinct()

        self.fields['source_allocation'].queryset = valid_project_allocations
        self.fields['destination_allocation'].queryset = valid_project_allocations

        logger.debug(f"BudgetTransferForm: User {user.username if user else 'Anon'}. Valid allocations count: {valid_project_allocations.count()}")

    def clean(self):
        cleaned_data = super().clean()
        source_alloc = cleaned_data.get('source_allocation')
        dest_alloc = cleaned_data.get('destination_allocation')
        amount = cleaned_data.get('amount')

        if not all([source_alloc, dest_alloc, amount]):
            return cleaned_data

        if source_alloc == dest_alloc:
            raise ValidationError(_("تخصیص مبدأ و مقصد نمی‌توانند یکسان باشند."))

        # چک کردن وضعیت قفل به صورت property (tuple) روی مدل مرتبط
        if source_alloc.budget_period.is_locked[0]:
            raise ValidationError(_("تخصیص پروژه مبدأ یا بودجه‌های والد آن برای انتقال قفل شده است."))

        if dest_alloc.budget_period.is_locked[0]:
            raise ValidationError(_("تخصیص پروژه مقصد یا بودجه‌های والد آن برای دریافت انتقال قفل شده است."))

        if source_alloc.budget_period_id != dest_alloc.budget_period_id:
            raise ValidationError(_("جابجایی بودجه فقط بین تخصیص‌های یک دوره بودجه امکان‌پذیر است."))

        if not hasattr(source_alloc, 'get_remaining_amount') or not callable(source_alloc.get_remaining_amount):
            logger.error(f"Method 'get_remaining_amount' missing or not callable on BudgetAllocation {source_alloc.pk}")
            raise ValidationError(_("خطای سیستمی: امکان محاسبه باقیمانده مبدأ وجود ندارد."))

        remaining = source_alloc.get_remaining_amount()
        if amount > remaining:
            raise ValidationError(
                _("مبلغ جابجایی ({}) از بودجه باقیمانده تخصیص مبدأ ({}) بیشتر است.").format(
                    format_currency_for_display(amount),
                    format_currency_for_display(remaining)
                )
            )
        return cleaned_data

    def execute_transfer(self):
        from budgets.models import BudgetTransaction, BudgetHistory
        user = self.user
        source_alloc = self.cleaned_data['source_allocation']
        dest_alloc = self.cleaned_data['destination_allocation']
        amount = self.cleaned_data['amount']
        description = self.cleaned_data.get('description', '')

        transfer_id = f"TRNSFR-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"

        with transaction.atomic():
            logger.info(f"Transfer: Creating RETURN Tx from BudgetAllocation {source_alloc.pk} for amount {amount}")
            return_tx = BudgetTransaction.objects.create(
                allocation=source_alloc,
                transaction_type='RETURN',
                amount=amount,
                description=_("بازگشت جهت جابجایی به تخصیص پروژه {} ({}). {}").format(dest_alloc.project.name, dest_alloc.pk, description),
                created_by=user,
                transaction_id=f"{transfer_id}-RET-{source_alloc.pk}"
            )

            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(source_alloc),
                object_id=source_alloc.pk,
                action='REALLOCATE_OUT',
                amount=amount,
                created_by=user,
                details=_("جابجایی مبلغ {:,} ریال از {} به {}").format(amount, source_alloc, dest_alloc),
                transaction_id=return_tx.transaction_id
            )

            logger.info(f"Transfer: Creating ADJUSTMENT_INCREASE Tx to BudgetAllocation {dest_alloc.pk} for amount {amount}")
            alloc_tx = BudgetTransaction.objects.create(
                allocation=dest_alloc,
                transaction_type='ADJUSTMENT_INCREASE',
                amount=amount,
                description=_("افزایش جهت جابجایی از تخصیص پروژه {} ({}). {}").format(source_alloc.project.name, source_alloc.pk, description),
                created_by=user,
                transaction_id=f"{transfer_id}-ADD-{dest_alloc.pk}"
            )

            dest_alloc.allocated_amount = F('allocated_amount') + amount
            dest_alloc.save(update_fields=['allocated_amount'], skip_status_update=True)
            dest_alloc.refresh_from_db()

            logger.info(f"Transfer: Destination BudgetAllocation {dest_alloc.pk} allocated_amount updated.")

            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(dest_alloc),
                object_id=dest_alloc.pk,
                action='REALLOCATE_IN',
                amount=amount,
                created_by=user,
                details=_("دریافت مبلغ {:,} ریال از {} به {}").format(amount, source_alloc, dest_alloc),
                transaction_id=alloc_tx.transaction_id
            )

        logger.info(f"Budget transfer executed by {user.username}: {amount} from {source_alloc.pk} to {dest_alloc.pk}")

        return return_tx, alloc_tx

# تابع کمکی برای فرمت ارز
def format_currency_for_display(value):
    try:
        return "{:,.0f}".format(value)
    except Exception:
        return str(value)


# =========================================================


class BudgetReturnForm(forms.Form):
    allocation = forms.ModelChoiceField(
        queryset=BudgetAllocation.objects.all(),
        label=_("تخصیص بودجه"),
        widget=forms.HiddenInput()
    )
    amount = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        label=_("مبلغ برگشتی"),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ (ریال)')})
    )
    description = forms.CharField(
        required=False,
        label=_("توضیحات"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات (اختیاری)')})
    )

    def __init__(self, *args, user=None, allocation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.allocation = allocation
        if allocation:
            self.fields['allocation'].initial = allocation
            self.fields['allocation'].queryset = BudgetAllocation.objects.filter(
                pk=allocation)

    def clean(self):
        cleaned_data = super().clean()
        allocation = cleaned_data.get('allocation')
        amount = cleaned_data.get('amount')

        if not allocation or not amount:
            raise forms.ValidationError(_('تمام فیلدها الزامی هستند.'))

        # بررسی قفل بودن تخصیص یا دوره
        if allocation.budget_allocation.is_locked or allocation.budget_allocation.budget_period.is_locked:
            raise forms.ValidationError(_('تخصیص یا دوره بودجه قفل شده است.'))

        # بررسی بودجه آزاد
        free_budget = self.get_free_budget(allocation)
        if amount > free_budget:
            raise forms.ValidationError(
                _(f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه آزاد ({free_budget:,.0f} ریال) باشد.")
            )

        return cleaned_data

    def get_free_budget(self, allocation):
        cache_key = f"free_budget_{allocation.pk}"
        free_budget = cache.get(cache_key)
        if free_budget is None:
            transactions = BudgetTransaction.objects.filter(
                allocation=allocation.budget_allocation,
                project=allocation.project
            ).aggregate(
                consumed=Sum('amount', filter=Q(transaction_type='CONSUMPTION')),
                returned=Sum('amount', filter=Q(transaction_type='RETURN'))
            )
            consumed = transactions['consumed'] or Decimal('0')
            returned = transactions['returned'] or Decimal('0')

            # وضعیت‌ها کُدی هستند (Status.code). فیلتر بر اساس code
            tankhah_consumed = Tankhah.objects.filter(
                project_budget_allocation=allocation,
                status__code__in=['APPROVED', 'PAID']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            factor_consumed = Factor.objects.filter(
                tankhah__project_budget_allocation=allocation,
                status__code='PAID'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            free_budget = allocation.allocated_amount - consumed + returned - tankhah_consumed - factor_consumed
            cache.set(cache_key, free_budget, timeout=300)
        return free_budget

    def save(self):
        from django.utils import timezone
        allocation = self.cleaned_data['allocation']
        amount = self.cleaned_data['amount']
        description = self.cleaned_data['description']
        transaction_id = f"RET-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"

        from django.db import transaction
        with transaction.atomic():
            transaction = BudgetTransaction.objects.create(
                allocation=allocation.budget_allocation,
                project=allocation.project,
                transaction_type='RETURN',
                amount=amount,
                description=description or f"برگشت بودجه از پروژه {allocation.project.name}",
                created_by=self.user,
                transaction_id=transaction_id
            )
            allocation.returned_amount = (allocation.returned_amount or Decimal('0')) + amount
            allocation.allocated_amount -= amount
            allocation.budget_allocation.returned_amount = (
                allocation.budget_allocation.returned_amount or Decimal('0')
            ) + amount
            allocation.budget_allocation.allocated_amount -= amount
            allocation.budget_allocation.budget_period.returned_amount = (
                allocation.budget_allocation.budget_period.returned_amount or Decimal('0')
            ) + amount
            allocation.budget_allocation.budget_period.total_allocated -= amount
            allocation.save(update_fields=['returned_amount', 'allocated_amount'])
            allocation.budget_allocation.save(update_fields=['returned_amount', 'allocated_amount'])
            allocation.budget_allocation.budget_period.save(update_fields=['returned_amount', 'total_allocated'])

            from budgets.models import BudgetHistory
            from django.contrib.contenttypes.models import ContentType
            BudgetHistory.objects.create(
                content_type=ContentType.objects.get_for_model(BudgetAllocation),
                object_id=allocation.id,
                action='RETURN',
                amount=amount,
                created_by=self.user,
                details=description or f"برگشت بودجه از پروژه {allocation.project.name}",
                transaction_type='RETURN',
                transaction_id=transaction_id
            )

            from budgets.budget_calculations import check_budget_status
            status, message = check_budget_status(allocation.budget_allocation.budget_period)
            if status in ('warning', 'locked', 'completed', 'stopped'):
                allocation.budget_allocation.send_notification(status, message)
            allocation.budget_allocation.send_notification(
                'return',
                f"مبلغ {amount:,.0f} ریال از پروژه {allocation.project.name} برگشت داده شد."
            )

        return transaction

