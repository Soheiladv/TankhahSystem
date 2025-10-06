from django import forms
from django.utils.translation import gettext_lazy as _

from .models import PurchaseRequest


class PurchaseRequestForm(forms.ModelForm):
    date = forms.CharField(
        label=_('تاریخ'),
        widget=forms.TextInput(
            attrs={
                'data-jdp': '',
                'class': 'form-control',
                'placeholder': _('مثال: 1403/01/17'),
                'autocomplete': 'off',
            }
        ),
        required=True,
    )

    class Meta:
        model = PurchaseRequest
        fields = ['organization', 'project', 'subproject', 'date', 'description']
        labels = {
            'organization': _('سازمان'),
            'project': _('پروژه'),
            'subproject': _('زیرپروژه'),
            'description': _('توضیحات'),
        }
        widgets = {
            'organization': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'subproject': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('توضیحات اختیاری')})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure Bootstrap classes on any unhandled fields
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get('class', '')
            if isinstance(widget, (forms.TextInput, forms.Textarea, forms.NumberInput)):
                if 'form-control' not in css:
                    widget.attrs['class'] = (css + ' form-control').strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                if 'form-select' not in css:
                    widget.attrs['class'] = (css + ' form-select').strip()

        # فیلتر وابسته پروژه/زیرپروژه بر اساس سازمان/پروژه انتخاب‌شده
        from core.models import Project, SubProject
        from django.db.models import Q

        selected_org_id = None
        selected_project_id = None

        data = self.data if self.is_bound else None
        if data and data.get('organization'):
            selected_org_id = data.get('organization')
        elif self.instance and getattr(self.instance, 'organization_id', None):
            selected_org_id = self.instance.organization_id

        if data and data.get('project'):
            selected_project_id = data.get('project')
        elif self.instance and getattr(self.instance, 'project_id', None):
            selected_project_id = self.instance.project_id

        # Filter projects
        if 'project' in self.fields:
            if selected_org_id:
                try:
                    base = Project.objects.filter(organizations__id=selected_org_id)
                except Exception:
                    base = Project.objects.all()
                # فقط پروژه‌های فعال و منقضی‌نشده (در صورت وجود فیلدها)
                active_q = Q()
                if hasattr(Project, 'is_active'):
                    active_q &= Q(is_active=True)
                if hasattr(Project, 'end_date'):
                    from django.utils import timezone as _tz
                    active_q &= Q(end_date__isnull=True) | Q(end_date__gte=_tz.now().date())
                if hasattr(Project, 'due_date'):
                    from django.utils import timezone as _tz
                    active_q &= Q(due_date__isnull=True) | Q(due_date__gte=_tz.now().date())
                self.fields['project'].queryset = base.filter(active_q).distinct()
            else:
                # در حالت اولیه، همه پروژه‌ها را نمایش بده تا کاربر بتواند انتخاب کند
                self.fields['project'].queryset = Project.objects.all()

        # Filter subprojects
        if 'subproject' in self.fields:
            if selected_project_id:
                qs = SubProject.objects.filter(project_id=selected_project_id)
                # فیلتر فعال و تاریخ انقضا اگر وجود دارد
                active_q = Q()
                if hasattr(SubProject, 'is_active'):
                    active_q &= Q(is_active=True)
                if hasattr(SubProject, 'end_date'):
                    from django.utils import timezone as _tz
                    active_q &= Q(end_date__isnull=True) | Q(end_date__gte=_tz.now().date())
                if hasattr(SubProject, 'due_date'):
                    from django.utils import timezone as _tz
                    active_q &= Q(due_date__isnull=True) | Q(due_date__gte=_tz.now().date())
                self.fields['subproject'].queryset = qs.filter(active_q)
            elif selected_org_id:
                try:
                    self.fields['subproject'].queryset = SubProject.objects.filter(project__organizations__id=selected_org_id).distinct()
                except Exception:
                    self.fields['subproject'].queryset = SubProject.objects.none()
            else:
                self.fields['subproject'].queryset = SubProject.objects.none()


