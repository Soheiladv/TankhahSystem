from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from core.PermissionBase import PermissionBaseView
from core.models import Permission
from core.workflow.forms_workflow import PermissionForm
from core.workflow.views_workflow import WorkflowAdminRequiredMixin


class PermissionListView(WorkflowAdminRequiredMixin, ListView):
    model = Permission
    template_name = 'core/workflow/Permission/permission_list.html'
    context_object_name = 'permissions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Permission.objects.all().select_related(
            'organization', 'on_status'
        ).prefetch_related(
            'allowed_posts', 'allowed_actions'
        ).order_by('organization__name', 'entity_type')

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(organization__name__icontains=search_query) |
                Q(on_status__name__icontains=search_query) |
                Q(entity_type__icontains=search_query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class PermissionCreateView___(WorkflowAdminRequiredMixin, CreateView):
    model = Permission
    form_class = PermissionForm
    template_name = 'core/workflow/Permission/permission_form.html'
    success_url = reverse_lazy('permission_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("تعریف مجوز جدید")
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("مجوز جدید با موفقیت ایجاد شد."))
        return super().form_valid(form)


class PermissionCreateView(PermissionBaseView, CreateView):
    model = Permission
    form_class = PermissionForm
    template_name = 'core/workflow/Permission/permission_form.html'
    permission_required = 'workflow.Permission_add'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'created_by': self.request.user
        }
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # تنظیم entity_type از transition انتخاب شده
        if form.cleaned_data.get('transition'):
            form.instance.entity_type = form.cleaned_data['transition'].entity_type

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('workflow:permission_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('ایجاد مجوز جدید')
        return context

class PermissionUpdateView(WorkflowAdminRequiredMixin, UpdateView):
    model = Permission
    form_class = PermissionForm
    template_name = 'core/workflow/Permission/permission_form.html'
    success_url = reverse_lazy('permission_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ویرایش مجوز")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("مجوز با موفقیت به‌روزرسانی شد."))
        return super().form_valid(form)


class PermissionDeleteView(WorkflowAdminRequiredMixin, DeleteView):
    model = Permission
    template_name = 'core/workflow/Permission/permission_confirm_delete.html'
    success_url = reverse_lazy('permission_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("حذف مجوز")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("مجوز با موفقیت حذف شد."))
        return super().delete(request, *args, **kwargs)