from django.views.generic import DetailView
from budgets.models import PaymentOrder
from core.PermissionBase import PermissionBaseView


class FactorItemsDetailView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'tankhah/Factors/factor_items_detail.html'
    # permission_required = ['tankhah.factor_view']
    check_object_permissions = ['tankhah.factor_view']
    context_object_name = 'payment_order'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factors = self.object.related_factors.all()
        context['factor_items'] = [item for factor in factors for item in factor.items.all()]
        return context