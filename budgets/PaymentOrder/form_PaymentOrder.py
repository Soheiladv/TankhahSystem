# tankhah/forms.py
from django import forms
from django.db import transaction

from budgets.models import Payee, PaymentOrder
from core.models import Organization, WorkflowStage
from tankhah.models import Tankhah, Factor

from django.utils.translation import gettext_lazy as _

# budgets/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from budgets.models import PaymentOrder, Payee
from tankhah.models import Tankhah, Factor
from core.models import Organization, WorkflowStage
from accounts.models import CustomUser
import jdatetime
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)
class PaymentOrderForm(forms.ModelForm):
    pass
    # payee = forms.ModelChoiceField(
    #     queryset=Payee.objects.filter(is_active=True).order_by('name'),
    #     label=_('دریافت‌کننده'), widget=forms.Select(attrs={'class': 'form-select'})
    # )
    # tankhah = forms.ModelChoiceField(
    #     queryset=Tankhah.objects.filter(status__in=['APPROVED', 'PAID']),
    #     label=_('تنخواه'), widget=forms.Select(attrs={'class': 'form-select'})
    # )
    # related_tankhah = forms.ModelChoiceField(
    #     queryset=Tankhah.objects.filter(status__in=['APPROVED', 'PAID']),
    #     label=_('تنخواه مرتبط'), required=False, widget=forms.Select(attrs={'class': 'form-select'})
    # )
    # related_factors = forms.ModelMultipleChoiceField(
    #     queryset=Factor.objects.filter(status='APPROVED'),
    #     label=_('فاکتورهای مرتبط'), required=False,
    #     widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    # )
    # organization = forms.ModelChoiceField(
    #     queryset=Organization.objects.filter(is_active=True),
    #     label=_('سازمان'), widget=forms.Select(attrs={'class': 'form-select'})
    # )
    #
    # issue_date = forms.CharField(
    #     label=_('تاریخ صدور'),
    #     widget=forms.TextInput(attrs={
    #         'data-jdp': '',
    #         'class': 'form-control',
    #         'placeholder': _('تاریخ را انتخاب کنید (1404/01/17)')
    #     })
    # )
    # class Meta:
    #     model = PaymentOrder
    #     fields = [
    #          'payee', 'amount', 'description', 'payee_account_number', 'payee_iban',
    #         'related_tankhah', 'related_factors', 'organization', 'notes', 'issue_date',
    #         'min_signatures', 'current_stage'
    #     ]#'tankhah',
    #     widgets = {
    #         'amount': forms.NumberInput(attrs={'class': 'form-control'}),
    #         'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    #         'payee_account_number': forms.TextInput(attrs={'class': 'form-control'}),
    #         'payee_iban': forms.TextInput(attrs={'class': 'form-control'}),
    #         'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
    #         'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    #         'min_signatures': forms.NumberInput(attrs={'class': 'form-control'}),
    #         'current_stage': forms.Select(attrs={'class': 'form-select'}),
    #         'order_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
    #         # معمولا فقط خواندنی
    #         'payment_tracking_id': forms.TextInput(attrs={'class': 'form-control'}),
    #         'payment_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
    #         # اگر DateTimeField است
    #         'paid_by': forms.Select(attrs={'class': 'form-select'}),
    #         'status': forms.Select(attrs={'class': 'form-select'}),
    #         'is_locked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    #
    #     }
    #
    # def __init__(self, *args, user=None, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.user = user
    #     if user and not user.is_superuser:
    #         self.fields['organization'].queryset = Organization.objects.filter(
    #             userpost__user=user, userpost__is_active=True
    #         ).distinct()
    #         self.fields['tankhah'].queryset = Tankhah.objects.filter(
    #             organization__in=self.fields['organization'].queryset,
    #             status__in=['APPROVED', 'PAID']
    #         )
    #         self.fields['related_tankhah'].queryset = Tankhah.objects.filter(
    #             organization__in=self.fields['organization'].queryset,
    #             status__in=['APPROVED', 'PAID']
    #         )
    #     if 'organization' in self.fields and self.user and not self.user.is_superuser:
    #         # این منطق نیاز به UserPost دارد و باید مطمئن شوید کار می‌کند
    #         # user_organizations = Organization.objects.filter(
    #         #    post__userpost__user=self.user, post__userpost__is_active=True
    #         # ).distinct()
    #         # self.fields['organization'].queryset = user_organizations
    #         pass # فعلا غیرفعال برای جلوگیری از خطای احتمالی دیگر
    #
    #     if self.instance and self.instance.pk and self.instance.issue_date:
    #         if isinstance(self.fields['issue_date'].widget, forms.TextInput): # اگر ویجت متنی است (برای تقویم شمسی)
    #             try:
    #                 # تبدیل تاریخ میلادی به شمسی برای نمایش اولیه
    #                 j_date_display = jdatetime.date.fromgregorian(date=self.instance.issue_date)
    #                 self.initial['issue_date'] = j_date_display.strftime('%Y/%m/%d')
    #             except Exception as e:
    #                 logger.warning(f"Could not convert issue_date to Jalali for display: {e}")
    #
    #     # مقداردهی اولیه فیلد payment_date اگر از نوع DateTimeField است
    #     if self.instance and self.instance.pk and self.instance.payment_date:
    #         if isinstance(self.fields['issue_date'].widget, forms.DateTimeInput):
    #             # فرمت باید با type='datetime-local' سازگار باشد: YYYY-MM-DDTHH:MM
    #              self.initial['issue_date'] = self.instance.payment_date.strftime('%Y-%m-%dT%H:%M')
    #
    # def clean_amount(self):
    #     amount = self.cleaned_data.get('amount')
    #     if amount <= 0:
    #         raise forms.ValidationError(_('مبلغ باید مثبت باشد.'))
    #     return amount
    #
    # def clean_issue_date(self):
    #     date_str = self.cleaned_data.get('issue_date')
    #     if not date_str:
    #         raise forms.ValidationError(_('تاریخ صدور اجباری است.'))
    #     try:
    #         j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
    #         gregorian_date = j_date.togregorian()
    #         return timezone.make_aware(gregorian_date)
    #     except ValueError:
    #         raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
    #
    # def clean(self):
    #     cleaned_data = super().clean()
    #     tankhah = cleaned_data.get('tankhah')
    #     organization = cleaned_data.get('organization')
    #     if tankhah and organization and tankhah.organization != organization:
    #         raise forms.ValidationError(_('تنخواه انتخاب‌شده با سازمان سازگار نیست.'))
    #     return cleaned_data
    #
    # def clean_min_signatures(self):
    #     min_signatures = self.cleaned_data.get('min_signatures')
    #     if min_signatures < 1:
    #         raise forms.ValidationError(_('حداقل تعداد امضا باید ۱ یا بیشتر باشد.'))
    #     return min_signatures
    #
    #
    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     if not instance.pk and self.user:
    #         instance.created_by = self.user
    #         if not instance.current_stage:
    #             instance.current_stage = WorkflowStage.objects.filter(
    #                 entity_type='PAYMENTORDER', order=1
    #             ).first()
    #     if commit:
    #         with transaction.atomic():
    #             instance.save()
    #             instance.related_factors.set(self.cleaned_data.get('related_factors', []))
    #             self.save_m2m()
    #     return instance