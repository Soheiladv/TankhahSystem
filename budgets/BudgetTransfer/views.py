from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
import socket
import jdatetime

from budgets.models import BudgetTransaction, BudgetAllocation, BudgetHistory
from budgets.budget_calculations import create_budget_transaction
from core.PermissionBase import PermissionBaseView
from BudgetsSystem.utils import parse_jalali_date, to_english_digits, convert_jalali_to_gregorian
from datetime import datetime, time

from .forms import BudgetTransferForm


class BudgetTransferListView(PermissionBaseView, View):
    template_name = 'budgets/budget_transfer/transfer_list.html'
    permission_codename = 'budgets.BudgetTransaction_view'

    def get(self, request):
        qs = BudgetTransaction.objects.filter(transaction_type__in=['INCREASE', 'DECREASE']).select_related('allocation').order_by('-timestamp')

        query = (request.GET.get('q') or '').strip()
        tx_type = (request.GET.get('type') or '').strip().upper()
        date_from = (request.GET.get('date_from') or '').strip()
        date_to = (request.GET.get('date_to') or '').strip()

        if query:
            qs = qs.filter(
                Q(description__icontains=query) |
                Q(allocation__organization__name__icontains=query) |
                Q(allocation__budget_item__name__icontains=query) |
                Q(allocation__project__name__icontains=query)
            )

        if tx_type in ('INCREASE', 'DECREASE'):
            qs = qs.filter(transaction_type=tx_type)

        # تاریخ‌های جلالی: انتظار ورودی مانند 1403/07/15
        if date_from:
            try:
                d_from = convert_jalali_to_gregorian(to_english_digits(date_from))
                qs = qs.filter(timestamp__date__gte=d_from)
            except Exception:
                pass
        if date_to:
            try:
                d_to = convert_jalali_to_gregorian(to_english_digits(date_to))
                qs = qs.filter(timestamp__date__lte=d_to)
            except Exception:
                pass

        paginator = Paginator(qs, 20)
        page_number = request.GET.get('page')
        transfers = paginator.get_page(page_number)

        # حفظ پارامترها برای صفحه‌بندی
        context = {
            'transfers': transfers,
            'q': query,
            'type': tx_type,
            'date_from': date_from,
            'date_to': date_to,
        }
        return render(request, self.template_name, context)


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
