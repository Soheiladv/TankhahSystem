# --- ProjectBudgetAllocation CRUD ---
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

from budgets.ProjectBudgetAllocation.forms_ProjectBudgetAllocation import ProjectBudgetAllocationForm
from budgets.models import ProjectBudgetAllocation, BudgetPeriod
from core.PermissionBase import PermissionBaseView
from budgets.budget_calculations import (
    get_budget_details, get_organization_budget,
    get_project_remaining_budget, get_subproject_remaining_budget, get_subproject_total_budget, get_project_total_budget
)
import logging

from core.models import Organization, Project

logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _

class ProjectBudgetAllocationListView(PermissionBaseView, ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # kwargs['organization_id'] = self.kwargs['organization_id']
        # kwargs['initial']['created_by'] = self.request.user
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        from django.shortcuts import get_object_or_404
        from core.models import Organization
        organization = get_object_or_404(Organization, id=organization_id)
        queryset = ProjectBudgetAllocation.objects.filter(
            budget_allocation__organization=organization
        ).select_related('project', 'subproject', 'budget_allocation__budget_period')
        logger.info(f"Allocations for org {organization_id}: {list(queryset.values('id', 'allocated_amount'))}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        from core.models import Organization
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        context['organization'] = organization
        context['budget_details'] = get_budget_details(organization)
        logger.debug(f"ProjectBudgetAllocationListView context: {context}")
        return context

class ProjectBudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['budget_details'] = get_budget_details(self.object.project)
        logger.debug(f"ProjectBudgetAllocationDetailView context: {context}")
        return context

class ProjectBudgetAllocationCreateView(PermissionBaseView, CreateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        budget_periods = BudgetPeriod.objects.filter(organization=organization, is_active=True)

        if not budget_periods.exists():
            messages.warning(self.request, _("هیچ دوره بودجه فعالی برای این شعبه یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
                'budget_details': get_budget_details(organization)
            })
            return context

        from budgets import BudgetAllocation
        budget_allocations = BudgetAllocation.objects.filter(budget_period__in=budget_periods, is_active=True)
        if not budget_allocations.exists():
            messages.warning(self.request, _("هیچ تخصیص بودجه‌ای برای این دوره‌ها یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
                'budget_details': get_budget_details(organization)
            })
            return context

        total_org_budget = get_organization_budget(organization)
        budget_allocation = budget_allocations.first()
        budget_period = budget_allocation.budget_period
        projects = Project.objects.filter(organizations=organization, is_active=True)

        for project in projects:
            project.total_budget = get_project_total_budget(project)
            project.remaining_budget = get_project_remaining_budget(project)
            project.remaining_percent = (
                (project.remaining_budget / project.total_budget * 100)
                if project.total_budget > 0 else 0
            )
            project.total_percent = (
                (project.total_budget / total_org_budget * 100)
                if total_org_budget > 0 else 0
            )
            for subproject in project.subprojects.filter(is_active=True):
                subproject.total_budget = get_subproject_total_budget(subproject)
                subproject.remaining_budget = get_subproject_remaining_budget(subproject)
                subproject.remaining_percent = (
                    (subproject.remaining_budget / subproject.total_budget * 100)
                    if subproject.total_budget > 0 else 0
                )
                subproject.total_percent = (
                    (subproject.total_budget / project.total_budget * 100)
                    if project.total_budget > 0 else 0
                )

        context.update({
            'organization': organization,
            'budget_allocation': budget_allocation,
            'budget_period': budget_period,
            'total_org_budget': total_org_budget,
            'remaining_amount': budget_period.get_remaining_amount(),
            'remaining_percent': (
                (context['remaining_amount'] / budget_period.total_amount * 100)
                if budget_period.total_amount > 0 else 0
            ),
            'warning_threshold': budget_period.warning_threshold,
            'projects': projects,
            'budget_details': get_budget_details(organization)
        })
        logger.debug(f"ProjectBudgetAllocationCreateView context: {context}")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        kwargs['user'] = self.request.user
        logger.debug(f"Form kwargs: {kwargs}")
        return kwargs

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return self.render_to_response(self.get_context_data(form=form))

    @transaction.atomic
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        remaining = form.instance.budget_allocation.get_remaining_amount()
        if form.instance.allocated_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining}) است.')
            return self.form_invalid(form)
        try:
            response = super().form_valid(form)
            logger.info(f"New allocation saved: {self.object.pk} - {self.object.allocated_amount}")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ثبت شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on create: {str(e)}")
            form.add_error('allocated_amount', str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.kwargs['organization_id']})


    def dispatch(self, request, *args, **kwargs):
        try:
            Organization.objects.get(id=self.kwargs['organization_id'])
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(request, _("سازمان موردنظر یافت نشد"))
            from django.shortcuts import redirect
            return redirect('budgetperiod_list')
        return super().dispatch(request, *args, **kwargs)

class ProjectBudgetAllocationEditView(PermissionBaseView, UpdateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation_edit.html'
    context_object_name = 'allocation'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.object.budget_allocation.organization_id
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        old_amount = self.get_object().allocated_amount
        new_amount = form.instance.allocated_amount
        remaining = self.get_object().budget_allocation.get_remaining_amount() + old_amount
        if new_amount > remaining:
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining}) است.')
            return self.form_invalid(form)
        try:
            response = super().form_valid(form)
            logger.info(f"Allocation {self.object.pk} updated")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ویرایش شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on edit: {str(e)}")
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})

class ProjectBudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_delete.html'
    context_object_name = 'allocation'

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        logger.info(f"Allocation {self.object.pk} deleted")
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(self.request, _("تخصیص بودجه با موفقیت حذف شد"))
        from django.shortcuts import redirect
        return redirect(success_url)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})
