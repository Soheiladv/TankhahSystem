from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _
from django import forms
from django.utils.translation import gettext_lazy as _
from tankhah.models import FactorItem

from django import forms
from django.utils.translation import gettext_lazy as _
from tankhah.models import FactorItem
from core.models import AccessRule, PostAction
from tankhah.constants import ACTION_TYPES
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها
import logging

logger = logging.getLogger('FactorItemApprovalForm')


# ===
class FactorItemApprovalForm(forms.ModelForm):
    status = forms.ChoiceField(
        label=_("اقدام"),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'required': 'required'
        })
    )
    comment = forms.CharField(
        label=_("توضیحات"),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 1,
            'class': 'form-control form-control-sm',
            'placeholder': _('توضیحات (برای رد الزامی است)')
        })
    )
    is_temporary = forms.BooleanField(
        required=False,
        label=_("اقدام موقت"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_bulk_action = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput(),
        initial=False
    )

    class Meta:
        model = FactorItem
        fields = ('status', 'comment', 'is_temporary', 'is_bulk_action')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        current_stage = kwargs.pop('current_stage', None)
        super().__init__(*args, **kwargs)
        self.has_allowed_actions = False
        logger.debug(
            f"[FactorItemApprovalForm] Initializing form for user '{user.username if user else 'N/A'}' "
            f"in stage '{current_stage.stage if current_stage else 'N/A'}' "
            f"for factor item '{self.instance.id if self.instance else 'N/A'}'"
        )

        allowed_actions = set()
        if user and current_stage:
            logger.debug(f"[FactorItemApprovalForm] Step 1: Fetching user post")
            user_post = user.userpost_set.filter(is_active=True).first()
            if user_post:
                logger.debug(f"[FactorItemApprovalForm] Active post found: {user_post.post_id}")
                logger.debug(f"[FactorItemApprovalForm] Step 2: Fetching allowed actions")
                allowed_actions.update(
                    AccessRule.objects.filter(
                        organization=current_stage.organization,
                        stage_order=current_stage.stage_order,
                        post=user_post.post,
                        entity_type='FACTORITEM',
                        is_active=True
                    ).values_list('action_type', flat=True)
                )
                logger.debug(f"[FactorItemApprovalForm] Allowed actions from AccessRule: {allowed_actions}")
            else:
                logger.warning(f"[FactorItemApprovalForm] No active post for user '{user.username}'")

            # بررسی دسترسی سوپریوزر یا HQ
            logger.debug(f"[FactorItemApprovalForm] Step 3: Checking superuser or HQ access")
            if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
                logger.info(f"[FactorItemApprovalForm] User '{user.username}' has superuser/global perm. Adding allowed actions")
                allowed_actions.update(['APPROVE', 'REJECT'])
            else:
                user_orgs = set()
                for user_post in user.userpost_set.filter(is_active=True).select_related('post__organization'):
                    org = user_post.post.organization
                    user_orgs.add(org)
                    parent = org.parent_organization
                    while parent:
                        user_orgs.add(parent)
                        parent = parent.parent_organization
                if any(org.is_core for org in user_orgs):
                    logger.info(f"[FactorItemApprovalForm] User '{user.username}' is HQ user. Adding allowed actions")
                    allowed_actions.update(['APPROVE', 'REJECT'])

        # تنظیم گزینه‌های فیلد status
        logger.debug(f"[FactorItemApprovalForm] Step 4: Setting status field choices")
        self.fields['status'].choices = [('', _('--- انتخاب کنید ---'))] + [
            (code, label) for code, label in ACTION_TYPES if code in allowed_actions
        ]
        logger.debug(f"[FactorItemApprovalForm] Status choices: {self.fields['status'].choices}")

        if not allowed_actions:
            logger.warning(f"[FactorItemApprovalForm] No allowed actions. Disabling form fields")
            self.fields['status'].widget.attrs['disabled'] = 'disabled'
            self.fields['comment'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_temporary'].widget.attrs['disabled'] = 'disabled'
        else:
            self.has_allowed_actions = True
            logger.debug(f"[FactorItemApprovalForm] Form fields enabled with allowed actions")

    def clean(self):
        logger.debug(f"[FactorItemApprovalForm] Step 5: Cleaning form data for item '{self.instance.id}'")
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comment = cleaned_data.get('comment', '').strip()

        if not self.has_allowed_actions:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: No allowed actions for user")
            raise forms.ValidationError(_('هیچ اقدامی برای شما در این مرحله مجاز نیست.'))

        if status == 'REJECT' and not comment:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: Comment required for REJECT")
            self.add_error('comment', _('برای رد کردن، توضیحات الزامی است.'))
        if status and status not in [code for code, _ in ACTION_TYPES]:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: Invalid status '{status}'")
            self.add_error('status',  ('اقدام انتخاب‌شده نامعتبر است.'))

        logger.debug(f"[FactorItemApprovalForm] Cleaned data: {cleaned_data}")
        return cleaned_data

class FactorItemApprovalForm__(forms.ModelForm):
    status = forms.ChoiceField(
        label=_("اقدام"),
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm',
            'required': 'required'
        })
    )
    comment = forms.CharField(
        label=_("توضیحات"),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 1,
            'class': 'form-control form-control-sm',
            'placeholder': _('توضیحات (برای رد الزامی است)')
        })
    )
    is_temporary = forms.BooleanField(
        required=False,
        label=_("اقدام موقت"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = FactorItem
        fields = ('status', 'comment', 'is_temporary')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        current_stage = kwargs.pop('current_stage', None)
        super().__init__(*args, **kwargs)
        self.has_allowed_actions = False
        logger.debug(
            f"[FactorItemApprovalForm] Initializing form for user '{user.username if user else 'N/A'}' "
            f"in stage '{current_stage.stage if current_stage else 'N/A'}' "
            f"for factor item '{self.instance.id if self.instance else 'N/A'}'"
        )

        allowed_actions = set()
        if user and current_stage:
            logger.debug(f"[FactorItemApprovalForm] Step 1: Fetching user post")
            user_post = user.userpost_set.filter(is_active=True).first()
            if user_post:
                logger.debug(f"[FactorItemApprovalForm] Active post found: {user_post.post_id}")
                logger.debug(f"[FactorItemApprovalForm] Step 2: Fetching allowed actions")
                allowed_actions.update(
                    AccessRule.objects.filter(
                        organization=current_stage.organization,
                        stage_order=current_stage.stage_order,
                        post=user_post.post,
                        entity_type='FACTORITEM',  # فقط FACTORITEM
                        is_active=True
                    ).values_list('action_type', flat=True)
                )
                logger.debug(f"[FactorItemApprovalForm] Allowed actions from AccessRule: {allowed_actions}")
            else:
                logger.warning(f"[FactorItemApprovalForm] No active post for user '{user.username}'")

            # بررسی دسترسی سوپریوزر یا HQ
            logger.debug(f"[FactorItemApprovalForm] Step 3: Checking superuser or HQ access")
            if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
                logger.info(f"[FactorItemApprovalForm] User '{user.username}' has superuser/global perm. Adding allowed actions")
                allowed_actions.update(['APPROVE', 'REJECT'])  # فقط اقدامات مجاز برای FACTORITEM
            else:
                user_orgs = set()
                for user_post in user.userpost_set.filter(is_active=True).select_related('post__organization'):
                    org = user_post.post.organization
                    user_orgs.add(org)
                    parent = org.parent_organization
                    while parent:
                        user_orgs.add(parent)
                        parent = parent.parent_organization
                if any(org.is_core for org in user_orgs):
                    logger.info(f"[FactorItemApprovalForm] User '{user.username}' is HQ user. Adding allowed actions")
                    allowed_actions.update(['APPROVE', 'REJECT'])  # فقط اقدامات مجاز برای FACTORITEM

        # تنظیم گزینه‌های فیلد status
        logger.debug(f"[FactorItemApprovalForm] Step 4: Setting status field choices")
        logger.info(f'ACTION_TYPES 👎👎🤣🤣{ACTION_TYPES }')
        self.fields['status'].choices = [('', _('--- انتخاب کنید ---'))] + [
            (code, label) for code, label in ACTION_TYPES if code in allowed_actions
        ]
        logger.debug( f" 'n\'[FactorItemApprovalForm] Status choices: {self.fields['status'].choices}")

        if not allowed_actions:
            logger.warning(f"[FactorItemApprovalForm] No allowed actions. Disabling form fields")
            self.fields['status'].widget.attrs['disabled'] = 'disabled'
            self.fields['comment'].widget.attrs['disabled'] = 'disabled'
            self.fields['is_temporary'].widget.attrs['disabled'] = 'disabled'
        else:
            self.has_allowed_actions = True
            logger.debug(f"[FactorItemApprovalForm] Form fields enabled with allowed actions")

    def clean(self):
        logger.debug(f"[FactorItemApprovalForm] Step 5: Cleaning form data for item '{self.instance.id}'")
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        comment = cleaned_data.get('comment', '').strip()

        if not self.has_allowed_actions:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: No allowed actions for user")
            raise forms.ValidationError(_('هیچ اقدامی برای شما در این مرحله مجاز نیست.'))

        if status == 'REJECT' and not comment:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: Comment required for REJECT")
            self.add_error('comment', _('برای رد کردن، توضیحات الزامی است.'))
        if status and status not in [code for code, _ in ACTION_TYPES]:
            logger.warning(f"[FactorItemApprovalForm] Validation failed: Invalid status '{status}'")
            self.add_error('status',  ('اقدام انتخاب‌شده نامعتبر است.'))

        logger.debug(f"[FactorItemApprovalForm] Cleaned data: {cleaned_data}")
        return cleaned_data

FactorItemApprovalFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemApprovalForm,
    fields=('status', 'comment', 'is_temporary'),
    extra=0,
    can_delete=False
)

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
