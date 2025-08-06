from django import forms
from core.models import Status, Action, Transition, Post
from django.utils.translation import gettext_lazy as _
import logging
logger = logging.getLogger('WorkflowFormLogger')

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
        fields = ['name', 'organization','entity_type', 'from_status',
                  'action', 'to_status' ,'allowed_posts', 'is_active']


        # **تغییر کلیدی:** افزودن کلاس‌های CSS به ویجت‌ها
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'from_status': forms.Select(attrs={'class': 'form-select'}),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'to_status': forms.Select(attrs={'class': 'form-select'}),
            'allowed_posts': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # محدود کردن گزینه‌ها به رکوردهای فعال برای جلوگیری از انتخاب موارد بازنشسته
        active_statuses = Status.objects.filter(is_active=True)
        active_actions = Action.objects.filter(is_active=True)

        self.fields['from_status'].queryset = active_statuses
        self.fields['action'].queryset = active_actions
        self.fields['to_status'].queryset = active_statuses

        self.fields['allowed_posts'].queryset = Post.objects.filter(is_active=True).select_related(
            'organization').order_by('organization__name', 'level', 'name')
        self.fields['allowed_posts'].label_from_instance = lambda obj: f"{obj.name} ({obj.organization.name})"