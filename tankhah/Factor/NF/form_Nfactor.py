import logging
import jdatetime  # Assuming jdatetime is installed
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from BudgetsSystem.utils import format_jalali_date, to_english_digits, parse_jalali_date
from core.models import Project, SubProject, AccessRule, Organization
from tankhah.models import   FactorItem
from tankhah.utils import restrict_to_user_organization
from django import forms
from django.utils import timezone
from decimal import Decimal
import jdatetime

from tankhah.models import Factor, Tankhah, ItemCategory
from budgets.budget_calculations import get_tankhah_remaining_budget
from django.utils.translation import gettext_lazy as _
# ===== CONFIGURATION & CONSTANTS =====
logger = logging.getLogger('FactorFormsLogger')

ALLOWED_EXTENSIONS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png']
ALLOWED_EXTENSIONS_STR = ", ".join(ALLOWED_EXTENSIONS)
# Helper function to convert date (can be moved to utils)
def convert_to_farsi_numbers(text):
    """Converts English digits in a string to Farsi digits."""
    mapping = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')
    return str(text).translate(mapping)
# --- Form for Factor Documents (Multiple Upload) ---
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
                    import os
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
# --- Form for Tankhah Documents (Multiple Upload) ---
class TankhahDocumentForm(forms.Form):
    documents = MultipleFileField(
        label=_("پیوست‌های تنخواه - بارگذاری مدارک تنخواه (فقط {} مجاز است)".format(ALLOWED_EXTENSIONS_STR)),
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
                    import os
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
class Update_FactorForm(forms.ModelForm):
    date = forms.CharField(
        label='تاریخ فاکتور',
        required=True,
        widget=forms.TextInput(attrs={
            'data-jdp': '',  # برای فعال‌سازی Jalali date picker
            'class': 'form-control form-control-sm',
            'placeholder': 'مثال: 1403/01/17'
        })
    )
    category = forms.ModelChoiceField(
        queryset=ItemCategory.objects.all(),
        label="دسته‌بندی هزینه",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        empty_label=None
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'category', 'date', 'amount', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm ltr-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2}),
        }
        labels = {
            'tankhah': 'تنخواه مرتبط',
            'date': 'تاریخ فاکتور',
            'amount': 'مبلغ کل فاکتور (ریال)',
            'description': 'شرح کلی فاکتور',
            'category': 'دسته‌بندی اصلی هزینه',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.tankhah_instance = kwargs.pop('tankhah', None)
        super().__init__(*args, **kwargs)

        # غیرفعال کردن فیلد تنخواه در حالت ویرایش
        if self.instance and self.instance.pk:
            if 'tankhah' in self.fields:
                self.fields['tankhah'].disabled = True
                self.fields['tankhah'].widget.attrs['readonly'] = True
                self.fields['tankhah'].help_text = 'تنخواه قابل ویرایش نیست.'

            # تنظیم تاریخ جلالی برای حالت ویرایش
            # if self.instance.date and not self.initial.get('date'):
            try:
                self.initial['date'] = format_jalali_date(self.instance.date)
                logger.debug(f"Set initial date for Factor {self.instance.pk}: {self.initial['date']}")
            except Exception as e:
                logger.error(f"Error setting initial date for Factor {self.instance.pk}: {e}")
                self.initial['date'] = ''

        # فیلتر کردن تنخواه‌ها
        try:
            initial_stage = AccessRule.objects.order_by('order').first()
            initial_stage_order = initial_stage.order if initial_stage else 0
        except Exception as e:
            logger.error(f"Error getting initial workflow stage: {e}")
            initial_stage_order = 0

        tankhah_queryset = Tankhah.objects.none()
        if self.user:
            user_orgs = restrict_to_user_organization(self.user)
            base_filter = models.Q(
                status__in=['DRAFT', 'PENDING'],
                current_stage__order=initial_stage_order
            )
            if user_orgs is None:
                tankhah_queryset = Tankhah.objects.filter(base_filter)
            else:
                projects = Project.objects.filter(organizations__id__in=user_orgs)
                subprojects = SubProject.objects.filter(project__in=projects)
                org_filter = models.Q(organization__id__in=user_orgs)
                project_filter = models.Q(project__in=projects)
                subproject_filter = models.Q(subproject__in=subprojects)
                tankhah_queryset = Tankhah.objects.filter(
                    base_filter & (org_filter | project_filter | subproject_filter)
                ).distinct()

            tankhah_queryset = tankhah_queryset.select_related('organization', 'project', 'subproject', 'current_stage')
            self.fields['tankhah'].queryset = tankhah_queryset
            logger.info(f"User {self.user.username}: Tankhah queryset count = {tankhah_queryset.count()}")

        # تنظیم مقدار اولیه تنخواه
        if self.tankhah_instance:
            if tankhah_queryset.filter(pk=self.tankhah_instance.pk).exists():
                self.initial['tankhah'] = self.tankhah_instance
            else:
                logger.warning(
                    f"Passed tankhah instance (pk={self.tankhah_instance.pk}) is not in the valid queryset for user {self.user.username}")

        # تنظیم تاریخ پیش‌فرض به امروز (جلالی) اگر مقدار اولیه وجود نداشته باشد
        if not self.initial.get('date'):
            try:
                today_jalali = jdatetime.date.today().strftime('%Y/%m/%d')
                self.initial['date'] = today_jalali
                logger.debug(f"Set default date to today: {today_jalali}")
            except Exception as e:
                logger.error(f"Error setting default Jalali date: {e}")

    def clean_date(self):
        """تبدیل تاریخ جلالی به میلادی."""
        date_str = self.cleaned_data.get('date')
        if not date_str:
            logger.error("Date is empty")
            raise forms.ValidationError('وارد کردن تاریخ الزامی است.')
        try:
            date_str = to_english_digits(date_str)
            parsed_date = parse_jalali_date(date_str, field_name='تاریخ')
            logger.debug(f"Parsed date: Jalali='{date_str}', Gregorian='{parsed_date}'")
            return parsed_date
        except Exception as e:
            logger.error(f"Error parsing date: {date_str}, Error: {e}")
            raise forms.ValidationError('فرمت تاریخ نامعتبر است. از فرمت YYYY/MM/DD استفاده کنید (مثال: 1403/01/17).')

    def clean_amount(self):
        """اعتبارسنجی مبلغ."""
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError('وارد کردن مبلغ کل فاکتور الزامی است.')
        if not isinstance(amount, Decimal):
            raise forms.ValidationError('مقدار نامعتبر برای مبلغ.')
        # if amount <= Decimal('0'):
        #     raise forms.ValidationError('مبلغ کل فاکتور باید بزرگتر از صفر باشد.')
        return amount

    def clean(self):
        """اعتبارسنجی کلی فرم."""
        cleaned_data = super().clean()
        return cleaned_data
# -----------------------------------------------------------------------------------------------------------

# ===== UTILITY FUNCTIONS =====
def parse_jalali_date(date_str):
    """تبدیل تاریخ جلالی به تاریخ میلادی"""
    try:
        if not date_str:
            raise ValueError("تاریخ ارائه نشده است")
        year, month, day = map(int, date_str.split('/'))
        jalali_date = jdatetime.date(year, month, day)
        return jalali_date.togregorian()
    except (ValueError, TypeError) as e:
        logger.error(f"خطا در پردازش تاریخ جلالی: {str(e)}, ورودی: {date_str}")
        raise forms.ValidationError(_('فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY/MM/DD استفاده کنید.'))
# ===== CORE BUSINESS LOGIC =====
class FactorForm(forms.ModelForm):
    """
    فرم اصلی برای ایجاد یک فاکتور.
    مسئولیت: گرفتن داده‌های کلی فاکتور و اعتبارسنجی اولیه.
    """
    date = forms.CharField(
        label=_('تاریخ ثبت فاکتور'),
        widget=forms.TextInput(attrs={
            'data-jdp': '',
            'class': 'form-control',
            'placeholder': _('1404/01/17'),
        })
    )

    class Meta:
        model = Factor
        fields = ['tankhah', 'category', 'date', 'payee','amount', 'description']
        widgets = {
            'tankhah': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        logger.debug(
            f"[FactorForm.__init__] شروع مقداردهی اولیه برای کاربر '{self.user.username if self.user else 'Anonymous'}'.")

        # فیلتر اولیه تنخواه‌ها
        tankhah_queryset = Tankhah.objects.filter(
            is_archived=False,
            status__code__in=['DRAFT', 'PENDING', 'APPROVED'],
            due_date__gte=timezone.now(),
            project__isnull=False
        ).select_related('organization', 'project').order_by('-created_at')

        # اگر کاربر وارد سیستم شده و سوپر یوزر نیست، فیلتر دسترسی اعمال شود
        if self.user and not self.user.is_superuser:
            # سازمان‌های قابل دسترسی کاربر
            user_posts = self.user.userpost_set.filter(is_active=True).select_related('post__organization')
            if not user_posts.exists():
                logger.warning(f"[FactorForm.__init__] کاربر '{self.user.username}' هیچ پست فعال ندارد.")
                raise forms.ValidationError(_('شما هیچ پست فعال سازمانی ندارید. لطفاً با مدیر سیستم تماس بگیرید.'))

            # استخراج سازمان‌های قابل دسترسی
            user_orgs = set()
            central_orgs = set()
            for up in user_posts:
                org = getattr(up.post, 'organization', None)
                if org:
                    if org.is_core:
                        central_orgs.add(org)  # دفتر مرکزی
                    else:
                        user_orgs.add(org)  # شعبات عادی

            # اگر کاربر دفتر مرکزی دارد، شعبات زیرمجموعه را هم اضافه می‌کنیم
            for core_org in central_orgs:
                descendants = core_org.sub_organizations.filter(is_active=True)
                user_orgs.update(descendants)

            if not user_orgs:
                logger.warning(f"[FactorForm.__init__] هیچ سازمان فعال برای کاربر '{self.user.username}' یافت نشد.")
                raise forms.ValidationError(_('شما به هیچ شعبه‌ای دسترسی ندارید. لطفاً با مدیر سیستم تماس بگیرید.'))

            # اعمال فیلتر بر queryset تنخواه‌ها
            tankhah_queryset = tankhah_queryset.filter(
                Q(organization__in=user_orgs) |
                Q(project__organizations__in=user_orgs)
            ).distinct()
            logger.debug(f"[FactorForm.__init__] تعداد تنخواه‌های قابل دسترسی پس از فیلتر: {tankhah_queryset.count()}")

        # تنظیم queryset فیلد
        self.fields['tankhah'].queryset = tankhah_queryset

        # اگر initial برای تنخواه تعیین شده، فیلد غیرفعال شود
        if 'tankhah' in self.initial:
            self.fields['tankhah'].disabled = True
            logger.debug(f"[FactorForm.__init__] فیلد تنخواه غیرفعال شد: {self.initial['tankhah']}")

        # تنظیم مقدار اولیه تاریخ
        if not self.initial.get('date'):
            self.initial['date'] = jdatetime.date.today().strftime('%Y/%m/%d')
        elif self.instance and self.instance.pk and self.instance.date:
            self.initial['date'] = jdatetime.date.fromgregorian(date=self.instance.date).strftime('%Y/%m/%d')

        logger.debug(f"[FactorForm.__init__] مقداردهی اولیه فرم کامل شد.")

    def clean_date(self):
        """اعتبارسنجی تاریخ جلالی"""
        date_str = self.cleaned_data.get('date')
        try:
            return parse_jalali_date(date_str)
        except (ValueError, TypeError):
            logger.warning(f"[FactorForm.clean_date] فرمت تاریخ نامعتبر: {date_str}")
            raise forms.ValidationError(_('فرمت تاریخ نامعتبر است.'))

    def clean_tankhah(self):
        """اعتبارسنجی تنخواه"""
        tankhah = self.cleaned_data.get('tankhah')
        if not tankhah:
            logger.warning("[FactorForm.clean_tankhah] تنخواه انتخاب نشده است")
            raise forms.ValidationError(_('لطفاً یک تنخواه انتخاب کنید.'))

        if tankhah.due_date < timezone.now():
            logger.warning(f"[FactorForm.clean_tankhah] تنخواه {tankhah.number} منقضی شده است: {tankhah.due_date}")
            raise forms.ValidationError(_('تنخواه انتخاب‌شده منقضی شده است.'))

        if not isinstance(tankhah.project, Project):
            logger.error(f"[FactorForm.clean_tankhah] پروژه نامعتبر برای تنخواه {tankhah.number}: {tankhah.project}")
            raise forms.ValidationError(_('پروژه مرتبط با تنخواه نامعتبر است.'))

        # بررسی دسترسی کاربر به سازمان تنخواه و پروژه
        if self.user and not self.user.is_superuser:
            user_posts = self.user.userpost_set.filter(is_active=True).select_related('post__organization')
            user_orgs = {up.post.organization for up in user_posts
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            if not user_orgs:
                logger.warning(f"[FactorForm.clean_tankhah] هیچ سازمان شعبه‌ای برای کاربر '{self.user.username}' یافت نشد")
                raise forms.ValidationError(_('شما به هیچ شعبه‌ای دسترسی ندارید.'))

            # بررسی سازمان تنخواه
            if tankhah.organization not in user_orgs:
                logger.warning(f"[FactorForm.clean_tankhah] کاربر '{self.user.username}' به سازمان تنخواه {tankhah.organization.name} دسترسی ندارد")
                raise forms.ValidationError(_('شما به سازمان این تنخواه دسترسی ندارید.'))

            # بررسی سازمان‌های پروژه
            project_orgs = set(tankhah.project.organizations.filter(is_core=False, is_holding=False))
            if not project_orgs.issubset(user_orgs):
                logger.warning(f"[FactorForm.clean_tankhah] کاربر '{self.user.username}' به برخی سازمان‌های پروژه {tankhah.project.name} دسترسی ندارد")
                raise forms.ValidationError(_('شما به تمام سازمان‌های مرتبط با پروژه این تنخواه دسترسی ندارید.'))

        return tankhah

    def clean_payee(self):
        payee = self.cleaned_data.get('payee')
        national_id = self.data.get('national_id')  # اگر از طریق مودال دریافت شود
        entity_type = self.data.get('entity_type')
        from budgets.models import Payee
        if national_id and Payee.objects.filter(national_id=national_id, entity_type=entity_type).exists():
            raise forms.ValidationError(_("دریافت‌کننده‌ای با این کد ملی/شناسه حقوقی قبلاً ثبت شده است."))
        return payee

    def clean(self):
        """اعتبارسنجی نهایی فرم"""
        cleaned_data = super().clean()
        tankhah = cleaned_data.get('tankhah')
        amount = cleaned_data.get('amount')
        logger.debug(f"[FactorForm.clean] شروع اعتبارسنجی نهایی. تنخواه: {tankhah}, مبلغ: {amount}")

        if not all([tankhah, amount]):
            logger.warning("[FactorForm.clean] تنخواه یا مبلغ وجود ندارد. بررسی بودجه متوقف شد.")
            return cleaned_data

        remaining_budget = get_tankhah_remaining_budget(tankhah)
        if amount > remaining_budget:
            error_msg = _('مبلغ فاکتور ({:,.0f} ریال) از بودجه باقی‌مانده ({:,.0f} ریال) بیشتر است.').format(
                amount, remaining_budget)
            logger.warning(f"[FactorForm.clean] خطای اعتبارسنجی: {error_msg}")
            raise forms.ValidationError(error_msg)

        if tankhah.project_budget_allocation and tankhah.project_budget_allocation.budget_period:
            budget_period = tankhah.project_budget_allocation.budget_period
            is_locked, lock_reason = budget_period.is_locked
            if is_locked:
                logger.warning(f"[FactorForm.clean] خطای اعتبارسنجی: دوره بودجه قفل است. دلیل: {lock_reason}")
                raise forms.ValidationError(lock_reason)

        logger.debug("[FactorForm.clean] اعتبارسنجی فرم با موفقیت انجام شد")
        return cleaned_data
# -----------------------------------------------------------------------------------------------------------
class FactorItemForm(forms.ModelForm):
    """فرم برای هر ردیف فاکتور."""

    class Meta:
        model = FactorItem
        fields = ['description', 'quantity', 'unit_price']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # **تغییرات کلیدی:** اضافه کردن کلاس‌های CSS
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end quantity-field'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control form-control-sm text-end unit-price-field'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # اگر فرم برای حذف علامت خورده، اعتبارسنجی نکن
        if self.cleaned_data.get('DELETE'):
            return cleaned_data

        # اگر فرم خالی است (یک ردیف اضافی که پر نشده)، خطا نده
        if not self.has_changed():
            return cleaned_data

        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        if quantity is None or unit_price is None or cleaned_data.get('description') is None:
            raise forms.ValidationError(_("لطفاً تمام فیلدهای این ردیف را پر کنید یا آن را حذف کنید."))

        if quantity <= 0:
            self.add_error('quantity', _('تعداد باید مثبت باشد.'))
        if unit_price < 0:
            self.add_error('unit_price', _('قیمت واحد نمی‌تواند منفی باشد.'))

        return cleaned_data
#-----------------------------------------------------------------------------------------------------------

