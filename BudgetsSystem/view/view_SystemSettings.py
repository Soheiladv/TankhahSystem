from django.contrib import messages
import logging

from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, CreateView, UpdateView
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
import json

from core.models import SystemSettings
from core.PermissionBase import PermissionBaseView


class SystemSettingsDashboardView(PermissionBaseView, TemplateView):
    permission_codename = 'core.SystemSettings_access'

    template_name = 'core/system_settings_dashboard.html'
    login_url = reverse_lazy('accounts:login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj = SystemSettings.objects.first()
        context['settings'] = settings_obj
        context['has_settings'] = settings_obj is not None
        return context


logger = logging.getLogger(__name__)


class SystemSettingsCreateView(PermissionBaseView, CreateView):
    permission_codename = 'core.SystemSettings_access'
    model = SystemSettings
    from core.forms import SystemSettingsForm
    form_class = SystemSettingsForm
    template_name = 'core/system_settings_form_tabs.html'
    # fields = [
    #     'budget_locked_percentage_default',
    #     'budget_warning_threshold_default',
    #     'budget_warning_action_default',
    #     'allocation_locked_percentage_default',
    #     'tankhah_used_statuses',
    #     'tankhah_accessible_organizations',
    #     'tankhah_payment_ceiling_default',
    #     'tankhah_payment_ceiling_enabled_default',
    #     'enforce_strict_approval_order',
    #     'allow_bypass_org_chart',
    #     'allow_action_without_org_chart',
    # ]
    # permission_required = 'core.change_organization'
    success_url = reverse_lazy('system_settings_dashboard')

    def get(self, request, *args, **kwargs):
        # نمایش فرم ایجاد را به ویرایش هدایت می‌کنیم
        return redirect('system_settings_update', pk=1)

    @transaction.atomic
    def form_valid(self, form):
        try:
            # همیشه روی singleton بنویس تا از هرگونه درج تکراری جلوگیری شود
            obj = SystemSettings.get_solo()
            for field, value in form.cleaned_data.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)
            obj.save()
            messages.success(self.request, _("تنظیمات سیستم با موفقیت ذخیره شد."))
            return redirect('system_settings_dashboard')
        except Exception as e:
            logger.error("SystemSettings create failed", exc_info=True)
            form.add_error(None, str(e))
            messages.error(self.request, _("خطا در ذخیره تنظیمات: ") + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("ثبت انجام نشد. لطفاً خطاهای فرم را برطرف کنید."))
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': _("ایجاد تنظیمات سیستم"),
            'form_title': _("ایجاد/ویرایش تنظیمات سیستم"),
            'submit_text': _("ذخیره"),
            'submit_icon': 'fas fa-save',
            'submit_class': 'btn-primary',
            'breadcrumbs': [
                {'name': _("تنظیمات سیستم"), 'url': reverse_lazy('system_settings_dashboard')},
                {'name': _("ایجاد"), 'active': True}
            ],
            'is_create': True
        })
        return context

class SystemSettingsUpdateView(PermissionBaseView, UpdateView):
    permission_codename = 'core.SystemSettings_access'
    model = SystemSettings
    template_name = 'core/system_settings_form_tabs.html'
    from core.forms import SystemSettingsForm
    form_class = SystemSettingsForm
    success_url = reverse_lazy('system_settings_dashboard')

    def get_object(self, queryset=None):
        # همواره Singleton را برگردان (اگر نبود بساز)
        return SystemSettings.get_solo()

    def post(self, request, *args, **kwargs):
        # اطمینان از اینکه فرم روی singleton بایند می‌شود
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _("تنظیمات سیستم با موفقیت ذخیره شد."))
            return response
        except Exception as e:
            logger.error("SystemSettings update failed", exc_info=True)
            form.add_error(None, str(e))
            messages.error(self.request, _("خطا در بروزرسانی تنظیمات: ") + str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("ثبت انجام نشد. لطفاً خطاهای فرم را برطرف کنید."))
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object or SystemSettings.get_solo()
        is_create = obj.pk is None
        context.update({
            'page_title': _("ایجاد/ویرایش تنظیمات سیستم") if is_create else _("ویرایش تنظیمات سیستم"),
            'form_title': _("ایجاد/ویرایش تنظیمات سیستم") if is_create else _("ویرایش تنظیمات سیستم"),
            'submit_text': _("ذخیره") if is_create else _("بروزرسانی"),
            'submit_icon': 'fas fa-save' if is_create else 'fas fa-edit',
            'submit_class': 'btn-primary',
            'breadcrumbs': [
                {'name': _("تنظیمات سیستم"), 'url': reverse_lazy('system_settings_dashboard')},
                {'name': _("ایجاد/ویرایش") if is_create else _("ویرایش"), 'active': True}
            ],
            'is_create': is_create,
            'is_edit': not is_create,
            'last_modified': getattr(obj, 'updated_at', None),
            'modified_by': getattr(obj, 'modified_by', None)
        })
        return context

class SystemSettingsResetView(PermissionBaseView, TemplateView):

    template_name = 'core/system_settings_reset.html'
    login_url = reverse_lazy('accounts:login')
    permission_codename = 'core.SystemSettings_access'
    success_url = reverse_lazy('system_settings_dashboard')

    def post(self, request, *args, **kwargs):
        settings = SystemSettings.objects.first()
        if settings:
            settings.delete()
            messages.success(request, _("تنظیمات سیستم با موفقیت بازنشانی شد."))
        else:
            messages.info(request, _("تنظیماتی برای بازنشانی یافت نشد."))
        return redirect(self.success_url)

