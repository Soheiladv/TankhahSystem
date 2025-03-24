import json

from django.contrib import messages
from core.PermissionBase import  PermissionBaseView
from django.db.models import Q, Sum, F
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic import TemplateView

from .forms import OrganizationForm, ProjectForm, PostForm, UserPostForm, PostHistoryForm, WorkflowStageForm
from .models import Organization, Project, Post, UserPost, PostHistory, WorkflowStage
#######################################################################################
# داشبورد آماری تنخواه گردان
class DashboardView_flows_1(PermissionBaseView, TemplateView):
    template_name = 'core/dashboard1.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}
    permission_codenames = ['core.DashboardView_flows_view']  # تغییر به لیست

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user

        # گرفتن مراحل به ترتیب (پایین به بالا: order=5 تا order=0)
        workflow_stages = WorkflowStage.objects.all().order_by('-order')
        context['workflow_stages'] = workflow_stages

        # گرفتن پست‌های سازمانی کاربر
        user_posts = self.request.user.userpost_set.all()
        user_post_ids = [up.post.id for up in user_posts]
        logger.info(f"User {self.request.user} posts: {user_post_ids}")

        # دیکشنری برای ذخیره اطلاعات تنخواه‌ها
        tanbakh_by_stage = {}

        for stage in workflow_stages:
            # تنخواه‌ها در این مرحله
            tanbakhs = Tanbakh.objects.filter(current_stage=stage)

            # شمارش تنخواه‌ها
            draft_count = tanbakhs.filter(status='DRAFT').count()
            created_by_user_count = tanbakhs.filter(created_by=self.request.user).count()
            rejected_count = tanbakhs.filter(status='REJECTED').count()
            completed_count = tanbakhs.filter(status='COMPLETED').count()

            # تعیین رنگ و برچسب بر اساس مرحله و وضعیت
            if stage.order == 5 and draft_count > 0:  # شروع فرآیند (پایین‌ترین)
                color_class = 'bg-warning'  # نارنجی
                status_label = 'پیش‌نویس (جدید)'
            elif stage.order == 0 and tanbakhs.exists():  # سوپروایزر یا معاون مالی (بالاترین)
                if completed_count > 0:
                    color_class = 'bg-primary'  # آبی
                    status_label = 'تمام‌شده'
                elif rejected_count > 0:
                    color_class = 'bg-danger'  # قرمز
                    status_label = 'رد شده'
                else:
                    color_class = 'bg-info'  # فیروزه‌ای برای در حال بررسی
                    status_label = 'در حال بررسی سوپروایزر'
            elif created_by_user_count > 0:  # ثبت‌شده توسط کاربر
                color_class = 'bg-success'  # سبز
                status_label = 'ثبت‌شده توسط شما'
            elif rejected_count > 0:  # رد شده
                color_class = 'bg-danger'  # قرمز
                status_label = 'رد شده'
            elif completed_count > 0:  # تمام‌شده
                color_class = 'bg-primary'  # آبی
                status_label = 'تمام‌شده'
            else:  # در حال بررسی در مراحل میانی
                color_class = 'bg-secondary'  # خاکستری
                status_label = 'در انتظار بررسی'

            total_count = tanbakhs.count()
            tanbakh_by_stage[stage] = {
                'count': total_count,
                'color_class': color_class,
                'status_label': status_label,
            }
            logger.info(
                f"Stage {stage.name} (order={stage.order}): {total_count} tanbakhs, Color: {color_class}, Status: {status_label}")

        context['tanbakh_by_stage'] = tanbakh_by_stage
        return context


class DashboardView_flows(TemplateView):
    template_name = 'core/dashboard1.html'  # Adjust this to your actual template path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_posts = user.userpost_set.all()
        user_orgs = [up.post.organization for up in user_posts] if user_posts else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # Filter Tanbakh objects based on user permissions
        tanbakhs = Tanbakh.objects.all()
        if not is_hq_user and not self.request.user.is_superuser:
            tanbakhs = tanbakhs.filter(organization__in=user_orgs)

        # Summary of Tanbakh statuses
        context['tanbakh_summary'] = {
            'no_factor': {
                'count': tanbakhs.filter(factors__isnull=True).count(),
                'orgs': list(
                    tanbakhs.filter(factors__isnull=True).values_list('organization__name', flat=True).distinct())
            },
            'registered': {
                'count': tanbakhs.filter(factors__isnull=False).count(),
                'orgs': list(
                    tanbakhs.filter(factors__isnull=False).values_list('organization__name', flat=True).distinct())
            },
            'pending': {
                'count': tanbakhs.filter(status='PENDING').count(),
                'orgs': list(tanbakhs.filter(status='PENDING').values_list('organization__name', flat=True).distinct())
            },
            'archived': {
                'count': tanbakhs.filter(is_archived=True).count(),
                'orgs': list(tanbakhs.filter(is_archived=True).values_list('organization__name', flat=True).distinct())
            }
        }

        # Workflow stages with approvers
        workflow_stages = WorkflowStage.objects.all().order_by('-order')
        tanbakh_by_stage = {}
        for stage in workflow_stages:
            stage_tanbakhs = tanbakhs.filter(current_stage=stage)
            can_approve = user.has_perm('tanbakh.tanbakh_approve') and any(
                p.post.stageapprover_set.filter(stage=stage).exists() for p in user_posts
            )
            # Use 'post__name' instead of 'post__title'
            approvers = StageApprover.objects.filter(stage=stage).values_list('post__name', flat=True)

            tanbakh_by_stage[stage] = {
                'count': stage_tanbakhs.count(),
                'color_class': 'bg-info' if stage_tanbakhs.filter(status='PENDING').exists() else 'bg-secondary',
                'status_label': 'در انتظار تأیید' if stage_tanbakhs.filter(
                    status='PENDING').exists() else 'بدون تنخواه',
                'tanbakhs': stage_tanbakhs,
                'can_approve': can_approve,
                'approvers': list(approvers),
            }
        context['tanbakh_by_stage'] = tanbakh_by_stage

        return context


