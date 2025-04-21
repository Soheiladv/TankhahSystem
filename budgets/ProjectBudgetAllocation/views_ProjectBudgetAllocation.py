import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404
from django.utils.translation import gettext_lazy as _
# --- ProjectBudgetAllocation CRUD ---
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView

from budgets.ProjectBudgetAllocation.forms_ProjectBudgetAllocation import ProjectBudgetAllocationForm
from budgets.models import ProjectBudgetAllocation, BudgetPeriod, BudgetTransaction, BudgetAllocation
from core.PermissionBase import PermissionBaseView
from budgets.budget_calculations import (
    get_budget_details, get_organization_budget,
    get_project_remaining_budget, get_subproject_remaining_budget, get_subproject_total_budget,
    get_project_total_budget, get_project_used_budget
)
import logging

from core.models import Organization, Project, SubProject

logger = logging.getLogger(__name__)

class ProjectBudgetAllocationListView(ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list.html'
    context_object_name = 'allocations'
    paginate_by = 10

    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        organization = get_object_or_404(Organization, id=organization_id)
        project_id = self.request.GET.get('project_id')
        queryset = ProjectBudgetAllocation.objects.filter(
            budget_allocation__organization=organization,
            budget_allocation__is_active=True
        ).select_related(
            'project', 'subproject', 'budget_allocation__budget_period', 'budget_allocation__organization'
        ).order_by('-allocation_date')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        logger.info(f"Allocations for org {organization_id}: {queryset.count()} records")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])

        # دریافت تخصیص‌های بودجه سازمان
        budget_allocations = BudgetAllocation.objects.filter(
            organization=organization, is_active=True
        ).select_related('budget_period')

        # محاسبه بودجه کل و باقی‌مانده سازمان
        total_org_budget = budget_allocations.aggregate(
            total=Sum('allocated_amount')
        )['total'] or Decimal('0')

        consumed = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining_org_budget = total_org_budget - consumed + returned

        # داده‌های پروژه‌ها
        project_data = []
        projects = Project.objects.filter(
            organizations=organization, is_active=True
        ).prefetch_related('subprojects')

        for project in projects:
            project_allocations = ProjectBudgetAllocation.objects.filter(
                project=project, subproject__isnull=True
            )
            total_budget = project_allocations.aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')

            # استفاده از related_name صحیح: project_allocations
            project_budget_allocations = BudgetAllocation.objects.filter(
                project_allocations__project=project
            )
            consumed = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            remaining_budget = total_budget - consumed + returned
            remaining_percentage = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )
            allocated_percentage = (
                (total_budget / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')
            )

            project_data.append({
                'project': project,
                'total_budget': total_budget,
                'remaining_budget': remaining_budget,
                'remaining_percentage': remaining_percentage,
                'allocated_percentage': allocated_percentage
            })

        # بررسی شرایط خاص
        if not budget_allocations.exists():
            messages.warning(self.request, _("هیچ تخصیص بودجه فعالی برای این سازمان یافت نشد"))

        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'remaining_org_budget': remaining_org_budget,
            'project_data': project_data,
        })
        logger.info(f"Context prepared for organization {organization.id}: {context}")
        return context


