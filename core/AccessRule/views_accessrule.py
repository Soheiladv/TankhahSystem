# core/views.py
import logging

from django.contrib import messages
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
class AccessRuleListView(PermissionBaseView, ListView):
    model = AccessRule
    template_name = 'core/accessrule/accessrule_list.html'
    context_object_name = 'access_rules'
    paginate_by = 10
    permission_codenames = ['core.AccessRule_view']
    check_organization = True
    extra_context = {'title': _('لیست قوانین دسترسی')}

    def get_queryset(self):
        queryset = super().get_queryset().select_related('organization', 'stage').order_by('id')
        query = self.request.GET.get('q', '')
        is_active = self.request.GET.get('is_active', '')
        entity_type = self.request.GET.get('entity_type', '')

        if query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(organization__name__icontains=query) |
                Q(branch__icontains=query) |
                Q(entity_type__icontains=query)
            )

        if is_active:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        logger.info(f"AccessRule queryset count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['is_active'] = self.request.GET.get('is_active', '')
        context['entity_type'] = self.request.GET.get('entity_type', '')
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

class ___PostAccessRuleAssignView(FormView):
    template_name = 'core/accessrule/post_access_rule_assign_b.html'
    form_class = PostAccessRuleForm
    success_url = reverse_lazy('accessrule_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت پست‌ها و قوانین دسترسی')
        context['entity_types'] = AccessRule.ENTITY_TYPES
        context['action_types'] = AccessRule.ACTION_TYPES
        total_columns = 4 + len(AccessRule.ENTITY_TYPES) * len(AccessRule.ACTION_TYPES)
        context['total_table_columns'] = total_columns
        logger.info(f"Context prepared. Form posts: {len(context['form'].posts)}, Total columns: {total_columns}")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            if not (
                self.request.user.userpost_set.filter(post__organization__is_holding=True).exists() or
                self.request.user.userpost_set.filter(post__branch='HQ').exists()
            ):
                user_orgs = self.request.user.userpost_set.filter(is_active=True).values('post__organization')
                kwargs['user_organizations'] = user_orgs
                logger.debug(f"Filtered by user organizations: {user_orgs}")
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        logger.info(f"درخواست POST دریافت شد. داده‌ها: {dict(request.POST)}")

        # اعتبارسنجی فیلدهای قانون
        valid_action_types = dict(AccessRule.ACTION_TYPES).keys()  # ['APPROVE', 'REJECT', 'VIEW', 'SIGN_PAYMENT']
        invalid_fields = []

        for field in request.POST:
            if '_rule_' in field and not field.endswith('_stage'):
                parts = field.split('_')
                if len(parts) < 5:
                    invalid_fields.append(field)
                    continue
                entity_type = parts[3]
                action_type = 'SIGN_PAYMENT' if field.endswith('_SIGN_PAYMENT') else parts[4]
                if action_type not in valid_action_types:
                    invalid_fields.append(field)

        if invalid_fields:
            logger.warning(f"فیلدهای نامعتبر یافت شد: {invalid_fields}")
            messages.error(request, f"فیلدهای نامعتبر: {', '.join(invalid_fields)}")
            # افزودن خطاها به فرم برای لاگ‌گیری بهتر
            form.add_error(None, f"فیلدهای نامعتبر: {', '.join(invalid_fields)}")
            return self.form_invalid(form)

        if form.is_valid():
            logger.info("فرم معتبر است، ادامه ذخیره‌سازی")
            return self.form_valid(form)
        else:
            logger.error(f"فرم نامعتبر است. خطاها: {form.errors.as_json()}, غیرفیلدی: {form.non_field_errors()}")
            if not form.errors:
                messages.error(request, "فرم به دلیل خطای ناشناخته نامعتبر است. لطفاً دوباره تلاش کنید.")
            return self.form_invalid(form)

    def form_invalid(self, form):
        logger.error(
            f"فرم نامعتبر است. خطاها: {form.errors.as_json()}, غیرفیلدی: {form.non_field_errors()}, داده‌ها: {dict(self.request.POST)}")
        messages.error(self.request, _('خطایی در ذخیره‌سازی رخ داد. لطفاً ورودی‌ها را بررسی کنید.'))
        # نمایش خطاهای خاص فیلدها و غیرفیلدی
        for field, errors in form.errors.items():
            for error in errors:
                messages.warning(self.request, f"خطا در فیلد {field}: {error}")
        for error in form.non_field_errors():
            messages.warning(self.request, f"خطای عمومی: {error}")
        return super().form_invalid(form)

    def form_valid(self, form):
        try:
            cleaned_data = form.cleaned_data
            logger.info(f"پردازش داده‌های فرم. فیلدها: {list(cleaned_data.keys())}")

            # جمع‌آوری پست‌های تغییرکرده
            post_ids = set()
            for field_name in cleaned_data:
                if '_rule_' in field_name and not field_name.endswith('_stage'):
                    try:
                        post_id = int(field_name.split('_')[1])
                        post_ids.add(post_id)
                    except (IndexError, ValueError):
                        logger.warning(f"فرمت نام فیلد نامعتبر: {field_name}")
                        continue
            logger.info(f"شناسه‌های پست برای پردازش: {post_ids}")

            # به‌روزرسانی سطح پست‌ها
            posts_to_update = []
            for field_name in cleaned_data:
                if field_name.endswith('_level'):
                    try:
                        post_id = int(field_name.split('_')[1])
                        level = cleaned_data[field_name] or 1
                        post = Post.objects.get(id=post_id)
                        post.level = level
                        posts_to_update.append(post)
                        logger.debug(f"پست {post.name} به سطح {level} به‌روزرسانی می‌شود")
                    except Post.DoesNotExist:
                        logger.error(f"پست با شناسه {post_id} یافت نشد")
                        continue

            if posts_to_update:
                Post.objects.bulk_update(posts_to_update, ['level'])
                logger.info(f"{len(posts_to_update)} پست به‌روزرسانی شد")

            # حذف قوانین قبلی برای پست‌های انتخاب‌شده
            if post_ids:
                AccessRule.objects.filter(post__id__in=post_ids).delete()
                logger.info(f"قوانین برای پست‌ها حذف شد: {post_ids}")

            # ایجاد قوانین جدید
            rules_to_create = []
            for field_name in cleaned_data:
                if '_rule_' in field_name and not field_name.endswith('_stage'):
                    parts = field_name.split('_')
                    if len(parts) >= 5:
                        try:
                            post_id = int(parts[1])
                            entity_type = parts[3]
                            action_type = parts[4]
                            if cleaned_data[field_name]:
                                stage = cleaned_data.get(f"{field_name}_stage")
                                if stage:
                                    post = Post.objects.get(id=post_id)
                                    rules_to_create.append(
                                        AccessRule(
                                            post=post,
                                            organization=post.organization,
                                            branch=post.branch or '',
                                            stage=stage,
                                            action_type=action_type,
                                            entity_type=entity_type,
                                            is_active=True,
                                            is_payment_order_signer=(action_type == 'SIGN_PAYMENT')
                                        )
                                    )
                                    logger.debug(f"قانون برای پست {post.name} ایجاد خواهد شد: {entity_type}/{action_type}")
                                else:
                                    logger.warning(f"مرحله برای {field_name} وجود ندارد، رد می‌شود")
                        except Post.DoesNotExist:
                            logger.error(f"پست با شناسه {post_id} یافت نشد")
                            continue

            if rules_to_create:
                AccessRule.objects.bulk_create(rules_to_create)
                logger.info(f"{len(rules_to_create)} قانون ایجاد شد")
            else:
                logger.info("هیچ قانونی برای ایجاد وجود ندارد")

            messages.success(self.request, 'پست‌ها و قوانین با موفقیت ذخیره شدند.')
            logger.info("ذخیره‌سازی با موفقیت انجام شد")
            return super().form_valid(form)

        except Exception as e:
            logger.exception(f"خطای غیرمنتظره در form_valid: {str(e)}")
            messages.error(self.request, 'خطای غیرمنتظره‌ای رخ داد.')
            return self.form_invalid(form)


# budgets/views.py

class PostAccessRuleAssignView(FormView):
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

    def form_valid(self, form):
        """
        Called when the form is valid.
        """
        try:
            form.save()  # The save logic is now encapsulated in the form
            messages.success(self.request, _('پست‌ها و قوانین دسترسی با موفقیت ذخیره شدند.'))
            logger.info("Form saved successfully.")
            return super().form_valid(form)
        except Exception as e:
            logger.exception(f"An unexpected error occurred during form saving: {str(e)}")
            messages.error(self.request, _('خطای غیرمنتظره‌ای در هنگام ذخیره‌سازی رخ داد.'))
            return self.form_invalid(form)  # Re-render with errors if save fails

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