# core/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Branch

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['code', 'name', 'is_active']
        labels = {
            'code': _("کد شاخه"),
            'name': _("نام شاخه"),
            'is_active': _("وضعیت فعال"),
        }
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("کد منحصر به فرد شاخه")}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _("نام کامل شاخه")}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }