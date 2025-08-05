from django import forms
from core.models import Status, Action, Transition, Post, Permission, Organization
from django.utils.translation import gettext_lazy as _
class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name', 'code', 'description', 'is_initial', 'is_final_approve', 'is_final_reject']

        # **تغییر کلیدی:** افزودن کلاس‌های CSS به ویجت‌ها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': ' '}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': ' '}),
            'is_initial': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_approve': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_final_reject': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

        # کمک به تمپلیت با ارسال help_text
        help_texts = {
            'name': _('عنوان فارسی باشد (مثال: پیش نویس).'),
            'code': _('فقط حروف بزرگ انگلیسی، اعداد و آندرلاین مجاز است (مثال: PENDING_APPROVAL).'),
        }
class ActionForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
class TransitionForm(forms.ModelForm):
    class Meta:
        model = Transition
        fields = ['name', 'entity_type', 'from_status', 'action', 'to_status']
        # **تغییر کلیدی:** افزودن کلاس‌های CSS به ویجت‌ها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'from_status': forms.Select(attrs={'class': 'form-select'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'to_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن گزینه‌ها به رکوردهای فعال برای جلوگیری از انتخاب موارد بازنشسته
        active_statuses = Status.objects.filter(is_active=True)
        active_actions = Action.objects.filter(is_active=True)

        self.fields['from_status'].queryset = active_statuses
        self.fields['action'].queryset = active_actions
        self.fields['to_status'].queryset = active_statuses
# Core
class PermissionForm_________(forms.ModelForm):
    # ما queryset را در __init__ به صورت داینامیک فیلتر می‌کنیم
    allowed_posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),  # شروع با کوئरी‌ست خالی
        widget=forms.CheckboxSelectMultiple,
        label=_("پست‌های مجاز"),
        required=False  # چون با AJAX پر می‌شود و ممکن است در ابتدا خالی باشد
    )

    class Meta:
        model = Permission
        # **مهم:** ما فیلد entity_type را از اینجا حذف می‌کنیم، چون در گذار (Transition) مشخص شده است
        fields = ['organization', 'transition', 'allowed_posts']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'transition': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن گزینه‌ها به رکوردهای فعال
        self.fields['transition'].queryset = Transition.objects.filter(is_active=True)

        # اگر فرم با داده‌های اولیه (در حالت ویرایش) یا داده‌های POST ارسال شده باشد،
        # queryset پست‌ها را برای اعتبارسنجی پر می‌کنیم.
        organization = None
        if self.instance and self.instance.pk:
            organization = self.instance.organization
        elif 'organization' in self.data:
            try:
                organization = Organization.objects.get(pk=self.data.get('organization'))
            except Organization.DoesNotExist:
                pass

        if organization:
            self.fields['allowed_posts'].queryset = Post.objects.filter(organization=organization,
                                                                        is_active=True).order_by('level', 'name')


class PermissionForm(forms.ModelForm):
    allowed_posts = forms.ModelMultipleChoiceField(
        queryset=Post.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label=_("پست‌های مجاز"),
        required=False
    )

    allowed_actions = forms.ModelMultipleChoiceField(
        queryset=Action.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label=_("اقدامات مجاز"),
        required=False
    )

    class Meta:
        model = Permission
        fields = ['organization', 'transition', 'allowed_posts', 'on_status', 'allowed_actions']
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'transition': forms.Select(attrs={'class': 'form-select'}),
            'on_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # فیلتر گذارهای فعال
        self.fields['transition'].queryset = Transition.objects.filter(is_active=True)

        # فیلتر اقدامات فعال
        self.fields['allowed_actions'].queryset = Action.objects.filter(is_active=True)

        # تنظیم entity_type بر اساس transition انتخاب شده
        if self.instance and self.instance.transition:
            self.fields['entity_type'].initial = self.instance.transition.entity_type
        elif 'transition' in self.data:
            try:
                transition = Transition.objects.get(pk=self.data.get('transition'))
                self.fields['entity_type'].initial = transition.entity_type
            except (Transition.DoesNotExist, ValueError):
                pass

        # فیلتر وضعیت‌ها بر اساس entity_type
        entity_type = None
        if self.instance and self.instance.pk:
            entity_type = self.instance.entity_type
        elif 'transition' in self.data:
            try:
                transition = Transition.objects.get(pk=self.data.get('transition'))
                entity_type = transition.entity_type
            except (Transition.DoesNotExist, ValueError):
                pass

        if entity_type:
            self.fields['on_status'].queryset = Status.objects.filter(
                entity_type=entity_type,
                is_active=True
            )

        # فیلتر پست‌های سازمانی فعال
        organization = None
        if self.instance and self.instance.pk:
            organization = self.instance.organization
        elif 'organization' in self.data:
            try:
                organization = Organization.objects.get(pk=self.data.get('organization'))
            except Organization.DoesNotExist:
                pass

        if organization:
            self.fields['allowed_posts'].queryset = Post.objects.filter(
                organization=organization,
                is_active=True
            ).order_by('level', 'name')
