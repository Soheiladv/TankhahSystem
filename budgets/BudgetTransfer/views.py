from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.db import transaction
import socket
import jdatetime

from budgets.models import BudgetTransaction, BudgetAllocation, BudgetHistory
from budgets.budget_calculations import create_budget_transaction
from core.PermissionBase import PermissionBaseView

from .forms import BudgetTransferForm


class BudgetTransferListView(PermissionBaseView, View):
    template_name = 'budgets/budget_transfer/transfer_list.html'
    permission_codename = 'budgets.BudgetTransaction_view'

    def get(self, request):
        transfers = BudgetTransaction.objects.filter(transaction_type__in=['INCREASE', 'DECREASE']).order_by('-timestamp')[:200]
        return render(request, self.template_name, {'transfers': transfers})


def _build_allocation_meta(qs):
    meta = []
    for a in qs:
        try:
            remaining = float(a.get_remaining_amount())
        except Exception:
            remaining = 0.0
        meta.append({
            'id': a.id,
            'label': str(a),
            'remaining': remaining,
            'org': getattr(getattr(a, 'organization', None), 'name', None),
            'item': getattr(getattr(a, 'budget_item', None), 'name', None),
        })
    return meta


class BudgetTransferCreateView(PermissionBaseView, View):
    template_name = 'budgets/budget_transfer/transfer_form.html'
    permission_codename = 'budgets.BudgetTransaction_add'

    def _context(self, form):
        allocations = BudgetAllocation.objects.select_related('organization', 'budget_item', 'project').all()[:500]
        return {
            'form': form,
            'allocation_meta': _build_allocation_meta(allocations),
            'jalali_now': jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M'),
            'current_user': self.request.user if hasattr(self, 'request') else None,
        }

    def get(self, request):
        self.request = request
        form = BudgetTransferForm()
        return render(request, self.template_name, self._context(form))

    def post(self, request):
        self.request = request
        form = BudgetTransferForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(form))

        source: BudgetAllocation = form.cleaned_data['source_allocation']
        target: BudgetAllocation = form.cleaned_data['target_allocation']
        amount = form.cleaned_data['amount']
        user = request.user
        # Build auto description (includes user, date, src/dst, client info)
        jalali_now = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = request.META.get('REMOTE_ADDR')
        client_host = socket.gethostname()
        auto_desc = (
            f"انتقال مبلغ {amount:,.0f} ریال از تخصیص {source.pk} ({source.organization.name if source.organization else '—'} / {source.budget_item.name if source.budget_item else '—'}) "
            f"به تخصیص {target.pk} ({target.organization.name if target.organization else '—'} / {target.budget_item.name if target.budget_item else '—'}) "
            f"در تاریخ {jalali_now} توسط کاربر {getattr(user, 'username', 'سیستم')}."
        )
        meta_desc = f" [IP:{client_ip} | HOST:{client_host}]"
        user_desc = (form.cleaned_data.get('description') or '').strip()
        description = (auto_desc + (f" توضیحات: {user_desc}" if user_desc else '') + meta_desc).strip()

        try:
            with transaction.atomic():
                tx_dec = create_budget_transaction(
                    budget_source_obj=source,
                    transaction_type='DECREASE',
                    amount=amount,
                    created_by=user,
                    description=description,
                    client_ip=client_ip,
                    client_host=client_host,
                )
                tx_inc = create_budget_transaction(
                    budget_source_obj=target,
                    transaction_type='INCREASE',
                    amount=amount,
                    created_by=user,
                    description=description,
                    client_ip=client_ip,
                    client_host=client_host,
                )
                if tx_dec:
                    BudgetHistory.log_change(
                        obj=source,
                        action='REALLOCATE',
                        amount=amount,
                        created_by=user,
                        details=f"کاهش بابت انتقال به تخصیص مقصد {target.pk}",
                        transaction_type='RETURN',
                        transaction_id=tx_dec.transaction_id,
                    )
                if tx_inc:
                    BudgetHistory.log_change(
                        obj=target,
                        action='REALLOCATE',
                        amount=amount,
                        created_by=user,
                        details=f"افزایش بابت انتقال از تخصیص مبدا {source.pk}",
                        transaction_type='ALLOCATION',
                        transaction_id=tx_inc.transaction_id,
                    )
        except Exception as e:
            messages.error(request, f"خطا در ثبت انتقال: {e}")
            return render(request, self.template_name, self._context(form))

        messages.success(request, 'انتقال با موفقیت ثبت شد.')
        return redirect(reverse('budget_transfer:transfer_list'))
