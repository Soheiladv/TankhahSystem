# core/views.py
import logging
from collections import defaultdict

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import FormView
from django.views.generic import ListView
from core.AccessRule.forms_accessrule import PostAccessRuleForm_new, PostAccessRuleHybridForm, PostAccessRuleAssignForm, \
    UnifiedAccessForm, WorkflowForm
from core.models import AccessRule, Post, Organization
from core.views import PermissionBaseView
logger = logging.getLogger(__name__)
def userGiud_AccessRule(request):
    return render(request, template_name='core/accessrule/help_userAccessRule.html')
class UserGuideView(TemplateView):
    template_name = 'core/accessrule/user_guide.html'
    extra_context = {'title': _('راهنمای کاربر: تخصیص قوانین دسترسی')}

# It's good practice to define choices once for reusability
# You might already have these in your models or a constants file.
# If not, define them here or import them.
ENTITY_TYPE_CHOICES = [
    ('FACTOR', _('فاکتور')),
    ('PAYMENTORDER', _('دستور پرداخت')),
    ('TANKHAH', _('تنخواه')),
    ('BUDGET', _('بودجه')), # Added BUDGET and REPORTS for completeness
    ('REPORTS', _('گزارشات')),
]
from tankhah.constants import ACTION_TYPES, ENTITY_TYPES
#-------------- New AccessRule Models
class AccessRuleListView(PermissionBaseView, ListView):
    model = AccessRule
    template_name = 'core/accessrule/accessrule_list.html'
    context_object_name = 'access_rules'
    paginate_by = 10
    permission_codenames = ['core.AccessRule_view']
    check_organization = True
    extra_context = {
        'title': _('لیست قوانین دسترسی'),
        'entity_type_choices':  ENTITY_TYPES,
        'action_type_choices':  ACTION_TYPES,
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related('organization', 'post').order_by('stage_order',
                                                                                          'organization__name')

        # دریافت پارامترهای فیلتر
        query = self.request.GET.get('q', '')
        is_active_param = self.request.GET.get('is_active', '')
        entity_type_param = self.request.GET.get('entity_type', '')
        action_type_param = self.request.GET.get('action_type', '')
        stage_order_param = self.request.GET.get('stage_order', '')

        # اعمال فیلترها
        if query:
            queryset = queryset.filter(
                Q(organization__name__icontains=query) |
                Q(post__name__icontains=query) |
                # Q(stage_name__icontains=query) |
                Q(entity_type__icontains=query) |
                Q(action_type__icontains=query)
            )

        if is_active_param:
            queryset = queryset.filter(is_active=(is_active_param == 'true'))

        if entity_type_param:
            queryset = queryset.filter(entity_type=entity_type_param)

        if action_type_param:
            queryset = queryset.filter(action_type=action_type_param)

        if stage_order_param:
            try:
                queryset = queryset.filter(stage_order=int(stage_order_param))
            except ValueError:
                pass

        logger.info(f"AccessRule queryset count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        context['entity_type_filter'] = self.request.GET.get('entity_type', '')
        context['action_type_filter'] = self.request.GET.get('action_type', '')
        context['stage_order_filter'] = self.request.GET.get('stage_order', '')
        context['total_access_rules'] = self.get_queryset().count()
        return context
class AccessRuleDetailView(PermissionBaseView, DetailView):
    model = AccessRule
    template_name = 'core/accessrule/accessrule_detail.html'
    context_object_name = 'access_rule'
    permission_codenames = ['core.AccessRule_view']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات قانون دسترسی') + f" - {self.object.organization} - {self.object.stage_name}"
        return context
class AccessRuleCreateView(PermissionBaseView, CreateView):
    model = AccessRule
    form_class = PostAccessRuleForm_new
    template_name = 'core/accessrule/accessrule_form.html'
    success_url = reverse_lazy('accessrule_list')
    permission_codenames = ['core.AccessRule_add']
    check_organization = True
    extra_context = {'title': _('ایجاد قانون دسترسی جدید')}

    def form_valid(self, form):
        messages.success(self.request, _('قانون دسترسی با موفقیت ایجاد شد.'))
        return super().form_valid(form)
class AccessRuleUpdateView(PermissionBaseView, UpdateView):
    model = AccessRule
    form_class = PostAccessRuleForm_new
    template_name = 'core/accessrule/accessrule_form.html'
    success_url = reverse_lazy('accessrule_list')
    permission_codenames = ['core.AccessRule_update']
    check_organization = True
    extra_context = {'title': _('ویرایش قانون دسترسی')}

    def form_valid(self, form):
        messages.success(self.request, _('قانون دسترسی با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)
class AccessRuleDeleteView(PermissionBaseView, DeleteView):
    model = AccessRule
    template_name = 'core/accessrule/accessrule_confirm_delete.html'
    success_url = reverse_lazy('accessrule_list')
    permission_codenames = ['core.AccessRule_delete']
    check_organization = True
    extra_context = {'title': _('حذف قانون دسترسی')}

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('قانون دسترسی با موفقیت حذف شد.'))
        return super().post(request, *args, **kwargs)
#----------------------------------------------------
# --- Assigne Rolle
class PostRuleReportView(PermissionBaseView, ListView):
    template_name = 'core/accessrule/post_rule_report.html'
    model = Post
    context_object_name = 'posts'
    permission_codenames = ['core.AccessRule_view']
    check_organization = False
    extra_context = {'title': _('گزارش قوانین دسترسی پست‌ها')}

    def get_queryset(self):
        return Post.objects.select_related('organization').prefetch_related('accessrule_set').order_by(
            'organization__name', 'level')
    # template_name = 'core/accessrule/post_access_rule_assign_a.html'

class PostAccessRuleAssignView_old(PermissionBaseView, FormView):
    template_name = 'core/accessrule/post_access_rule_assign_hybrid.html'
    form_class = PostAccessRuleHybridForm
    success_url = reverse_lazy('accessrule_list')
    permission_codenames = ['core.AccessRule_add', 'core.AccessRule_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("تنظیم مجوزهای پست‌ها (مدل هیبریدی)")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # اضافه کردن کاربر به kwargs فرم

        posts_query = Post.objects.filter(is_active=True).select_related(
            'organization', 'branch'
        ).order_by('organization__name', 'level', 'name')

        if not self.request.user.is_superuser:
            user_org_ids = self.request.user.userpost_set.filter(
                is_active=True
            ).values_list('post__organization_id', flat=True).distinct()
            posts_query = posts_query.filter(organization_id__in=user_org_ids)

        kwargs['posts_query'] = posts_query
        return kwargs

    def form_valid(self, form):
        try:
            if form.save():  # فراخوانی متد save بدون پارامتر
                messages.success(self.request, _('مجوزهای پست‌ها با موفقیت به‌روزرسانی شدند.'))
            else:
                messages.warning(self.request, _('هیچ تغییری در مجوزهای پست‌ها اعمال نشد.'))
        except Exception as e:
            logger.exception(f"Error while saving Hybrid Access Rule Form: {e}")
            messages.error(self.request, _('خطایی در هنگام ذخیره‌سازی رخ داد: {}').format(e))
            return self.form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request,
                     _('لطفاً خطاهای فرم را برطرف کنید. به یاد داشته باشید که برای تأیید/رد، تعیین سطح الزامی است.'))
        return super().form_invalid(form)

class PostAccessRuleAssignView(PermissionBaseView, FormView):
    template_name = 'core/accessrule/post_access_rule_assign.html' # یک تمپلیت جدید و تمیز
    form_class = PostAccessRuleAssignForm
    permission_codenames = ['core.AccessRule_add', 'core.AccessRule_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # این ویو باید بداند برای کدام سازمان و کدام نوع موجودیت کار می‌کند
        self.organization = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
        self.entity_type = self.kwargs['entity_type']
        self.success_url = reverse('post_access_rule_assign', args=[self.organization.pk, self.entity_type])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'organization': self.organization,
            'entity_type': self.entity_type,
            'user': self.request.user
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _(f"مدیریت گردش کار برای '{self.entity_type}' در سازمان '{self.organization.name}'")
        context['organization'] = self.organization
        context['entity_type'] = self.entity_type
        return context

    def form_valid(self, form):
        try:
            form.save()
            messages.success(self.request, _('قوانین گردش کار با موفقیت به‌روزرسانی شدند.'))
        except Exception as e:
            logger.exception(f"Error while saving Access Rule Form: {e}")
            messages.error(self.request, _('خطایی در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)

        return super().form_valid(form)

#-------------------------------------------------------------------------------------------
class SelectWorkflowView(PermissionBaseView, TemplateView):
    template_name = 'core/accessrule/workflow_select.html'
    permission_codenames = ['core.AccessRule_add']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("انتخاب گردش کار برای مدیریت")
        if self.request.user.is_superuser:
            context['organizations'] = Organization.objects.filter(is_active=True)
        else:
            user_org_ids = self.request.user.userpost_set.filter(
                is_active=True
            ).values_list('post__organization_id', flat=True).distinct()
            context['organizations'] = Organization.objects.filter(id__in=user_org_ids, is_active=True)
        context['entity_types'] = ENTITY_TYPES
        return context


class WorkflowBuilderView(PermissionBaseView, FormView):
    template_name = 'core/accessrule/unified_access_assign.html'
    form_class = UnifiedAccessForm
    permission_codenames = ['core.AccessRule_add', 'core.AccessRule_update']
    check_organization  = True
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.organization = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
            self.entity_type = self.kwargs['entity_type']
            if self.entity_type not in [e[0] for e in ENTITY_TYPES]:
                raise Http404("Entity type not valid")
        except KeyError:
            raise Http404("Organization or Entity Type not specified in URL.")
        self.success_url = reverse('workflow_builder', args=[self.organization.pk, self.entity_type])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'organization': self.organization,
            'entity_type': self.entity_type,
            'user': self.request.user
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context['form']
        entity_label = dict(ENTITY_TYPES).get(self.entity_type, self.entity_type)
        context['title'] = _(f"طراحی گردش کار برای '{entity_label}' در سازمان '{self.organization.name}'")
        context['organization'] = self.organization
        context['entity_type'] = self.entity_type

        workflow_data = sorted(form.levels_data.items())

        has_data_to_display = bool(workflow_data)
        if not has_data_to_display and self.request.method == 'GET':
            messages.warning(self.request, _(f"هیچ پست فعالی برای سازمان '{self.organization.name}' یافت نشد."))

        context['workflow_data'] = workflow_data
        context['has_data_to_display'] = has_data_to_display
        return context

    def form_valid(self, form):
        try:
            form.save()
            messages.success(self.request, _('قوانین دسترسی با موفقیت به‌روزرسانی شدند.'))
        except Exception as e:
            logger.exception(f"Error while saving Unified Access Form: {e}")
            messages.error(self.request, _('خطایی در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)
        return super().form_valid(form)


class WorkflowBuilderView(PermissionBaseView, FormView):
    template_name = 'core/accessrule/workflow_builder.html'
    form_class = WorkflowForm
    permission_codenames = ['core.AccessRule_add', 'core.AccessRule_update']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.organization = get_object_or_404(Organization, pk=self.kwargs['org_pk'])
            self.entity_type = self.kwargs['entity_type']
            if self.entity_type not in [e[0] for e in ENTITY_TYPES]:
                raise Http404("Entity type not valid")
        except KeyError:
            raise Http404("Organization or Entity Type not specified in URL.")
        self.success_url = reverse('workflow_builder', args=[self.organization.pk, self.entity_type])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'organization': self.organization,
            'entity_type': self.entity_type,
            'user': self.request.user
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context['form']
        entity_label = dict(ENTITY_TYPES).get(self.entity_type, self.entity_type)
        context['title'] = _(f"طراحی گردش کار برای '{entity_label}' در '{self.organization.name}' و زیرمجموعه‌ها")
        context['organization'] = self.organization
        context['entity_type'] = self.entity_type

        workflow_data = sorted(form.levels_data.items())
        context['workflow_data'] = workflow_data
        context['has_data_to_display'] = bool(workflow_data)

        # --- بخش جدید: آماده‌سازی داده برای تب گزارش ---
        report_data = defaultdict(list)
        if hasattr(form, 'cleaned_data'):  # اگر فرم ارسال شده باشد، از داده‌های تمیز شده استفاده کن
            for level, data in form.levels_data.items():
                stage_name = form.cleaned_data.get(f'stage_name__{level}') or _(f"مرحله سطح {level}")
                for post_data in data['posts_data']:
                    post = post_data['post_obj']
                    for action_field in post_data['workflow_actions']:
                        if form.cleaned_data.get(action_field.name):
                            report_data[post].append({'stage_name': stage_name, 'action_label': action_field.label})
        else:  # در غیر این صورت (درخواست GET)، از داده‌های اولیه استفاده کن
            for level, data in workflow_data:
                stage_name = form.fields[f'stage_name__{level}'].initial or _(f"مرحله سطح {level}")
                for post_data in data['posts_data']:
                    post = post_data['post_obj']
                    for action_field in post_data['workflow_actions']:
                        if action_field.field.initial:
                            report_data[post].append({'stage_name': stage_name, 'action_label': action_field.label})

        # مرتب‌سازی گزارش برای نمایش بهتر
        context['report_data'] = sorted(report_data.items(), key=lambda item: (item[0].level, item[0].name))

        return context

    def form_valid(self, form):
        try:
            form.save()
            messages.success(self.request, _('گردش کار با موفقیت ذخیره شد.'))
        except Exception as e:
            logger.exception(f"Error while saving Workflow Form: {e}")
            messages.error(self.request, _('خطایی در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)
        return super().form_valid(form)