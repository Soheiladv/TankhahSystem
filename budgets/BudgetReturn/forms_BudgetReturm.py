import logging
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import jdatetime
from Tanbakhsystem.utils import format_jalali_date, parse_jalali_date
from budgets.models import BudgetPeriod, SystemSettings, BudgetTransaction, BudgetAllocation
from core.templatetags.rcms_custom_filters import number_to_farsi_words

logger = logging.getLogger(__name__)


class BudgetReturnForm(forms.ModelForm):
    """ فرم برای ثبت تراکنش برگشت:"""
    class Meta:
        model = BudgetTransaction
        fields = ['allocation', 'amount', 'description']
        widgets = {
            'allocation': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 1}),
        }
        labels = {
            'allocation': _('تخصیص بودجه'),
            'amount': _('مبلغ برگشتی'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['allocation'].queryset = BudgetAllocation.objects.filter(is_active=True)
        self.instance.transaction_type = 'RETURN'
        # self.instance.created_by = kwargs.get('user')
        if user:
            self.instance.created_by = user

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        allocation = self.cleaned_data.get('allocation')
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ برگشتی باید مثبت باشد.'))
        if amount > allocation.allocated_amount:
            raise forms.ValidationError(_('مبلغ برگشتی نمی‌تواند بیشتر از تخصیص باشد.'))
        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transaction_type = 'RETURN'
        if commit:
            instance.save()
            status, message = instance.allocation.check_allocation_status()
            if status in ('warning', 'locked', 'completed', 'stopped'):
                instance.allocation.send_notification(status, message)
            # اعلان برگشت
            instance.allocation.send_notification(
                'return',
                f"مبلغ {instance.amount:,} تومان از تخصیص {instance.allocation.id} برگشت داده شد."
            )
        return instance
