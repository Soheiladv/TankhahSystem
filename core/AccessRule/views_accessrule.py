# core/views.py
import logging

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic import FormView
from django.views.generic import ListView
from core.AccessRule.forms_accessrule import AccessRuleForm, PostAccessRuleForm
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

class AccessRuleListView(PermissionBaseView, ListView):
    model = AccessRule
    template_name = 'core/accessrule/accessrule_list.html'
    context_object_name = 'access_rules'
    paginate_by = 10
    permission_codenames = ['core.accessrule_view'] # Ensure this matches your actual permission
    check_organization = True
    extra_context = {
        'title': _('لیست قوانین دسترسی'),
        'entity_type_choices': ENTITY_TYPE_CHOICES, # Pass choices to the template
    }

    def get_queryset(self):
        queryset = super().get_queryset().select_related('organization', 'post', 'stage').order_by('-id')
        # Using '-id' to show latest rules first, or you can order by 'organization__name', 'post__name' etc.

        # Get filter parameters
        query = self.request.GET.get('q', '')
        is_active_param = self.request.GET.get('is_active', '')
        entity_type_param = self.request.GET.get('entity_type', '')

        # Apply filters
        if query:
            # Use Q objects for OR conditions
            queryset = queryset.filter(
                Q(organization__name__icontains=query) |
                Q(post__name__icontains=query) | # Assuming you want to search by post name too
                Q(entity_type__icontains=query) |
                Q(action_type__icontains=query) # Allow searching by action type
            )

        if is_active_param:
            queryset = queryset.filter(is_active=(is_active_param == 'true'))

        if entity_type_param:
            queryset = queryset.filter(entity_type=entity_type_param)

        logger.info(f"AccessRule queryset count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass filter values back to the template for sticky filters
        context['query'] = self.request.GET.get('q', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '') # Renamed to avoid conflict with model field if any
        context['entity_type_filter'] = self.request.GET.get('entity_type', '') # Renamed

        # Calculate total_access_rules BEFORE pagination
        # Use .count() on the filtered (but not paginated) queryset
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
        context['title'] = _('جزئیات قانون دسترسی') + f" - {self.object.organization}"
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

    def post(self, request, *args, **kwargs):
        messages.success(self.request, _('قانون دسترسی با موفقیت حذف شد.'))
        return super().post(request, *args, **kwargs)
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

class OK__PostAccessRuleAssignView(FormView):
    template_name = 'core/accessrule/post_access_rule_assign_b.html'
    form_class = PostAccessRuleForm
    success_url = reverse_lazy('accessrule_list')  # Ensure this URL name is correct

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت پست‌ها و قوانین دسترسی')
        # These context variables are no longer strictly needed by the template,
        # as the form's post_fields_data contains all necessary info.
        # total_columns and entity/action types can be removed.
        # context['entity_types'] = AccessRule.ENTITY_TYPES
        # context['action_types'] = AccessRule.ACTION_TYPES
        # context['total_table_columns'] = 4 + len(AccessRule.ENTITY_TYPES) * len(AccessRule.ACTION_TYPES)
        logger.info(f"Context prepared for PostAccessRuleAssignView.")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pass the user's organizations to the form for filtering posts
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            # Check if user has posts in holding organization or HQ branch
            if not (
                    self.request.user.userpost_set.filter(post__organization__is_holding=True,
                                                          is_active=True).exists() or
                    self.request.user.userpost_set.filter(post__branch='HQ', is_active=True).exists()
            ):
                # Filter posts by organizations where the user has an active post
                user_orgs = self.request.user.userpost_set.filter(is_active=True).values_list('post__organization',
                                                                                              flat=True).distinct()
                # Pass a QuerySet of Organization objects or a list of their IDs
                kwargs['user_organizations'] = Organization.objects.filter(id__in=user_orgs)
                logger.debug(f"Form kwargs filtered by user organizations: {list(user_orgs)}")
            else:
                logger.debug("User is superuser or has holding/HQ post, showing all posts.")
        else:
            logger.debug("User not authenticated or is superuser, showing all posts (or no filtering applied).")
        return kwargs

    # def form_valid(self, form):
    #     """
    #     Called when the form is valid.
    #     """
    #     try:
    #         form.save()  # The save logic is now encapsulated in the form
    #         messages.success(self.request, _('پست‌ها و قوانین دسترسی با موفقیت ذخیره شدند.'))
    #         logger.info("Form saved successfully.")
    #         return super().form_valid(form)
    #     except Exception as e:
    #         logger.exception(f"An unexpected error occurred during form saving: {str(e)}")
    #         messages.error(self.request, _('خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی رخ داد.'))
    #         return self.form_invalid(form)  # Re-render with errors if save fails

    def form_valid(self, form):
        try:
            # request.user را به متد save فرم منتقل کنید
            form.save(user=self.request.user)
            messages.success(self.request, _('پست‌ها و قوانین دسترسی با موفقیت ذخیره شدند.'))
            logger.info("فرم با موفقیت ذخیره شد.")
            return super().form_valid(form)
        except Exception as e:
            logger.exception(f"خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی فرم رخ داد: {str(e)}")
            messages.error(self.request, _('خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)  # در صورت بروز خطا، فرم را با خطاها نمایش دهید

    def form_invalid(self, form):
        """
        Called when the form is invalid.
        """
        logger.error(f"Form is invalid. Errors: {form.errors.as_json()}, Non-field errors: {form.non_field_errors()}")
        messages.error(self.request, _('خطایی در ذخیره‌سازی رخ داد. لطفاً ورودی‌ها را بررسی کنید.'))

        # Display specific field errors and non-field errors using Django messages
        # These will be caught and displayed by the template's message handling
        for field, errors in form.errors.items():
            for error in errors:
                messages.warning(self.request, f"{_('خطا در فیلد')} {field}: {error}")
        for error in form.non_field_errors():
            messages.warning(self.request, f"{_('خطای عمومی')}: {error}")

        return super().form_invalid(form)
class PostAccessRuleAssignView(FormView):
    template_name = 'core/accessrule/post_access_rule_assign_b.html'  # نام تمپلیت جدید و بهینه
    form_class = PostAccessRuleForm
    success_url = reverse_lazy('accessrule_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("تنظیم قوانین دسترسی پست‌ها")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        posts_query = Post.objects.filter(is_active=True).select_related('organization', 'parent')

        if not self.request.user.is_superuser:
            user_orgs = self.request.user.userpost_set.filter(is_active=True).values_list('post__organization',
                                                                                          flat=True).distinct()
            posts_query = posts_query.filter(organization__id__in=user_orgs)

        kwargs['posts_query'] = posts_query
        logger.debug(f"Passing {posts_query.count()} posts to PostAccessRuleForm.")
        return kwargs

    def form_valid(self, form):
        try:
            form.save(user=self.request.user)
            messages.success(self.request, _('پست‌ها و قوانین دسترسی با موفقیت ذخیره شدند.'))
            logger.info("فرم با موفقیت ذخیره شد.")
            return super().form_valid(form)
        except Exception as e:
            logger.exception(f"خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی فرم رخ داد: {str(e)}")
            messages.error(self.request, _('خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(f"فرم نامعتبر است. خطاها: {form.errors.as_json()}, خطاهای غیرفیلدی: {form.non_field_errors()}")
        messages.error(self.request, _('خطایی در ذخیره‌سازی رخ داد. لطفاً ورودی‌ها را بررسی کنید.'))

        for field, errors in form.errors.items():
            display_field_name = field
            if field.startswith('post_') and field.endswith('_level'):
                post_id = field.split('_')[1]
                try:
                    post = Post.objects.get(id=post_id)
                    display_field_name = f"{_('سطح پست')}: {post.name}"
                except Post.DoesNotExist:
                    pass
            elif field.startswith('rule_') or field.startswith('signer_'):
                display_field_name = _("قانون دسترسی")

            # messages.warning(self.request, f"{_('خطا در فیلد')} {display_field_name}: {error}")

        for error in form.non_field_errors():
            messages.warning(self.request, f"{_('خطای عمومی')}: {error}")

        return super().form_invalid(form)
