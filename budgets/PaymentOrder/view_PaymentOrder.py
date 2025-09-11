import logging
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, View
from core.PermissionBase import PermissionBaseView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.db import transaction

from budgets.models import PaymentOrder
from budgets.PaymentOrder.form_PaymentOrder import PaymentOrderForm
from core.models import UserPost, Transition, Status
from tankhah.models import ApprovalLog

logger = logging.getLogger(__name__)

def get_available_actions(user, payment_order):
    """
    بر اساس وضعیت فعلی دستور پرداخت و پست کاربر، اقدامات مجاز را برمی‌گرداند.
    """
    if not user.is_authenticated or payment_order.is_locked:
        return []

    user_posts = UserPost.objects.filter(user=user, is_active=True).values_list('post', flat=True)
    if not user_posts:
        return []

    # پیدا کردن گذارهای (transitions) ممکن از وضعیت فعلی
    possible_transitions = Transition.objects.filter(
        from_status=payment_order.status,
        entity_type__code='PAYMENTORDER',  # اطمینان از اینکه گذار برای دستور پرداخت است
        allowed_posts__in=list(user_posts),
        is_active=True
    ).select_related('action', 'to_status').distinct()

    return list(possible_transitions)

class PaymentOrderListView(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_list.html'
    context_object_name = 'payment_orders'
    permission_required = 'budgets.PaymentOrder_view'
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        queryset = PaymentOrder.objects.select_related(
            'tankhah', 'organization', 'project', 'payee', 'created_by', 'status'
        )

        if not user.is_superuser:
            user_orgs = UserPost.objects.filter(user=user, is_active=True).values_list('post__organization__pk', flat=True)
            queryset = queryset.filter(organization__pk__in=user_orgs)

        query = self.request.GET.get('query', '')
        status_code = self.request.GET.get('status', '')

        if query:
            queryset = queryset.filter(
                Q(order_number__icontains=query) |
                Q(description__icontains=query) |
                Q(payee__name__icontains=query) |
                Q(tankhah__number__icontains=query)
            ).distinct()

        if status_code:
            queryset = queryset.filter(status__code=status_code)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query', '')
        context['status'] = self.request.GET.get('status', '')
        context['status_choices'] = Status.objects.filter(is_active=True).values('code', 'name')
        return context

class PaymentOrderCreateView(PermissionBaseView, CreateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    success_url = reverse_lazy('budgets:paymentorder_list')
    permission_required = 'budgets.PaymentOrder_add'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت ایجاد شد.')
            return response

class PaymentOrderUpdateView(PermissionBaseView, UpdateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    success_url = reverse_lazy('budgets:paymentorder_list')
    permission_required = 'budgets.PaymentOrder_update'

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت به‌روزرسانی شد.')
            return response

class PaymentOrderDeleteView(PermissionBaseView, DeleteView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_confirm_delete.html'
    success_url = reverse_lazy('budgets:paymentorder_list')
    permission_required = 'budgets.PaymentOrder_delete'

    def post(self, request, *args, **kwargs):
        payment_order = self.get_object()
        with transaction.atomic():
            payment_order.delete()
            messages.success(request, f'دستور پرداخت {payment_order.order_number} با موفقیت حذف شد.')
        return redirect(self.success_url)

class PaymentOrderDetailView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    context_object_name = 'payment_order'
    permission_required = 'budgets.PaymentOrder_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_order = self.get_object()
        context['available_actions'] = get_available_actions(self.request.user, payment_order)
        context['approval_logs'] = ApprovalLog.objects.filter(
            content_type=ContentType.objects.get_for_model(payment_order),
            object_id=payment_order.pk
        ).order_by('-timestamp')
        return context

class PerformActionView(PermissionBaseView, View):
    permission_required = 'budgets.PaymentOrder_sign' # A general permission to perform actions

    def post(self, request, *args, **kwargs):
        payment_order_pk = kwargs.get('pk')
        action_pk = kwargs.get('action_pk')
        payment_order = get_object_or_404(PaymentOrder, pk=payment_order_pk)
        
        available_actions = get_available_actions(request.user, payment_order)
        
        # پیدا کردن گذار مربوط به اقدام انتخاب شده
        selected_transition = next((t for t in available_actions if t.action.pk == action_pk), None)

        if not selected_transition:
            messages.error(request, _("شما مجاز به انجام این اقدام نیستید یا این اقدام دیگر معتبر نیست."))
            return redirect(payment_order.get_absolute_url())

        try:
            with transaction.atomic():
                from_status = payment_order.status
                to_status = selected_transition.to_status

                # تغییر وضعیت دستور پرداخت
                payment_order.status = to_status
                
                # اگر وضعیت نهایی است، دستور پرداخت را قفل کن
                if to_status.is_final_approve or to_status.is_final_reject:
                    payment_order.is_locked = True

                payment_order.save()

                # ثبت لاگ اقدام
                user_post = UserPost.objects.filter(user=request.user, is_active=True).first()
                ApprovalLog.objects.create(
                    content_object=payment_order,
                    from_status=from_status,
                    to_status=to_status,
                    action=selected_transition.action,
                    user=request.user,
                    post=user_post.post if user_post else None,
                    comment=request.POST.get('comment', '')
                )

                messages.success(request, _("اقدام شما با موفقیت ثبت شد."))
                logger.info(f"User {request.user.username} performed action '{selected_transition.action.name}' on PaymentOrder {payment_order.order_number}")

        except Exception as e:
            messages.error(request, _("خطایی در هنگام پردازش اقدام رخ داد."))
            logger.error(f"Error performing action on PaymentOrder {payment_order.pk} by user {request.user.username}: {e}", exc_info=True)

        return redirect(payment_order.get_absolute_url())

class PaymentOrderReviewView(PaymentOrderListView):
    template_name = 'budgets/paymentorder/payment_order_review.html'
    permission_codenames = ['budgets.PaymentOrder_view']
