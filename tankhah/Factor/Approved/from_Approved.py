from django import forms
from django.utils.translation import gettext_lazy as _

from tankhah.constants import ACTION_TYPES
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها
import logging

logger = logging.getLogger('FactorItemApprovalForm')


class FactorItemApprovalForm(forms.ModelForm):

    status = forms.ChoiceField(

        choices=[('', _('---------'))] + [(k, v) for k, v in ACTION_TYPES if k in ['APPROVE', 'REJECTE']],

        widget=forms.Select(attrs={'class': 'form-control form-select',
                               'placeholder': _('اقدام'),
                                'style': 'max-width: 200px;'}),
                                label=_("اقدام"),
                                required=False,
                                initial='PENDING'
    )
    comment = forms.CharField(
        label=_("توضیحات اقدام"),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('توضیحات خود را برای این ردیف وارد کنید...'),
            'class': 'form-control form-control-sm'
        })
    )
    is_temporary = forms.BooleanField(
        required=False,
        label=_("اقدام موقت"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text=_("با انتخاب این گزینه، اقدام شما نهایی نخواهد بود و دیگران نیز می‌توانند اقدام کنند.")
    )
    #
    # description = forms.CharField(
    #     widget=forms.Textarea(attrs={
    #         'class': 'form-control',
    #         'rows': 2,
    #         'placeholder': _(' توضیحات خود را اینجا وارد کنید...'),
    #         'style': 'max-width: 500px;'
    #     }),
    #     required=False,
    #     label=_("شرح"),
    #  )

    class Meta:
        model = FactorItem
        fields = ('status',   'comment', 'is_temporary')
        # widgets = {
        #     'status': forms.HiddenInput(),
        #     'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        #     'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        #     'is_temporary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        # }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.status:
            # self.fields['status'].initial = self.instance.status
            # اطمینان حاصل کنید که مقدار initial از بین choices موجود انتخاب می‌شود.
            if self.instance.status in dict(self.fields['status'].choices):
                self.fields['status'].initial = self.instance.status
            else:
                # اگر وضعیت موجود در choices نیست، به PENDING برگردانید یا یک مقدار پیش‌فرض دیگر
                self.fields['status'].initial = 'PENDING'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comment = cleaned_data.get('comment', '').strip()

        # اگر اقدامی (رد یا تایید) انتخاب شده، توضیحات اجباری است
        if status == 'REJECTE' and not comment:
            self.add_error('comment', _('برای رد کردن یک ردیف، نوشتن توضیحات الزامی است.'))

        return cleaned_data
# ===
class FactorApprovalForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label=_("توضیحات کلی")
    )

    class Meta:
        model = Factor
        fields = ['comment']


class FactorApprovalForm___(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label=_("توضیحات کلی")
    )

    class Meta:
        model = Factor  # استفاده از کلاس مدل واقعی
        fields = ['comment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for item in self.instance.items.all():
            self.fields[f'action_{item.id}'] = forms.ChoiceField(
                choices=[
                    ('', _('-------')),
                    ('APPROVE', _('تأیید')),
                    ('REJECTE', _('رد')),
                ],
                label=f"وضعیت ردیف: {item.description}",
                widget=forms.Select(attrs={'class': 'form-control'}),
                required=False
            )
            self.fields[f'comment_{item.id}'] = forms.CharField(
                label=f"توضیحات برای {item.description}",
                widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
                required=False
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            for item in self.instance.items.all():
                action_field = f'action_{item.id}'
                comment_field = f'comment_{item.id}'
                if action_field in self.cleaned_data and self.cleaned_data[action_field]:
                    item.status = self.cleaned_data[action_field]
                    item.comment = self.cleaned_data[comment_field]
                    item.save()
        return instance

