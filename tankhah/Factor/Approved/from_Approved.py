from django import forms
from django.utils.translation import gettext_lazy as _
from tankhah.models import FactorItem
from core.models import Status, PostAction
from tankhah.constants import ACTION_TYPES
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها
import logging

logger = logging.getLogger('FactorItemApprovalForm')

#----------------------------
class FactorForm(forms.ModelForm):
    class Meta:
        model = Factor
        fields = ['tankhah', 'date', 'description', 'category', 'is_emergency']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tankhah': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'is_emergency': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tankhah': _('تنخواه مرتبط'),
            'date': _('تاریخ فاکتور'),
            'description': _('توضیحات'),
            'category': _('دسته‌بندی'),
            'is_emergency': _('اضطراری'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields['tankhah'].disabled = True
            logger.debug(f"Factor form initialized for existing factor {self.instance.pk}")

    def clean(self):
        cleaned_data = super().clean()
        logger.debug("Factor form clean method called")

        if not self.user:
            raise forms.ValidationError(_("کاربر معین نشده است."))

        tankhah = cleaned_data.get('tankhah')
        if tankhah and tankhah.status not in ['DRAFT', 'PENDING']:
            raise forms.ValidationError(_("تنخواه انتخاب شده در وضعیت مجاز نیست."))

        return cleaned_data

class FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'quantity', 'unit_price', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
        }
        labels = {
            'description': _('شرح ردیف'),
            'quantity': _('تعداد'),
            'unit_price': _('قیمت واحد'),
            'amount': _('مبلغ کل'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.is_locked:
            for field in self.fields:
                self.fields[field].disabled = True
            logger.debug(f"FactorItem form initialized for locked item {self.instance.pk}")

    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        if quantity is not None and quantity <= 0:
            logger.warning("Quantity must be positive")
            raise forms.ValidationError({'quantity': _('تعداد باید بزرگتر از صفر باشد.')})

        if unit_price is not None and unit_price < 0:
            logger.warning("Unit price cannot be negative")
            raise forms.ValidationError({'unit_price': _('قیمت واحد نمی‌تواند منفی باشد.')})

        if quantity and unit_price:
            cleaned_data['amount'] = quantity * unit_price
            logger.debug(f"Calculated amount: {cleaned_data['amount']}")

        return cleaned_data

class FactorApprovalForm(forms.ModelForm):
    status = forms.ChoiceField(
        choices=[],
        label=_("اقدام"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    comment = forms.CharField(
        required=False,
        label=_("توضیحات"),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('توضیحات (برای رد الزامی)')
        })
    )
    is_temporary = forms.BooleanField(
        required=False,
        label=_("اقدام موقت"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = FactorItem
        fields = ['status', 'comment', 'is_temporary']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.stage = kwargs.pop('stage', None)
        super().__init__(*args, **kwargs)

        if self.stage and self.user:
            post = self.user.userpost_set.filter(is_active=True).first()
            if post:
                actions = PostAction.objects.filter(
                    post=post.post,
                    stage=self.stage,
                    entity_type='FACTORITEM'
                ).values_list('action_type', flat=True)
                self.fields['status'].choices = [
                    (action, dict(ACTION_TYPES).get(action))
                    for action in actions
                ]
                logger.debug(f"Available actions for approval: {actions}")

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comment = cleaned_data.get('comment', '').strip()

        if status == 'REJECTE' and not comment:
            logger.warning("Rejection requires comment")
            raise forms.ValidationError({
                'comment': _("برای رد کردن، توضیحات الزامی است.")
            })

        return cleaned_data
#  ------------------------New -----------------------#

class FactorItemApprovalForm________(forms.ModelForm):
    """
    فرم برای هر ردیف فاکتور در صفحه تایید.
    گزینه‌های "اقدام" به صورت داینامیک از ویو به آن تزریق می‌شود.
    """
    # فیلد "اقدام" را به جای status، صریحاً action می‌نامیم تا شفاف باشد
    action = forms.ChoiceField(
        choices=[],  # این لیست در ویو پر خواهد شد
        label=_("اقدام"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False  # ممکن است کاربر برای برخی ردیف‌ها اقدامی نکند
    )

    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2,
                                     'placeholder': _('توضیحات (برای رد الزامی است)')}),
        required=False,
        label=_('توضیحات')
    )
    is_temporary = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        label=_('موقت')
    )

    class Meta:
        model = FactorItem
        fields = []  # ما هیچ فیلدی از خود مدل را مستقیماً ویرایش نمی‌کنیم

    def __init__(self, *args, **kwargs):
        allowed_actions = kwargs.pop('allowed_actions', [])
        super().__init__(*args, **kwargs)

        self.allowed_actions = allowed_actions
        self.has_allowed_actions = bool(self.allowed_actions)

        if self.has_allowed_actions:
            # choices را با آبجکت‌های Action که از ویو آمده‌اند، پر می‌کنیم
            self.fields['action'].choices = [('', '---------')] + [(action.code, action.name) for action in
                                                                   allowed_actions]
        else:
            # اگر هیچ اقدامی مجاز نباشد، تمام فیلدها را غیرفعال کن
            for field in self.fields.values():
                field.disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.has_allowed_actions:
            return cleaned_data

        action_code = cleaned_data.get('action')
        comment = cleaned_data.get('comment', '').strip()

        # اگر کاربر اقدامی انتخاب کرده باشد...
        if action_code:
            # آیا این اقدام در لیست اقدامات مجاز ما هست؟
            if action_code not in [action.code for action in self.allowed_actions]:
                raise forms.ValidationError(_('اقدام انتخاب‌شده برای شما غیرمجاز است.'))

            # آیا برای رد کردن، توضیحات وارد شده؟
            if action_code == 'REJECT' and not comment:
                self.add_error('comment', _('برای رد کردن، نوشتن توضیحات الزامی است.'))

        return cleaned_data

class FactorItemApprovalForm(forms.ModelForm):
    """
    فرم برای هر ردیف فاکتور در صفحه تایید.
    گزینه‌های "اقدام" به صورت داینامیک از ویو (بر اساس مدل Action) به آن تزریق می‌شود.
    """
    action = forms.ChoiceField(
        choices=[],  # این لیست در ویو پر خواهد شد
        label=_("اقدام"),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False  # کاربر ممکن است برای برخی ردیف‌ها اقدامی انتخاب نکند
    )

    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2,
                                     'placeholder': _('توضیحات (برای رد الزامی است)')}),
        required=False,
        label=_('توضیحات')
    )
    is_temporary = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False,
        label=_('موقت')
    )

    class Meta:
        model = FactorItem
        fields = []  # ما هیچ فیلدی از خود مدل را مستقیماً از طریق این فرم ویرایش نمی‌کنیم

    def __init__(self, *args, **kwargs):
        allowed_actions = kwargs.pop('allowed_actions', [])
        super().__init__(*args, **kwargs)

        self.allowed_actions = allowed_actions
        self.has_allowed_actions = bool(self.allowed_actions)

        if self.has_allowed_actions:
            # choices را با اشیاء Action که از ویو آمده‌اند، پر می‌کنیم
            self.fields['action'].choices = [('', '---------')] + [(action.code, action.name) for action in
                                                                   allowed_actions]
        else:
            # اگر هیچ اقدامی مجاز نباشد، تمام فیلدها را غیرفعال کن
            for field_name in ['action', 'comment', 'is_temporary']:
                self.fields[field_name].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.has_allowed_actions:
            return cleaned_data

        action_code = cleaned_data.get('action')
        comment = cleaned_data.get('comment', '').strip()

        if action_code:
            # اعتبارسنجی‌ها
            if action_code not in [action.code for action in self.allowed_actions]:
                raise forms.ValidationError(_('اقدام انتخاب‌شده برای شما غیرمجاز است.'))
            if action_code == 'REJECT' and not comment:
                self.add_error('comment', _('برای رد کردن، نوشتن توضیحات الزامی است.'))

        return cleaned_data
