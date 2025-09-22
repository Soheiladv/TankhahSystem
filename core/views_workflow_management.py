"""
ویوهای مدیریت قوانین گردش کار
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .models import Organization, Post, Status, Action, Transition, PostAction, EntityType
from .models import PostRuleAssignment
from .workflow_management import WorkflowRuleManager
from tankhah.models import StageApprover

logger = logging.getLogger(__name__)


# class WorkflowTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
#     """
#     لیست تمپلیت‌های قوانین گردش کار
#     """
#     model = WorkflowRuleTemplate
#     template_name = 'core/workflow/template_list.html'
#     context_object_name = 'templates'
#     paginate_by = 20
#     permission_required = 'core.WorkflowRuleTemplate_view'
#     
#     def get_queryset(self):
#         queryset = WorkflowRuleTemplate.objects.filter(is_active=True)
#         
#         # فیلتر بر اساس سازمان
#         if 'organization_id' in self.request.GET:
#             queryset = queryset.filter(organization_id=self.request.GET['organization_id'])
#         
#         # فیلتر بر اساس نوع موجودیت
#         if 'entity_type' in self.request.GET:
#             queryset = queryset.filter(entity_type=self.request.GET['entity_type'])
#         
#         # فیلتر بر اساس عمومی بودن
#         if 'is_public' in self.request.GET:
#             queryset = queryset.filter(is_public=self.request.GET['is_public'] == 'true')
#         
#         return queryset.select_related('organization', 'created_by').order_by('-created_at')
#     
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['organizations'] = Organization.objects.filter(is_active=True)
#         context['entity_types'] = [
#             ('FACTOR', _('فاکتور')),
#             ('TANKHAH', _('تنخواه')),
#             ('PAYMENTORDER', _('دستور پرداخت')),
#             ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
#         ]
#         return context


# class WorkflowTemplateDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
#     """
#     جزئیات تمپلیت قوانین گردش کار
#     """
#     model = WorkflowRuleTemplate
#     template_name = 'core/workflow/template_detail.html'
#     context_object_name = 'template'
#     permission_required = 'core.WorkflowRuleTemplate_view'
#     
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         template = self.get_object()
#         
#         # خلاصه قوانین
#         context['workflow_summary'] = WorkflowRuleManager.get_workflow_summary(
#             template.organization, template.entity_type
#         )
#         
#         # اعتبارسنجی قوانین
#         context['validation_result'] = WorkflowRuleManager.validate_workflow_consistency(
#             template.organization, template.entity_type
#         )
#         
#         return context

# class WorkflowTemplateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
#     """
#     ویرایش تمپلیت قوانین گردش کار
#     """
#     model = WorkflowRuleTemplate
#     template_name = 'core/workflow/template_form.html'
#     fields = ['name', 'description', 'organization', 'entity_type', 'is_public', 'is_active']
#     permission_required = 'core.WorkflowRuleTemplate_change'
#     success_url = reverse_lazy('workflow_management:template_list')
#     
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['organizations'] = Organization.objects.filter(is_active=True)
#         context['entity_types'] = [
#             ('FACTOR', _('فاکتور')),
#             ('TANKHAH', _('تنخواه')),
#             ('PAYMENTORDER', _('دستور پرداخت')),
#             ('BUDGET', _('بودجه')),
#         ]
#         context['is_edit'] = True
#         return context


# class WorkflowTemplateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
#     """
#     حذف تمپلیت قوانین گردش کار
#     """
#     model = WorkflowRuleTemplate
#     template_name = 'core/workflow/template_confirm_delete.html'
#     permission_required = 'core.WorkflowRuleTemplate_delete'
#     success_url = reverse_lazy('workflow_management:template_list')
#     
#     def delete(self, request, *args, **kwargs):
#         self.object = self.get_object()
#         # حذف نرم (غیرفعال کردن)
#         self.object.is_active = False
#         self.object.save()
#         messages.success(request, f'تمپلیت "{self.object.name}" با موفقیت حذف شد.')
#         return redirect(self.get_success_url())


# class WorkflowTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
#     """
#     ایجاد تمپلیت جدید قوانین گردش کار
#     """
#     model = WorkflowRuleTemplate
#     template_name = 'core/workflow/template_form.html'
#     fields = ['name', 'description', 'organization', 'entity_type', 'is_public']
#     permission_required = 'core.WorkflowRuleTemplate_add'
#     success_url = reverse_lazy('workflow_management:template_list')
#     
#     def form_valid(self, form):
#         form.instance.created_by = self.request.user
#         form.instance.is_active = True
#         # ایجاد rules_data خالی
#         form.instance.rules_data = {
#             'statuses': [],
#             'actions': [],
#             'transitions': [],
#             'post_actions': [],
#         }
#         response = super().form_valid(form)
#         messages.success(self.request, f'تمپلیت "{form.instance.name}" با موفقیت ایجاد شد.')
#         return response
#     
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['organizations'] = Organization.objects.filter(is_active=True)
#         context['entity_types'] = [
#             ('FACTOR', _('فاکتور')),
#             ('TANKHAH', _('تنخواه')),
#             ('PAYMENTORDER', _('دستور پرداخت')),
#             ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
#         ]
#         return context