#######################################################################################
# سازمان‌ها
# @method_decorator(has_permission('Organization_view'), name='dispatch')
class OrganizationListView(PermissionBaseView, ListView):
    model = Organization
    template_name = 'core/organization_list.html'
    context_object_name = 'organizations'
    paginate_by = 10
    extra_context = {'title': _('لیست سازمان‌ها')}
    permission_codename =  'core.Organization_view'
    check_organization = True  # فعال کردن چک سازمان


    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(code__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


# @method_decorator(has_permission('Organization_view'), name='dispatch')
class OrganizationDetailView(PermissionBaseView, DetailView):
    model = Organization
    template_name = 'core/organization_detail.html'
    context_object_name = 'organization'
    permission_codename =  'core.Organization_view'
    check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات سازمان') + f" - {self.object.code}"
        return context


# @method_decorator(has_permission('Organization_add'), name='dispatch')
class OrganizationCreateView(PermissionBaseView, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')

    permission_codename =  'core.Organization_add'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد سازمان جدید')
        return context


# @method_decorator(has_permission('Organization_update'), name='dispatch')
class OrganizationUpdateView(PermissionBaseView, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')
    permission_codename =  'core.Organization_update'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش سازمان') + f" - {self.object.code}"
        return context


# @method_decorator(has_permission('Organization_delete'), name='dispatch')
class OrganizationDeleteView(PermissionBaseView, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')
    permission_codename =  'core.Organization_delete'
    check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('سازمان با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# پروژه‌ها
# @method_decorator(has_permission('Project_view'), name='dispatch')
class ProjectListView(PermissionBaseView, ListView):
    model = Project
    template_name = 'core/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    extra_context = {'title': _('لیست پروژه‌ها')}
    permission_codename =  'core.Project_view'
    check_organization = True  # فعال کردن چک سازمان

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(code__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context


# @method_decorator(has_permission('Project_view'), name='dispatch')
class ProjectDetailView(PermissionBaseView, DetailView):
    model = Project
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    permission_codename = 'core.Project_view'
    check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tanbakhs = Tanbakh.objects.filter(project=self.object).select_related('current_stage')
        context['tanbakhs'] = tanbakhs
        context['title'] = _('جزئیات پروژه') + f" - {self.object.code}"
        return context


# @method_decorator(has_permission('Project_add'), name='dispatch')
class ProjectCreateView(PermissionBaseView, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_add'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('پروژه با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form errors:", form.errors)  # برای دیباگ
        messages.error(self.request, _('خطایی در ثبت پروژه رخ داد. لطفاً اطلاعات را بررسی کنید.'))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد پروژه جدید')
        return context


# @method_decorator(has_permission('Project_update'), name='dispatch')
class ProjectUpdateView(PermissionBaseView, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_update'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('پروژه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش پروژه') + f" - {self.object.code}"
        return context


# @method_decorator(has_permission('Project_delete'), name='dispatch')
class ProjectDeleteView(PermissionBaseView, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_delete'
    check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پروژه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --------------


#-- داشبورد گزارشات مالی
from django.views.generic import TemplateView
from django.db.models import Sum, F
from tanbakh.models import Tanbakh, Factor, FactorItem, StageApprover
from core.models import WorkflowStage, Organization
import json
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class FinancialDashboardView(PermissionBaseView, TemplateView):
    """داشبورد گزارشات تنخواه گردان"""
    template_name = 'tanbakh/Reports/calc_dashboard.html'
    login_url = '/accounts/login/'
    # permission_codename = 'core.Project_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # سازمان‌های مرتبط با کاربر
        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)

        # فیلتر تنخواه‌ها بر اساس دسترسی کاربر
        if is_hq_user:
            tanbakhs = Tanbakh.objects.all()  # کاربران HQ همه تنخواه‌ها را می‌بینند
            organizations = Organization.objects.exclude(org_type='HQ')  # مجتمع‌ها
        else:
            tanbakhs = Tanbakh.objects.filter(organization__in=user_orgs)  # فقط تنخواه‌های سازمان کاربر
            organizations = user_orgs

        # مجموع تنخواه‌ها
        context['total_tanbakh_amount'] = tanbakhs.aggregate(total=Sum('amount'))['total'] or 0

        # تنخواه‌های آرشیو شده
        context['archived_tanbakhs'] = tanbakhs.filter(is_archived=True).count()

        # وضعیت تنخواه‌ها در هر مرحله
        stages = WorkflowStage.objects.all()
        context['pending_by_stage'] = {
            stage.name: tanbakhs.filter(current_stage=stage, status='PENDING').count()
            for stage in stages
        }
        context['stages'] = stages

        # اطلاعات فاکتورها
        factors = Factor.objects.filter(tanbakh__in=tanbakhs)
        context['total_factor_amount'] = factors.aggregate(total=Sum('amount'))['total'] or 0
        context['approved_factors'] = factors.filter(status='APPROVED').count()
        context['rejected_factors'] = factors.filter(status='REJECTED').count()
        context['pending_factors'] = factors.filter(status='PENDING').count()

        # داده‌ها برای هر مجتمع
        org_data = []
        chart_labels = []
        chart_tanbakh_amounts = []
        chart_factor_amounts = []
        chart_approved_items = []

        for org in organizations:
            org_tanbakhs = tanbakhs.filter(organization=org)
            org_factors = Factor.objects.filter(tanbakh__in=org_tanbakhs)

            org_info = {
                'name': org.name,
                'total_tanbakh_amount': org_tanbakhs.aggregate(total=Sum('amount'))['total'] or 0,
                'total_factor_amount': org_factors.aggregate(total=Sum('amount'))['total'] or 0,
                'approved_factors': org_factors.filter(status='APPROVED').count(),
                'rejected_factors': org_factors.filter(status='REJECTED').count(),
                'pending_factors': org_factors.filter(status='PENDING').count(),
                'approved_items_amount': FactorItem.objects.filter(
                    factor__in=org_factors, status='APPROVED'
                ).aggregate(total=Sum(F('amount') * F('quantity')))['total'] or 0,
            }
            org_data.append(org_info)

            chart_labels.append(org.name)
            chart_tanbakh_amounts.append(org_info['total_tanbakh_amount'])
            chart_factor_amounts.append(org_info['total_factor_amount'])
            chart_approved_items.append(org_info['approved_items_amount'])

        context['org_data'] = org_data

        # داده‌ها برای چارت
        context['chart_data'] = json.dumps({
            'labels': chart_labels,
            'datasets': [
                {'label': str(_('مبلغ تنخواه‌ها')), 'data': chart_tanbakh_amounts, 'backgroundColor': 'rgba(54, 162, 235, 0.5)'},
                {'label': str(_('مبلغ فاکتورها')), 'data': chart_factor_amounts, 'backgroundColor': 'rgba(255, 99, 132, 0.5)'},
                {'label': str(_('جمع ردیف‌های تأییدشده')), 'data': chart_approved_items, 'backgroundColor': 'rgba(75, 192, 192, 0.5)'}
            ]
        })

        return context

class AllLinksView(PermissionBaseView, TemplateView):
    template_name = 'core/core_index.html'  # تمپلیت Index
    extra_context = {'title': _('همه لینک‌ها')}
    # permission_codename = 'core.Project_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تعریف دستی لینک‌ها - می‌تونید از URLResolver هم استفاده کنید
        context['links'] = [
            {'name': _('داشبورد'), 'url': 'dashboard', 'icon': 'fas fa-tachometer-alt'},
            {'name': _('لیست سازمان‌ها'), 'url': 'organization_list', 'icon': 'fas fa-building'},
            {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست پروژه‌ها'), 'url': 'project_list', 'icon': 'fas fa-project-diagram'},
            {'name': _('ایجاد پروژه'), 'url': 'project_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست تنخواه‌ها'), 'url': 'tanbakh_list', 'icon': 'fas fa-file-invoice'},
            {'name': _('ایجاد تنخواه'), 'url': 'tanbakh_create', 'icon': 'fas fa-plus'},
            {'name': _(' فهرست فاکتور'), 'url': 'factor_list', 'icon': 'fas fa-plus'},
            {'name': _('مدیریت کاربر و سیستم'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-user'},
        ]
        return context

#-- روند تنخواه گردانی داشبورد ---
class PostListView(PermissionBaseView, ListView):
    model = Post
    template_name = 'core/post/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    extra_context = {'title': _('لیست پست‌های سازمانی')}
    permission_codenames = ['core.Post_view']

    def get_queryset(self):
        qs = super().get_queryset()
        sort_order = self.request.GET.get('sort', 'asc')  # پیش‌فرض: از پایین به بالا
        if sort_order == 'desc':
            qs = qs.order_by('-level')  # از بالا به پایین
            logger.info("Sorting posts from high to low level")
        else:
            qs = qs.order_by('level')  # از پایین به بالا
            logger.info("Sorting posts from low to high level")
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_sort'] = self.request.GET.get('sort', 'asc')
        return context
# @method_decorator(has_permission('Post_view'), name='dispatch')
class PostDetailView(PermissionBaseView, DetailView):
    model = Post
    template_name = 'core/post/post_detail.html'
    context_object_name = 'post'
    extra_context = {'title': _('جزئیات پست سازمانی')}
    permission_codename = 'core.Post_view'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from tanbakh.models import StageApprover
        context['stages'] = StageApprover.objects.filter(post=self.object).select_related('stage')
        return context


# @method_decorator(has_permission('Post_add'), name='dispatch')
class PostCreateView(PermissionBaseView, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    # permission_required = 'core.Post_add'
    permission_codename = 'core.Post_add'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('پست سازمانی با موفقیت ایجاد شد.'))
        return super().form_valid(form)


# @method_decorator(has_permission('Post_update'), name='dispatch')
class PostUpdateView(PermissionBaseView, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    # permission_required = 'core.Post_update'
    permission_codename = 'core.Post_update'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('پست سازمانی با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


# @method_decorator(has_permission('Post_delete'), name='dispatch')
class PostDeleteView(PermissionBaseView, DeleteView):
    model = Post
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('post_list')
    # permission_required = 'core.Post_delete'
    permission_codename = 'core.Post_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پست سازمانی با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --- UserPost Views ---
# @method_decorator(has_permission('UserPost_view'), name='dispatch')
class UserPostListView(PermissionBaseView, ListView):
    model = UserPost
    template_name = 'core/post/userpost_list.html'
    context_object_name = 'userposts'
    paginate_by = 10
    extra_context = {'title': _('لیست اتصالات کاربر به پست')}

    permission_codename = 'core.UserPost_view'
    # check_organization = True  # فعال کردن چک سازمان

# @method_decorator(has_permission('UserPost_add'), name='dispatch')
class UserPostCreateView(PermissionBaseView, CreateView):
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    # permission_required = 'tanbakh.UserPost_add'
    permission_codename = 'core.UserPost_add'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت ایجاد شد.'))
        return super().form_valid(form)


# @method_decorator(has_permission('UserPost_update'), name='dispatch')
class UserPostUpdateView(PermissionBaseView, UpdateView):
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    # permission_required = 'tanbakh.UserPost_update'
    permission_codename = 'core.UserPost_update'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


# @method_decorator(has_permission('UserPost_delete'), name='dispatch')
class UserPostDeleteView(PermissionBaseView, DeleteView):
    model = UserPost
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('userpost_list')
    # permission_required = 'tanbakh.UserPost_delete'
    permission_codename = 'core.UserPost_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --- PostHistory Views ---
# @method_decorator(has_permission('view_posthistory'), name='dispatch')
class PostHistoryListView(PermissionBaseView, ListView):
    model = PostHistory
    template_name = 'core/post/posthistory_list.html'
    context_object_name = 'histories'
    paginate_by = 10
    extra_context = {'title': _('لیست تاریخچه پست‌ها')}
    permission_codename = 'core.view_posthistory'
    # check_organization = True  # فعال کردن چک سازمان


# @method_decorator(has_permission('add_posthistory'), name='dispatch')
class PostHistoryCreateView(PermissionBaseView, CreateView):
    model = PostHistory
    form_class = PostHistoryForm
    template_name = 'core/post/posthistory_form.html'
    success_url = reverse_lazy('posthistory_list')
    # permission_required = 'tanbakh.add_posthistory'
    permission_codename = 'core.add_posthistory'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        form.instance.changed_by = self.request.user
        messages.success(self.request, _('تاریخچه پست با موفقیت ثبت شد.'))
        return super().form_valid(form)


# @method_decorator(has_permission('delete_posthistory'), name='dispatch')
class PostHistoryDeleteView(PermissionBaseView, DeleteView):
    model = PostHistory
    template_name = 'core/post/posthistory_confirm_delete.html'
    success_url = reverse_lazy('posthistory_list')
    # permission_required = 'tanbakh.delete_posthistory'
    permission_codename = 'core.delete_posthistory'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تاریخچه پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# ---- WorkFlow


class WorkflowStageListView(PermissionBaseView, ListView):
    model = WorkflowStage
    template_name = "core/workflow_stage/workflow_stage_list.html"
    context_object_name = "stages"
    # permission_required = "core.WorkflowStage_view"
    permission_codename = 'core.WorkflowStage_view'
    # check_organization = True  # فعال کردن چک سازمان


class WorkflowStageCreateView(PermissionBaseView, CreateView):
    model = WorkflowStage
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    # permission_required = "core.WorkflowStage_add"
    permission_codename = 'core.WorkflowStage_add'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "افزودن مرحله جدید"
        return context


class WorkflowStageUpdateView(PermissionBaseView, UpdateView):
    model = WorkflowStage
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    # permission_required = "core.WorkflowStage_update"
    permission_codename = 'core.WorkflowStage_update'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "ویرایش مرحله"
        return context


class WorkflowStageDeleteView(PermissionBaseView, DeleteView):
    model = WorkflowStage
    template_name = "core/workflow_stage/workflow_stage_confirm_delete.html"
    success_url = reverse_lazy("workflow_stage_list")
    # permission_required = "core.WorkflowStage_delete"
    permission_codename = 'core.WorkflowStage_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stage"] = self.get_object()
        return context
