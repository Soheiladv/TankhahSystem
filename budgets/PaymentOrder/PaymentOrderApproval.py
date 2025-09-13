# در budgets/views.py
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView

from budgets.PaymentOrder.form_PaymentOrder import PaymentOrderApprovalForm
from budgets.models import PaymentOrder
from core.PermissionBase import PermissionBaseView
from tankhah.models import ApprovalLog


class PaymentOrderApprovalListView(PermissionBaseView, ListView):
    """لیست دستورات پرداخت در انتظار تایید"""
    model = PaymentOrder
    template_name = 'budgets/paymentorder/approval_list.html'
    context_object_name = 'pending_orders'

    def get_queryset(self):
        return PaymentOrder.objects.filter(
            status__code__in=['PENDING_APPROVAL', 'DRAFT'],
            is_locked=False
        ).select_related('tankhah', 'payee', 'organization')


class PaymentOrderApprovalView(PermissionBaseView, UpdateView):
    model = PaymentOrder
    form_class = PaymentOrderApprovalForm
    template_name = 'budgets/paymentorder/approval_form.html'

    def form_valid(self, form):
        with transaction.atomic():
            # تغییر وضعیت
            form.instance.status = form.cleaned_data['status']
            form.instance.save()

            # ثبت لاگ
            ApprovalLog.objects.create(
                content_object=form.instance,
                action='APPROVED' if form.cleaned_data['status'].code == 'APPROVED' else 'REJECTED',
                user=self.request.user,
                comment=form.cleaned_data['notes']
            )

            # ارسال اعلان
            from notificationApp.utils import send_notification
            send_notification(
                sender=self.request.user,
                users=[form.instance.created_by],
                verb='PAYMENTORDER_APPROVED' if form.cleaned_data[
                                                    'status'].code == 'APPROVED' else 'PAYMENTORDER_REJECTED',
                description=f"دستور پرداخت {form.instance.order_number} {'تایید' if form.cleaned_data['status'].code == 'APPROVED' else 'رد'} شد.",
                target=form.instance,
                entity_type='PAYMENTORDER',
                priority='HIGH'
            )

            messages.success(self.request, 'دستور پرداخت با موفقیت پردازش شد.')
            return redirect('paymentorder_approval_list')
