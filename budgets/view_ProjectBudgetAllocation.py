# budgets/views.py
import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView

from budgets.forms import ProjectBudgetAllocationForm
from budgets.models import BudgetAllocation, ProjectBudgetAllocation, BudgetPeriod
from core.models import Organization, Project

logger = logging.getLogger(__name__)
#---
# budgets/views.py
class ProjectBudgetAllocationCreateView(LoginRequiredMixin, CreateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        try:
            response = super().form_valid(form)
            logger.info(f"New allocation saved: {self.object.pk} - {self.object.allocated_amount}")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ثبت شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on create: {str(e)}")
            form.add_error('allocated_amount', str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        # برای اینکه کانتکست کامل رو تو حالت خطا هم داشته باشیم
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation',
                            kwargs={'organization_id': self.kwargs['organization_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # چک کردن سازمان
        try:
            organization = Organization.objects.get(id=self.kwargs['organization_id'])
            logger.info(f"Organization found: {organization.id} - {organization.name}")
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(self.request, _("سازمان موردنظر یافت نشد"))
            return redirect(
                'budgetperiod_list')  # اینجا نمی‌تونم redirect برگردونم، پس بعداً تو dispatch مدیریت می‌کنم

        # چک کردن BudgetPeriod
        budget_periods = BudgetPeriod.objects.filter(organization=organization)
        if not budget_periods.exists():
            logger.warning(f"No budget periods found for org {organization.id}")
            messages.warning(self.request, _("هیچ دوره بودجه فعالی برای این شعبه یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
            })
            return context

        # بودجه‌های تخصیص‌یافته
        budget_allocations = BudgetAllocation.objects.filter(budget_period__in=budget_periods)
        if not budget_allocations.exists():
            logger.warning(f"No budget allocations found for org {organization.id}")
            messages.warning(self.request, _("هیچ تخصیص بودجه‌ای برای این دوره‌ها یافت نشد"))
            context.update({
                'organization': organization,
                'form': None,
                'projects': [],
            })
            return context

        # محاسبات بودجه
        total_org_budget = budget_allocations.aggregate(total=Sum('allocated_amount'))['total'] or 0
        budget_allocation = budget_allocations.first()
        budget_period = budget_allocation.budget_period
        remaining_amount = budget_period.get_remaining_amount()
        remaining_percent = (
                    remaining_amount / budget_period.total_amount * 100) if budget_period.total_amount > 0 else 0
        warning_threshold = budget_period.warning_threshold

        # پروژه‌ها
        projects = Project.objects.filter(organizations=organization, is_active=True)
        logger.info(f"Projects found: {list(projects.values('id', 'name'))}")

        # محاسبات پروژه‌ها و زیرپروژه‌ها
        for project in projects:
            total_budget = \
            ProjectBudgetAllocation.objects.filter(project=project).aggregate(total=Sum('allocated_amount'))[
                'total'] or 0
            remaining_budget = project.get_remaining_budget()
            project.remaining_percent = (remaining_budget / total_budget * 100) if total_budget > 0 else 0
            project.total_percent = (total_budget / total_org_budget * 100) if total_org_budget > 0 else 0
            for subproject in project.subprojects.filter(is_active=True):
                subproject_total = \
                ProjectBudgetAllocation.objects.filter(subproject=subproject).aggregate(total=Sum('allocated_amount'))[
                    'total'] or 0
                subproject_remaining = subproject.get_remaining_budget()
                subproject.remaining_percent = (
                            subproject_remaining / subproject_total * 100) if subproject_total > 0 else 0
                subproject.total_percent = (subproject_total / total_budget * 100) if total_budget > 0 else 0

        # پر کردن کانتکست
        context.update({
            'organization': organization,
            'budget_allocation': budget_allocation,
            'budget_period': budget_period,
            'total_org_budget': total_org_budget,
            'remaining_amount': remaining_amount,
            'remaining_percent': remaining_percent,
            'warning_threshold': warning_threshold,
            'projects': projects,
        })

        logger.debug(f"Context prepared: {context}")
        return context

    def dispatch(self, request, *args, **kwargs):
        # مدیریت ریدایرکت سازمان پیدا نشده
        try:
            Organization.objects.get(id=self.kwargs['organization_id'])
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(request, _("سازمان موردنظر یافت نشد"))
            return redirect('budgetperiod_list')
        return super().dispatch(request, *args, **kwargs)
#---

# لیست تخصیص‌ها
class ProjectBudgetAllocationListView(LoginRequiredMixin, ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        organization = get_object_or_404(Organization, id=organization_id)
        queryset = ProjectBudgetAllocation.objects.filter(
            budget_allocation__organization=organization
        ).select_related('project', 'subproject', 'budget_allocation__budget_period')
        logger.info(f"Allocations for org {organization_id}: {list(queryset.values('id', 'allocated_amount'))}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        return context

# جزئیات تخصیص
class ProjectBudgetAllocationDetailView(LoginRequiredMixin, DetailView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        logger.info(f"Detail view for allocation {obj.pk}")
        return obj

# ویرایش تخصیص
class ProjectBudgetAllocationEditView(LoginRequiredMixin, UpdateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation_edit.html'
    context_object_name = 'allocation'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.object.budget_allocation.organization_id
        return kwargs

    def form_valid(self, form):
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

# حذف تخصیص
class ProjectBudgetAllocationDeleteView(LoginRequiredMixin, DeleteView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_delete.html'
    context_object_name = 'allocation'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        logger.info(f"Allocation {self.object.pk} deleted")
        success_url = self.get_success_url()
        self.object.delete()
        messages.success(self.request, _("تخصیص بودجه با موفقیت حذف شد"))
        return redirect(success_url)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})

# ایجاد تخصیص جدید
class ProjectBudgetAllocationCreateView1(LoginRequiredMixin, CreateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        try:
            response = super().form_valid(form)
            logger.info(f"New allocation saved: {self.object.pk} - {self.object.allocated_amount}")
            messages.success(self.request, _("تخصیص بودجه با موفقیت ثبت شد"))
            return response
        except ValidationError as e:
            logger.error(f"Validation error on create: {str(e)}")
            form.add_error(None, str(e))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.kwargs['organization_id']})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        budget_allocations = BudgetAllocation.objects.filter(organization=organization)

        if not budget_allocations.exists():
            logger.warning(f"No budget allocations for org {organization.id}")
            messages.warning(self.request, _("هیچ تخصیص بودجه‌ای برای این شعبه یافت نشد"))

        total_org_budget = budget_allocations.aggregate(total=Sum('allocated_amount'))['total'] or 0
        budget_allocation = budget_allocations.first()
        budget_period = budget_allocation.budget_period if budget_allocation else None

        context.update({
            'organization': organization,
            'budget_allocation': budget_allocation,
            'budget_period': budget_period,
            'total_org_budget': total_org_budget,
            'remaining_amount': budget_period.get_remaining_amount() if budget_period else 0,
            'remaining_percent': (context[
                                      'remaining_amount'] / budget_period.total_amount * 100) if budget_period and budget_period.total_amount > 0 else 0,
            'warning_threshold': budget_period.warning_threshold if budget_period else 50,
            'projects': Project.objects.filter(organizations=organization, is_active=True),
        })

        # محاسبات پروژه‌ها و زیرپروژه‌ها
        for project in context['projects']:
            total_budget = \
            ProjectBudgetAllocation.objects.filter(project=project).aggregate(total=Sum('allocated_amount'))[
                'total'] or 0
            remaining_budget = project.get_remaining_budget()
            project.remaining_percent = (remaining_budget / total_budget * 100) if total_budget > 0 else 0
            project.total_percent = (total_budget / total_org_budget * 100) if total_org_budget > 0 else 0
            for subproject in project.subprojects.filter(is_active=True):
                subproject_total = \
                    ProjectBudgetAllocation.objects.filter(subproject=subproject).aggregate(
                        total=Sum('allocated_amount'))[
                        'total'] or 0
                subproject_remaining = subproject.get_remaining_budget()
                subproject.remaining_percent = (
                        subproject_remaining / subproject_total * 100) if subproject_total > 0 else 0
                subproject.total_percent = (subproject_total / total_budget * 100) if total_budget > 0 else 0

        logger.debug(f"Context prepared: {context}")
        return context