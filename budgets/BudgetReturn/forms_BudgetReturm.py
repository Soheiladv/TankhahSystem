import logging
from django import forms
from decimal import Decimal

from budgets.models import BudgetTransaction
from budgets.budget_calculations import check_budget_status
from django.utils.translation import gettext_lazy as _
logger = logging.getLogger("BudgetReturnForm")

class  BudgetReturnForm(forms.ModelForm):
    # دلایل رایج بازگشت بودجه
    RETURN_REASON_CHOICES = [
        ('END_OF_PROJECT', _('اتمام پروژه و وجود مانده')),
        ('COST_SAVING', _('صرفه‌جویی در هزینه‌ها')),
        ('CANCEL_ACTIVITY', _('لغو بخشی از فعالیت‌ها')),
        ('BUDGET_CORRECTION', _('اصلاح تخصیص بودجه')),
        ('OTHER', _('سایر موارد (در توضیحات ذکر شود)')),
    ]
    amount = forms.DecimalField(
        label=_('مبلغ برگشتی'),
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
             'inputmode': 'numeric',  # به جای type=number
             'autocomplete': 'off','placeholder': _('مبلغ بازگشتی را به ریال وارد کنید'),
        })
    )

    # اضافه کردن فیلد دلیل بازگشت
    return_reason = forms.ChoiceField(
        choices=RETURN_REASON_CHOICES,
        label=_('دلیل اصلی بازگشت وجه'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = BudgetTransaction
        fields = ['amount', 'return_reason', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
                'placeholder': _('مبلغ (ریال)'),
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('توضیحات به صورت خودکار بر اساس دلیل و مبلغ تولید می‌شود. در صورت نیاز آن را ویرایش کنید.')
            }),
        }
        labels = {
            'amount': _('مبلغ برگشتی'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, allocation=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.allocation = allocation
        self.user = user
        if allocation:
            self.instance.allocation = allocation
            logger.debug(f"BudgetReturnForm initialized with allocation ID: {allocation.pk}")
        if user:
            self.instance.created_by = user
            logger.debug(f"Form initialized with user: {user.username}")
        self.instance.transaction_type = 'RETURN'

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        logger.debug(f"Validating amount: {amount} for allocation ID: {self.allocation.pk if self.allocation else 'None'}")

        if amount is None:
            logger.error("Amount is missing or None")
            raise forms.ValidationError(_('مبلغ برگشتی الزامی است.'))

        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError):
            logger.error(f"Invalid amount format: {amount}")
            raise forms.ValidationError(_('مبلغ برگشتی باید یک عدد معتبر باشد.'))

        if amount <= 0:
            logger.error(f"Invalid amount: {amount} (must be positive)")
            raise forms.ValidationError(_('مبلغ برگشتی باید مثبت باشد.'))

        if not self.allocation:
            logger.error("No allocation provided")
            raise forms.ValidationError(_('تخصیص بودجه مشخص نشده است.'))

        # بررسی مبلغ تخصیص‌یافته
        if amount > self.allocation.allocated_amount:
            logger.error(
                f"Amount {amount:,.0f} exceeds allocated_amount {self.allocation.allocated_amount:,.0f} "
                f"for allocation ID: {self.allocation.pk}"
            )
            raise forms.ValidationError(
                _(
                    f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از مبلغ تخصیص‌یافته "
                    f"({self.allocation.allocated_amount:,.0f} ریال) باشد."
                )
            )

        # بررسی بودجه باقی‌مانده تخصیص
        remaining_budget = self.allocation.get_remaining_amount()
        logger.debug(
            f"Allocation remaining budget: {remaining_budget} for allocation ID: {self.allocation.pk}"
        )
        if amount > remaining_budget:
            logger.error(
                f"Amount {amount:,.0f} exceeds remaining_budget {remaining_budget:,.0f} "
                f"for allocation ID: {self.allocation.pk}"
            )
            raise forms.ValidationError(
                _(
                    f"مبلغ برگشتی ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده تخصیص "
                    f"({remaining_budget:,.0f} ریال) باشد."
                )
            )

        logger.info(f"Amount {amount} validated successfully for allocation ID: {self.allocation.pk}")
        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transaction_type = 'RETURN'
        logger.debug(f"Saving BudgetTransaction with amount: {instance.amount}, allocation ID: {self.allocation.pk}")

        if commit:
            try:
                instance.save()
                logger.info(f"BudgetTransaction saved with ID: {instance.pk}")

                # ارسال اعلان‌ها
                status, message = check_budget_status(self.allocation.budget_period)
                logger.debug(f"Budget period status: {status}, message: {message}")
                if status in ('warning', 'locked', 'completed'):
                    self.allocation.send_notification(status, message)
                    logger.info(f"Notification sent for status: {status}")
                self.allocation.send_notification(
                    'return',
                    f"مبلغ {instance.amount:,.0f} ریال از تخصیص {self.allocation.id} برگشت داده شد."
                )
                logger.info(f"Return notification sent for allocation ID: {self.allocation.pk}")

            except Exception as e:
                logger.error(f"Validation error during save: {str(e)}")
                raise

        return instance


