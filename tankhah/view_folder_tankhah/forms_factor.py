# import os
# import logging
# from decimal import Decimal
# from django.core.exceptions import ValidationError
# from django.db.models import Q
#
# from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget, \
#     get_tankhah_remaining_budget
#
# logger = logging.getLogger(__name__)
#
# from django.db import models
# from .utils import restrict_to_user_organization
# import jdatetime
# from django.utils import timezone
# from Tanbakhsystem.utils import convert_to_farsi_numbers, to_english_digits
# from core.models import WorkflowStage, Project, Organization
# from .models import Factor, ApprovalLog, FactorItem, Tankhah, get_default_workflow_stage
# from core.models import SubProject
# from django import forms
# from django.utils.translation import gettext_lazy as _
# from django.forms import inlineformset_factory
# from Tanbakhsystem.base import JalaliDateForm
#
#
# class FactorItemApprovalForm(forms.Form):
#     item_id = forms.IntegerField(widget=forms.HiddenInput)
#     # action = forms.ChoiceField(
#     #     choices=[('APPROVE', 'تأیید'), ('REJECT', 'رد'), ('NONE', 'هیچکدام')],
#     #     widget=forms.HiddenInput,
#     #     initial='NONE'
#     # )
#     # comment = forms.CharField(
#     #     required=False,
#     #     widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control comment-field'})
#     # )
#     #
#     action = forms.ChoiceField(
#         choices=[
#             ('PENDING', _('در انتظار')),
#             ('APPROVE', _('تأیید')),
#             ('REJECT', _('رد')),
#         ],
#         widget=forms.Select(attrs={'class': 'form-control form-select', 'style': 'max-width: 200px;'}),
#         label=_("اقدام"),
#         required=False,
#         initial='PENDING'
#     )
#     comment = forms.CharField(
#         widget=forms.Textarea(attrs={
#             'class': 'form-control',
#             'rows': 2,
#             'placeholder': _('توضیحات خود را اینجا وارد کنید...'),
#             'style': 'max-width: 500px;'
#         }),
#         required=False,
#         label=_("توضیحات")
#     )
#
# # ------------ New
# class FactorApprovalForm(forms.ModelForm):
#     """فرم تأیید یا رد فاکتور و ردیف‌های آن"""
#
#     comment = forms.CharField(
#         widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
#         required=False,
#         label=_("توضیحات کلی")
#     )
#
#     class Meta:
#         model = Factor
#         fields = ['comment']  # فقط توضیحات کلی برای کل فاکتور
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # اضافه کردن فیلدهای پویا برای هر ردیف فاکتور
#         for item in self.instance.items.all():
#             self.fields[f'action_{item.id}'] = forms.ChoiceField(
#                 choices=[
#                     ('', _('-------')),
#                     ('APPROVED', _('تأیید')),
#                     ('REJECTED', _('رد')),
#                 ],
#                 label=f"وضعیت ردیف: {item.description}",
#                 widget=forms.Select(attrs={'class': 'form-control'}),
#                 required=False
#             )
#             self.fields[f'comment_{item.id}'] = forms.CharField(
#                 label=f"توضیحات برای {item.description}",
#                 widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#                 required=False
#             )
#
#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         if commit:
#             instance.save()
#             # به‌روزرسانی وضعیت ردیف‌ها
#             for item in self.instance.items.all():
#                 action_field = f'action_{item.id}'
#                 comment_field = f'comment_{item.id}'
#                 if action_field in self.cleaned_data and self.cleaned_data[action_field]:
#                     item.status = self.cleaned_data[action_field]
#                     item.comment = self.cleaned_data[comment_field]
#                     item.save()
#         return instance
# # ------------
# class TankhahForm(JalaliDateForm):
#     date = forms.CharField(
#         label=_('تاریخ'),
#         widget=forms.TextInput(attrs={
#             'data-jdp': '',
#             'class': 'form-control',
#             'placeholder': _('مثال: 1404/01/17'),
#         })
#     )
#     due_date = forms.CharField(
#         label=_('مهلت زمانی'),
#         required=False,
#         widget=forms.TextInput(attrs={
#             'data-jdp': '',
#             'class': 'form-control',
#             'placeholder': _('مثال: 1404/01/17'),
#         })
#     )
#
#     class Meta:
#         model = Tankhah
#         fields = ['date', 'organization', 'project', 'subproject', 'letter_number', 'due_date', 'amount', 'description']
#         widgets = {
#             'organization': forms.Select(attrs={'class': 'form-control'}),
#             'project': forms.Select(attrs={'class': 'form-control'}),
#             'subproject': forms.Select(attrs={'class': 'form-control'}),
#             'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
#             'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
#             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
#         }
#
#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)
#         super().__init__(*args, **kwargs)
#
#         if self.user:
#             user_orgs = set(up.post.organization for up in self.user.userpost_set.filter(is_active=True))
#             self.fields['organization'].queryset = Organization.objects.filter(id__in=[org.id for org in user_orgs])
#             self.fields['project'].queryset = Project.objects.filter(organizations__in=user_orgs).distinct()
#
#             # فیلتر زیرپروژه‌ها
#             if 'project' in self.data:
#                 try:
#                     project_id = int(self.data.get('project'))
#                     self.fields['subproject'].queryset = SubProject.objects.filter(project_id=project_id)
#                 except (ValueError, TypeError):
#                     self.fields['subproject'].queryset = SubProject.objects.none()
#             elif self.instance.pk and self.instance.project:
#                 self.fields['subproject'].queryset = SubProject.objects.filter(project=self.instance.project)
#             else:
#                 self.fields['subproject'].queryset = SubProject.objects.none()
#
#             # غیرفعال کردن فیلدها در صورت عدم دسترسی
#             if self.instance.pk and self.instance.organization:
#                 user_posts = self.user.userpost_set.filter(is_active=True)
#                 if not any(post.post.organization == self.instance.organization for post in user_posts):
#                     for field_name in self.fields:
#                         if field_name not in ['status', 'description']:
#                             self.fields[field_name].disabled = True
#
#         self.set_jalali_initial('date', 'date')
#         self.set_jalali_initial('due_date', 'due_date')
#
#     def clean(self):
#         cleaned_data = super().clean()
#         project = cleaned_data.get('project')
#         subproject = cleaned_data.get('subproject')
#         amount = cleaned_data.get('amount')
#
#         if subproject and subproject.project != project:
#             raise forms.ValidationError(_("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))
#
#         if project and amount:
#             remaining_budget = get_subproject_remaining_budget(subproject) if subproject else get_project_remaining_budget(project)
#             if amount > remaining_budget:
#                 raise forms.ValidationError(
#                     _(f"مبلغ واردشده ({amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است.")
#                 )
#
#         return cleaned_data
#
#     def clean_date(self):
#         return self.clean_jalali_date('date') or timezone.now()
#
#     def clean_due_date(self):
#         return self.clean_jalali_date('due_date')
#
#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         if self.user:
#             user_post = self.user.userpost_set.filter(post__organization=instance.organization, is_active=True).first()
#             if not instance.pk:
#                 instance.created_by = self.user
#                 instance.last_stopped_post = user_post.post if user_post else None
#         if commit:
#             instance.save()
#         return instance
#
# class TanbakhApprovalForm(forms.ModelForm):
#     comment = forms.CharField(
#         widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
#         required=False,
#         label=_("توضیحات")
#     )
#
#     class Meta:
#         model = Tankhah
#         fields = []  # هیچ فیلد دیگری از مدل نیاز نیست
# # فرم برای اقلام فاکتور
# class FactorItemForm(forms.ModelForm):
#     """فرم ایجاد و ویرایش اقلام فاکتور"""
#     class Meta:
#         model = FactorItem
#         fields = ['description', 'amount', 'quantity']
#         widgets = {
#             'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('شرح ردیف')}),
#             'amount': forms.NumberInput(attrs={'class': 'form-control','placeholder': 'مبلغ را وارد کنید'}),
#             'quantity': forms.NumberInput(
#                 attrs={'class': 'form-control quantity-field', 'placeholder': _('تعداد'), 'min': '1'}),
#         }
#
#     def clean(self):
#         cleaned_data = super().clean()
#         amount = cleaned_data.get('amount')
#         quantity = cleaned_data.get('quantity')
#         if amount is not None and amount <= 0:
#             raise forms.ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
#         if quantity is not None and quantity < 1:
#             raise forms.ValidationError(_('تعداد باید حداقل ۱ باشد.'))
#         return cleaned_data
#
# class ApprovalForm(forms.ModelForm):
#     """فرم ثبت تأیید یا رد"""
#     action = forms.ChoiceField(choices=[
#         ('APPROVE', 'تأیید'),
#         ('REJECT', 'رد'),
#         ('RETURN', 'بازگشت'),
#         ('CANCEL', 'لغو')
#     ])
#
#     class Meta:
#         model = ApprovalLog
#         # fields = ['tankhah', 'factor', 'comment', 'action']  # user و date توسط سیستم پر می‌شوند
#         fields = ['action', 'comment', 'tankhah', 'factor', 'factor_item']
#         widgets = {
#             'tankhah': forms.Select(attrs={'class': 'form-control'}),
#             'factor': forms.Select(attrs={'class': 'form-control'}),
#             'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
#             'action': forms.Select(attrs={'class': 'form-control'}),
#
#             # 'tankhah': forms.HiddenInput(),
#             # 'factor': forms.HiddenInput(),
#             'factor_item': forms.HiddenInput(),
#
#             # 'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#         }
#         labels = {
#             'tankhah': _('تنخواه'),
#             'factor': _('فاکتور'),
#             'comment': _('توضیحات'),
#             'action': _('شاخه'),
#             # 'is_approved': _('تأیید شده؟'),
#         }
#
# """این فرم وضعیت و مرحله فعلی تنخواه را نمایش می‌دهد:"""
# class TankhahStatusForm(forms.ModelForm):
#     class Meta:
#         model = Tankhah
#         fields = ['status', 'current_stage', 'due_date', 'approved_by']
#         widgets = {
#             'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
#             'current_stage': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
#             'due_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
#             'approved_by': forms.SelectMultiple(attrs={'class': 'form-control', 'disabled': 'disabled'}),
#         }
#         labels = {
#             'status': _('وضعیت'),
#             'current_stage': _('مرحله فعلی'),
#             'due_date': _('مهلت زمانی'),
#             'approved_by': _('تأییدکنندگان'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # غیرفعال کردن فیلدها برای نمایش فقط خواندنی
#         for field in self.fields.values():
#             field.disabled = True
#
# class FactorStatusForm(forms.ModelForm):
#     class Meta:
#         model = Factor
#         fields = ['status']
#         widgets = {
#             'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
#         }
#         labels = {
#             'status': _('وضعیت'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields['status'].disabled = True
#
# """*** مهم ***"""
# """چون در مدل TanbakhDocument فقط یک document ذخیره می‌شود، اما ما چندین فایل را آپلود می‌کنیم. بنابراین نیازی به ModelForm نیست."""
# class MultipleFileInput(forms.ClearableFileInput):
#     allow_multiple_selected = True  # امکان انتخاب چندین فایل را فعال می‌کند
#
# class MultipleFileField(forms.FileField):
#     def __init__(self, *args, **kwargs):
#         # kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
#         kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}))
#         super().__init__(*args, **kwargs)
#
#     def clean(self, data, initial=None):
#         single_file_clean = super().clean
#         if isinstance(data, (list, tuple)):
#             # result = [single_file_clean(d, initial) for d in data]
#             # اطمینان از اینکه فقط فایل‌های آپلود شده معتبر را برمی‌گردانیم
#             result = [single_file_clean(d, initial) for d in data if d is not None]
#         else:
#             result = single_file_clean(data, initial)
#         return result
# # --- تعریف پسوندهای مجاز ---
# # ! لیست پسوندهای مجاز رو اینجا تعریف کن (با نقطه و حروف کوچک)
# ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png']
# # می‌تونی فرمت‌های دیگه مثل .txt, .odt, .ods, .gif, .zip, .rar رو هم اضافه کنی
# ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS) # برای نمایش در پیام خطا
#
# # --- فرم اسناد فاکتور (اصلاح شده با اعتبارسنجی) ---
# class FactorDocumentForm(forms.Form):
#     files = MultipleFileField(
#         label=_("بارگذاری اسناد فاکتور (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
#         required=False,
#         widget=MultipleFileInput(
#             attrs={
#                 'multiple': True,
#                 'class': 'form-control form-control-sm', # کلاس برای استایل بهتر
#                 'accept': ",".join(ALLOWED_EXTENSIONS) # راهنمایی به مرورگر برای فیلتر فایل‌ها
#                 }
#             )
#         )
#
#     def clean_files(self):
#         """اعتبارسنجی نوع فایل‌های آپلود شده برای اسناد فاکتور."""
#         files = self.cleaned_data.get('files')
#         if files: # اگر فایلی آپلود شده بود
#             invalid_files = []
#             for uploaded_file in files:
#                 if uploaded_file: # اطمینان از اینکه فایل None نیست
#                     # گرفتن پسوند فایل و تبدیل به حروف کوچک
#                     ext = os.path.splitext(uploaded_file.name)[1].lower()
#                     if ext not in ALLOWED_EXTENSIONS:
#                         invalid_files.append(uploaded_file.name)
#                         logger.warning(f"Invalid file type uploaded for FactorDocument: {uploaded_file.name} (type: {ext})")
#
#             # اگر فایل نامعتبری وجود داشت، خطا ایجاد کن
#             if invalid_files:
#                 invalid_files_str = ", ".join(invalid_files)
#                 error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
#                     files=invalid_files_str,
#                     allowed=ALLOWED_EXTENSIONS_STR
#                 )
#                 from django.core.exceptions import ValidationError
#                 raise ValidationError(error_msg)
#         return files # برگرداندن لیست فایل‌های (احتمالا) معتبر
#
# # --- فرم اسناد تنخواه (اصلاح شده با اعتبارسنجی) ---
# class TankhahDocumentForm(forms.Form):
#     # prefix='tankhah_docs'
#     documents = MultipleFileField(
#         label=_("بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
#         required=False,
#          widget=MultipleFileInput(
#             attrs={
#                 'multiple': True,
#                 'class': 'form-control form-control-sm',
#                 'accept': ",".join(ALLOWED_EXTENSIONS)
#                 }
#             )
#         )
#
#     def clean_documents(self):
#         """اعتبارسنجی نوع فایل‌های آپلود شده برای اسناد تنخواه."""
#         files = self.cleaned_data.get('documents')
#         if files:
#             invalid_files = []
#             for uploaded_file in files:
#                  if uploaded_file:
#                     ext = os.path.splitext(uploaded_file.name)[1].lower()
#                     if ext not in ALLOWED_EXTENSIONS:
#                         invalid_files.append(uploaded_file.name)
#                         logger.warning(f"Invalid file type uploaded for TankhahDocument: {uploaded_file.name} (type: {ext})")
#
#             if invalid_files:
#                 invalid_files_str = ", ".join(invalid_files)
#                 error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
#                     files=invalid_files_str,
#                     allowed=ALLOWED_EXTENSIONS_STR
#                 )
#                 from django.core.exceptions import ValidationError
#                 raise ValidationError(error_msg)
#         return files
#
#
# class FactorForm(forms.ModelForm):
#     date = forms.CharField(
#         label=_('تاریخ'),
#         widget=forms.TextInput(attrs={
#             'data-jdp': '',
#             'class': 'form-control',
#             'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
#         })
#     )
#     # amount = forms.DecimalField(
#     #     widget=NumberToWordsWidget(attrs={'placeholder': 'مجموع ارقام فاکتور را وارد کنید'}),
#     #     label='مبلغ'
#     # )
#     # number = forms.DecimalField(
#     #     widget=NumberToWordsWidget(attrs={'placeholder': 'تعداد را وارد کنید'}),
#     #     label='تعداد'
#     # )
#
#     class Meta:
#         model = Factor
#         fields = ['tankhah', 'date', 'amount', 'description']
#         widgets = {
#             'amount': forms.NumberInput(attrs={'class': 'form-control' }),
#             'tankhah': forms.Select(attrs={'class': 'form-control'}),
#             'description': forms.Textarea(
#                 attrs={'class': 'form-control', 'rows': 1, 'placeholder': _('توضیحات فاکتور')}),
#             }
#         labels = {
#             'tankhah': _('تنخواه'),
#             'date': _('تاریخ'),
#             'amount': _('مبلغ'),
#             'description': _('توضیحات'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         self.user = kwargs.pop('user', None)
#         self.tankhah = kwargs.pop('tankhah', None)
#         super().__init__(*args, **kwargs)
#         initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None
#
#         if self.user:
#             user_orgs = restrict_to_user_organization(self.user)
#             if user_orgs is None:  # HQ یا Superuser
#                 self.fields['tankhah'].queryset = Tankhah.objects.filter(
#                     status__in=['DRAFT', 'PENDING'],
#                     current_stage__order=initial_stage_order
#                 )
#             else:  # شعبات
#                 projects = Project.objects.filter(organizations__in=user_orgs)
#                 subprojects = SubProject.objects.filter(project__in=projects)
#                 queryset = Tankhah.objects.filter(
#                     status__in=['DRAFT', 'PENDING'],
#                     current_stage__order=initial_stage_order
#                 ).filter(
#                     models.Q(organization__in=user_orgs) |
#                     models.Q(project__in=projects) |
#                     models.Q(subproject__in=subprojects)
#                 ).distinct()
#                 self.fields['tankhah'].queryset = queryset
#                 logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")
#
#         if self.instance.pk:
#             self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.instance.tankhah.id)
#             self.fields['tankhah'].initial = self.instance.tankhah
#             if self.instance.date:
#                 j_date = jdatetime.date.fromgregorian(date=self.instance.date)
#                 jalali_date_str = j_date.strftime('%Y/%m/%d')
#                 self.fields['date'].initial = jalali_date_str
#                 self.initial['date'] = jalali_date_str
#
#             amount_rounded = round(Decimal(self.instance.amount))
#                 # ویجت CharField انتظار رشته دارد
#             self.initial['amount'] = str(int(amount_rounded))
#             logger.info(f'Initial amount set for widget: {self.initial["amount"]}')
#
#         elif self.tankhah:
#             self.fields['tankhah'].initial = self.tankhah
#
#         if self.instance.pk and self.user and not self.user.has_perm('tankhah.Factor_full_edit'):
#             for field_name in self.fields:
#                 self.fields[field_name].disabled = True
#
#     def clean_date(self):
#         date_str = self.cleaned_data.get('date')
#         if not date_str:
#             raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
#         try:
#             j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
#             gregorian_date = j_date.togregorian()
#             return timezone.make_aware(gregorian_date)
#         except ValueError:
#             raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
#
#     def clean_amount(self):
#         amount_str = self.cleaned_data.get('amount', '')  # چون CharField است، مقدار رشته‌ای است
#         if amount_str is None or str(amount_str).strip() == '':
#             raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
#
#         from decimal import InvalidOperation
#         try:
#             # 1. تبدیل اعداد فارسی به انگلیسی و حذف کاما
#             # حتما تابع to_english_digits را import کرده باشید
#             english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
#
#             # 2. تبدیل به Decimal برای دقت (یا float اگر دقت خیلی بالا لازم نیست)
#             amount_decimal = Decimal(english_amount_str)
#
#             # 3. گرد کردن به نزدیک‌ترین عدد صحیح
#             # round() پایتون به نزدیک‌ترین زوج گرد می‌کند (برای x.5)
#             # Decimal.quantize(Decimal('1')) روش دقیق‌تر گرد کردن عادی است
#             # اما round() معمولا کافیست
#             amount_rounded = round(amount_decimal)
#
#             # 4. تبدیل به عدد صحیح (int)
#             amount_int = int(amount_rounded)
#
#             # 5. اعتبارسنجی مقدار
#             if amount_int <= 0:
#                 raise forms.ValidationError(_("مبلغ باید بزرگتر از صفر باشد."))
#
#             logger.info(
#                 f"Cleaned amount: Original='{amount_str}', English='{english_amount_str}', Decimal='{amount_decimal}', RoundedInt='{amount_int}'")
#             return amount_int  # مقدار گرد شده و صحیح را برمی‌گردانیم
#
#         except (ValueError, TypeError, InvalidOperation):
#             logger.warning(f"Invalid amount input: '{amount_str}'")
#             raise forms.ValidationError(_("لطفاً یک عدد معتبر برای مبلغ وارد کنید (فقط عدد)."))
#
#
#     def clean_quantity(self):
#         quantity_str = self.cleaned_data.get('quantity', '')
#         if quantity_str:
#             try:
#                 # تبدیل اعداد پارسی به انگلیسی
#                 quantity_str = to_english_digits(str(quantity_str))
#                 quantity_val = int(quantity_str)
#                 if quantity_val <= 0:
#                     raise forms.ValidationError(_("تعداد باید بزرگتر از صفر باشد."))
#                 return quantity_val
#             except (ValueError, TypeError):
#                 raise forms.ValidationError(_("لطفاً یک عدد معتبر برای تعداد وارد کنید."))
#         raise forms.ValidationError(_("وارد کردن تعداد الزامی است."))
#
#     def save(self, commit=True):
#         instance = super().save(commit=False)
#         if self.user and self.instance.pk and self.has_changed():
#             old_instance = Factor.objects.get(pk=self.instance.pk)
#             for field in self.changed_data:
#                 old_value = getattr(old_instance, field)
#                 new_value = getattr(instance, field)
#                 logger.info(f"تغییر در فاکتور {instance.number}: {field} از {old_value} به {new_value} توسط {self.user}")
#         if commit:
#             instance.save()
#         return instance
#
# class old__FactorForm(forms.ModelForm):
#     date = forms.CharField(
#         label=_('تاریخ فاکتور'),
#         widget=forms.TextInput(attrs={
#             'data-jdp': '',
#             'class': 'form-control form-control-sm',
#             'placeholder': _('مثال: ۱۴۰۳/۰۴/۲۷')
#         })
#     )
#     amount = forms.DecimalField(
#         label=_("مبلغ کل فاکتور (ریال)"),
#         max_digits=20,
#         decimal_places=2,
#         widget=forms.NumberInput(attrs={
#             'class': 'form-control form-control-sm ltr-input total-factor-amount',
#             'placeholder': _('مبلغ کل فاکتور'),
#             'step': '0.01'
#         }),
#         help_text=_("این مبلغ باید برابر با مجموع مبالغ ردیف‌ها باشد.")
#     )
#
#     class Meta:
#         from tankhah.models import Factor   # وارد کردن مدل‌ها
#         model = Factor
#         fields = ['tankhah', 'date', 'amount', 'description']
#         widgets = {
#             'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}),
#             'description': forms.Textarea(
#                 attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': _('توضیحات کلی فاکتور (اختیاری)')}),
#         }
#         labels = {
#             'tankhah': _('مربوط به تنخواه شماره'),
#             'description': _('توضیحات'),
#         }
#
#     def __init__(self, *args, **kwargs):
#         from tankhah.models import  Tankhah  # وارد کردن مدل‌ها
#         self.user = kwargs.pop('user', None)
#         tankhah_instance = kwargs.pop('tankhah', None)
#         super().__init__(*args, **kwargs)
#
#         initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None
#         if self.user:
#             from tankhah.models import   Tankhah  # وارد کردن مدل‌ها
#             from tankhah.utils import restrict_to_user_organization
#             user_orgs = restrict_to_user_organization(self.user)
#             base_tankhah_qs = Tankhah.objects.filter(is_archived=False)
#             if user_orgs is None:
#                 self.fields['tankhah'].queryset = base_tankhah_qs
#             else:
#                 projects = Project.objects.filter(organizations__in=user_orgs)
#                 subprojects = SubProject.objects.filter(project__in=projects)
#                 queryset = base_tankhah_qs.filter(
#                     Q(organization__in=user_orgs) |
#                     Q(project__in=projects) |
#                     Q(subproject__in=subprojects)
#                 ).distinct()
#                 self.fields['tankhah'].queryset = queryset
#                 logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")
#
#         if self.instance and self.instance.pk:
#             if self.instance.date:
#                 try:
#                     j_date = jdatetime.date.fromgregorian(date=self.instance.date)
#                     self.initial['date'] = j_date.strftime('%Y/%m/%d')
#                 except Exception as e:
#                     logger.error(f"Error converting date for instance {self.instance.pk}: {e}")
#                     self.initial['date'] = ''
#             self.initial['amount'] = self.instance.amount
#             self.fields['tankhah'].disabled = True
#             self.fields['tankhah'].queryset = Tankhah.objects.filter(pk=self.instance.tankhah_id)
#             self.initial['tankhah'] = self.instance.tankhah_id
#         elif tankhah_instance:
#             self.initial['tankhah'] = tankhah_instance
#             self.fields['tankhah'].widget = forms.HiddenInput()
#
#         if self.instance.pk and self.user and not self.user.has_perm('tankhah.edit_full_tankhah'):
#             for field_name in self.fields:
#                 self.fields[field_name].disabled = True
#
#     def clean_date(self):
#         date_str = self.cleaned_data.get('date')
#         if not date_str:
#             raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
#         try:
#             date_str_en = to_english_digits(date_str)
#             j_dt = jdatetime.datetime.strptime(date_str_en, '%Y/%m/%d')
#             return j_dt.togregorian().date()
#         except (ValueError, TypeError):
#             raise forms.ValidationError(_('فرمت تاریخ نامعتبر است. مثال: ۱۴۰۳/۰۴/۲۷'))
#
#     def clean_amount(self):
#         amount = self.cleaned_data.get('amount')
#         if amount is None:
#             raise forms.ValidationError(_("وارد کردن مبلغ کل فاکتور الزامی است."))
#         if amount <= 0:
#             raise forms.ValidationError(_("مبلغ کل فاکتور باید بزرگتر از صفر باشد."))
#         return amount
#
#     def clean(self):
#         cleaned_data = super().clean()
#         factor_total_amount = cleaned_data.get('amount')
#         tankhah_instance = cleaned_data.get('tankhah')
#         items_total_amount = Decimal('0')
#         has_items = False
#
#         formset = FactorItemFormSet(self.data if self.is_bound else None, prefix='form', instance=self.instance if self.instance.pk else None)
#         logger.info(f"Formset data: {self.data.get('form-TOTAL_FORMS')}, {self.data.get('form-INITIAL_FORMS')}")
#         logger.info(f"Formset forms: {[form.cleaned_data for form in formset if form.cleaned_data]}")
#
#         if not formset.is_valid():
#             logger.warning(f"FactorItemFormSet is not valid: {formset.errors}")
#             logger.warning(f"Non-form errors: {formset.non_form_errors()}")
#             for form in formset:
#                 if form.errors:
#                     for field, errors in form.errors.items():
#                         self.add_error(None, f"ردیف {form.prefix}: {field} - {errors}")
#         else:
#             for form in formset:
#                 if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
#                     item_amount = form.cleaned_data.get('amount', Decimal('0'))
#                     if item_amount > 0:
#                         items_total_amount += item_amount
#                         has_items = True
#
#         if not has_items and self.is_bound:
#             self.add_error(None, _("فاکتور باید حداقل دارای یک ردیف با مبلغ معتبر باشد."))
#
#         if factor_total_amount is not None and has_items:
#             if abs(factor_total_amount - items_total_amount) > 0.01:
#                 self.add_error('amount', _(
#                     "مبلغ کل فاکتور ({amount_factor}) با مجموع مبالغ ردیف‌ها ({amount_items}) مطابقت ندارد."
#                 ).format(
#                     amount_factor=factor_total_amount.normalize(),
#                     amount_items=items_total_amount.normalize()
#                 ))
#                 logger.warning("Mismatch between factor amount and items sum.")
#
#         if tankhah_instance and factor_total_amount is not None:
#             try:
#                 tankhah_remaining = get_tankhah_remaining_budget(tankhah_instance)
#                 if factor_total_amount > tankhah_remaining:
#                     self.add_error('amount', _(
#                         "مبلغ کل فاکتور ({factor_amount}) نمی‌تواند از باقی‌مانده تنخواه ({tankhah_remain}) بیشتر باشد."
#                     ).format(
#                         factor_amount=factor_total_amount.normalize(),
#                         tankhah_remain=tankhah_remaining.normalize()
#                     ))
#                     logger.warning("Factor amount exceeds remaining tankhah budget.")
#             except Exception as e:
#                 logger.error(f"Error getting tankhah remaining budget: {e}")
#                 self.add_error(None, _("خطا در بررسی بودجه تنخواه."))
#
#         return cleaned_data
#
# # فرم برای اقلام فاکتور
# class old___FactorItemForm(forms.ModelForm):
#     """فرم ایجاد و ویرایش اقلام فاکتور"""
#     class Meta:
#         from tankhah.models import  FactorItem  # وارد کردن مدل‌ها
#         model = FactorItem
#         fields = ['description', 'amount', 'quantity']
#         widgets = {
#             'description': forms.TextInput(
#                 attrs={'class': 'form-control form-control-sm', 'placeholder': _('شرح ردیف')}),
#             'amount': forms.NumberInput(
#                 attrs={'class': 'form-control form-control-sm ltr-input amount-field', 'placeholder': _('مبلغ کل'),
#                        'step': '0.01'}),
#             'quantity': forms.NumberInput(
#                 attrs={'class': 'form-control form-control-sm ltr-input quantity-field', 'placeholder': _('تعداد'),
#                        'min': '1', 'step': '0.01'}),
#         }
#
#     def clean(self):
#         cleaned_data = super().clean()
#         amount = cleaned_data.get('amount')
#         quantity = cleaned_data.get('quantity')
#         if amount is not None and amount <= 0:
#             raise ValidationError(_('مبلغ باید بزرگ‌تر از صفر باشد.'))
#         if quantity is not None and quantity < 1:
#             raise ValidationError(_('تعداد باید حداقل ۱ باشد.'))
#         logger.info(f"Cleaned FactorItemForm: description={cleaned_data.get('description')}, amount={amount}, quantity={quantity}")
#         return cleaned_data
# # تعریف فرم‌ست در انتهای فایل
# FactorItemFormSet = inlineformset_factory(
#       Factor, FactorItem, form=FactorItemForm,
#     fields=['description', 'amount', 'quantity'],
#     extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
# )
#
#
#
# # import os
# # import logging
# # from decimal import Decimal
# #
# # from django.core.exceptions import ValidationError
# # from django.db.models import Q
# #
# # import tankhah.models
# # # from dis import CONVERT_VALUE
# #
# # from Tanbakhsystem.widgets import NumberToWordsWidget
# # from budgets.budget_calculations import get_subproject_remaining_budget, get_project_remaining_budget, \
# #     get_tankhah_remaining_budget
# #
# # logger = logging.getLogger(__name__)
# #
# # from django.db import models
# # from .utils import restrict_to_user_organization
# # import jdatetime
# # from django.utils import timezone
# # from Tanbakhsystem.utils import convert_to_farsi_numbers, to_english_digits
# # from core.models import WorkflowStage, Project, Organization,SubProject
# # from django import forms
# # from django.utils.translation import gettext_lazy as _
# # from django.forms import inlineformset_factory
# # from Tanbakhsystem.base import JalaliDateForm
# #
# #
# # class FactorItemApprovalForm(forms.Form):
# #     item_id = forms.IntegerField(widget=forms.HiddenInput)
# #     # action = forms.ChoiceField(
# #     #     choices=[('APPROVE', 'تأیید'), ('REJECT', 'رد'), ('NONE', 'هیچکدام')],
# #     #     widget=forms.HiddenInput,
# #     #     initial='NONE'
# #     # )
# #     # comment = forms.CharField(
# #     #     required=False,
# #     #     widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control comment-field'})
# #     # )
# #     #
# #     action = forms.ChoiceField(
# #         choices=[
# #             ('PENDING', _('در انتظار')),
# #             ('APPROVE', _('تأیید')),
# #             ('REJECT', _('رد')),
# #         ],
# #         widget=forms.Select(attrs={'class': 'form-control form-select', 'style': 'max-width: 200px;'}),
# #         label=_("اقدام"),
# #         required=False,
# #         initial='PENDING'
# #     )
# #     comment = forms.CharField(
# #         widget=forms.Textarea(attrs={
# #             'class': 'form-control',
# #             'rows': 2,
# #             'placeholder': _('توضیحات خود را اینجا وارد کنید...'),
# #             'style': 'max-width: 500px;'
# #         }),
# #         required=False,
# #         label=_("توضیحات")
# #     )
# #
# # # ------------ New
# # class FactorApprovalForm(forms.ModelForm):
# #     """فرم تأیید یا رد فاکتور و ردیف‌های آن"""
# #
# #     comment = forms.CharField(
# #         widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
# #         required=False,
# #         label=_("توضیحات کلی")
# #     )
# #
# #     class Meta:
# #         from .models import Factor
# #         model = Factor
# #         fields = ['comment']  # فقط توضیحات کلی برای کل فاکتور
# #
# #     def __init__(self, *args, **kwargs):
# #         super().__init__(*args, **kwargs)
# #         # اضافه کردن فیلدهای پویا برای هر ردیف فاکتور
# #         for item in self.instance.items.all():
# #             self.fields[f'action_{item.id}'] = forms.ChoiceField(
# #                 choices=[
# #                     ('', _('-------')),
# #                     ('APPROVED', _('تأیید')),
# #                     ('REJECTED', _('رد')),
# #                 ],
# #                 label=f"وضعیت ردیف: {item.description}",
# #                 widget=forms.Select(attrs={'class': 'form-control'}),
# #                 required=False
# #             )
# #             self.fields[f'comment_{item.id}'] = forms.CharField(
# #                 label=f"توضیحات برای {item.description}",
# #                 widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
# #                 required=False
# #             )
# #
# #     def save(self, commit=True):
# #         instance = super().save(commit=False)
# #         if commit:
# #             instance.save()
# #             # به‌روزرسانی وضعیت ردیف‌ها
# #             for item in self.instance.items.all():
# #                 action_field = f'action_{item.id}'
# #                 comment_field = f'comment_{item.id}'
# #                 if action_field in self.cleaned_data and self.cleaned_data[action_field]:
# #                     item.status = self.cleaned_data[action_field]
# #                     item.comment = self.cleaned_data[comment_field]
# #                     item.save()
# #         return instance
# # # ------------
# # class TankhahForm(JalaliDateForm):
# #     date = forms.CharField(
# #         label=_('تاریخ'),
# #         widget=forms.TextInput(attrs={
# #             'data-jdp': '',
# #             'class': 'form-control',
# #             'placeholder': _('مثال: ۱۴۰۳/۰۴/۲۷')
# #         })
# #     )
# #     due_date = forms.CharField(
# #         label=_('مهلت زمانی'),
# #         required=False,
# #         widget=forms.TextInput(attrs={
# #             'data-jdp': '',
# #             'class': 'form-control',
# #             'placeholder': _('مثال: 1404/01/17'),
# #         })
# #     )
# #     amount = forms.DecimalField(
# #         label=_("مبلغ کل فاکتور (ریال)"),
# #         max_digits=20,
# #         decimal_places=2,
# #         widget=forms.NumberInput(attrs={
# #             'class': 'form-control form-control-sm ltr-input total-factor-amount',
# #             'placeholder': _('مبلغ کل فاکتور'),
# #             'step': '0.01'
# #         }),
# #         help_text=_("این مبلغ باید برابر با مجموع مبالغ ردیف‌ها باشد.")
# #     )
# #
# #     class Meta:
# #         from .models import  Tankhah  # وارد کردن مدل‌ها
# #         model = Tankhah
# #         fields = ['date', 'organization', 'project', 'subproject', 'letter_number', 'due_date', 'amount', 'description', 'budget_allocation']
# #         widgets = {
# #             'organization': forms.Select(attrs={'class': 'form-control'}),
# #             'project': forms.Select(attrs={'class': 'form-control'}),
# #             'subproject': forms.Select(attrs={'class': 'form-control'}),
# #             'letter_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('اختیاری')}),
# #             'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
# #             'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
# #             'budget_allocation': forms.HiddenInput(),  # مخفی کردن فیلد
# #         }
# #         labels = {
# #             'tankhah': _('مربوط به تنخواه شماره'),
# #             'description': _('توضیحات'),
# #         }
# #
# #     def __init__(self, *args, **kwargs):
# #         self.user = kwargs.pop('user', None)
# #         tankhah_instance = kwargs.pop('tankhah', None)
# #         # غیراجباری کردن فیلد budget_allocation
# #         self.fields['budget_allocation'].required = False
# #         super().__init__(*args, **kwargs)
# #         initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None
# #
# #         if self.user:
# #             user_orgs = set(up.post.organization for up in self.user.userpost_set.filter(is_active=True))
# #             self.fields['organization'].queryset = Organization.objects.filter(id__in=[org.id for org in user_orgs])
# #             self.fields['project'].queryset = Project.objects.filter(organizations__in=user_orgs).distinct()
# #
# #             # فیلتر زیرپروژه‌ها
# #             if 'project' in self.data:
# #                 try:
# #                     project_id = int(self.data.get('project'))
# #                     self.fields['subproject'].queryset = SubProject.objects.filter(project_id=project_id)
# #                 except (ValueError, TypeError):
# #                     self.fields['subproject'].queryset = SubProject.objects.none()
# #             elif self.instance.pk and self.instance.project:
# #                 self.fields['subproject'].queryset = SubProject.objects.filter(project=self.instance.project)
# #             else:
# #                 self.fields['subproject'].queryset = SubProject.objects.none()
# #
# #             # غیرفعال کردن فیلدها در صورت عدم دسترسی
# #             if self.instance.pk and self.instance.organization:
# #                 user_posts = self.user.userpost_set.filter(is_active=True)
# #                 if not any(post.post.organization == self.instance.organization for post in user_posts):
# #                     for field_name in self.fields:
# #                         if field_name not in ['status', 'description']:
# #                             self.fields[field_name].disabled = True
# #
# #             # مقداردهی خودکار budget_allocation
# #             if 'project' in self.data:
# #                 try:
# #                     project_id = int(self.data.get('project'))
# #                     project = Project.objects.get(id=project_id)
# #                     subproject_id = self.data.get('subproject')
# #                     subproject = SubProject.objects.get(id=subproject_id) if subproject_id else None
# #
# #                     from budgets.models import ProjectBudgetAllocation
# #                     if subproject:
# #                         allocation = ProjectBudgetAllocation.objects.filter(
# #                             subproject=subproject
# #                         ).first()
# #                     else:
# #                         allocation = ProjectBudgetAllocation.objects.filter(
# #                             project=project,
# #                             subproject__isnull=True
# #                         ).first()
# #
# #                     if allocation:
# #                         self.initial['budget_allocation'] = allocation.budget_allocation.id
# #                         self.data = self.data.copy()  # برای تغییر مقدار در data
# #                         self.data['budget_allocation'] = str(allocation.budget_allocation.id)
# #
# #                     else:
# #                         self.add_error(None, _("تخصیص بودجه معتبر برای این پروژه/زیرپروژه یافت نشد."))
# #                 except (ValueError, Project.DoesNotExist, SubProject.DoesNotExist):
# #                     self.add_error('project', _("پروژه یا زیرپروژه نامعتبر است."))
# #
# #         self.set_jalali_initial('date', 'date')
# #         self.set_jalali_initial('due_date', 'due_date')
# #
# #     def clean(self):
# #         cleaned_data = super().clean()
# #         project = cleaned_data.get('project')
# #         subproject = cleaned_data.get('subproject')
# #         amount = cleaned_data.get('amount')
# #         budget_allocation = cleaned_data.get('budget_allocation')
# #
# #         logger.info(f"داده‌های پاک‌شده در clean: {cleaned_data}")
# #
# #         if subproject and subproject.project != project:
# #             raise forms.ValidationError(_("زیرپروژه باید متعلق به پروژه انتخاب‌شده باشد."))
# #
# #         if project and amount:
# #             remaining_budget = get_subproject_remaining_budget(subproject) if subproject else get_project_remaining_budget(project)
# #             if amount > remaining_budget:
# #                 raise forms.ValidationError(
# #                     _(f"مبلغ واردشده ({amount:,.0f} ریال) بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) است.")
# #                 )
# #
# #         # اعتبارسنجی budget_allocation
# #         if not budget_allocation:
# #             logger.warning("budget_allocation مقدار ندارد. این ممکن است باعث مشکلاتی در مراحل بعدی شود.")
# #             # می‌توانید در اینجا تصمیم بگیرید که خطا اضافه کنید یا خیر
# #             # self.add_error('budget_allocation', _("تخصیص بودجه الزامی است."))
# #
# #         return cleaned_data
# #
# #     def clean_date(self):
# #         return self.clean_jalali_date('date') or timezone.now()
# #
# #     def clean_due_date(self):
# #         return self.clean_jalali_date('due_date')
# #
# #     def save(self, commit=True):
# #         instance = super().save(commit=False)
# #         if self.user:
# #             user_post = self.user.userpost_set.filter(post__organization=instance.organization, is_active=True).first()
# #             if not instance.pk:
# #                 instance.created_by = self.user
# #                 instance.last_stopped_post = user_post.post if user_post else None
# #         if commit:
# #             instance.save()
# #         return instance
# #
# # class TanbakhApprovalForm(forms.ModelForm):
# #     comment = forms.CharField(
# #         widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
# #         required=False,
# #         label=_("توضیحات")
# #     )
# #
# #     class Meta:
# #         from .models import   Tankhah  # وارد کردن مدل‌ها
# #         model = Tankhah
# #         fields = []  # هیچ فیلد دیگری از مدل نیاز نیست
# # class OLD___FactorForm(forms.ModelForm):
# #     date = forms.CharField(
# #         label=_('تاریخ'),
# #         widget=forms.TextInput(attrs={
# #             'data-jdp': '',
# #             'class': 'form-control',
# #             'placeholder': convert_to_farsi_numbers(_('تاریخ را انتخاب کنید (1404/01/17)'))
# #         })
# #     )
# #
# #     class Meta:
# #         from .models import Factor # وارد کردن مدل‌ها
# #         model = Factor
# #         fields = ['tankhah', 'date', 'amount', 'description']
# #         widgets = {
# #             'amount': forms.NumberInput(attrs={'class': 'form-control' }),
# #             'tankhah': forms.Select(attrs={'class': 'form-control'}),
# #             'description': forms.Textarea(
# #                 attrs={'class': 'form-control', 'rows': 1, 'placeholder': _('توضیحات فاکتور')}),
# #             }
# #         labels = {
# #             'tankhah': _('تنخواه'),
# #             'date': _('تاریخ'),
# #             'amount': _('مبلغ'),
# #             'description': _('توضیحات'),
# #         }
# #
# #     def __init__(self, *args, **kwargs):
# #         from .models import  Tankhah  # وارد کردن مدل‌ها
# #         self.user = kwargs.pop('user', None)
# #         self.tankhah = kwargs.pop('tankhah', None)
# #         super().__init__(*args, **kwargs)
# #         initial_stage_order = WorkflowStage.objects.order_by('order').first().order if WorkflowStage.objects.exists() else None
# #
# #         if self.user:
# #             from .models import  Tankhah  # وارد کردن مدل‌ها
# #             user_orgs = restrict_to_user_organization(self.user)
# #             if user_orgs is None:  # HQ یا Superuser
# #                 self.fields['tankhah'].queryset = Tankhah.objects.filter(
# #                     status__in=['DRAFT', 'PENDING'],
# #                     current_stage__order=initial_stage_order
# #                 )
# #             else:  # شعبات
# #                 projects = Project.objects.filter(organizations__in=user_orgs)
# #                 subprojects = SubProject.objects.filter(project__in=projects)
# #                 queryset = Tankhah.objects.filter(
# #                     status__in=['DRAFT', 'PENDING'],
# #                     current_stage__order=initial_stage_order
# #                 ).filter(
# #                     models.Q(organization__in=user_orgs) |
# #                     models.Q(project__in=projects) |
# #                     models.Q(subproject__in=subprojects)
# #                 ).distinct()
# #                 self.fields['tankhah'].queryset = queryset
# #                 logger.info(f"Tankhah queryset: {list(queryset.values('number', 'project__name', 'subproject__name'))}")
# #
# #         if self.instance.pk:
# #             self.fields['tankhah'].queryset = Tankhah.objects.filter(id=self.instance.tankhah.id)
# #             self.fields['tankhah'].initial = self.instance.tankhah
# #             if self.instance.date:
# #                 j_date = jdatetime.date.fromgregorian(date=self.instance.date)
# #                 jalali_date_str = j_date.strftime('%Y/%m/%d')
# #                 self.fields['date'].initial = jalali_date_str
# #                 self.initial['date'] = jalali_date_str
# #
# #             amount_rounded = round(Decimal(self.instance.amount))
# #                 # ویجت CharField انتظار رشته دارد
# #             self.initial['amount'] = str(int(amount_rounded))
# #             logger.info(f'Initial amount set for widget: {self.initial["amount"]}')
# #
# #         elif self.tankhah:
# #             self.fields['tankhah'].initial = self.tankhah
# #
# #         if self.instance.pk and self.user and not self.user.has_perm('tankhah.Factor_full_edit'):
# #             for field_name in self.fields:
# #                 self.fields[field_name].disabled = True
# #
# #     def clean_date(self):
# #         date_str = self.cleaned_data.get('date')
# #         if not date_str:
# #             raise forms.ValidationError(_('تاریخ فاکتور اجباری است.'))
# #         try:
# #             j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d')
# #             gregorian_date = j_date.togregorian()
# #             return timezone.make_aware(gregorian_date)
# #         except ValueError:
# #             raise forms.ValidationError(_('لطفاً تاریخ معتبری وارد کنید (مثل 1404/01/17).'))
# #
# #     def clean_amount(self):
# #         amount_str = self.cleaned_data.get('amount', '')  # چون CharField است، مقدار رشته‌ای است
# #         if amount_str is None or str(amount_str).strip() == '':
# #             raise forms.ValidationError(_("وارد کردن مبلغ الزامی است."))
# #
# #         from decimal import InvalidOperation
# #         try:
# #             # 1. تبدیل اعداد فارسی به انگلیسی و حذف کاما
# #             # حتما تابع to_english_digits را import کرده باشید
# #             english_amount_str = to_english_digits(str(amount_str)).replace(',', '')
# #
# #             # 2. تبدیل به Decimal برای دقت (یا float اگر دقت خیلی بالا لازم نیست)
# #             amount_decimal = Decimal(english_amount_str)
# #
# #             # 3. گرد کردن به نزدیک‌ترین عدد صحیح
# #             # round() پایتون به نزدیک‌ترین زوج گرد می‌کند (برای x.5)
# #             # Decimal.quantize(Decimal('1')) روش دقیق‌تر گرد کردن عادی است
# #             # اما round() معمولا کافیست
# #             amount_rounded = round(amount_decimal)
# #
# #             # 4. تبدیل به عدد صحیح (int)
# #             amount_int = int(amount_rounded)
# #
# #             # 5. اعتبارسنجی مقدار
# #             if amount_int <= 0:
# #                 raise forms.ValidationError(_("مبلغ باید بزرگتر از صفر باشد."))
# #
# #             logger.info(
# #                 f"Cleaned amount: Original='{amount_str}', English='{english_amount_str}', Decimal='{amount_decimal}', RoundedInt='{amount_int}'")
# #             return amount_int  # مقدار گرد شده و صحیح را برمی‌گردانیم
# #
# #         except (ValueError, TypeError, InvalidOperation):
# #             logger.warning(f"Invalid amount input: '{amount_str}'")
# #             raise forms.ValidationError(_("لطفاً یک عدد معتبر برای مبلغ وارد کنید (فقط عدد)."))
# #
# #     def clean(self):
# #         cleaned_data = super().clean()
# #         amount = cleaned_data.get('amount')
# #         tankhah = cleaned_data.get('tankhah')
# #
# #         # اعتبارسنجی بودجه تنخواه
# #         if tankhah and amount:
# #             tankhah_remaining = get_tankhah_remaining_budget(tankhah)
# #             if amount > tankhah_remaining:
# #                 raise ValidationError(
# #                     _(f"مبلغ فاکتور ({amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده تنخواه ({tankhah_remaining:,.0f} ریال) باشد.")
# #                 )
# #
# #         # اعتبارسنجی اقلام
# #         if self.data and 'form-TOTAL_FORMS' in self.data:
# #             from tankhah.view_folder_tankhah.forms_factor import FactorItemFormSet
# #             formset = FactorItemFormSet(self.data, self.files, prefix='form')
# #             if formset.is_valid():
# #                 total_items_amount = sum(
# #                     Decimal(form.cleaned_data.get('amount', 0)) * form.cleaned_data.get('quantity', 1)
# #                     for form in formset if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
# #                 )
# #                 if amount is not None and total_items_amount != amount:
# #                     raise ValidationError(
# #                         _(f"مجموع مبالغ اقلام ({total_items_amount:,.0f} ریال) با مبلغ فاکتور ({amount:,.0f} ریال) مطابقت ندارد.")
# #                     )
# #             else:
# #                 for form in formset:
# #                     for field, errors in form.errors.items():
# #                         for error in errors:
# #                             self.add_error(None, f"ردیف {form.prefix}: {field} - {error}")
# #
# #
# #         return cleaned_data
# #
# #     def clean_quantity(self):
# #         quantity_str = self.cleaned_data.get('quantity', '')
# #         if quantity_str:
# #             try:
# #                 # تبدیل اعداد پارسی به انگلیسی
# #                 quantity_str = to_english_digits(str(quantity_str))
# #                 quantity_val = int(quantity_str)
# #                 if quantity_val <= 0:
# #                     raise forms.ValidationError(_("تعداد باید بزرگتر از صفر باشد."))
# #                 return quantity_val
# #             except (ValueError, TypeError):
# #                 raise forms.ValidationError(_("لطفاً یک عدد معتبر برای تعداد وارد کنید."))
# #         raise forms.ValidationError(_("وارد کردن تعداد الزامی است."))
# #
# #     def save(self, commit=True):
# #         from .models import Factor   # وارد کردن مدل‌ها
# #         instance = super().save(commit=False)
# #         if self.user and self.instance.pk and self.has_changed():
# #             old_instance = Factor.objects.get(pk=self.instance.pk)
# #             for field in self.changed_data:
# #                 old_value = getattr(old_instance, field)
# #                 new_value = getattr(instance, field)
# #                 logger.info(f"تغییر در فاکتور {instance.number}: {field} از {old_value} به {new_value} توسط {self.user}")
# #         if commit:
# #             instance.save()
# #         return instance
# # # FactorItemFormSet = inlineformset_factory(
# # #     tankhah.models.Factor , tankhah.models.FactorItem, form=FactorItemForm,
# # #     fields=['description', 'amount', 'quantity'],
# # #     extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
# # # )
# #
# # class ApprovalForm(forms.ModelForm):
# #     """فرم ثبت تأیید یا رد"""
# #     action = forms.ChoiceField(choices=[
# #         ('APPROVE', 'تأیید'),
# #         ('REJECT', 'رد'),
# #         ('RETURN', 'بازگشت'),
# #         ('CANCEL', 'لغو')
# #     ])
# #
# #     class Meta:
# #         from tankhah.models import ApprovalLog
# #         model = ApprovalLog
# #         # fields = ['tankhah', 'factor', 'comment', 'action']  # user و date توسط سیستم پر می‌شوند
# #         fields = ['action', 'comment', 'tankhah', 'factor', 'factor_item']
# #         widgets = {
# #             'tankhah': forms.Select(attrs={'class': 'form-control'}),
# #             'factor': forms.Select(attrs={'class': 'form-control'}),
# #             'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('توضیحات اختیاری')}),
# #             'action': forms.Select(attrs={'class': 'form-control'}),
# #
# #             # 'tankhah': forms.HiddenInput(),
# #             # 'factor': forms.HiddenInput(),
# #             'factor_item': forms.HiddenInput(),
# #
# #             # 'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
# #         }
# #         labels = {
# #             'tankhah': _('تنخواه'),
# #             'factor': _('فاکتور'),
# #             'comment': _('توضیحات'),
# #             'action': _('شاخه'),
# #             # 'is_approved': _('تأیید شده؟'),
# #         }
# #
# # """این فرم وضعیت و مرحله فعلی تنخواه را نمایش می‌دهد:"""
# # class TankhahStatusForm(forms.ModelForm):
# #     class Meta:
# #         from tankhah.models import Tankhah
# #         model = Tankhah
# #         fields = ['status', 'current_stage', 'due_date', 'approved_by']
# #         widgets = {
# #             'status': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
# #             'current_stage': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
# #             'due_date': forms.DateInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
# #             'approved_by': forms.SelectMultiple(attrs={'class': 'form-control', 'disabled': 'disabled'}),
# #         }
# #         labels = {
# #             'status': _('وضعیت'),
# #             'current_stage': _('مرحله فعلی'),
# #             'due_date': _('مهلت زمانی'),
# #             'approved_by': _('تأییدکنندگان'),
# #         }
# #
# #     def __init__(self, *args, **kwargs):
# #         super().__init__(*args, **kwargs)
# #         # غیرفعال کردن فیلدها برای نمایش فقط خواندنی
# #         for field in self.fields.values():
# #             field.disabled = True
# #
# # """*** مهم ***"""
# # """چون در مدل TanbakhDocument فقط یک document ذخیره می‌شود، اما ما چندین فایل را آپلود می‌کنیم. بنابراین نیازی به ModelForm نیست."""
# # class MultipleFileInput(forms.ClearableFileInput):
# #     allow_multiple_selected = True  # امکان انتخاب چندین فایل را فعال می‌کند
# #
# # class MultipleFileField(forms.FileField):
# #     def __init__(self, *args, **kwargs):
# #         # kwargs.setdefault("widget", MultipleFileInput(attrs={'class': 'form-control'}))
# #         kwargs.setdefault("widget", MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}))
# #         super().__init__(*args, **kwargs)
# #
# #     def clean(self, data, initial=None):
# #         single_file_clean = super().clean
# #         if isinstance(data, (list, tuple)):
# #             # result = [single_file_clean(d, initial) for d in data]
# #             # اطمینان از اینکه فقط فایل‌های آپلود شده معتبر را برمی‌گردانیم
# #             result = [single_file_clean(d, initial) for d in data if d is not None]
# #         else:
# #             result = single_file_clean(data, initial)
# #         return result
# # # --- تعریف پسوندهای مجاز ---
# # # ! لیست پسوندهای مجاز رو اینجا تعریف کن (با نقطه و حروف کوچک)
# # ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png']
# # # می‌تونی فرمت‌های دیگه مثل .txt, .odt, .ods, .gif, .zip, .rar رو هم اضافه کنی
# # ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS) # برای نمایش در پیام خطا
# #
# # # --- فرم اسناد فاکتور (اصلاح شده با اعتبارسنجی) ---
# # class FactorDocumentForm(forms.Form):
# #     files = MultipleFileField(
# #         label=_("بارگذاری اسناد فاکتور (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
# #         required=False,
# #         widget=MultipleFileInput(
# #             attrs={
# #                 'multiple': True,
# #                 'class': 'form-control form-control-sm', # کلاس برای استایل بهتر
# #                 'accept': ",".join(ALLOWED_EXTENSIONS) # راهنمایی به مرورگر برای فیلتر فایل‌ها
# #                 }
# #             )
# #         )
# #
# #     def clean_files(self):
# #         """اعتبارسنجی نوع فایل‌های آپلود شده برای اسناد فاکتور."""
# #         files = self.cleaned_data.get('files')
# #         if files: # اگر فایلی آپلود شده بود
# #             invalid_files = []
# #             for uploaded_file in files:
# #                 if uploaded_file: # اطمینان از اینکه فایل None نیست
# #                     # گرفتن پسوند فایل و تبدیل به حروف کوچک
# #                     ext = os.path.splitext(uploaded_file.name)[1].lower()
# #                     if ext not in ALLOWED_EXTENSIONS:
# #                         invalid_files.append(uploaded_file.name)
# #                         logger.warning(f"Invalid file type uploaded for FactorDocument: {uploaded_file.name} (type: {ext})")
# #
# #             # اگر فایل نامعتبری وجود داشت، خطا ایجاد کن
# #             if invalid_files:
# #                 invalid_files_str = ", ".join(invalid_files)
# #                 error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
# #                     files=invalid_files_str,
# #                     allowed=ALLOWED_EXTENSIONS_STR
# #                 )
# #                 from django.core.exceptions import ValidationError
# #                 raise ValidationError(error_msg)
# #         return files # برگرداندن لیست فایل‌های (احتمالا) معتبر
# #
# # # --- فرم اسناد تنخواه (اصلاح شده با اعتبارسنجی) ---
# # class TankhahDocumentForm(forms.Form):
# #     # prefix='tankhah_docs'
# #     documents = MultipleFileField(
# #         label=_("بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
# #         required=False,
# #          widget=MultipleFileInput(
# #             attrs={
# #                 'multiple': True,
# #                 'class': 'form-control form-control-sm',
# #                 'accept': ",".join(ALLOWED_EXTENSIONS)
# #                 }
# #             )
# #         )
# #
# #     def clean_documents(self):
# #         """اعتبارسنجی نوع فایل‌های آپلود شده برای اسناد تنخواه."""
# #         files = self.cleaned_data.get('documents')
# #         if files:
# #             invalid_files = []
# #             for uploaded_file in files:
# #                  if uploaded_file:
# #                     ext = os.path.splitext(uploaded_file.name)[1].lower()
# #                     if ext not in ALLOWED_EXTENSIONS:
# #                         invalid_files.append(uploaded_file.name)
# #                         logger.warning(f"Invalid file type uploaded for TankhahDocument: {uploaded_file.name} (type: {ext})")
# #
# #             if invalid_files:
# #                 invalid_files_str = ", ".join(invalid_files)
# #                 error_msg = _("فایل(های) زیر دارای فرمت غیرمجاز هستند: {files}. فرمت‌های مجاز: {allowed}").format(
# #                     files=invalid_files_str,
# #                     allowed=ALLOWED_EXTENSIONS_STR
# #                 )
# #                 from django.core.exceptions import ValidationError
# #                 raise ValidationError(error_msg)
# #         return files
# #
#
#
