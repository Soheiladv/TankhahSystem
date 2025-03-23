import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum, F
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic import TemplateView

from accounts.has_role_permission import has_permission
from tanbakh.models import Tanbakh, Factor, FactorItem
from .forms import OrganizationForm, ProjectForm, PostForm, UserPostForm, PostHistoryForm, WorkflowStageForm
from .models import Organization, Project, Post, UserPost, PostHistory, WorkflowStage


# سازمان‌ها
@method_decorator(has_permission('Organization_view'), name='dispatch')
class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'core/organization_list.html'
    context_object_name = 'organizations'
    paginate_by = 10
    extra_context = {'title': _('لیست سازمان‌ها')}

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


@method_decorator(has_permission('Organization_view'), name='dispatch')
class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'core/organization_detail.html'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات سازمان') + f" - {self.object.code}"
        return context


@method_decorator(has_permission('Organization_add'), name='dispatch')
class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد سازمان جدید')
        return context


@method_decorator(has_permission('Organization_update'), name='dispatch')
class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش سازمان') + f" - {self.object.code}"
        return context


@method_decorator(has_permission('Organization_delete'), name='dispatch')
class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('سازمان با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# پروژه‌ها
@method_decorator(has_permission('Project_view'), name='dispatch')
class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'core/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    extra_context = {'title': _('لیست پروژه‌ها')}

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


@method_decorator(has_permission('Project_view'), name='dispatch')
class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tanbakhs = Tanbakh.objects.filter(project=self.object).select_related('current_stage')
        context['tanbakhs'] = tanbakhs
        context['title'] = _('جزئیات پروژه') + f" - {self.object.code}"
        return context


@method_decorator(has_permission('Project_add'), name='dispatch')
class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')

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


@method_decorator(has_permission('Project_update'), name='dispatch')
class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        messages.success(self.request, _('پروژه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش پروژه') + f" - {self.object.code}"
        return context


@method_decorator(has_permission('Project_delete'), name='dispatch')
class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پروژه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --------------
# UPlink SoftWare
class IndexView( TemplateView):
    # Fascades = True
    template_name = 'index.html'
    extra_context = {'title': _('داشبورد')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['complexes'] = Organization.objects.filter(org_type='COMPLEX')
        context['hq'] = Organization.objects.filter(org_type='HQ').first()
        context['projects'] = Project.objects.all()
        context['tanbakhs'] = Tanbakh.objects.filter(organization__org_type='COMPLEX')[:5]
        # اضافه کردن مراحل گردش کار
        context['workflow_stages'] = WorkflowStage.objects.all()
        context['tanbakh_by_stage'] = {
            stage: Tanbakh.objects.filter(current_stage=stage).count() for stage in context['workflow_stages']
        }
        return context

#-- داشبورد گزارشات مالی
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum, F
from tanbakh.models import Tanbakh, Factor, FactorItem
from core.models import WorkflowStage, Organization
import json
from django.utils.translation import gettext_lazy as _

class FinancialDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tanbakh/Reports/calc_dashboard.html'
    login_url = '/accounts/login/'

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

class AllLinksView(LoginRequiredMixin, TemplateView):
    template_name = 'core/core_index.html'  # تمپلیت Index
    extra_context = {'title': _('همه لینک‌ها')}

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
@method_decorator(has_permission('DashboardView_flows_view'), name='dispatch')
class DashboardView_flows(TemplateView):
    template_name = 'core/dashboard1.html'
    extra_context = {'title': _('داشبورد مدیریت')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user

        # گرفتن مراحل بدون کش
        workflow_stages = WorkflowStage.objects.all()
        context['workflow_stages'] = workflow_stages

        # محاسبه تعداد تنخواه‌های در انتظار با دیباگ
        tanbakh_pending_by_stage = {}
        for stage in workflow_stages:
            count = Tanbakh.objects.filter(current_stage=stage, status='PENDING').count()
            tanbakh_pending_by_stage[stage] = count
            print(f"Stage {stage.name}: {count} pending Tanbakhs")
        context['tanbakh_pending_by_stage'] = tanbakh_pending_by_stage
        return context


# ---dashboard Main
# @method_decorator(has_permission('Dashboard_view'), name='dispatch')
class DashboardView(TemplateView):
    template_name = 'core/dashboard.html'
    extra_context = {
        'title': _('داشبورد مدیریت'),
        # تعریف لینک‌ها به صورت دسته‌بندی‌شده
        'dashboard_links': {
                'روند تنخواه': [
                    {'name': _('روند تنخواه'), 'url': 'dashboard_flows', 'permission': 'Dashboard__view',
                     'icon': 'fas fa-link'},
                ],
                'سازمـان': [
                    {'name': _('فهرست سازمان‌ها'), 'url': 'organization_list', 'permission': 'organization_view',
                     'icon': 'fas fa-building'},
                    {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'permission': 'organization_add',
                     'icon': 'fas fa-plus'},
                ],

                'عنوان پروژه ': [
                    {'name': _('فهرست پروژه‌ها'), 'url': 'project_list', 'permission': 'project_view',
                     'icon': 'fas fa-project-diagram'},
                    {'name': _('ایجاد پروژه'), 'url': 'project_create', 'permission': 'project_add', 'icon': 'fas fa-plus'},
                ],
                'تنخواه': [
                    {'name': _('فهرست تنخواه'), 'url': 'tanbakh_list', 'permission': 'project_view',
                     'icon': 'fas fa-project-diagram'},
                    {'name': _('ایجاد تنخواه'), 'url': 'tanbakh_create', 'permission': 'project_add',
                     'icon': 'fas fa-plus'},
                ],

                ' فاکتورها': [
                    {'name': _('فهرست فاکتورها'), 'url': 'factor_list', 'permission': 'project_view',
                     'icon': 'fas fa-project-diagram'},
                    {'name': _('ایجاد فاکتور'), 'url': 'factor_create', 'permission': 'project_add', 'icon': 'fas fa-plus'},
                ],
                'پست و سلسله مراتب': [
                    {'name': _('فهرست پست‌ها'), 'url': 'post_list', 'permission': 'post_view', 'icon': 'fas fa-sitemap'},
                    {'name': _('ایجاد پست'), 'url': 'post_create', 'permission': 'post_add', 'icon': 'fas fa-plus'},
                ],
                'پست همکار در سازمان': [
                    {'name': _('فهرست اتصالات کاربر به پست'), 'url': 'userpost_list', 'permission': 'userpost_view',
                     'icon': 'fas fa-users'},
                    {'name': _('ایجاد اتصال'), 'url': 'userpost_create', 'permission': 'userpost_add',
                     'icon': 'fas fa-plus'},
                ],
                'تاریخچه پست ها': [
                    {'name': _('فهرست تاریخچه پست‌ها'), 'url': 'posthistory_list', 'permission': 'posthistory_view',
                     'icon': 'fas fa-history'},
                    {'name': _('ثبت تاریخچه'), 'url': 'posthistory_create', 'permission': 'posthistory_add',
                     'icon': 'fas fa-plus'},
                ],
                'گردش کار': [
                    {'name': _('فهرست گردش کار'), 'url': 'workflow_stage_list', 'permission': 'workflow_stage_create',
                     'icon': 'fas fa-history'},
                    {'name': _('ثبت گردش کار'), 'url': 'workflow_stage_create', 'permission': 'workflow_stage_create',
                     'icon': 'fas fa-plus'},
                ],
                'دیگر لینکها': [
                    {'name': _('همه لینک‌ها'), 'url': 'all_links', 'icon': 'fas fa-link'},
                    {'name': _('BI گزارشات'), 'url': 'financialDashboardView', 'icon': 'fas fa-link'},
                ],

        }
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # اضافه کردن اطلاعات کاربر برای نمایش در داشبورد (اختیاری)
        context['user'] = self.request.user
        return context


# --- Post Views ---
@method_decorator(has_permission('Post_view'), name='dispatch')
class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'core/post/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    extra_context = {'title': _('لیست پست‌های سازمانی')}


@method_decorator(has_permission('Post_view'), name='dispatch')
class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'core/post/post_detail.html'
    context_object_name = 'post'
    extra_context = {'title': _('جزئیات پست سازمانی')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from tanbakh.models import StageApprover
        context['stages'] = StageApprover.objects.filter(post=self.object).select_related('stage')
        return context


@method_decorator(has_permission('Post_add'), name='dispatch')
class PostCreateView(PermissionRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    permission_required = 'core.Post_add'

    def form_valid(self, form):
        messages.success(self.request, _('پست سازمانی با موفقیت ایجاد شد.'))
        return super().form_valid(form)


@method_decorator(has_permission('Post_update'), name='dispatch')
class PostUpdateView(PermissionRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    permission_required = 'core.Post_update'

    def form_valid(self, form):
        messages.success(self.request, _('پست سازمانی با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


@method_decorator(has_permission('Post_delete'), name='dispatch')
class PostDeleteView(PermissionRequiredMixin, DeleteView):
    model = Post
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('post_list')
    permission_required = 'core.Post_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پست سازمانی با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --- UserPost Views ---
@method_decorator(has_permission('UserPost_view'), name='dispatch')
class UserPostListView(LoginRequiredMixin, ListView):
    model = UserPost
    template_name = 'core/post/userpost_list.html'
    context_object_name = 'userposts'
    paginate_by = 10
    extra_context = {'title': _('لیست اتصالات کاربر به پست')}


@method_decorator(has_permission('UserPost_add'), name='dispatch')
class UserPostCreateView(PermissionRequiredMixin, CreateView):
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    permission_required = 'tanbakh.UserPost_add'

    def form_valid(self, form):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت ایجاد شد.'))
        return super().form_valid(form)


@method_decorator(has_permission('UserPost_update'), name='dispatch')
class UserPostUpdateView(PermissionRequiredMixin, UpdateView):
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    permission_required = 'tanbakh.UserPost_update'

    def form_valid(self, form):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)


@method_decorator(has_permission('UserPost_delete'), name='dispatch')
class UserPostDeleteView(PermissionRequiredMixin, DeleteView):
    model = UserPost
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('userpost_list')
    permission_required = 'tanbakh.UserPost_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# --- PostHistory Views ---
@method_decorator(has_permission('view_posthistory'), name='dispatch')
class PostHistoryListView(LoginRequiredMixin, ListView):
    model = PostHistory
    template_name = 'core/post/posthistory_list.html'
    context_object_name = 'histories'
    paginate_by = 10
    extra_context = {'title': _('لیست تاریخچه پست‌ها')}


@method_decorator(has_permission('add_posthistory'), name='dispatch')
class PostHistoryCreateView(PermissionRequiredMixin, CreateView):
    model = PostHistory
    form_class = PostHistoryForm
    template_name = 'core/post/posthistory_form.html'
    success_url = reverse_lazy('posthistory_list')
    permission_required = 'tanbakh.add_posthistory'

    def form_valid(self, form):
        form.instance.changed_by = self.request.user
        messages.success(self.request, _('تاریخچه پست با موفقیت ثبت شد.'))
        return super().form_valid(form)


@method_decorator(has_permission('delete_posthistory'), name='dispatch')
class PostHistoryDeleteView(PermissionRequiredMixin, DeleteView):
    model = PostHistory
    template_name = 'core/post/posthistory_confirm_delete.html'
    success_url = reverse_lazy('posthistory_list')
    permission_required = 'tanbakh.delete_posthistory'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تاریخچه پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# ---- WorkFlow


class WorkflowStageListView(PermissionRequiredMixin, ListView):
    model = WorkflowStage
    template_name = "core/workflow_stage/workflow_stage_list.html"
    context_object_name = "stages"
    permission_required = "core.WorkflowStage_view"


class WorkflowStageCreateView(PermissionRequiredMixin, CreateView):
    model = WorkflowStage
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_required = "core.WorkflowStage_add"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "افزودن مرحله جدید"
        return context


class WorkflowStageUpdateView(PermissionRequiredMixin, UpdateView):
    model = WorkflowStage
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_required = "core.WorkflowStage_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "ویرایش مرحله"
        return context


class WorkflowStageDeleteView(PermissionRequiredMixin, DeleteView):
    model = WorkflowStage
    template_name = "core/workflow_stage/workflow_stage_confirm_delete.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_required = "core.WorkflowStage_delete"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stage"] = self.get_object()
        return context
