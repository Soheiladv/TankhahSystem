from django.views.generic import ListView
from django.contrib.auth.mixins import PermissionRequiredMixin
from budgets.models import PaymentOrder
from budgets.models import BudgetAllocation
from core.PermissionBase import PermissionBaseView


class PaymentOrderReportView(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'reports/PaymentOrderReport/payment_order_report.html'
    permission_required = ['PaymentOrder_view']
    context_object_name = 'payment_orders'
    check_organization = True
    paginate_by = 10

    def get_queryset(self):
        queryset = PaymentOrder.objects.select_related(
            'tankhah', 'tankhah__project', 'tankhah__organization', 'payee'
        ).prefetch_related('related_factors', 'related_factors__items')
        return queryset.order_by('-issue_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # اطلاعات اضافی برای گزارشات
        payment_orders = context['payment_orders']
        report_data = []
        for po in payment_orders:
            factors = po.related_factors.all()
            budget_allocation = po.tankhah.project_budget_allocation
            report_data.append({
                'payment_order': po,
                'factors': factors,
                'factor_items': [
                    item for factor in factors for item in factor.items.all()
                ],
                'budget_allocation': {
                    'allocated_amount': budget_allocation.allocated_amount,
                    'remaining_amount': budget_allocation.get_remaining_amount(),
                },
                'tankhah': {
                    'number': po.tankhah.number,
                    'project': po.tankhah.project.name,
                    'organization': po.tankhah.organization.name,
                    'date': po.tankhah.date,
                    'due_date': po.tankhah.due_date,
                },
            })
        context['report_data'] = report_data
        return context