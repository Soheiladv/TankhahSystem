from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from accounts.has_role_permission import has_permission
from .forms import OrganizationForm, ProjectForm, PostForm, UserPostForm, PostHistoryForm
from django.views.generic import TemplateView
from tanbakh.models import Tanbakh
from django.utils.translation import gettext_lazy as _
from .models import Organization, Project, Post, UserPost, PostHistory


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
        context['tanbakhs'] = Tanbakh.objects.filter(project=self.object)
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

#--------------
#UPlink SoftWare
class IndexView(LoginRequiredMixin, TemplateView):
    Fascades = True
    template_name = 'index.html'
    extra_context = {'title': _('داشبورد')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['complexes'] = Organization.objects.filter(org_type='COMPLEX')
        context['hq'] = Organization.objects.filter(org_type='HQ').first()
        context['projects'] = Project.objects.all()
        context['tanbakhs'] = Tanbakh.objects.filter(organization__org_type='COMPLEX')[:5]  # ۵ تنخواه آخر
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

@method_decorator(has_permission('Dashboard_view'), name='dispatch')
class DashboardView2(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    extra_context = {'title': _('داشبورد')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # اطلاعات پایه برای همه کاربران
        context['complex_count'] = Organization.objects.filter(org_type='COMPLEX').count()
        context['project_count'] = Project.objects.count()
        context['tanbakh_count'] = Tanbakh.objects.count()
        context['active_projects'] = Project.objects.filter(end_date__isnull=True).count()

        # اطلاعات اضافی بر اساس سطح دسترسی
        if user.has_perm('Organization_view'):
            context['complexes'] = Organization.objects.filter(org_type='COMPLEX')
        if user.has_perm('Project_view'):
            context['projects'] = Project.objects.all()
        if user.has_perm('Tanbakh_view'):
            context['recent_tanbakhs'] = Tanbakh.objects.order_by('-date')[:5]

        # لینک‌ها برای کاربران با دسترسی خاص
        context['links'] = self.get_links(user)
        return context

    def get_links(self, user):
        links = []
        if user.has_perm('Dashboard_view'):
            links.append({'name': _('داشبورد'), 'url': 'dashboard', 'icon': 'fas fa-tachometer-alt'})
        if user.has_perm('Organization_view'):
            links.append({'name': _('لیست سازمان‌ها'), 'url': 'organization_list', 'icon': 'fas fa-building'})
        if user.has_perm('Organization_add'):
            links.append({'name': _('ایجاد سازمان'), 'url': 'organization_create', 'icon': 'fas fa-plus'})
        if user.has_perm('Project_view'):
            links.append({'name': _('لیست پروژه‌ها'), 'url': 'project_list', 'icon': 'fas fa-project-diagram'})
        if user.has_perm('Project_add'):
            links.append({'name': _('ایجاد پروژه'), 'url': 'project_create', 'icon': 'fas fa-plus'})
        if user.has_perm('Tanbakh_view'):
            links.append({'name': _('لیست تنخواه‌ها'), 'url': 'tanbakh_list', 'icon': 'fas fa-file-invoice'})
        if user.has_perm('Tanbakh_add'):
            links.append({'name': _('ایجاد تنخواه'), 'url': 'tanbakh_create', 'icon': 'fas fa-plus'})
        return links
# ---
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    extra_context = {
        'title': _('داشبورد مدیریت'),
        # تعریف لینک‌ها به صورت دسته‌بندی‌شده
        'dashboard_links': {
            'سازمـان': [
                {'name': _('لیست سازمان‌ها'), 'url': 'organization_list', 'icon': 'fas fa-building'},
                {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'icon': 'fas fa-plus'},
            ],
            'عنوان تنخواه (در قالب پروژه)': [
                {'name': _('لیست پروژه‌ها'), 'url': 'project_list', 'icon': 'fas fa-project-diagram'},
                {'name': _('ایجاد پروژه'), 'url': 'project_create', 'icon': 'fas fa-plus'},
            ],
            'پست و سلسله مراتب': [
                {'name': _('لیست پست‌ها'), 'url': 'post_list', 'icon': 'fas fa-sitemap'},
                {'name': _('ایجاد پست'), 'url': 'post_create', 'icon': 'fas fa-plus'},
            ],
            'پست همکار در سازمان': [
                {'name': _('لیست اتصالات کاربر به پست'), 'url': 'userpost_list', 'icon': 'fas fa-users'},
                {'name': _('ایجاد اتصال'), 'url': 'userpost_create', 'icon': 'fas fa-plus'},
            ],
            'تاریخچه پست ها': [
                {'name': _('لیست تاریخچه پست‌ها'), 'url': 'posthistory_list', 'icon': 'fas fa-history'},
                {'name': _('ثبت تاریخچه'), 'url': 'posthistory_create', 'icon': 'fas fa-plus'},
            ],
            'دیگر لینکها': [
                {'name': _('همه لینک‌ها'), 'url': 'all_links', 'icon': 'fas fa-link'},
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

