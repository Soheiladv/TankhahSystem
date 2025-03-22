from django.forms import inlineformset_factory

from Tanbakhsystem.utils import convert_to_farsi_numbers, convert_jalali_to_gregorian, convert_gregorian_to_jalali
from .models import Factor, ApprovalLog, FactorDocument
from .models import FactorItem

FactorItemFormSet = inlineformset_factory(Factor, FactorItem, fields=['description', 'amount', 'quantity'], extra=1)

from django.forms import inlineformset_factory
from .models import Factor, FactorItem

from .models import Tanbakh
from django import forms
from django.utils.translation import gettext_lazy as _

import logging

logger = logging.getLogger(__name__)


class TanbakhForm(forms.ModelForm):
    """فرم ایجاد و ویرایش تنخواه"""
    comment = forms.CharField(widget=forms.Textarea, required=False, label=_("توضیحات"))

    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    due_date = forms.CharField(
            label=_('فرصت باقی مانده'),
            widget=forms.TextInput(attrs={
                'data-jdp': '',
                'class': 'form-control',
                'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
            })
        )

    class Meta:
        model = Tanbakh  # مدل مشخص شده
        fields = ['date', 'organization', 'project', 'status', 'hq_status', 'last_stopped_post', 'letter_number',
                  'number','due_date', 'current_stage',                    'amount', 'description']

        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'hq_status': forms.Select(attrs={'class': 'form-control'}),
            'last_stopped_post': forms.Select(attrs={'class': 'form-control'}),
            'approved_by': forms.Select(attrs={'class': 'form-control'}),
            'number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره تنخواه'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'due_date': forms.DateInput(attrs={'class': 'persian-date'}),
        }
        labels = {
            'date': _('تاریخ'),
            'organization': _('مجتمع'),
            'project': _('پروژه'),
            'status': _('وضعیت'),
            'hq_status': _('وضعیت در HQ'),
            'last_stopped_post': _('آخرین پست متوقف‌شده'),
            'letter_number': _('شماره نامه'),
            'approved_by': _('تأییدکننده'),
            'number': _('شماره تنخواه'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            user_posts = self.user.userpost_set.all()
            if not any(post.post.organization == self.instance.organization for post in user_posts):
                for field_name in self.fields:
                    if field_name != 'status' and field_name != 'comment':
                        self.fields[field_name].disabled = True
        if self.instance.pk:
            self.fields['date'].initial = convert_gregorian_to_jalali(self.instance.date)
            self.fields['number'].initial = convert_to_farsi_numbers(self.instance.number)
            self.fields['amount'].initial = convert_to_farsi_numbers(self.instance.amount)

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        return convert_jalali_to_gregorian(date_str) if date_str else None

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            user_post = self.user.userpost_set.filter(post__organization=instance.organization).first()
            if not instance.pk:
                instance.created_by = self.user
                instance.last_stopped_post = user_post.post if user_post else None
            if self.has_changed() and 'status' in self.changed_data:
                old_status = Tanbakh.objects.get(pk=instance.pk).status if instance.pk else 'DRAFT'
                new_status = self.cleaned_data['status']
                action = 'APPROVE' if new_status != 'REJECTED' else 'REJECT'
                ApprovalLog.objects.create(
                    tanbakh=instance,
                    action=action,
                    user=self.user,
                    comment=self.cleaned_data['comment'],
                    post=user_post.post if user_post else None
                )
                if new_status == 'SENT_TO_HQ':
                    instance.current_stage = 'OPS'
                elif new_status == 'HQ_OPS_APPROVED':
                    instance.current_stage = 'FIN'
        if commit:
            instance.save()
        return instance


class FactorForm(forms.ModelForm):
    """فرم ایجاد و ویرایش فاکتور"""
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Factor
        fields = ['tanbakh', 'date', 'amount', 'description']  # status حذف شده
        widgets = {
            'tanbakh': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ را وارد کنید')}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات فاکتور')}),
            # 'file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'tanbakh': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
            # 'file': _('فایل پیوست'),
        }

    def clean_date(self):
        """تبدیل تاریخ شمسی به میلادی هنگام اعتبارسنجی فرم"""
        date_str = self.cleaned_data.get('date')
        return convert_jalali_to_gregorian(date_str) if date_str else None

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # استخراج user از kwargs و حذف آن
        super().__init__(*args, **kwargs)  # فراخوانی super بعد از حذف user
        if self.instance.pk:
            self.fields['date'].initial = convert_gregorian_to_jalali(self.instance.date)
            self.fields['amount'].initial = convert_to_farsi_numbers(self.instance.amount)
        if self.user and not self.user.has_perm('Factor_full_edit'):
            for field_name in self.fields:
                if field_name != 'status':
                    self.fields[field_name].disabled = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and self.instance.pk and self.has_changed():
            old_instance = Factor.objects.get(pk=self.instance.pk)
            for field in self.changed_data:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                logger.info(
                    f"تغییر در فاکتور {instance.number}: {field} از {old_value} به {new_value} توسط {self.user}")
            if 'status' in self.changed_data:
                instance.approved_by = self.user  # ثبت تأییدکننده
        if commit:
            instance.save()
        return instance


class FactorItemForm(forms.ModelForm):
    """فرم ایجاد و ویرایش اقلام فاکتور"""

    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('شرح ردیف')}),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control amount-field', 'placeholder': _('مبلغ'), 'step': '0.01'}),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        return amount

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 1:
            raise forms.ValidationError(_('تعداد باید حداقل ۱ باشد.'))
        return quantity




class ApprovalForm(forms.ModelForm):
    """فرم ثبت تأیید یا رد"""

    class Meta:
        model = ApprovalLog
        fields = ['tanbakh', 'factor', 'comment', 'action']  # user و date توسط سیستم پر می‌شوند
        widgets = {
            'tanbakh': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
            'action': forms.Select(attrs={'class': 'form-control'}),
            # 'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tanbakh': _('تنخواه'),
            'factor': _('فاکتور'),
            'comment': _('توضیحات'),
            'action': _('شاخه'),
            # 'is_approved': _('تأیید شده؟'),
        }

# فرم‌ست برای اقلام فاکتور
FactorItemFormSet = inlineformset_factory(
    Factor,  # مدل والد (فاکتور)
    FactorItem,  # مدل فرزند (اقلام فاکتور)
    form=FactorItemForm,  # فرم تعریف‌شده بالا
    fields=['description', 'amount', 'quantity'],
    extra=1,  # تعداد فرم‌های خالی پیش‌فرض
    can_delete=True  # امکان حذف ردیف‌ها
)

from django.forms import inlineformset_factory

FactorDocumentFormSet = inlineformset_factory(
    Factor,
    FactorDocument,
    fields=['file'],
    extra=1,  # تعداد فرم‌های خالی اولیه
    can_delete=True,
    widgets={
        'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
    },
    labels={
        'file': _('فایل پیوست'),
    }
)
