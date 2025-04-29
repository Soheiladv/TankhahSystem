import logging
import os
from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget
from .utils import restrict_to_user_organization
import jdatetime
from django.utils import timezone
from Tanbakhsystem.utils import convert_to_farsi_numbers, to_english_digits
from Tanbakhsystem.base import JalaliDateForm
from tankhah.models import Factor, FactorItem, Tankhah  # وارد کردن مدل‌ها

logger = logging.getLogger(__name__)

class FactorItemApprovalForm(forms.Form):
    item_id = forms.IntegerField(widget=forms.HiddenInput)
    action = forms.ChoiceField(
        choices=[
            ('PENDING', _('در انتظار')),
            ('APPROVE', _('تأیید')),
            ('REJECT', _('رد')),
        ],
        widget=forms.Select(attrs={'class': 'form-control form-select', 'style': 'max-width: 200px;'}),
        label=_("اقدام"),
        required=False,
        initial='PENDING'
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('توضیحات خود را اینجا وارد کنید...'),
            'style': 'max-width: 500px;'
        }),
        required=False,
        label=_("توضیحات")
    )

class FactorApprovalForm(forms.ModelForm):
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
            for item in self.instance.items.all():
                action_field = f'action_{item.id}'
                comment_field = f'comment_{item.id}'
                if action_field in self.cleaned_data and self.cleaned_data[action_field]:
                    item.status = self.cleaned_data[action_field]
                    item.comment = self.cleaned_data[comment_field]
                    item.save()
        return instance

class TankhahForm(JalaliDateForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('مثال: 1404/01/17'),
        })
    )
    due_date = forms.CharField(
        label=_('مهلت زمانی'),
        required=False,
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('مثال: 1404/01/17'),
        })
    )

    class Meta:
        model = Tankhah
        fields = ['date', 'organization', 'project', 'subproject', 'letter_number', 'due_date', 'amount', 'description']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'subproject': forms.Select(attrs={'class': 'form-control'}),
            'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        from core.models import Organization, Project, SubProject
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            user_orgs = set(up.post.organization for up in self.user.userpost_set.filter(is_active=True))
            self.fields['organization'].queryset = Organization.objects.filter(id__in=[org.id for org in user_orgs])
            self.fields['project'].queryset = Project.objects.filter(organizations__in=user_orgs).distinct()

            if 'project' in self.data:
                try:
                    project_id = int(self.data.get('project'))
                    self.fields['subproject'].queryset = SubProject.objects.filter(project_id=project_id)
                except (ValueError, TypeError):
                    self.fields['subproject'].queryset = SubProject.objects.none()
            elif self.instance.pk and self.instance.project:
                self.fields['subproject'].queryset = SubProject.objects.filter(project=self.instance.project)
            else:
                self.fields['subproject'].queryset = SubProject.objects.none()

            if self.instance.pk and self.instance.organization:
                user_posts = self.user.userpost_set.filter(is_active=True)
                if not any(post.post.organization == self.instance.organization for post in user_posts):
                    for field_name in self.fields:
                        if field_name not in ['status', 'description']:
                            self.fields[field_name].disabled = True

        self.set_jalali_initial('date', 'date')
        self.set_jalali_initial('due_date', 'due_date')

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        subproject = cleaned_data.get('subproject')
        amount = cleaned_data.get('amount')

        if subproject and subproject.project != project:
            raise forms.ValidationError(_("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))

        if project and amount:
            remaining_budget = get_subproject_remaining_budget(subproject) if subproject else get_project_remaining_budget(project)
            if amount > remaining_budget:
                raise forms.ValidationError(
                    _(f"مبلغ واردشده ({amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است.")
                )

        return cleaned_data

    def clean_date(self):
        return self.clean_jalali_date('date') or timezone.now()

    def clean_due_date(self):
        return self.clean_jalali_date('due_date')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            user_post = self.user.userpost_set.filter(post__organization=instance.organization, is_active=True).first()
            if not instance.pk:
                instance.created_by = self.user
                instance.last_stopped_post = user_post.post if user_post else None
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
        fields = []

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
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 1, 'placeholder': _('توضیحات فاکتور')}),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'date': _('تاریخ'),
            'amount': _('مبلغ'),
            'description': _('توضیحات'),
        }

    def __init__(self, *args, **kwargs):
        from core.models import WorkflowStage, Project, SubProject
        self.user = kwargs.pop('user', None)
        self.tankhah = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None

        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            if user_orgs is None:
                self.fields['tankhah'].queryset = Tankhah.objects.filter(
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                )
            else:
                projects = Project.objects.filter(organizations__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
                from django.db.models import Q
                queryset = Tankhah.objects.filter(
                    status__in=['DRAFT', 'PENDING'],
                    current_stage__order=initial_stage_order
                ).filter(
                    Q(organization__in=user_orgs) |
                    Q(project__in=projects) |
                    Q(subproject__in=subprojects)
                ).distinct()
                self.fields['tankhah'].queryset = queryset
                logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")

        if self.instance.pk:
            self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.instance.tankhah.id)
            self.fields['tankhah'].initial = self.instance.tankhah
            if self.instance.date:
                j_date = jdatetime.date.fromgregorian(date=self.instance.date)
                jalali_date_str = j_date.strftime('%Y/%m/%d')
                self.fields['date'].initial = jalali_date_str
                self.initial['date'] = jalali_date_str

            amount = self.instance.amount
            if amount is not None:
                self.initial['amount'] = str(int(round(Decimal(amount))))
                logger.info(f'Initial amount set for widget: {self.initial["amount"]}')

        elif self.tankhah:
            self.fields['tankhah'].initial = self.tankhah

        if self.instance.pk and self.user and not self.user.has_perm('tankhah.Factor_full_edit'):
            for field_name in self.fields:
                self.fields[field_name].disabled = True

    def clean_date(self):
        date_str = self.cleaned_data.get('date')
        if not date_str:
            logger.error("خطا: تاریخ فاکتور وارد نشده است")
            raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
        try:
            j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
            gregorian_date = j_date.togregorian()
            logger.info(f"تاریخ تبدیل‌شده: {gregorian_date}")
            return timezone.make_aware(gregorian_date)
        except ValueError:
            # logger.error(f"خطا در تبدیل تاریخ: {e}")
            raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
        if amount <= 0:
            raise forms.ValidationError(_("مبلغ باید بزرگتر از صفر باشد."))
        return amount

    def clean(self):
        cleaned_data = super().clean()
        logger.info(f"داده‌های اعتبارسنجی‌شده: {cleaned_data}")
        return cleaned_data

    def save(self, commit=True):
        logger.info(f"Starting save for factor by {self.user}, commit={commit}, data={self.cleaned_data}")
        instance = super().save(commit=False)
        if self.user:
            if self.instance.pk and self.has_changed():
                old_instance = Factor.objects.get(pk=self.instance.pk)
                for field in self.changed_data:
                    old_value = getattr(old_instance, field)
                    new_value = getattr(instance, field)
                    logger.info(
                        f"Change in factor (ID: {instance.pk}): {field} from {old_value} to {new_value} by {self.user}")
            else:
                logger.info(f"Creating new factor by {self.user}: {self.cleaned_data}")
        if commit:
            instance.save()
            logger.info(f"Factor saved: ID={instance.pk}, number={instance.number}")
        return instance

