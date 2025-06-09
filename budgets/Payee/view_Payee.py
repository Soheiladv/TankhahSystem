from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.utils.translation import gettext_lazy as _

from budgets.forms import PayeeForm
from budgets.models import Payee
from core.PermissionBase import PermissionBaseView
import logging
logger = logging.getLogger(__name__)
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

# --- Payee CRUD ---
class PayeeListView(PermissionBaseView, ListView):
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    context_object_name = 'payees'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(national_id__icontains=query) |
                Q(iban__icontains=query)
            )
        payee_type = self.request.GET.get('payee_type')
        if payee_type:
            queryset = queryset.filter(payee_type=payee_type)
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['payee_type'] = self.request.GET.get('payee_type', '')
        context['payee_types'] = Payee.PAYEE_TYPES
        logger.debug(f"PayeeListView context: {context}")
        return context
class PayeeDetailView(PermissionBaseView, DetailView):
    model = Payee
    template_name = 'budgets/payee/payee_detail.html'
    context_object_name = 'payee'
    permission_required = ['budgets.Payee_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات دریافت‌کننده')
        return context
class PayeeCreateView(PermissionBaseView, CreateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت ایجاد شد.')
            return response
class PayeeUpdateView(PermissionBaseView, UpdateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance.name} با موفقیت به‌روزرسانی شد.')
            return response
class PayeeDeleteView(PermissionBaseView, DeleteView):
    model = Payee
    template_name = 'budgets/payee/payee_confirm_delete.html'
    success_url = reverse_lazy('payee_list')

    def post(self, request, *args, **kwargs):
        payee = self.get_object()
        with transaction.atomic():
            payee.delete()
            messages.success(request, f'دریافت‌کننده {payee.name} {payee.family} با موفقیت حذف شد.')
        return redirect(self.success_url)