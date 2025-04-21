import logging
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import jdatetime
from Tanbakhsystem.utils import format_jalali_date, parse_jalali_date
from budgets.budget_calculations import get_project_remaining_budget, check_budget_status
from budgets.models import BudgetPeriod, SystemSettings, BudgetTransaction, BudgetAllocation
from core.templatetags.rcms_custom_filters import number_to_farsi_words
logger = logging.getLogger(__name__)

# budgets/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from decimal import Decimal

class BudgetReturnForm(forms.ModelForm):
    class Meta:
        model = BudgetTransaction
        fields = ['amount', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'مبلغ (ریال)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات'}),
        }
        labels = {
            'amount': _('مبلغ برگشتی'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.allocation = kwargs.pop('allocation', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.allocation:
            self.instance.allocation = self.allocation.budget_allocation
        if self.user:
            self.instance.created_by = self.user
        self.instance.transaction_type = 'RETURN'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if not amount:
            raise forms.ValidationError(_('مبلغ برگشتی الزامی است.'))
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ برگشتی باید مثبت باشد.'))

        if self.allocation:
            # محاسبه مصرف خالص
            consumed = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                allocation__project=self.allocation.project,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation=self.allocation.budget_allocation,
                allocation__project=self.allocation.project,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            total_consumed = consumed - returned

            # بررسی سقف بازگشت
            if amount > total_consumed:
                raise forms.ValidationError(
                    _(f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف خالص ({total_consumed:,.0f} ریال) باشد.")
                )

            # بررسی بودجه باقی‌مانده پروژه
            remaining_budget = get_project_remaining_budget(self.allocation.project)
            if amount > remaining_budget:
                raise forms.ValidationError(
                    _(f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده پروژه ({remaining_budget:,.0f} ریال) باشد.")
                )

        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transaction_type = 'RETURN'
        if commit:
            instance.save()
            # بررسی وضعیت بودجه و ارسال اعلان
            status, message = check_budget_status(instance.allocation.budget_period)
            if status in ('warning', 'locked', 'completed', 'stopped'):
                instance.allocation.send_notification(status, message)
            instance.allocation.send_notification(
                'return',
                f"مبلغ {instance.amount:,.0f} ریال از تخصیص {instance.allocation.id} برگشت داده شد."
            )
        return instance