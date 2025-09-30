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
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from core.models import Action, Status
from core.models import Organization, Post, UserPost, Transition, EntityType
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
        # Dashboard widget flags removed; no coupling with system settings
        return context


logger = logging.getLogger(__name__)
# =========================================================
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
        # Read-only workflow meta to show meaningful info instead of raw JSONs
        try:
            context['workflow_actions'] = Action.objects.filter(is_active=True).order_by('name')
        except Exception:
            context['workflow_actions'] = []
        try:
            context['workflow_statuses'] = Status.objects.filter(is_active=True).order_by('name')
        except Exception:
            context['workflow_statuses'] = []
        return context
# =========================================================
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
# =========================================================
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

class OrgActionsReportView(PermissionBaseView, TemplateView):

    template_name = 'core/system_settings_org_actions.html'
    permission_codename = 'core.SystemSettings_access'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q') or 'هتل لاله سرعین'
        target_org = Organization.objects.filter(name__icontains=query).first()
        context['query'] = query
        context['organization'] = target_org
        # Provide all active organizations to power the searchable combo/datalist
        try:
            context['organizations'] = Organization.objects.filter(is_active=True).order_by('name').values('id', 'name', 'code')
        except Exception:
            context['organizations'] = []
        context['rows'] = []
        if not target_org:
            return context

        # Resolve EntityType for FACTOR
        try:
            factor_entity = EntityType.objects.get(code='FACTOR')
        except Exception:
            factor_entity = None

        # Build per-user allowed actions based on both Transitions and PostRuleAssignments
        posts = Post.objects.filter(organization=target_org, is_active=True)
        user_posts = UserPost.objects.filter(post__in=posts, is_active=True).select_related('user', 'post')
        
        # Also include users with cross-org PRA (users whose posts are in different org but have PRA for target_org)
        from core.models import PostRuleAssignment
        cross_org_pra_posts = PostRuleAssignment.objects.filter(
            organization=target_org,
            entity_type=factor_entity.code if factor_entity else 'FACTOR',
            is_active=True
        ).exclude(post__organization=target_org).values_list('post', flat=True)
        
        cross_org_user_posts = UserPost.objects.filter(
            post__in=cross_org_pra_posts,
            is_active=True
        ).select_related('user', 'post')
        
        # Combine both user_posts lists
        all_user_posts = list(user_posts) + list(cross_org_user_posts)
        transitions = Transition.objects.filter(organization=target_org, is_active=True)
        if factor_entity:
            transitions = transitions.filter(entity_type=factor_entity)

        # Preload allowed posts per transition
        transitions = transitions.select_related('action', 'to_status', 'from_status').prefetch_related('allowed_posts')
        
        # Get PostRuleAssignments for this organization (including cross-org PRA)
        from core.models import PostRuleAssignment
        pra_list = PostRuleAssignment.objects.filter(
            organization=target_org,
            entity_type=factor_entity.code if factor_entity else 'FACTOR',
            is_active=True
        ).select_related('action', 'post')
        
        # Also get cross-org PRA (PRA where post is in different org but PRA is for target_org)
        cross_org_pra = PostRuleAssignment.objects.filter(
            organization=target_org,
            entity_type=factor_entity.code if factor_entity else 'FACTOR',
            is_active=True
        ).exclude(post__organization=target_org).select_related('action', 'post')
        
        # Combine both PRA lists
        all_pra = list(pra_list) + list(cross_org_pra)
        
        for up in all_user_posts:
            allowed = []
            
            # Check Transition-based permissions
            for tr in transitions:
                if up.post in tr.allowed_posts.all():
                    allowed.append({
                        'action_name': getattr(tr.action, 'name', ''),
                        'action_code': getattr(tr.action, 'code', ''),
                        'from_status': getattr(tr.from_status, 'name', ''),
                        'to_status': getattr(tr.to_status, 'name', ''),
                        'is_initial_from': getattr(tr.from_status, 'is_initial', False),
                        'is_final_to': getattr(tr.to_status, 'is_final_approve', False),
                        'is_reject_to': getattr(tr.to_status, 'is_final_reject', False),
                        'source': 'Transition'
                    })
            
            # Check PostRuleAssignment-based permissions (including cross-org)
            for pra in all_pra:
                if pra.post == up.post:
                    # Find matching transitions for this action
                    matching_transitions = transitions.filter(action=pra.action)
                    for tr in matching_transitions:
                        allowed.append({
                            'action_name': getattr(tr.action, 'name', ''),
                            'action_code': getattr(tr.action, 'code', ''),
                            'from_status': getattr(tr.from_status, 'name', ''),
                            'to_status': getattr(tr.to_status, 'name', ''),
                            'is_initial_from': getattr(tr.from_status, 'is_initial', False),
                            'is_final_to': getattr(tr.to_status, 'is_final_approve', False),
                            'is_reject_to': getattr(tr.to_status, 'is_final_reject', False),
                            'source': 'PostRuleAssignment'
                        })
            
            # Remove duplicates based on action_code
            seen_actions = set()
            unique_allowed = []
            for item in allowed:
                action_key = item['action_code']
                if action_key not in seen_actions:
                    seen_actions.add(action_key)
                    unique_allowed.append(item)
            
            has_initial_start = any(item.get('is_initial_from') for item in unique_allowed)
            context['rows'].append({
                'user': up.user,
                'post': up.post,
                'allowed': unique_allowed,
                'has_initial_start': has_initial_start,
            })
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

# =========================================================
# API: Toggle dashboard widget visibility (approve/deny)
# =========================================================
class ToggleDashboardWidgetView(PermissionBaseView, TemplateView):
    permission_codename = 'core.SystemSettings_access'
    check_organization = True

    def post(self, request, *args, **kwargs):
        return JsonResponse({'ok': False, 'error': 'Dashboard widget toggles are disabled'}, status=400)