# @login_required
# @require_http_methods(["POST"])
# def create_template_from_existing(request):
#     """
#     ایجاد تمپلیت از قوانین موجود
#     """
#     try:
#         organization_id = request.POST.get('organization_id')
#         entity_type = request.POST.get('entity_type')
#         name = request.POST.get('name')
#         description = request.POST.get('description', '')
#         
#         if not all([organization_id, entity_type, name]):
#             return JsonResponse({
#                 'success': False,
#                 'message': 'تمام فیلدهای اجباری باید پر شوند.'
#             })
#         
#         organization = get_object_or_404(Organization, id=organization_id)
#         
#         template = WorkflowRuleManager.create_rule_template_from_existing(
#             organization=organization,
#             entity_type=entity_type,
#             template_name=name,
#             description=description
#         )
#         
#         return JsonResponse({
#             'success': True,
#             'message': f'تمپلیت {name} با موفقیت ایجاد شد.',
#             'template_id': template.id
#         })
#         
#     except Exception as e:
#         logger.error(f"خطا در ایجاد تمپلیت: {str(e)}")
#         return JsonResponse({
#             'success': False,
#             'message': f'خطا در ایجاد تمپلیت: {str(e)}'
#         })


# @login_required
# def apply_template_to_organization(request, template_id):
#     """
#     اعمال تمپلیت به یک سازمان
#     """
#     if request.method == 'GET':
#         # نمایش فرم اعمال تمپلیت
#         template = get_object_or_404(WorkflowRuleTemplate, id=template_id)
#         organizations = Organization.objects.filter(is_active=True)
#         
#         context = {
#             'template': template,
#             'organizations': organizations,
#         }
#         return render(request, 'core/workflow/apply_template.html', context)
#     
#     elif request.method == 'POST':
#         try:
#             template = get_object_or_404(WorkflowRuleTemplate, id=template_id)
#             target_organization_id = request.POST.get('target_organization_id')
#             
#             if not target_organization_id:
#                 return JsonResponse({
#                     'success': False,
#                     'message': 'سازمان مقصد باید انتخاب شود.'
#                 })
#             
#             target_organization = get_object_or_404(Organization, id=target_organization_id)
#             
#             # Apply template to organization - this method needs to be implemented in the model
#             # For now, we'll return success
#             success = True
#             
#             if success:
#                 return JsonResponse({
#                     'success': True,
#                     'message': f'تمپلیت با موفقیت به سازمان {target_organization.name} اعمال شد.'
#                 })
#             else:
#                 return JsonResponse({
#                     'success': False,
#                     'message': 'خطا در اعمال تمپلیت.'
#                 })
#             
#         except Exception as e:
#             logger.error(f"خطا در اعمال تمپلیت: {str(e)}")
#             return JsonResponse({
#                 'success': False,
#                 'message': f'خطا در اعمال تمپلیت: {str(e)}'
#             })
#     
#     else:
#         return JsonResponse({
#             'success': False,
#             'message': 'متد غیرمجاز'
#         })


@login_required
def step_by_step_guide(request):
    """
    راهنمای قدم به قدم گردش کار
    """
    return render(request, 'core/workflow/simple_dashboard.html')


class StatusListView(LoginRequiredMixin, ListView):
    """
    لیست وضعیت‌ها
    """
    model = Status
    template_name = 'core/workflow/Status/status_list.html'
    context_object_name = 'statuses'
    paginate_by = 20
    
    def get_queryset(self):
        return Status.objects.filter(is_active=True).order_by('name')


