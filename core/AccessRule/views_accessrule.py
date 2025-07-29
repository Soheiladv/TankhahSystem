# core/views.py
import logging

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import FormView
from django.views.generic import ListView
from core.AccessRule.forms_accessrule import AccessRuleForm, PostAccessRuleForm, PostAccessRuleForm_new
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
    form_class = AccessRuleForm
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
    form_class = AccessRuleForm
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

class PostAccessRuleAssignView(PermissionBaseView, FormView):
    template_name = 'core/accessrule/post_access_rule_assignnew.html'
    form_class = PostAccessRuleForm_new
    success_url = reverse_lazy('accessrule_list')
    permission_codenames = ['core.AccessRule_add', 'core.AccessRule_update']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("تنظیم قوانین دسترسی پست‌ها")
        context['action_type_choices'] =  ACTION_TYPES
        context['entity_type_choices'] =  ENTITY_TYPES
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # مهم: پست‌ها را بر اساس level مرتب کنید تا در فرم نیز به همین ترتیب نمایش داده شوند.
        # این کار را قبلاً انجام داده‌اید و درست است.
        posts_query = Post.objects.filter(is_active=True).select_related('organization', 'parent').order_by('level', 'name')

        if not self.request.user.is_superuser:
            user_orgs = self.request.user.userpost_set.filter(is_active=True).values_list('post__organization', flat=True).distinct()
            posts_query = posts_query.filter(organization__id__in=user_orgs)

        kwargs['posts_query'] = posts_query
        logger.debug(f"Passing {posts_query.count()} posts to PostAccessRuleForm, sorted by level.")
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # تابع save در فرم اکنون بدون تلاش برای تغییر level پست، فقط قوانین را ذخیره می‌کند.
                form.save(user=self.request.user)
                messages.success(self.request, _('قوانین دسترسی پست‌ها با موفقیت ذخیره شدند.'))
                logger.info("PostAccessRuleForm successfully saved.")
                return super().form_valid(form)
        except ValueError as e:
            logger.exception(f"ValueError while saving form: {str(e)}")
            messages.error(self.request, f"{_('خطا در ذخیره‌سازی قوانین')}: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            logger.exception(f"Unexpected error while saving form: {str(e)}")
            messages.error(self.request, _('خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی رخ داد. لطفاً با پشتیبانی تماس بگیرید.'))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid. Errors: {form.errors.as_json()}, Non-field errors: {form.non_field_errors()}")
        messages.error(self.request, _('لطفاً حداقل یک قانون دسترسی (مانند ویرایش، مشاهده، تأیید یا رد) برای یکی از پست‌ها انتخاب کنید یا ترتیب مراحل را بررسی کنید.'))

        for field, errors in form.errors.items():
            display_field_name = field
            # این بخش مربوط به فیلد level بود که حذف خواهد شد
            # if field.startswith('post_') and field.endswith('_level'):
            #     post_id = field.split('_')[1]
            #     try:
            #         post = Post.objects.get(id=post_id)
            #         display_field_name = f"{_('سطح پست')}: {post.name}"
            #     except Post.DoesNotExist:
            #         pass
            if field.startswith('rule_') or field.startswith('signer_') or field.startswith('new_stage_'):
                display_field_name = _("قانون دسترسی یا مرحله جدید")
            for error in errors:
                messages.warning(self.request, f"{_('خطا در فیلد')} {display_field_name}: {error}")

        for error in form.non_field_errors():
            messages.warning(self.request, f"{_('خطای عمومی')}: {error}")

        return super().form_invalid(form)
