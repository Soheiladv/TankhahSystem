from django import forms
from django.core.exceptions import ValidationError

from budgets.models import BudgetAllocation


class BudgetTransferForm(forms.Form):
    source_allocation = forms.ModelChoiceField(queryset=BudgetAllocation.objects.all(), label='مبدا تخصیص')
    target_allocation = forms.ModelChoiceField(queryset=BudgetAllocation.objects.all(), label='مقصد تخصیص')
    amount = forms.DecimalField(min_value=0, decimal_places=0, label='مبلغ انتقال (ریال)')
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}), label='توضیحات')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['source_allocation'].widget.attrs.update({'class': 'form-select'})
        self.fields['target_allocation'].widget.attrs.update({'class': 'form-select'})
        self.fields['amount'].widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned = super().clean()
        src = cleaned.get('source_allocation')
        dst = cleaned.get('target_allocation')
        amt = cleaned.get('amount')
        if src and dst and src.id == dst.id:
            raise ValidationError('مبدا و مقصد نمی‌توانند یکسان باشند.')
        if src and amt is not None:
            remaining = getattr(src, 'get_remaining_amount', None)
            if callable(remaining):
                try:
                    rem = float(src.get_remaining_amount())
                except Exception:
                    rem = 0
            else:
                rem = 0
            if float(amt) > rem:
                raise ValidationError('مبلغ انتقال از مانده مجاز مبدا بیشتر است.')
        return cleaned
