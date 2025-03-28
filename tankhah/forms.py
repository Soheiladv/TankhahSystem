import logging

from .utils import restrict_to_user_organization

logger = logging.getLogger(__name__)
import jdatetime
from django.utils import timezone
from Tanbakhsystem.utils import convert_to_farsi_numbers
from core.models import WorkflowStage
from .models import Factor, ApprovalLog, FactorDocument, FactorItem, Tankhah
from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory

class FactorItemApprovalForm(forms.Form):
    action = forms.ChoiceField(choices=[('', '-----'), ('APPROVE', 'تأیید'), ('REJECT', 'رد')], required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False)


# ------------ New
class FactorApprovalForm(forms.ModelForm):
    """فرم تأیید یا رد فاکتور و ردیف‌های آن"""

    comment = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        label=_("توضیحات کلی")
    )

    class Meta:
        model = Factor
        fields = ['comment']  # فقط توضیحات کلی برای کل فاکتور

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # اضافه کردن فیلدهای پویا برای هر ردیف فاکتور
        for item in self.instance.items.all():
            self.fields[f'action_{item.id}'] = forms.ChoiceField(
                choices=[
                    ('', _('-------')),
                    ('APPROVED', _('تأیید')),
                    ('REJECTED', _('رد')),
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
            # به‌روزرسانی وضعیت ردیف‌ها
            for item in self.instance.items.all():
                action_field = f'action_{item.id}'
                comment_field = f'comment_{item.id}'
                if action_field in self.cleaned_data and self.cleaned_data[action_field]:
                    item.status = self.cleaned_data[action_field]
                    item.comment = self.cleaned_data[comment_field]
                    item.save()
        return instance


# ------------
class TankhahForm(forms.ModelForm):
    # description = forms.CharField(widget=forms.Textarea, required=False, label=_("توضیحات"))

    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )
    due_date = forms.CharField(
        label=_('مهلت باقی مانده'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
        })
    )

    class Meta:
        model = Tankhah
        fields = ['date', 'organization', 'project', 'letter_number',
                  'due_date', 'amount', 'description']  # 'current_stage','last_stopped_post', 'status','hq_status',
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
            # 'status': forms.Select(attrs={'class': 'form-control'}),
            # 'hq_status': forms.Select(attrs={'class': 'form-control'}),
            # 'last_stopped_post': forms.Select(attrs={'class': 'form-control'}),
            # 'current_stage': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'date': _('تاریخ'),
            'organization': _('مجتمع'),
            'project': _('پروژه'),
            # 'status': _('وضعیت'),
            # 'hq_status': _('وضعیت در HQ'),
            # 'last_stopped_post': _('آخرین پست متوقف‌شده'),
            'letter_number': _('شماره نامه درصورت الصاق نامه در اتوماسیون اداری'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # for field in ['current_stage',]: #   'last_stopped_post''status', 'hq_status',
        #     self.fields[field].widget = forms.HiddenInput()

        if self.user:
            user_posts = self.user.userpost_set.all()
            if self.instance.pk and self.instance.organization:
                if not any(post.post.organization == self.instance.organization for post in user_posts):
                    for field_name in self.fields:
                        if field_name != 'status' and field_name != 'description':
                            self.fields[field_name].disabled = True
        if self.instance.pk:
            self.fields['date'].initial = jdatetime.date.fromgregorian(date=self.instance.date).strftime('%Y/%m/%d')
            self.fields['due_date'].initial = (
                jdatetime.date.fromgregorian(date=self.instance.due_date).strftime('%Y/%m/%d')
                if self.instance.due_date else ''
            )

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if date_str:
            try:
                j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
                gregorian_date = j_date.togregorian()
                # تبدیل به datetime آگاه از منطقه زمانی
                return timezone.make_aware(gregorian_date)
            except ValueError:
                raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
        return timezone.now()  # مقدار پیش‌فرض در صورت خالی بودن

    def clean_due_date(self):
        due_date_str = self.cleaned_data.get('due_date')
        if due_date_str:
            try:
                j_date = jdatetime.datetime.strptime(due_date_str, '%Y/%m/%d')
                gregorian_date = j_date.togregorian()
                # تبدیل به datetime آگاه از منطقه زمانی
                return timezone.make_aware(gregorian_date)
            except ValueError:
                raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
        return None  # اختیاری بودن due_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            user_post = self.user.userpost_set.filter(post__organization=instance.organization).first()
            if not instance.pk:
                instance.created_by = self.user
                instance.last_stopped_post = user_post.post if user_post else None
            if self.has_changed() and 'status' in self.changed_data:
                old_status = Tankhah.objects.get(pk=instance.pk).status if instance.pk else 'DRAFT'
                new_status = self.cleaned_data['status']
                action = 'APPROVE' if new_status != 'REJECTED' else 'REJECT'
                from .models import ApprovalLog
                ApprovalLog.objects.create(
                    tankhah=instance,
                    action=action,
                    user=self.user,
                    comment=self.cleaned_data['comment'],
                    post=user_post.post if user_post else None
                )
                if new_status == 'SENT_TO_HQ':
                    instance.current_stage = WorkflowStage.objects.get(name='OPS')
                elif new_status == 'HQ_OPS_APPROVED':
                    instance.current_stage = WorkflowStage.objects.get(name='FIN')
        if commit:
            instance.save()
        return instance


class TanbakhApprovalForm(forms.ModelForm):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        label=_("توضیحات")
    )

    class Meta:
        model = Tankhah
        fields = []  # هیچ فیلد دیگری از مدل نیاز نیست


