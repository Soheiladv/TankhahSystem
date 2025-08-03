from django import forms
from django.forms import inlineformset_factory
from tankhah.models import Factor, FactorItem, AccessRule, Tankhah
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class FactorForm(forms.ModelForm):
    class Meta:
        model = Factor
        fields = ['tankhah', 'date', 'description', 'category', 'is_emergency']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'is_emergency': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tankhah = cleaned_data.get('tankhah')
        if tankhah:
            if tankhah.status not in ['DRAFT', 'PENDING']:
                raise forms.ValidationError(_("تنخواه انتخاب‌شده در وضعیت مجاز نیست."))
            if tankhah.due_date and tankhah.due_date.date() < timezone.now().date():
                raise forms.ValidationError(_("تنخواه منقضی شده است."))
        return cleaned_data

FactorItemFormSet = inlineformset_factory(
    Factor, FactorItem,
    fields=['description', 'quantity', 'unit_price', 'amount'],
    extra=1, can_delete=True,
    widgets={
        'description': forms.TextInput(attrs={'class': 'form-control'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
        'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
    }
)

class FactorRejectForm(forms.Form):
    rejected_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label=_("دلیل رد"),
        required=True,
        min_length=10,
        error_messages={'min_length': _("دلیل رد باید حداقل 10 کاراکتر باشد.")}
    )

class FactorTempApproveForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label=_("شرایط تأیید موقت"),
        required=True
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label=_("مهلت ارائه مدارک"),
        required=True
    )

    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date < timezone.now().date():
            raise forms.ValidationError(_("مهلت باید در آینده باشد."))
        return due_date

class FactorChangeStageForm(forms.Form):
    new_stage = forms.ModelChoiceField(
        queryset=AccessRule.objects.none(),
        label=_("مرحله جدید"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label=_("دلیل تغییر مرحله"),
        required=True
    )

    def __init__(self, factor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_stage'].queryset = AccessRule.objects.filter(
            organization=factor.tankhah.organization,
            entity_type='FACTOR',
            is_active=True
        ).order_by('stage_order')

class FactorBatchApproveForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label=_("توضیحات (اختیاری)"),
        required=False
    )