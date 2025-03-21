from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import OrganizationForm, ProjectForm
from .models import Organization, Project
from django.utils.translation import gettext_lazy as _


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

# سازمان‌ها
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


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'core/organization_detail.html'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات سازمان') + f" - {self.object.code}"
        return context


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


class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('سازمان با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)


# پروژه‌ها
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


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_detail.html'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tanbakhs'] = Tanbakh.objects.filter(project=self.object)
        context['title'] = _('جزئیات پروژه') + f" - {self.object.code}"
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')

    def form_valid(self, form):
        messages.success(self.request, _('پروژه با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد پروژه جدید')
        return context


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


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پروژه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

#--------------
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

class AllLinksView(LoginRequiredMixin, TemplateView):
    template_name = 'core/core_index.html'  # تمپلیت Index
    extra_context = {'title': _('همه لینک‌ها')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تعریف دستی لینک‌ها - می‌تونید از URLResolver هم استفاده کنید
        context['links'] = [
            {'name': _('داشبورد'), 'url': 'index', 'icon': 'fas fa-tachometer-alt'},
            {'name': _('لیست سازمان‌ها'), 'url': 'organization_list', 'icon': 'fas fa-building'},
            {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست پروژه‌ها'), 'url': 'project_list', 'icon': 'fas fa-project-diagram'},
            {'name': _('ایجاد پروژه'), 'url': 'project_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست تنخواه‌ها'), 'url': 'tanbakh_list', 'icon': 'fas fa-file-invoice'},
            {'name': _('ایجاد تنخواه'), 'url': 'tanbakh_create', 'icon': 'fas fa-plus'},
            {'name': _('ایجاد فاکتور'), 'url': 'factor_create', 'icon': 'fas fa-plus'},
            {'name': _('مدیریت کاربر و سیستم'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-user'},
        ]
        return context


from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Organization, Project
from tanbakh.models import Tanbakh
from django.utils.translation import gettext_lazy as _

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'
    extra_context = {'title': _('داشبورد')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['complex_count'] = Organization.objects.filter(org_type='COMPLEX').count()
        context['hq'] = Organization.objects.filter(org_type='HQ').first()
        context['project_count'] = Project.objects.count()
        context['tanbakh_count'] = Tanbakh.objects.count()
        context['recent_tanbakhs'] = Tanbakh.objects.order_by('-date')[:5]  # ۵ تنخواه آخر
        context['active_projects'] = Project.objects.filter(end_date__isnull=True).count()
        return context