class FactorForm(forms.ModelForm):
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
        fields = ['tankhah', 'date', 'amount', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': _('مبلغ را وارد کنید')}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات فاکتور')}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)
        initial_stage_order = WorkflowStage.objects.order_by(
            '-order').first().order if WorkflowStage.objects.exists() else None

        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            if user_orgs is None:  # HQ یا Superuser
                self.fields['tankhah'].queryset = Tankhah.objects.filter(
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                )
            else:  # شعبات
                self.fields['tankhah'].queryset = Tankhah.objects.filter(
                    organization__in=user_orgs,
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                )

        # تنظیمات برای ویرایش
        if self.instance.pk:
            self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.instance.tankhah.id)
            self.fields['tankhah'].initial = self.instance.tankhah
            if self.instance.date:
                j_date = jdatetime.date.fromgregorian(date=self.instance.date)
                jalali_date_str = j_date.strftime('%Y/%m/%d')
                self.fields['date'].initial = jalali_date_str
                self.initial['date'] = jalali_date_str
            self.fields['amount'].initial = convert_to_farsi_numbers(self.instance.amount)
        elif self.tankhah:
            self.fields['tankhah'].initial = self.tankhah

        # غیرفعال کردن فیلدها در صورت عدم دسترسی
        if self.instance.pk and self.user and not self.user.has_perm('tankhah.Factor_full_edit'):
            for field_name in self.fields:
                self.fields[field_name].disabled = True

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            return timezone.make_aware(gregorian_date)
        except ValueError:
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and self.instance.pk and self.has_changed():
            old_instance = Factor.objects.get(pk=self.instance.pk)
            for field in self.changed_data:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                logger.info(
                    f"تغییر در فاکتور {instance.number}: {field} از {old_value} به {new_value} توسط {self.user}")
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

# FactorItemFormSet = inlineformset_factory(Factor, FactorItem, fields=['description', 'amount', 'quantity'], extra=1)
FactorItemFormSet = inlineformset_factory(Factor, FactorItem, form=FactorItemForm, fields=['description', 'amount', 'quantity'], extra=1,can_delete=True)


class ApprovalForm(forms.ModelForm):
    """فرم ثبت تأیید یا رد"""
    action = forms.ChoiceField(choices=[
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('RETURN', 'بازگشت'),
        ('CANCEL', 'لغو')
    ])

    class Meta:
        model = ApprovalLog
        fields = ['tankhah', 'factor', 'comment', 'action']  # user و date توسط سیستم پر می‌شوند
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
            'action': forms.Select(attrs={'class': 'form-control'}),
            # 'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'factor': _('فاکتور'),
            'comment': _('توضیحات'),
            'action': _('شاخه'),
            # 'is_approved': _('تأیید شده؟'),
        }


"""این فرم وضعیت و مرحله فعلی تنخواه را نمایش می‌دهد:"""

class TankhahStatusForm(forms.ModelForm):
    class Meta:
        model = Tankhah
        fields = ['status', 'current_stage', 'due_date', 'approved_by']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'current_stage': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'approved_by': forms.SelectMultiple(attrs={'class': 'form-control', 'disabled': 'disabled'}),
        }
        labels = {
            'status': _('وضعیت'),
            'current_stage': _('مرحله فعلی'),
            'due_date': _('مهلت زمانی'),
            'approved_by': _('تأییدکنندگان'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # غیرفعال کردن فیلدها برای نمایش فقط خواندنی
        for field in self.fields.values():
            field.disabled = True


class FactorStatusForm(forms.ModelForm):
    class Meta:
        model = Factor
        fields = ['status']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
        labels = {
            'status': _('وضعیت'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].disabled = True


class FactorItemFormSet(forms.inlineformset_factory(Factor, FactorItem,
                                                    fields=('description', 'amount', 'quantity'),
                                                    extra=1, can_delete=True)):
    pass


# فرم برای اسناد فاکتور
# class FactorDocumentForm(forms.ModelForm):
#     class Meta:
#         model = FactorDocument
#         fields = ['file']
#         widgets = {
#             'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
#         }
#         labels = {'file': _('فایل پیوست')}




"""*** مهم ***"""
"""چون در مدل TanbakhDocument فقط یک document ذخیره می‌شود، اما ما چندین فایل را آپلود می‌کنیم. بنابراین نیازی به ModelForm نیست."""
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True  # امکان انتخاب چندین فایل را فعال می‌کند

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

# فرم برای اقلام فاکتور
class FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

FactorItemFormSet = inlineformset_factory(
    Factor, FactorItem,
    form=FactorItemForm,
    fields=['description', 'amount', 'quantity'],
    extra=1,
    can_delete=True
)

# فرم اسناد فاکتور (چندفایلی، بدون ModelForm)
class FactorDocumentForm(forms.Form):
    files = MultipleFileField(label=_("بارگذاری اسناد فاکتور"), required=False)

# فرم اسناد تنخواه (چندفایلی، بدون ModelForm)
class TankhahDocumentForm(forms.Form):
    documents = MultipleFileField(label=_("بارگذاری مدارک تنخواه"), required=False)