class StatusCreateView(LoginRequiredMixin, CreateView):
    """
    ایجاد وضعیت جدید
    """
    model = Status
    template_name = 'core/workflow/Status/status_form.html'
    fields = ['name', 'code', 'description', 'is_initial', 'is_final_approve', 'is_final_reject']
    success_url = reverse_lazy('workflow_management:status_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.is_active = True
        return super().form_valid(form)


class StatusUpdateView(LoginRequiredMixin, UpdateView):
    """
    ویرایش وضعیت
    """
    model = Status
    template_name = 'core/workflow/Status/status_form.html'
    fields = ['name', 'code', 'description', 'is_initial', 'is_final_approve', 'is_final_reject']
    success_url = reverse_lazy('workflow_management:status_list')


class StatusDeleteView(LoginRequiredMixin, DeleteView):
    """
    حذف وضعیت
    """
    model = Status
    template_name = 'core/workflow/Status/confirm_retire.html'
    success_url = reverse_lazy('workflow_management:status_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        return redirect(self.success_url)


class ActionListView(LoginRequiredMixin, ListView):
    """
    لیست اقدامات
    """
    model = Action
    template_name = 'core/workflow/Action/action_list.html'
    context_object_name = 'actions'
    paginate_by = 20
    
    def get_queryset(self):
        return Action.objects.filter(is_active=True).order_by('name')


class ActionCreateView(LoginRequiredMixin, CreateView):
    """
    ایجاد اقدام جدید
    """
    model = Action
    template_name = 'core/workflow/Action/action_form.html'
    fields = ['name', 'code', 'description']
    success_url = reverse_lazy('workflow_management:action_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.is_active = True
        return super().form_valid(form)


class ActionUpdateView(LoginRequiredMixin, UpdateView):
    """
    ویرایش اقدام
    """
    model = Action
    template_name = 'core/workflow/Action/action_form.html'
    fields = ['name', 'code', 'description']
    success_url = reverse_lazy('workflow_management:action_list')


class ActionDeleteView(LoginRequiredMixin, DeleteView):
    """
    حذف اقدام
    """
    model = Action
    template_name = 'core/workflow/Action/confirm_retire.html'
    success_url = reverse_lazy('workflow_management:action_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        return redirect(self.success_url)


@login_required
def complete_guide(request):
    """
    راهنمای کامل سیستم مدیریت گردش کار
    """
    return render(request, 'core/workflow/complete_guide.html')


@login_required
def simple_workflow_dashboard(request):
    """
    داشبورد ساده مدیریت گردش کار
    """
    try:
        # آمار کلی
        templates_count = 0  # WorkflowRuleTemplate حذف شده
        statuses_count = Status.objects.filter(is_active=True).count()
        actions_count = Action.objects.filter(is_active=True).count()
        assignments_count = PostRuleAssignment.objects.filter(is_active=True).count()
        transitions_count = Transition.objects.filter(is_active=True).count()
        
        # آمار اخیر
        recent_statuses = Status.objects.filter(is_active=True).order_by('-created_at')[:5]
        recent_actions = Action.objects.filter(is_active=True).order_by('-created_at')[:5]
        recent_assignments = PostRuleAssignment.objects.filter(is_active=True).order_by('-created_at')[:5]
        
        # آمار بر اساس نوع موجودیت
        entity_stats = {}
        for entity_type in ['TANKHAH', 'FACTOR', 'PAYMENTORDER']:
            entity_stats[entity_type] = {
                'statuses': Status.objects.filter(is_active=True).count(),
                'actions': Action.objects.filter(is_active=True).count(),
                'assignments': PostRuleAssignment.objects.filter(
                    is_active=True, 
                    entity_type=entity_type
                ).count(),
            }
        
        context = {
            'templates_count': templates_count,
            'statuses_count': statuses_count,
            'actions_count': actions_count,
            'assignments_count': assignments_count,
            'transitions_count': transitions_count,
            'recent_statuses': recent_statuses,
            'recent_actions': recent_actions,
            'recent_assignments': recent_assignments,
            'entity_stats': entity_stats,
        }
        
        return render(request, 'core/workflow/simple_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"خطا در بارگذاری داشبورد: {e}")
        messages.error(request, f'خطا در بارگذاری داشبورد: {str(e)}')
        return render(request, 'core/workflow/simple_dashboard.html', {
            'templates_count': 0,
            'statuses_count': 0,
            'actions_count': 0,
            'assignments_count': 0,
            'transitions_count': 0,
            'recent_statuses': [],
            'recent_actions': [],
            'recent_assignments': [],
            'entity_stats': {},
        })


@login_required
def workflow_dashboard(request):
    """
    داشبورد ساده مدیریت گردش کار
    """
    try:
        # آمار کلی
        # templates_count = WorkflowRuleTemplate.objects.filter(is_active=True).count()
        templates_count = 0
        statuses_count = Status.objects.filter(is_active=True).count()
        actions_count = Action.objects.filter(is_active=True).count()
        transitions_count = Transition.objects.filter(is_active=True).count()
        
        # تمپلیت‌های اخیر
        # recent_templates = WorkflowRuleTemplate.objects.filter(is_active=True).order_by('-created_at')[:6]
        recent_templates = []
        
        # وضعیت‌ها
        statuses = Status.objects.filter(is_active=True).order_by('name')
        
        # اقدامات
        actions = Action.objects.filter(is_active=True).order_by('name')
        
        # انتقال‌ها
        transitions = Transition.objects.filter(is_active=True).select_related(
            'from_status', 'to_status', 'action', 'organization', 'entity_type'
        ).order_by('from_status__name')
        
        context = {
            'templates': recent_templates,
            'templates_count': templates_count,
            'statuses': statuses,
            'statuses_count': statuses_count,
            'actions': actions,
            'actions_count': actions_count,
            'transitions': transitions,
            'transitions_count': transitions_count,
        }
        
        return render(request, 'core/workflow/workflow_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"خطا در داشبورد گردش کار: {e}")
        messages.error(request, f"خطا در بارگذاری داشبورد: {str(e)}")
        return render(request, 'core/workflow/workflow_dashboard.html', {
            'templates': [],
            'templates_count': 0,
            'statuses': [],
            'statuses_count': 0,
            'actions': [],
            'actions_count': 0,
            'transitions': [],
            'transitions_count': 0,
        })


@login_required
def api_statuses(request):
    """
    API برای مدیریت وضعیت‌ها
    """
    if request.method == 'GET':
        statuses = Status.objects.filter(is_active=True).values('id', 'name', 'code', 'description', 'is_initial', 'is_final_approve', 'is_final_reject')
        return JsonResponse({'statuses': list(statuses)})
    
    elif request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            description = request.POST.get('description', '')
            is_initial = request.POST.get('is_initial') == 'on'
            is_final_approve = request.POST.get('is_final_approve') == 'on'
            is_final_reject = request.POST.get('is_final_reject') == 'on'
            
            status = Status.objects.create(
                name=name,
                code=code,
                description=description,
                is_initial=is_initial,
                is_final_approve=is_final_approve,
                is_final_reject=is_final_reject,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'وضعیت "{status.name}" با موفقیت ایجاد شد.',
                'status_id': status.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطا در ایجاد وضعیت: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'متد غیرمجاز'})


@login_required
def api_organizations(request):
    """
    API برای دریافت لیست سازمان‌ها
    """
    if request.method == 'GET':
        organizations = Organization.objects.filter(is_active=True).values('id', 'name', 'code')
        return JsonResponse({'organizations': list(organizations)})
    
    return JsonResponse({'success': False, 'message': 'متد غیرمجاز'})


@login_required
def api_actions(request):
    """
    API برای مدیریت اقدامات
    """
    if request.method == 'GET':
        actions = Action.objects.filter(is_active=True).values('id', 'name', 'code', 'description')
        return JsonResponse({'actions': list(actions)})
    
    elif request.method == 'POST':
        try:
            name = request.POST.get('name')
            code = request.POST.get('code')
            description = request.POST.get('description', '')
            
            action = Action.objects.create(
                name=name,
                code=code,
                description=description,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'اقدام "{action.name}" با موفقیت ایجاد شد.',
                'action_id': action.id
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'خطا در ایجاد اقدام: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'متد غیرمجاز'})


@login_required
def workflow_validation(request, organization_id, entity_type):
    """
    اعتبارسنجی قوانین گردش کار
    """
    try:
        organization = get_object_or_404(Organization, id=organization_id)
        
        validation_result = WorkflowRuleManager.validate_workflow_consistency(
            organization, entity_type
        )
        
        return JsonResponse(validation_result)
        
    except Exception as e:
        logger.error(f"خطا در اعتبارسنجی: {str(e)}")
        return JsonResponse({
            'is_valid': False,
            'errors': [f'خطا در اعتبارسنجی: {str(e)}'],
            'warnings': []
        })


@login_required
def workflow_summary(request, organization_id, entity_type):
    """
    خلاصه قوانین گردش کار
    """
    try:
        organization = get_object_or_404(Organization, id=organization_id)
        
        summary = WorkflowRuleManager.get_workflow_summary(organization, entity_type)
        
        if summary:
            return JsonResponse(summary)
        else:
            return JsonResponse({
                'error': 'خطا در دریافت خلاصه قوانین'
            })
        
    except Exception as e:
        logger.error(f"خطا در دریافت خلاصه: {str(e)}")
        return JsonResponse({
            'error': f'خطا در دریافت خلاصه: {str(e)}'
        })


@login_required
def export_workflow_rules(request, organization_id, entity_type):
    """
    صادرات قوانین گردش کار
    """
    try:
        organization = get_object_or_404(Organization, id=organization_id)
        format_type = request.GET.get('format', 'json')
        
        rules_data = WorkflowRuleManager.export_workflow_rules(
            organization, entity_type
        )
        
        if format_type == 'json':
            response = HttpResponse(
                json.dumps(rules_data, ensure_ascii=False, indent=2),
                content_type='application/json; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="workflow_rules_{entity_type}_{organization.code}.json"'
            return response
        
        elif format_type == 'yaml':
            import yaml
            response = HttpResponse(
                yaml.dump(rules_data, default_flow_style=False, allow_unicode=True),
                content_type='text/yaml; charset=utf-8'
            )
            response['Content-Disposition'] = f'attachment; filename="workflow_rules_{entity_type}_{organization.code}.yaml"'
            return response
        
        else:
            return JsonResponse({
                'error': 'فرمت پشتیبانی نشده'
            })
        
    except Exception as e:
        logger.error(f"خطا در صادرات: {str(e)}")
        return JsonResponse({
            'error': f'خطا در صادرات: {str(e)}'
        })


class PostRuleAssignmentListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    لیست تخصیص‌های قانون به پست‌ها
    """
    model = PostRuleAssignment
    template_name = 'core/workflow/post_rule_assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    permission_required = 'core.PostRuleAssignment_view'
    
    def get_queryset(self):
        queryset = PostRuleAssignment.objects.filter(is_active=True)
        
        # فیلتر بر اساس پست
        if 'post_id' in self.request.GET:
            queryset = queryset.filter(post_id=self.request.GET['post_id'])
        
        # فیلتر بر اساس نوع موجودیت
        if 'entity_type' in self.request.GET:
            queryset = queryset.filter(entity_type=self.request.GET['entity_type'])
        
        return queryset.select_related('post', 'action', 'organization').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = Post.objects.filter(is_active=True)
        context['entity_types'] = [
            ('FACTOR', _('فاکتور')),
            ('TANKHAH', _('تنخواه')),
            ('PAYMENTORDER', _('دستور پرداخت')),
            ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
        ]
        return context


@login_required
def assign_rule_to_post(request):
    """
    تخصیص قانون به پست
    """
    if request.method == 'GET':
        # نمایش فرم تخصیص
        posts = Post.objects.filter(is_active=True)
        # templates = WorkflowRuleTemplate.objects.filter(is_active=True)
        templates = []
        organizations = Organization.objects.filter(is_active=True)
        
        context = {
            'posts': posts,
            'templates': templates,
            'organizations': organizations,
        }
        return render(request, 'core/workflow/assign_rule_form.html', context)
    
    elif request.method == 'POST':
        try:
            post_id = request.POST.get('post_id')
            action_id = request.POST.get('action_id')
            organization_id = request.POST.get('organization_id')
            
            if not all([post_id, action_id, organization_id]):
                return JsonResponse({
                    'success': False,
                    'message': 'تمام فیلدهای اجباری باید پر شوند.'
                })
            
            post = get_object_or_404(Post, id=post_id)
            action = get_object_or_404(Action, id=action_id)
            organization = get_object_or_404(Organization, id=organization_id)
            
            entity_type = request.POST.get('entity_type', 'TANKHAH')
            assignment, created = PostRuleAssignment.objects.get_or_create(
                post=post,
                action=action,
                organization=organization,
                entity_type=entity_type,
                defaults={
                    'is_active': True,
                    'custom_settings': {},
                    'created_by': request.user
                }
            )
            
            if created:
                message = f'قانون با موفقیت به پست {post.name} تخصیص داده شد.'
            else:
                assignment.is_active = True
                assignment.save()
                message = f'تنظیمات قانون برای پست {post.name} به‌روزرسانی شد.'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'assignment_id': assignment.id
            })
            
        except Exception as e:
            logger.error(f"خطا در تخصیص قانون به پست: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در تخصیص قانون: {str(e)}'
            })


@login_required
def edit_rule_assignment(request, assignment_id):
    """
    ویرایش تخصیص قانون به پست
    """
    assignment = get_object_or_404(PostRuleAssignment, id=assignment_id)
    
    if request.method == 'GET':
        # نمایش فرم ویرایش
        posts = Post.objects.filter(is_active=True)
        actions = Action.objects.filter(is_active=True)
        organizations = Organization.objects.filter(is_active=True)
        
        context = {
            'assignment': assignment,
            'posts': posts,
            'actions': actions,
            'organizations': organizations,
            'entity_types': [
                ('TANKHAH', _('تنخواه')),
                ('FACTOR', _('فاکتور')),
                ('PAYMENTORDER', _('دستور پرداخت')),
            ]
        }
        return render(request, 'core/workflow/edit_rule_assignment.html', context)
    
    elif request.method == 'POST':
        try:
            post_id = request.POST.get('post_id')
            action_id = request.POST.get('action_id')
            organization_id = request.POST.get('organization_id')
            entity_type = request.POST.get('entity_type')
            is_active = request.POST.get('is_active') == 'on'
            
            if not all([post_id, action_id, organization_id, entity_type]):
                return JsonResponse({
                    'success': False,
                    'message': 'تمام فیلدهای اجباری باید پر شوند.'
                })
            
            post = get_object_or_404(Post, id=post_id)
            action = get_object_or_404(Action, id=action_id)
            organization = get_object_or_404(Organization, id=organization_id)
            
            assignment.post = post
            assignment.action = action
            assignment.organization = organization
            assignment.entity_type = entity_type
            assignment.is_active = is_active
            assignment.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تخصیص قانون با موفقیت به‌روزرسانی شد.',
                'assignment_id': assignment.id
            })
            
        except Exception as e:
            logger.error(f"خطا در ویرایش تخصیص قانون: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در ویرایش تخصیص: {str(e)}'
            })


@login_required
def delete_rule_assignment(request, assignment_id):
    """
    حذف تخصیص قانون به پست
    """
    if request.method == 'POST':
        try:
            assignment = get_object_or_404(PostRuleAssignment, id=assignment_id)
            assignment.is_active = False
            assignment.save()
            
            return JsonResponse({
                'success': True,
                'message': f'تخصیص قانون با موفقیت حذف شد.'
            })
            
        except Exception as e:
            logger.error(f"خطا در حذف تخصیص قانون: {e}")
            return JsonResponse({
                'success': False,
                'message': f'خطا در حذف تخصیص: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'متد غیرمجاز'
    })


@login_required
def get_post_effective_rules(request, assignment_id):
    """
    دریافت قوانین مؤثر برای یک پست
    """
    try:
        assignment = get_object_or_404(PostRuleAssignment, id=assignment_id)
        # Get effective rules - this method needs to be implemented in the model
        # For now, we'll return empty rules
        effective_rules = {}
        
        return JsonResponse({
            'success': True,
            'rules': effective_rules
        })
        
    except Exception as e:
        logger.error(f"خطا در دریافت قوانین مؤثر: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت قوانین مؤثر: {str(e)}'
        })


@login_required
def workflow_dashboard(request):
    """
    داشبورد مدیریت قوانین گردش کار
    """
    context = {
        'organizations': Organization.objects.filter(is_active=True),
        'entity_types': [
            ('FACTOR', _('فاکتور')),
            ('TANKHAH', _('تنخواه')),
            ('PAYMENTORDER', _('دستور پرداخت')),
            ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
        ],
        # 'recent_templates': WorkflowRuleTemplate.objects.filter(
        #     is_active=True
        # ).select_related('organization', 'created_by').order_by('-created_at')[:5],
        'recent_templates': [],
        # 'total_templates': WorkflowRuleTemplate.objects.filter(is_active=True).count(),
        'total_templates': 0,
        'total_assignments': PostRuleAssignment.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'core/workflow/dashboard.html', context)


# ==================== StageApprover Management Views ====================

class StageApproverListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    لیست StageApprover ها
    """
    model = StageApprover
    template_name = 'core/workflow/stage_approver_list.html'
    context_object_name = 'stage_approvers'
    paginate_by = 20
    permission_required = 'tankhah.stageapprover__view'
    
    def get_queryset(self):
        queryset = StageApprover.objects.filter(is_active=True)
        
        # فیلتر بر اساس مرحله
        if 'stage_id' in self.request.GET:
            queryset = queryset.filter(stage_id=self.request.GET['stage_id'])
        
        # فیلتر بر اساس پست
        if 'post_id' in self.request.GET:
            queryset = queryset.filter(post_id=self.request.GET['post_id'])
        
        # فیلتر بر اساس نوع موجودیت
        if 'entity_type' in self.request.GET:
            queryset = queryset.filter(entity_type=self.request.GET['entity_type'])
        
        # فیلتر بر اساس سازمان
        if 'organization_id' in self.request.GET:
            queryset = queryset.filter(post__organization_id=self.request.GET['organization_id'])
        
        return queryset.select_related('stage', 'post', 'post__organization').order_by('stage__name', 'post__name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stages'] = Status.objects.filter(is_active=True)
        context['posts'] = Post.objects.filter(is_active=True)
        context['organizations'] = Organization.objects.filter(is_active=True)
        context['entity_types'] = [
            ('FACTOR', _('فاکتور')),
            ('TANKHAH', _('تنخواه')),
            ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
        ]
        context['actions'] = [
            ('APPROVE', _('تأیید')),
            ('REJECT', _('رد')),
            ('PARTIAL', _('نیمه‌تأیید')),
        ]
        return context


class StageApproverCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    ایجاد StageApprover جدید
    """
    model = StageApprover
    template_name = 'core/workflow/stage_approver_form.html'
    fields = ['stage', 'post', 'entity_type', 'action', 'is_active']
    permission_required = 'tankhah.stageapprover__add'
    success_url = reverse_lazy('workflow_management:stage_approver_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تأییدکننده مرحله جدید')
        context['stages'] = Status.objects.filter(is_active=True)
        context['posts'] = Post.objects.filter(is_active=True)
        context['entity_types'] = [
            ('FACTOR', _('فاکتور')),
            ('TANKHAH', _('تنخواه')),
            ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
        ]
        context['actions'] = [
            ('APPROVE', _('تأیید')),
            ('REJECT', _('رد')),
            ('PARTIAL', _('نیمه‌تأیید')),
        ]
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'تأییدکننده مرحله "{form.instance.post.name}" برای "{form.instance.stage.name}" با موفقیت ایجاد شد.')
        return super().form_valid(form)


class StageApproverUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    ویرایش StageApprover
    """
    model = StageApprover
    template_name = 'core/workflow/stage_approver_form.html'
    fields = ['stage', 'post', 'entity_type', 'action', 'is_active']
    permission_required = 'tankhah.stageapprover__Update'
    success_url = reverse_lazy('workflow_management:stage_approver_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش تأییدکننده مرحله')
        context['is_edit'] = True
        context['stages'] = Status.objects.filter(is_active=True)
        context['posts'] = Post.objects.filter(is_active=True)
        context['entity_types'] = [
            ('FACTOR', _('فاکتور')),
            ('TANKHAH', _('تنخواه')),
            ('BUDGET_ALLOCATION', _('تخصیص بودجه')),
        ]
        context['actions'] = [
            ('APPROVE', _('تأیید')),
            ('REJECT', _('رد')),
            ('PARTIAL', _('نیمه‌تأیید')),
        ]
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'تأییدکننده مرحله "{form.instance.post.name}" برای "{form.instance.stage.name}" با موفقیت به‌روزرسانی شد.')
        return super().form_valid(form)


class StageApproverDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    حذف StageApprover
    """
    model = StageApprover
    template_name = 'core/workflow/stage_approver_confirm_delete.html'
    permission_required = 'tankhah.stageapprover__delete'
    success_url = reverse_lazy('workflow_management:stage_approver_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        messages.success(self.request, f'تأییدکننده مرحله "{self.object.post.name}" برای "{self.object.stage.name}" با موفقیت حذف شد.')
        return redirect(self.get_success_url())


@login_required
@require_http_methods(["POST"])
def bulk_create_stage_approvers(request):
    """
    ایجاد دسته‌ای StageApprover
    """
    try:
        data = json.loads(request.body)
        stage_id = data.get('stage_id')
        post_ids = data.get('post_ids', [])
        entity_type = data.get('entity_type', 'FACTOR')
        action = data.get('action', 'APPROVE')
        
        if not stage_id or not post_ids:
            return JsonResponse({
                'success': False,
                'message': 'مرحله و پست‌ها باید انتخاب شوند.'
            })
        
        stage = get_object_or_404(Status, id=stage_id)
        created_count = 0
        
        with transaction.atomic():
            for post_id in post_ids:
                post = get_object_or_404(Post, id=post_id)
                
                stage_approver, created = StageApprover.objects.get_or_create(
                    stage=stage,
                    post=post,
                    entity_type=entity_type,
                    defaults={
                        'action': action,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{created_count} تأییدکننده مرحله ایجاد شد.',
            'created_count': created_count
        })
        
    except Exception as e:
        logger.error(f"خطا در ایجاد دسته‌ای StageApprover: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در ایجاد تأییدکنندگان: {str(e)}'
        })


@login_required
def get_posts_by_organization(request, organization_id):
    """
    دریافت پست‌های یک سازمان
    """
    try:
        organization = get_object_or_404(Organization, id=organization_id)
        posts = Post.objects.filter(organization=organization, is_active=True).values('id', 'name', 'level')
        
        return JsonResponse({
            'success': True,
            'posts': list(posts)
        })
        
    except Exception as e:
        logger.error(f"خطا در دریافت پست‌ها: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت پست‌ها: {str(e)}'
        })


# ==================== Unified Workflow Management ====================

class UnifiedWorkflowManagementView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    نمای ترکیبی مدیریت قوانین گردش کار
    """
    template_name = 'core/workflow/unified_workflow_management.html'
    permission_required = 'core.PostRuleAssignment_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # آمار کلی
        context['post_rules_count'] = PostRuleAssignment.objects.filter(is_active=True).count()
        context['stage_approvers_count'] = StageApprover.objects.filter(is_active=True).count()
        context['organizations_count'] = Organization.objects.filter(is_active=True).count()
        context['stages_count'] = Status.objects.filter(is_active=True).count()
        
        return context


@login_required
def api_overview_stats(request):
    """
    API برای دریافت آمار کلی
    """
    try:
        stats = {
            'post_rules_count': PostRuleAssignment.objects.filter(is_active=True).count(),
            'stage_approvers_count': StageApprover.objects.filter(is_active=True).count(),
            'organizations_count': Organization.objects.filter(is_active=True).count(),
            'stages_count': Status.objects.filter(is_active=True).count(),
        }
        
        return JsonResponse({
            'success': True,
            **stats
        })
    except Exception as e:
        logger.error(f"خطا در دریافت آمار کلی: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت آمار: {str(e)}'
        })


@login_required
def api_post_rules(request):
    """
    API برای دریافت قوانین پست‌ها
    """
    try:
        queryset = PostRuleAssignment.objects.filter(is_active=True)
        
        # فیلترها
        if 'post_id' in request.GET:
            queryset = queryset.filter(post_id=request.GET['post_id'])
        if 'entity_type' in request.GET:
            queryset = queryset.filter(entity_type=request.GET['entity_type'])
        
        post_rules = []
        for rule in queryset.select_related('post', 'action', 'organization')[:20]:
            post_rules.append({
                'id': rule.id,
                'post_name': rule.post.name,
                'action_name': rule.action.name,
                'organization_name': rule.organization.name,
                'entity_type_display': rule.get_entity_type_display(),
                'is_active': rule.is_active,
            })
        
        # آخرین قوانین
        recent_rules = []
        for rule in PostRuleAssignment.objects.filter(is_active=True).select_related('post', 'action', 'organization').order_by('-created_at')[:5]:
            recent_rules.append({
                'id': rule.id,
                'post_name': rule.post.name,
                'action_name': rule.action.name,
                'organization_name': rule.organization.name,
                'entity_type_display': rule.get_entity_type_display(),
            })
        
        return JsonResponse({
            'success': True,
            'post_rules': post_rules,
            'recent_post_rules': recent_rules
        })
    except Exception as e:
        logger.error(f"خطا در دریافت قوانین پست‌ها: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت قوانین: {str(e)}'
        })


@login_required
def api_stage_approvers(request):
    """
    API برای دریافت تأییدکنندگان مراحل
    """
    try:
        queryset = StageApprover.objects.filter(is_active=True)
        
        # فیلترها
        if 'stage_id' in request.GET:
            queryset = queryset.filter(stage_id=request.GET['stage_id'])
        if 'post_id' in request.GET:
            queryset = queryset.filter(post_id=request.GET['post_id'])
        if 'entity_type' in request.GET:
            queryset = queryset.filter(entity_type=request.GET['entity_type'])
        
        stage_approvers = []
        for approver in queryset.select_related('stage', 'post', 'post__organization')[:20]:
            stage_approvers.append({
                'id': approver.id,
                'stage_name': approver.stage.name,
                'post_name': approver.post.name,
                'entity_type_display': approver.get_entity_type_display(),
                'action_display': approver.get_action_display() if approver.action else None,
                'is_active': approver.is_active,
            })
        
        # آخرین تأییدکنندگان
        recent_approvers = []
        for approver in StageApprover.objects.filter(is_active=True).select_related('stage', 'post')[:5]:
            recent_approvers.append({
                'id': approver.id,
                'stage_name': approver.stage.name,
                'post_name': approver.post.name,
                'entity_type_display': approver.get_entity_type_display(),
            })
        
        return JsonResponse({
            'success': True,
            'stage_approvers': stage_approvers,
            'recent_stage_approvers': recent_approvers
        })
    except Exception as e:
        logger.error(f"خطا در دریافت تأییدکنندگان مراحل: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت تأییدکنندگان: {str(e)}'
        })


@login_required
def api_filter_options(request):
    """
    API برای دریافت گزینه‌های فیلتر
    """
    try:
        posts = list(Post.objects.filter(is_active=True).values('id', 'name'))
        stages = list(Status.objects.filter(is_active=True).values('id', 'name'))
        
        return JsonResponse({
            'success': True,
            'posts': posts,
            'stages': stages
        })
    except Exception as e:
        logger.error(f"خطا در دریافت گزینه‌های فیلتر: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در دریافت گزینه‌ها: {str(e)}'
        })


@login_required
def api_check_duplicates(request):
    """
    API برای بررسی قوانین تکراری
    """
    try:
        # بررسی قوانین تکراری PostRuleAssignment
        from django.db.models import Count
        post_rule_duplicates = PostRuleAssignment.objects.filter(is_active=True).values(
            'post', 'action', 'organization', 'entity_type'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        duplicate_post_rules = []
        for duplicate in post_rule_duplicates:
            rules = PostRuleAssignment.objects.filter(
                post_id=duplicate['post'],
                action_id=duplicate['action'],
                organization_id=duplicate['organization'],
                entity_type=duplicate['entity_type'],
                is_active=True
            ).select_related('post', 'action', 'organization')
            
            duplicate_post_rules.append({
                'post_name': rules[0].post.name,
                'action_name': rules[0].action.name,
                'organization_name': rules[0].organization.name,
                'entity_type': rules[0].get_entity_type_display(),
                'count': len(rules),
                'rule_ids': [rule.id for rule in rules]
            })
        
        # بررسی تأییدکنندگان تکراری StageApprover
        stage_approver_duplicates = StageApprover.objects.filter(is_active=True).values(
            'stage', 'post', 'entity_type'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        duplicate_stage_approvers = []
        for duplicate in stage_approver_duplicates:
            approvers = StageApprover.objects.filter(
                stage_id=duplicate['stage'],
                post_id=duplicate['post'],
                entity_type=duplicate['entity_type'],
                is_active=True
            ).select_related('stage', 'post')
            
            duplicate_stage_approvers.append({
                'stage_name': approvers[0].stage.name,
                'post_name': approvers[0].post.name,
                'entity_type': approvers[0].get_entity_type_display(),
                'count': len(approvers),
                'approver_ids': [approver.id for approver in approvers]
            })
        
        return JsonResponse({
            'success': True,
            'duplicate_post_rules': duplicate_post_rules,
            'duplicate_stage_approvers': duplicate_stage_approvers,
            'total_duplicate_post_rules': len(duplicate_post_rules),
            'total_duplicate_stage_approvers': len(duplicate_stage_approvers)
        })
        
    except Exception as e:
        logger.error(f"خطا در بررسی قوانین تکراری: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'خطا در بررسی تکراری‌ها: {str(e)}'
        })