class SystemSettingsExportView(PermissionBaseView, TemplateView):

    permission_required = 'core.SystemSettings_access'

    def get(self, request, *args, **kwargs):
        settings_obj = SystemSettings.objects.first()
        if not settings_obj:
            return HttpResponseBadRequest(_("هیچ تنظیماتی برای خروجی وجود ندارد."))
        data = {
            'budget_locked_percentage_default': float(settings_obj.budget_locked_percentage_default or 0),
            'budget_warning_threshold_default': float(settings_obj.budget_warning_threshold_default or 0),
            'budget_warning_action_default': settings_obj.budget_warning_action_default,
            'allocation_locked_percentage_default': float(settings_obj.allocation_locked_percentage_default or 0),
            'tankhah_used_statuses': settings_obj.tankhah_used_statuses or [],
            'tankhah_accessible_organizations': settings_obj.tankhah_accessible_organizations or [],
            'tankhah_payment_ceiling_default': float(settings_obj.tankhah_payment_ceiling_default or 0),
            'tankhah_payment_ceiling_enabled_default': bool(settings_obj.tankhah_payment_ceiling_enabled_default),
            'enforce_strict_approval_order': bool(settings_obj.enforce_strict_approval_order),
            'allow_bypass_org_chart': bool(settings_obj.allow_bypass_org_chart),
            'allow_action_without_org_chart': bool(settings_obj.allow_action_without_org_chart),
        }
        content = json.dumps(data, ensure_ascii=False, indent=2)
        response = HttpResponse(content, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="system_settings_export.json"'
        return response

class SystemSettingsImportView(PermissionBaseView, TemplateView):

    template_name = 'core/system_settings_import.html'
    permission_codename = 'core.SystemSettings_access'

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            messages.error(request, _("فایل ارسال نشد."))
            return redirect('system_settings_dashboard')
        try:
            payload = json.load(file)
            settings_obj = SystemSettings.objects.first() or SystemSettings()
            for key, value in payload.items():
                if hasattr(settings_obj, key):
                    setattr(settings_obj, key, value)
            settings_obj.save()
            messages.success(request, _("تنظیمات با موفقیت ایمپورت شد."))
        except Exception as e:
            messages.error(request, _("ایمپورت ناموفق بود: ") + str(e))
        return redirect('system_settings_dashboard')

class SystemSettingsHealthView(PermissionBaseView, TemplateView):

    template_name = 'core/system_settings_health.html'
    permission_codename = 'core.SystemSettings_access'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        s = SystemSettings.objects.first()
        issues = []
        if not s:
            issues.append({'level': 'error', 'msg': _("هیچ تنظیماتی ثبت نشده است.")})
        else:
            if s.enforce_strict_approval_order and s.allow_bypass_org_chart:
                issues.append({'level': 'warning', 'msg': _("سخت‌گیری ترتیب و اجازه بایپس همزمان فعال‌اند. اولویت را مشخص کنید.")})
            if (s.tankhah_payment_ceiling_enabled_default and (s.tankhah_payment_ceiling_default is None or s.tankhah_payment_ceiling_default <= 0)):
                issues.append({'level': 'warning', 'msg': _("سقف تنخواه فعال است اما مقدار سقف نامعتبر است.")})
            if s.budget_locked_percentage_default is not None and s.budget_locked_percentage_default < 0:
                issues.append({'level': 'error', 'msg': _("درصد قفل بودجه نمی‌تواند منفی باشد.")})
            if s.budget_warning_threshold_default is not None and s.budget_warning_threshold_default < 0:
                issues.append({'level': 'error', 'msg': _("آستانه هشدار بودجه نمی‌تواند منفی باشد.")})
        context['issues'] = issues
        return context

class SystemSettingsPreviewView(PermissionBaseView, TemplateView):

    template_name = 'core/system_settings_preview.html'
    permission_codename = 'core.SystemSettings_access'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Snapshot settings
        s = SystemSettings.objects.first()
        context['settings'] = s
        # Recent factors for convenience
        try:
            from tankhah.models import Factor
            context['recent_factors'] = Factor.objects.order_by('-created_at').values('id', 'number')[:10]
        except Exception:
            context['recent_factors'] = []
        # User active posts summary
        try:
            from core.models import UserPost
            ups = UserPost.objects.filter(user=self.request.user, is_active=True).select_related('post','post__organization')
            context['user_posts'] = ups
        except Exception:
            context['user_posts'] = []
        return context

    def post(self, request, *args, **kwargs):
        factor_id = request.POST.get('factor_id')
        result = {'ok': False, 'error': None, 'next_steps': []}
        try:
            from tankhah.models import Factor
            from tankhah.Factor.FactorDetail.views_FactorDetail import get_user_allowed_transitions
            factor = Factor.objects.get(pk=int(factor_id))
            transitions = get_user_allowed_transitions(request.user, factor)
            for t in transitions:
                result['next_steps'].append({
                    'action': getattr(t.action, 'name', ''),
                    'to_status': getattr(t.to_status, 'name', ''),
                    'organization': getattr(getattr(t, 'organization', None), 'name', ''),
                })
            result['ok'] = True
        except Exception as e:
            result['error'] = str(e)
        return JsonResponse(result)