class FactorItemForm(forms.ModelForm):
    class Meta:
        model = FactorItem
        fields = ['description', 'amount', 'quantity']
        widgets = {
            'description': forms.TextInput(
                attrs={'class': 'form-control form-control-sm', 'placeholder': _('شرح ردیف')}),
            'amount': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input amount-field', 'step': '1', 'min': '0', 'placeholder': 'مبلغ را وارد کنید'}),
            'quantity': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        quantity = cleaned_data.get('quantity')
        description = cleaned_data.get('description')

        # اگه فرم خالیه (بدون توضیحات و مبلغ)، قبولش کن و نادیده بگیر
        # نادیده گرفتن فرم‌های خالی
        if not description and (amount is None or amount == 0) and (quantity is None or quantity == 1):
            self.cleaned_data['DELETE'] = True
            return cleaned_data

        # اعتبارسنجی برای فرم‌های پرشده
        if not description:
            raise forms.ValidationError(_('شرح ردیف الزامی است.'))
        if amount is None or amount <= 0:
            raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
        if quantity is None or quantity < 1:
            raise forms.ValidationError(_('تعداد باید حداقل ۱ باشد.'))
        return cleaned_data

class ApprovalForm(forms.ModelForm):
    action = forms.ChoiceField(choices=[
        ('APPROVE', 'تأیید'),
        ('REJECT', 'رد'),
        ('RETURN', 'بازگشت'),
        ('CANCEL', 'لغو')
    ])

    class Meta:
        from tankhah.models import ApprovalLog
        model = ApprovalLog
        fields = ['action', 'comment', 'tankhah', 'factor', 'factor_item']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-control'}),
            'factor': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
            'action': forms.Select(attrs={'class': 'form-control'}),
            'factor_item': forms.HiddenInput(),
        }
        labels = {
            'tankhah': _('تنخواه'),
            'factor': _('فاکتور'),
            'comment': _('توضیحات'),
            'action': _('شاخه'),
        }

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

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data if d is not None]
        else:
            result = single_file_clean(data, initial)
        return result

ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png']
ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS)

class FactorDocumentForm(forms.Form):
    files = MultipleFileField(
        label=_("بارگذاری اسناد فاکتور (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
        required=False,
        widget=MultipleFileInput(
            attrs={
                'multiple': True,
                'class': 'form-control form-control-sm',
                'accept': ",".join(ALLOWED_EXTENSIONS)
            }
        )
    )

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files:
            invalid_files = []
            for uploaded_file in files:
                if uploaded_file:
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        invalid_files.append(uploaded_file.name)
                        logger.warning(f"Invalid file type uploaded for FactorDocument: {uploaded_file.name} (type: {ext})")

            if invalid_files:
                invalid_files_str = ", ".join(invalid_files)
                error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
                    files=invalid_files_str,
                    allowed=ALLOWED_EXTENSIONS_STR
                )
                raise ValidationError(error_msg)
        return files

class TankhahDocumentForm(forms.Form):
    documents = MultipleFileField(
        label=_("بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
        required=False,
        widget=MultipleFileInput(
            attrs={
                'multiple': True,
                'class': 'form-control form-control-sm',
                'accept': ",".join(ALLOWED_EXTENSIONS)
            }
        )
    )

    def clean_documents(self):
        files = self.cleaned_data.get('documents')
        if files:
            invalid_files = []
            for uploaded_file in files:
                if uploaded_file:
                    ext = os.path.splitext(uploaded_file.name)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        invalid_files.append(uploaded_file.name)
                        logger.warning(f"Invalid file type uploaded for TankhahDocument: {uploaded_file.name} (type: {ext})")

            if invalid_files:
                invalid_files_str = ", ".join(invalid_files)
                error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
                    files=invalid_files_str,
                    allowed=ALLOWED_EXTENSIONS_STR
                )
                raise ValidationError(error_msg)
        return files


def get_factor_item_formset():
    from django.forms import inlineformset_factory
    return inlineformset_factory(
        Factor, FactorItem, form=FactorItemForm,
        fields=['description', 'amount', 'quantity'],
        # extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
        extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
    )