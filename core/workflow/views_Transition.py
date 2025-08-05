from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.utils.translation import gettext_lazy as _

from core.models import Action
from core.workflow.forms_workflow import ActionForm, TransitionForm
from core.workflow.views_workflow import WorkflowAdminRequiredMixin
from core.models import Transition



class TransitionListView(WorkflowAdminRequiredMixin, ListView):
    model = Transition
    template_name = 'core/workflow/Transition/transition_list.html'
    context_object_name = 'transitions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Transition.objects.filter(is_active=True).select_related(
            'from_status', 'action', 'to_status'
        ).order_by('entity_type', 'from_status__name')

        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class TransitionCreateView(WorkflowAdminRequiredMixin, CreateView):
    model = Transition
    form_class = TransitionForm
    template_name = 'core/workflow/Transition/transition_form.html'
    success_url = reverse_lazy('transition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("ایجاد گذار جدید در گردش کار")
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _("گذار جدید با موفقیت ایجاد شد."))
        return super().form_valid(form)


class TransitionUpdateView(WorkflowAdminRequiredMixin, DetailView):
    model = Transition
    template_name = 'core/workflow/Transition/transition_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = TransitionForm(instance=self.object)
        context['title'] = _(f"ایجاد نسخه جدید از گذار: {self.object.name}")
        context['is_update_mode'] = True
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = TransitionForm(request.POST)
        if form.is_valid():
            new_instance = form.save(commit=False)
            new_instance.created_by = request.user
            new_instance.save()
            self.object.is_active = False
            self.object.save(update_fields=['is_active'])
            messages.success(request, _(f"گذار '{self.object.name}' بازنشسته و نسخه جدید ایجاد شد."))
            return redirect('transition_list')
        context = self.get_context_data();
        context['form'] = form
        return self.render_to_response(context)


class TransitionDeleteView(WorkflowAdminRequiredMixin, DeleteView):
    model = Transition
    template_name = 'core/workflow/Transition/confirm_retire.html'
    success_url = reverse_lazy('transition_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _(f"بازنشسته کردن گذار: {self.object.name}")
        context['object_type'] = _("گذار")
        return context

    def form_valid(self, form):
        self.object.is_active = False
        self.object.save()
        messages.success(self.request, _(f"گذار '{self.object.name}' با موفقیت بازنشسته شد."))
        return redirect(self.get_success_url())