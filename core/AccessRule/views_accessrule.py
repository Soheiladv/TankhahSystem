# core/views.py
from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from core.AccessRule.forms_accessrule import AccessRuleForm
from core.models import AccessRule

from core.views import PermissionBaseView
import logging

logger = logging.getLogger(__name__)
def userGiud_AccessRule(request):
    return render(request, template_name='core/accessrule/help_userAccessRule.html')


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

        if query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(organization__name__icontains=query) |
                Q(branch__icontains=query) |
                Q(entity_type__icontains=query)
            )

        if is_active:
            queryset = queryset.filter(is_active=(is_active == 'true'))

        logger.info(f"AccessRule queryset count: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['is_active'] = self.request.GET.get('is_active', '')
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