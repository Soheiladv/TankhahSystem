# budgets/views.py
from django.views.generic import ListView
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Sum
from decimal import Decimal

from Tanbakhsystem.utils import parse_jalali_date, to_english_digits
from budgets.budget_calculations import get_project_remaining_budget, get_project_used_budget , \
    get_project_total_budget
from budgets.models import  BudgetAllocation, BudgetPeriod, BudgetItem
from  core.models import  Project
from core.models import Organization
from core.views import PermissionBaseView

import logging

logger = logging.getLogger(__name__)

class ProjectBudgetAllocationListView2D(PermissionBaseView, ListView):
    model = ProjectBudgetAllocation
    template_name = 'budgets/budget/project_budget_allocation_list_2d.html'
    context_object_name = 'project_allocations'
    paginate_by = 10
    permission_required = 'budgets.view_projectbudgetallocation'

    def get_queryset(self):
        queryset = ProjectBudgetAllocation.objects.filter(is_active=True).select_related(
            'budget_allocation__organization',
            'budget_allocation__budget_period',
            'project',
        )
        logger.info(f"ProjectBudgetAllocationListView queryset: {queryset.count()} records")

        # فیلتر سازمان
        organization_id = self.request.GET.get('organization')
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id, is_active=True)
                queryset = queryset.filter(budget_allocation__organization=organization)
            except Organization.DoesNotExist:
                logger.warning(f"Invalid organization_id: {organization_id}")
                messages.error(self.request, _('سازمان انتخاب‌شده نامعتبر است.'))

        # فیلترهای جستجو
        query = self.request.GET.get('q', '')
        date_from = self.request.GET.get('date_from', '')
        date_to = self.request.GET.get('date_to', '')
        project_id = self.request.GET.get('project')

        if query:
            queryset = queryset.filter(
                Q(project__name__icontains=query) |
                Q(project__code__icontains=query) |
                Q(budget_allocation__organization__name__icontains=query)
            )

        if project_id:
            try:
                project = Project.objects.get(id=project_id, is_active=True)
                queryset = queryset.filter(project=project)
            except Project.DoesNotExist:
                logger.warning(f"Invalid project_id: {project_id}")
                messages.error(self.request, _('پروژه انتخاب‌شده نامعتبر است.'))

        if date_from:
            try:
                date_from = parse_jalali_date(to_english_digits(date_from))
                queryset = queryset.filter(allocation_date__gte=date_from)
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
                messages.error(self.request, _('فرمت تاریخ شروع نامعتبر است.'))

        if date_to:
            try:
                date_to = parse_jalali_date(to_english_digits(date_to))
                queryset = queryset.filter(allocation_date__lte=date_to)
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
                messages.error(self.request, _('فرمت تاریخ پایان نامعتبر است.'))

        # بررسی دسترسی سازمانی
        user_organizations = self.request.user.get_authorized_organizations()
        queryset = queryset.filter(budget_allocation__organization__in=user_organizations)

        return queryset.order_by('-allocation_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization_id = self.request.GET.get('organization')
        project_id = self.request.GET.get('project')

        # مقداردهی اولیه
        total_allocated = Decimal('0')
        total_used = Decimal('0')
        total_remaining = Decimal('0')

        # محاسبه اطلاعات کل
        queryset = self.get_queryset()
        for allocation in queryset:
            project = allocation.project
            total_allocated += allocation.allocated_amount
            total_used += get_project_used_budget(project)
            total_remaining += get_project_remaining_budget(project)

        # اطلاعات سازمان
        organization = None
        if organization_id:
            try:
                organization = Organization.objects.get(id=organization_id, is_active=True)
                context['organization'] = organization
                from budgets.get_budget_details import get_budget_details
                context['org_budget'] = get_budget_details(entity=organization)
            except Organization.DoesNotExist:
                logger.warning(f"Invalid organization_id: {organization_id}")
                context['status_message'] = _('سازمان انتخاب‌شده نامعتبر است.')

        # اطلاعات پروژه
        project_data = {}
        if project_id:
            try:
                project = Project.objects.get(id=project_id, is_active=True)
                project_total = get_project_total_budget(project)
                project_used = get_project_used_budget(project)
                project_remaining = get_project_remaining_budget(project)
                project_data = {
                    'total': project_total,
                    'used': project_used,
                    'remaining': project_remaining,
                    'allocated_percentage': (project_used / project_total * Decimal('100')) if project_total > 0 else Decimal('0'),
                    'remaining_percentage': (project_remaining / project_total * Decimal('100')) if project_total > 0 else Decimal('0'),
                }
                logger.info(
                    f"Project {project.id}: total={project_total}, used={project_used}, "
                    f"remaining={project_remaining}"
                )
            except Project.DoesNotExist:
                logger.warning(f"Invalid project_id: {project_id}")
                context['status_message'] = _('پروژه انتخاب‌شده نامعتبر است.')

        context.update({
            'total_allocated': total_allocated,
            'total_used': total_used,
            'total_remaining': total_remaining,
            'project_data': project_data,
            'organizations': Organization.objects.filter(is_active=True, id__in=self.request.user.get_authorized_organizations()),
            'projects': Project.objects.filter(is_active=True),
            'status': 'filtered',
            'status_message': context.get('status_message', _('نمایش تخصیص‌های فیلترشده')),
            'query': self.request.GET.get('q', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'selected_organization': organization_id,
            'selected_project': project_id,
        })

        logger.debug(f"ProjectBudgetAllocationListView context: {context}")
        return context