from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from budgets.models import BudgetTransaction
from budgets.BudgetReturn.forms_BudgetReturm import BudgetReturnForm
from budgets.budget_calculations import (get_project_remaining_budget,
                                         get_project_remaining_budget,
                                         get_project_total_budget,
                                         get_project_used_budget,
                                         check_budget_status, get_organization_budget
                                         )
from core.PermissionBase import PermissionBaseView
import logging
logger = logging.getLogger(__name__)

#-----------------
class BudgetReturnView(PermissionBaseView, CreateView):
    model = BudgetTransaction
    form_class = BudgetReturnForm
    template_name = 'budgets/budget_return_form.html'
    permission_codename = 'budgets.BudgetTransaction_add'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    check_organization = True


    def get_allocation(self):
        try:
            allocation = ProjectBudgetAllocation.objects.get(pk=self.kwargs['allocation_id'], is_active=True)
            user_organizations = self.request.user.get_authorized_organizations()
            if not user_organizations.filter(pk=allocation.budget_allocation.organization.pk).exists():
                logger.warning(
                    f"User {self.request.user.username} attempted to access allocation {self.kwargs['allocation_id']} "
                    f"without organization permission"
                )
                raise PermissionDenied(self.permission_denied_message)
            return allocation
        except ProjectBudgetAllocation.DoesNotExist:
            logger.error(f"Allocation {self.kwargs['allocation_id']} does not exist or is inactive")
            messages.error(self.request, _('تخصیص بودجه مورد نظر یافت نشد یا غیرفعال است.'))
            return None


    def dispatch(self, request, *args, **kwargs):
        allocation = self.get_allocation()
        if not allocation:
            return redirect('budgetallocation_list')
        return super().dispatch(request, *args, **kwargs)


    def get_initial(self):
        initial = super().get_initial()
        allocation = self.get_allocation()
        if allocation:
            initial['allocation'] = allocation.budget_allocation
            initial['transaction_type'] = 'RETURN'
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        allocation = self.get_allocation()
        if not allocation:
            return context

        project = allocation.project
        organization = allocation.budget_allocation.organization
        budget_period = allocation.budget_allocation.budget_period

        from budgets.get_budget_details import get_budget_details
        context.update({
            'allocation': allocation,
            'project': project,
            'organization': organization,
            'total_budget': get_project_total_budget(project),
            'used_budget': get_project_used_budget(project),
            'remaining_budget': get_project_remaining_budget(project),
            'org_budget': get_organization_budget(organization),
            'budget_details': get_budget_details(entity=project),
            'budget_status': check_budget_status(budget_period)[0],
            'budget_status_message': check_budget_status(budget_period)[1],
        })
        return context

    # def get_context_data(self, **kwargs):
    #         context = super().get_context_data(**kwargs)
    #         allocation = self.get_allocation()
    #         if not allocation:
    #             return context
    #
    #         # محاسبه اطلاعات بودجه با استفاده از توابع
    #         project = allocation.project
    #         organization = allocation.budget_allocation.organization
    #         budget_period = allocation.budget_allocation.budget_period
    #
    #         total_budget = get_project_total_budget(project)
    #         used_budget = get_project_used_budget(project)
    #         remaining_budget = get_project_remaining_budget(project)
    #         org_budget = get_organization_budget(organization)
    #         budget_details = get_budget_details(entity=project)
    #         budget_status = check_budget_status(budget_period)
    #
    #         context.update({
    #             'allocation': allocation,
    #             'project': project,
    #             'organization': organization,
    #             'total_budget': total_budget,
    #             'used_budget': used_budget,
    #             'remaining_budget': remaining_budget,
    #             'org_budget': org_budget,
    #             'budget_details': budget_details,
    #             'budget_status': budget_status[0],
    #             'budget_status_message': budget_status[1],
    #         })
    #         return context

    def form_valid(self, form):
        allocation = self.get_allocation()
        if not allocation:
            return redirect('budgetallocation_list')

        # اعتبارسنجی اضافی با استفاده از توابع
        project = allocation.project
        remaining_budget = get_project_remaining_budget(project)
        consumed = get_project_used_budget(project)
        if form.instance.amount > consumed:
            form.add_error(
                'amount',
                _(f"مبلغ بازگشت ({form.instance.amount:,.0f} ریال) نمی‌تواند بیشتر از مصرف‌شده ({consumed:,.0f} ریال) باشد.")
            )
            return self.form_invalid(form)
        if form.instance.amount > remaining_budget:
            form.add_error(
                'amount',
                _(f"مبلغ بازگشت ({form.instance.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد.")
            )
            return self.form_invalid(form)

        # if form.instance.amount > remaining_budget:
        #     form.add_error('amount', _(f"مبلغ بازگشت ({form.instance.amount:,.0f} ریال) نمی‌تواند بیشتر از بودجه باقی‌مانده ({remaining_budget:,.0f} ریال) باشد."))
        #     return self.form_invalid(form)

        form.instance.created_by = self.request.user
        logger.info(f"User {self.request.user.username} created return transaction for allocation {allocation.id}")
        messages.success(self.request, _("تراکنش بازگشت بودجه با موفقیت ثبت شد."))

        # ثبت تراکنش و ارسال اعلان
        instance = form.save(commit=False)
        instance.transaction_type = 'RETURN'
        instance.save()

        # بررسی وضعیت بودجه و ارسال اعلان
        status, message = check_budget_status(allocation.budget_allocation.budget_period)
        if status in ('warning', 'locked', 'completed', 'stopped'):
            allocation.budget_allocation.send_notification(status, message)
        allocation.budget_allocation.send_notification(
            'return',
            f"مبلغ {instance.amount:,.0f} ریال از تخصیص {allocation.id} برگشت داده شد."
        )

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        allocation = self.get_allocation()
        if allocation:
            kwargs['allocation'] = allocation
            kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('project_budget_allocation_detail', kwargs={'pk': self.kwargs['allocation_id']})
#-----------------


""""گزارش‌گیری بودجه برگشتی:"""
from budgets.models import BudgetHistory, ProjectBudgetAllocation, BudgetTransaction


def get_returned_budgets(budget_period):
    from django.contrib.contenttypes.models import ContentType
    from budgets.models import  BudgetAllocation
    return BudgetHistory.objects.filter(
        content_type=ContentType.objects.get_for_model(BudgetAllocation),
        action='RETURN',
        content_object__budget_period=budget_period
    ).values('amount', 'details', 'created_at', 'created_by__username')