from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.utils.translation import gettext_lazy as _

from core.models import Action
from core.workflow.forms_workflow import ActionForm
from core.workflow.views_workflow import WorkflowAdminRequiredMixin
class ActionListView(WorkflowAdminRequiredMixin, ListView):
    model = Action
    template_name = 'core/workflow/Action/action_list.html'
    context_object_name = 'actions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Action.objects.filter(is_active=True).order_by('name')
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(Q(name__icontains=search_query) | Q(code__icontains=search_query))
        return queryset

class ActionCreteView(WorkflowAdminRequiredMixin, CreateView):
    model = Action
    form_class = ActionForm
    template_name = 'core/workflow/Action/action_form.html'
    success_url = reverse_lazy('action_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد اقدام جدید")
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("اقدام جدید با موفقیت ایجاد شد."))
        return super().form_valid(form)
class ActionUpdateView(WorkflowAdminRequiredMixin, DetailView):
    model = Action
    template_name = 'core/workflow/Action/action_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ActionForm(instance=self.object)
        context['title'] = _(f"ایجاد نسخه جدید از اقدام: {self.object.name}")
        context['is_update_mode'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ActionForm(request.POST)
        if form.is_valid():
            new_instance = form.save(commit=False)
            new_instance.created_by = request.user
            new_instance.save()
            self.object.is_active = False
            self.object.save(update_fields=['is_active'])
            messages.success(request, _(f"اقدام '{self.object.name}' بازنشسته و نسخه جدید ایجاد شد."))
            return redirect('action_list')
        context = self.get_context_data(); context['form'] = form
        return self.render_to_response(context)
class ActionDeleteView(WorkflowAdminRequiredMixin, DeleteView):
    model = Action
    template_name = 'core/workflow/Action/confirm_retire.html' # استفاده از تمپلیت عمومی
    success_url = reverse_lazy('action_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _(f"بازنشسته کردن اقدام: {self.object.name}")
        context['object_type'] = _("اقدام")
        return context

    def form_valid(self, form):
        self.object.is_active = False
        self.object.save()
        messages.success(self.request, _(f"اقدام '{self.object.name}' با موفقیت بازنشسته شد."))
        return redirect(self.get_success_url())