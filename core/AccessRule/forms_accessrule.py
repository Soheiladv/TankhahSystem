# core/forms.py
from django import forms
from core.models import AccessRule
from django.utils.translation import gettext_lazy as _

class AccessRuleForm(forms.ModelForm):
    class Meta:
        model = AccessRule
        fields = [
            'organization', 'branch', 'min_level', 'stage', 'action_type',
            'entity_type', 'is_payment_order_signer', 'is_active'
        ]
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'min_level': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'entity_type': forms.Select(attrs={'class': 'form-control'}),
            'is_payment_order_signer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'organization': _('سازمان'),
            'branch': _('شاخه'),
            'min_level': _('حداقل سطح'),
            'stage': _('مرحله'),
            'action_type': _('نوع اقدام'),
            'entity_type': _('نوع موجودیت'),
            'is_payment_order_signer': _('امضاکننده دستور پرداخت'),
            'is_active': _('فعال'),
        }

    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        is_payment_order_signer = cleaned_data.get('is_payment_order_signer')
        action_type = cleaned_data.get('action_type')

        # اعتبارسنجی: اگر is_payment_order_signer=True، entity_type باید PAYMENTORDER باشد
        if is_payment_order_signer and entity_type != 'PAYMENTORDER':
            self.add_error('entity_type', _('برای امضاکننده دستور پرداخت، نوع موجودیت باید PAYMENTORDER باشد.'))
        # اعتبارسنجی: SIGN_PAYMENT فقط برای PAYMENTORDER
        if action_type == 'SIGN_PAYMENT' and entity_type != 'PAYMENTORDER':
            self.add_error('action_type', _('اقدام SIGN_PAYMENT فقط برای نوع موجودیت PAYMENTORDER مجاز است.'))
        return cleaned_data