class ProjectBudgetAllocationDetailView(PermissionBaseView, DetailView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_detail.html'
    context_object_name = 'allocation'
    permission_codename = 'budgets.ProjectBudgetAllocation_view'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True

    def get_object(self, queryset=None):
        try:
            obj = super().get_object(queryset)
            if not obj.is_active:
                logger.error(f"Allocation {obj.pk} is inactive")
                raise Http404(_('تخصیص بودجه غیرفعال است.'))
            # بررسی دسترسی سازمانی
            try:
                user_organizations = self.request.user.get_authorized_organizations()
            except AttributeError:
                user_organizations = self.request.user.organizations.all()
            if not user_organizations.filter(pk=obj.budget_allocation.organization.pk).exists():
                logger.warning(
                    f"User {self.request.user.username} attempted to access allocation {obj.pk} "
                    f"without organization permission"
                )
                raise PermissionDenied(self.permission_denied_message)
            return obj
        except ProjectBudgetAllocation.DoesNotExist:
            logger.error(f"Allocation {self.kwargs['pk']} does not exist")
            messages.error(self.request, _('تخصیص بودجه مورد نظر یافت نشد.'))
            return None

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj:
            return redirect('budgetallocation_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation = self.get_object()
        if not allocation:
            return context

        organization = allocation.budget_allocation.organization
        budget_allocation = allocation.budget_allocation
        logger.debug(f"Preparing context for allocation {allocation.id}, organization {organization.name}")

        # بودجه کل سازمان
        total_org_budget = budget_allocation.allocated_amount
        logger.debug(f"Total organization budget: {total_org_budget}")

        # پیدا کردن زیرپروژه‌های مرتبط
        subprojects = SubProject.objects.filter(allocations=allocation)

        # محاسبه تراکنش‌ها
        consumed = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        returned = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        consumed_amount = consumed - returned
        logger.debug(f"Consumed: {consumed}, Returned: {returned}, Net consumed: {consumed_amount}")

        # بودجه باقی‌مانده
        remaining_org_budget = total_org_budget - BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0') + BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        logger.debug(f"Remaining organization budget: {remaining_org_budget}")

        # تراکنش‌های اخیر
        recent_transactions = BudgetTransaction.objects.filter(
            allocation=budget_allocation,
            allocation__project=allocation.project
        ).order_by('-timestamp')[:10]

        context.update({
            'organization': organization,
            'total_org_budget': total_org_budget,
            'consumed_amount': consumed_amount,
            'remaining_org_budget': remaining_org_budget,
            'subprojects': subprojects,
            'recent_transactions': recent_transactions,
            'project': allocation.project,
        })
        # اضافه کردن اطلاعات بودجه
        project = allocation.project
        context.update({
            'total_budget': get_project_total_budget(project),
            'used_budget': get_project_used_budget(project),
            'remaining_budget': get_project_remaining_budget(project),
            'budget_details': get_budget_details(entity=project),
        })

        return context

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error accessing allocation {self.kwargs.get('pk')}: {str(e)}")
            messages.error(request, _("خطایی در دسترسی به جزئیات تخصیص بودجه رخ داد."))
            return self.redirect_to_organizations()

    def redirect_to_organizations(self):
        return redirect('organization_list')


class ProjectBudgetAllocationCreateView(PermissionBaseView,CreateView):
    model = ProjectBudgetAllocation
    form_class = ProjectBudgetAllocationForm
    template_name = 'budgets/budget/project_budget_allocation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_object_or_404(Organization, id=self.kwargs['organization_id'])
        context['organization'] = organization

        # تخصیص‌های بودجه فعال
        budget_allocations = BudgetAllocation.objects.filter(
            organization=organization,
            is_active=True,
            budget_period__is_active=True
        ).select_related('budget_period', 'budget_item').order_by('-allocation_date')

        if not budget_allocations.exists():
            logger.warning(f"No active BudgetAllocation found for organization {organization.id}")
            messages.warning(self.request, _("هیچ تخصیص بودجه فعالی برای این سازمان یافت نشد"))
            context.update({
                'form': None,
                'projects': [],
                'budget_allocation': None,
                'budget_period': None,
                'total_org_budget': Decimal('0'),
                'remaining_amount': Decimal('0'),
                'remaining_percent': Decimal('0'),
                'warning_threshold': 50,
                'project_data': [],
                'budget_allocations_json': '[]',
                'subprojects_json': '[]',
            })
            return context

        # داده‌های JSON برای جاوااسکریپت
        from django_jalali.templatetags.jformat import jformat
        allocations_list_for_json = [
            {
                'id': alloc.id,
                'name': f"{alloc.budget_item.name} - {alloc.budget_period.name} ({alloc.allocation_date })",
                'allocated_amount': float(alloc.allocated_amount),
                'remaining_amount': float(alloc.get_remaining_amount()),
            } for alloc in budget_allocations
        ]
        context['budget_allocations_json'] = json.dumps(allocations_list_for_json, cls=DjangoJSONEncoder)

        subprojects_list = list(SubProject.objects.filter(
            project__organizations=organization,
            is_active=True
        ).values('id', 'name', 'project_id'))
        context['subprojects_json'] = json.dumps(subprojects_list, cls=DjangoJSONEncoder)

        # تخصیص اولیه
        form = context.get('form')
        initial_allocation_id = None
        if form and form.initial.get('budget_allocation'):
            initial_allocation_id = form.initial['budget_allocation']
        elif form and form.is_bound and form.data.get('budget_allocation'):
            initial_allocation_id = form.data['budget_allocation']

        budget_allocation = budget_allocations.filter(id=initial_allocation_id).first() or budget_allocations.first()
        context['budget_allocation'] = budget_allocation

        # محاسبه بودجه کل و باقی‌مانده شعبه
        total_org_budget = budget_allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
        consumed = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='CONSUMPTION'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        returned = BudgetTransaction.objects.filter(
            allocation__in=budget_allocations,
            transaction_type='RETURN'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining_amount = total_org_budget - consumed + returned
        remaining_percent = (remaining_amount / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')

        # محاسبه برای تخصیص انتخاب‌شده
        allocation_total = budget_allocation.allocated_amount if budget_allocation else Decimal('0')
        allocation_remaining = budget_allocation.get_remaining_amount() if budget_allocation else Decimal('0')
        allocation_remaining_percent = (
            (allocation_remaining / allocation_total * 100) if allocation_total > 0 else Decimal('0')
        )

        # پروژه‌ها
        projects = Project.objects.filter(
            organizations=organization,
            is_active=True
        ).prefetch_related('subprojects', 'budget_allocations').order_by('name')

        project_data = []
        for project in projects:
            total_budget = ProjectBudgetAllocation.objects.filter(
                project=project,
                subproject__isnull=True
            ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            project_budget_allocations = BudgetAllocation.objects.filter(
                project_allocations__project=project
            )
            consumed = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='CONSUMPTION'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            returned = BudgetTransaction.objects.filter(
                allocation__in=project_budget_allocations,
                transaction_type='RETURN'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            remaining_budget = total_budget - consumed + returned
            remaining_percentage = (
                (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
            )

            project.total_budget = total_budget
            project.remaining_budget = remaining_budget
            project.total_percent = (
                (total_budget / total_org_budget * 100) if total_org_budget > 0 else Decimal('0')
            )
            project.remaining_percent = remaining_percentage

            for subproject in project.subprojects.filter(is_active=True):
                subproject_budget = ProjectBudgetAllocation.objects.filter(
                    subproject=subproject
                ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                subproject_budget_allocations = BudgetAllocation.objects.filter(
                    project_allocations__subproject=subproject
                )
                sub_consumed = BudgetTransaction.objects.filter(
                    allocation__in=subproject_budget_allocations,
                    transaction_type='CONSUMPTION'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                sub_returned = BudgetTransaction.objects.filter(
                    allocation__in=subproject_budget_allocations,
                    transaction_type='RETURN'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                subproject.total_budget = subproject_budget
                subproject.remaining_budget = subproject_budget - sub_consumed + sub_returned
                subproject.remaining_percent = (
                    (subproject.remaining_budget / subproject_budget * 100) if subproject_budget > 0 else Decimal('0')
                )
                subproject.total_percent = (
                    (subproject_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
                )

            project_data.append({
                'project': project,
                'total_budget': total_budget,
                'remaining_budget': remaining_budget,
                'remaining_percentage': remaining_percentage
            })

        context.update({
            'budget_period': budget_allocation.budget_period if budget_allocation else None,
            'total_org_budget': total_org_budget,
            'remaining_amount': remaining_amount,
            'remaining_percent': remaining_percent,
            'allocation_total': allocation_total,
            'allocation_remaining': allocation_remaining,
            'allocation_remaining_percent': allocation_remaining_percent,
            'warning_threshold': budget_allocation.warning_threshold if budget_allocation else 50,
            'projects': projects,
            'project_data': project_data,
        })
        logger.info(f"Context prepared for organization {organization.id}")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['organization_id'] = self.kwargs['organization_id']
        kwargs['user'] = self.request.user
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
            messages.error(self.request, f'مبلغ تخصیص بیشتر از باقی‌مانده بودجه شعبه ({remaining:,} ریال) است.')
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
        return reverse_lazy('project_budget_allocation_list', kwargs={'organization_id': self.kwargs['organization_id']})

    def dispatch(self, request, *args, **kwargs):
        try:
            Organization.objects.get(id=self.kwargs['organization_id'])
        except Organization.DoesNotExist:
            logger.error(f"Organization with id={self.kwargs['organization_id']} not found")
            messages.error(request, _("سازمان موردنظر یافت نشد"))
            return redirect('budgetperiod_list')
        return super().dispatch(request, *args, **kwargs)

"""BudgetAllocationUpdateView داخل فایل دیگه ای """
class ProjectBudgetAllocationDeleteView(PermissionBaseView, DeleteView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_delete.html'
    context_object_name = 'allocation'

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        budget_allocation = self.object.budget_allocation
        logger.info(f"Allocation {self.object.pk} deleted")
        success_url = self.get_success_url()
        self.object.delete()
        # به‌روزرسانی remaining_amount
        budget_allocation.remaining_amount = budget_allocation.get_remaining_amount()
        budget_allocation.save(update_fields=['remaining_amount'])
        messages.success(self.request, _("تخصیص بودجه با موفقیت حذف شد"))
        from django.shortcuts import redirect
        return redirect(success_url)

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_list',
                            kwargs={'organization_id': self.object.budget_allocation.organization_id})

# Reports
class BudgetRealtimeReportView(PermissionBaseView, TemplateView):
    template_name = 'reports/realtime_report.html'
    permission_required = 'budgets.view_budgetallocation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.request.GET.get('organization_id')
        project_id = self.request.GET.get('project_id')

        organizations = Organization.objects.filter(is_active=True)
        data = []

        for org in organizations:
            if organization_id and org.id != int(organization_id):
                continue
            org_budget = get_organization_budget(org) or Decimal('0')
            org_remaining = sum(
                alloc.get_remaining_amount() for alloc in BudgetAllocation.objects.filter(
                    organization=org, is_active=True
                )
            ) or Decimal('0')
            projects = Project.objects.filter(organizations=org, is_active=True)
            project_data = []

            for project in projects:
                if project_id and project.id != int(project_id):
                    continue
                total_budget = project.get_total_budget() or Decimal('0')
                remaining_budget = project.get_remaining_budget() or Decimal('0')
                transactions = BudgetTransaction.objects.filter(
                    allocation__project_allocations__project=project
                ).order_by('-timestamp')[:10]  # محدود به 10 تراکنش اخیر
                project_data.append({
                    'project': project,
                    'total_budget': total_budget,
                    'remaining_budget': remaining_budget,
                    'allocated_percentage': (
                        (total_budget / org_budget * 100) if org_budget > 0 else Decimal('0')
                    ),
                    'remaining_percentage': (
                        (remaining_budget / total_budget * 100) if total_budget > 0 else Decimal('0')
                    ),
                    'transactions': transactions,
                })

            data.append({
                'organization': org,
                'total_budget': org_budget,
                'remaining_budget': org_remaining,
                'projects': project_data,
            })

        context.update({
            'report_data': data,
            'organizations': organizations,
            'selected_organization': organization_id,
            'selected_project': project_id,
        })
        logger.debug(f"BudgetRealtimeReportView context: {context}")
        return context