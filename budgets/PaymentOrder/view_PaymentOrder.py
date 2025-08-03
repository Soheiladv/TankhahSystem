import logging
from decimal import Decimal
from time import timezone

from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from falcon import async_to_sync

from accounts.models import CustomUser
from budgets.PaymentOrder.form_PaymentOrder import PaymentOrderForm
from budgets.models import PaymentOrder, generate_payment_order_number, Payee
from core.models import Organization, Project, UserPost, WorkflowStage
from notificationApp.models import NotificationRule
from notificationApp.utils import send_notification
from tankhah.models import Tankhah, StageApprover, ApprovalLog, Factor, TankhahAction, TankhActionType

logger = logging.getLogger(__name__)
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView, TemplateView
from core.PermissionBase import PermissionBaseView
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# --- PaymentOrder CRUD ---
from django.db.models import Q, Prefetch, Count


"""ایجاد خوکار دستور پرداخت """

class TankhahUpdateStatusView(PermissionBaseView, UpdateView):
    model = Tankhah
    fields = ['status', 'current_stage']
    template_name = 'budgets/paymentorder/tankhah_update_status.html'
    permission_required = 'tankhah.change_tankhah'

    def get_success_url(self):
        return reverse_lazy('tankhah_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        user = self.request.user
        try:
            with transaction.atomic():
                tankhah = form.save(commit=False)
                tankhah.save()
                logger.info(f"Tankhah {tankhah.number} status updated to {tankhah.status} by user {user.username}")

                if tankhah.current_stage and tankhah.current_stage.triggers_payment_order and \
                        tankhah.status == 'APPROVED':
                    logger.info(f"Conditions met to auto-create PaymentOrder for Tankhah {tankhah.number}")

                    # تعیین Payee
                    target_payee = None
                    if hasattr(tankhah, 'payee') and tankhah.payee:
                        target_payee = tankhah.payee
                    elif tankhah.factors.filter(payee__isnull=False).exists():
                        distinct_payees = tankhah.factors.filter(payee__isnull=False).values_list('payee', flat=True).distinct()
                        if len(distinct_payees) == 1:
                            target_payee = Payee.objects.get(pk=distinct_payees[0])
                        else:
                            messages.warning(self.request, _("امکان تعیین خودکار دریافت‌کننده وجود ندارد."))
                            return super().form_valid(form)

                    if not target_payee:
                        logger.warning(f"No payee found for Tankhah {tankhah.number}")
                        messages.warning(self.request, _("دریافت‌کننده برای دستور پرداخت مشخص نشده است."))
                        return super().form_valid(form)

                    initial_po_stage = WorkflowStage.objects.filter(
                        entity_type='PAYMENTORDER',
                        order=1,
                        is_active=True
                    ).first()
                    if not initial_po_stage:
                        logger.error("No initial workflow stage for PAYMENTORDER")
                        messages.error(self.request, _("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
                        return super().form_valid(form)

                    user_post = user.userpost_set.filter(is_active=True).first()
                    payment_order = PaymentOrder(
                        tankhah=tankhah,
                        related_tankhah=tankhah,
                        amount=tankhah.amount,
                        description=f"پرداخت برای تنخواه شماره {tankhah.number}",
                        organization=tankhah.organization,
                        project=tankhah.project if hasattr(tankhah, 'project') else None,
                        status='DRAFT',
                        created_by=user,
                        created_by_post=user_post.post if user_post else None,
                        current_stage=initial_po_stage,
                        issue_date=timezone.now().date(),
                        payee=target_payee,
                        min_signatures=initial_po_stage.min_signatures or 1
                    )
                    payment_order.save()

                    # لینک کردن فاکتورها
                    payment_order.related_factors.set(tankhah.factors.all())

                    # ایجاد ActionApproval برای امضاکنندگان
                    approving_posts = StageApprover.objects.filter(
                        stage=initial_po_stage,
                        is_active=True
                    ).select_related('post')
                    for stage_approver in approving_posts:
                        ApprovalLog.objects.create(
                            action=payment_order,
                            approver_post=stage_approver.post
                        )

                    # ارسال نوتیفیکیشن
                    eligible_users = set()
                    for stage_approver in approving_posts:
                        users = CustomUser.objects.filter(
                            userpost__post=stage_approver.post,
                            userpost__is_active=True
                        )
                        eligible_users.update(users)
                    for user_to_notify in eligible_users:
                        if user_to_notify != user:

                            send_notification(self.request.user, users=None, posts=None,
                                              verb='needs_approval', description=f"دستور پرداخت {payment_order.order_number} نیاز به امضای شما دارد.",
                                              target=self.object,
                                              entity_type=None, priority='MEDIUM')

                    logger.info(f"PaymentOrder {payment_order.order_number} created for Tankhah {tankhah.number}")
                    messages.success(self.request, f"دستور پرداخت {payment_order.order_number} ایجاد شد.")

        except Exception as e:
            logger.error(f"Error in TankhahUpdateStatusView: {e}", exc_info=True)
            messages.error(self.request, "خطایی در به‌روزرسانی تنخواه رخ داد.")
            return self.form_invalid(form)

        return super().form_valid(form)
# --------------------------------------------------------------------------
class PaymentOrderReviewView__ok(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/PaymentOrder/payment_order_review.html'
    context_object_name = 'payment_orders_data'
    paginate_by = 10
    permission_codenames = ['budgets.PaymentOrder_view']  # اصلاح مجوز
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی لازم برای مشاهده دستورات پرداخت را ندارید.')

    def get_queryset(self):
        user = self.request.user
        payment_order_ct = ContentType.objects.get_for_model(PaymentOrder)
        queryset = PaymentOrder.objects.select_related(
            'payee', 'tankhah', 'tankhah__organization', 'related_tankhah',
            'organization', 'project', 'current_stage', 'created_by', 'paid_by', 'created_by_post'
        ).prefetch_related(
            Prefetch(
                'related_factors',
                queryset=Factor.objects.select_related('tankhah')
            )
        )

        user_orgs = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).values_list('post__organization__pk', flat=True)
        if not user_orgs and not user.is_superuser:
            logger.warning(f"No organizations for user {user.username}")
            return queryset.none()
        if user_orgs:
            queryset = queryset.filter(organization__pk__in=user_orgs)

        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(description__icontains=search) |
                Q(payee__name__icontains=search) |
                Q(tankhah__number__icontains=search) |
                Q(related_tankhah__number__icontains=search) |
                Q(related_factors__number__icontains=search)
            ).distinct()

        status = self.request.GET.get('status', '')
        if status in [choice[0] for choice in PaymentOrder.STATUS_CHOICES]:
            queryset = queryset.filter(status=status)

        org_id = self.request.GET.get('organization_id', '')
        if org_id:
            queryset = queryset.filter(organization__id=org_id)
        proj_id = self.request.GET.get('project_id', '')
        if proj_id:
            queryset = queryset.filter(project__id=proj_id)

        logger.debug(f"Queryset filtered: user={user.username}, search={search}, status={status}, org={org_id}, proj={proj_id}")
        return queryset.order_by('-created_at')

    def get_approver_posts_for_stage(self, stage):
        if not stage:
            return []
        return list(StageApprover.objects.filter(
            stage=stage, is_active=True
        ).select_related('post', 'post__organization').values(
            'post__name', 'post__organization__name'
        ).distinct())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_orders_with_details = []
        payment_order_ct = ContentType.objects.get_for_model(PaymentOrder)

        for po in context['object_list']:
            # دستی گرفتن لاگ‌های ApprovalLog
            approval_logs = ApprovalLog.objects.filter(
                content_type=payment_order_ct,
                object_id=po.id
            ).select_related('user', 'post', 'post__organization', 'stage').order_by('timestamp')

            previous_actions = [
                {
                    'post_name': log.post.name if log.post else _('نامشخص'),
                    'post_org_name': log.post.organization.name if log.post and log.post.organization else _('نامشخص'),
                    'user_name': log.user.get_full_name() or log.user.username if log.user else _('سیستم'),
                    'action': log.action,
                    'timestamp': log.timestamp,
                    'comment': log.comment or '-',
                    'stage_name': log.stage.name if log.stage else _('نامشخص'),
                }
                for log in approval_logs
            ]

            next_approvers = []
            if po.current_stage and not po.is_locked and po.status not in ['PAID', 'REJECTED', 'CANCELLED']:
                next_approvers = self.get_approver_posts_for_stage(po.current_stage)

            tankhah_remaining = Decimal('0')
            project_remaining = Decimal('0')
            budget_message = ''
            if po.tankhah:
                tankhah_remaining = po.tankhah.budget - po.tankhah.spent
            elif po.related_tankhah:
                tankhah_remaining = po.related_tankhah.budget - po.related_tankhah.spent
            if po.project:
                project_remaining = po.project.budget - po.project.spent
            if po.status not in ['PAID', 'REJECTED', 'CANCELLED']:
                if po.amount > tankhah_remaining:
                    budget_message = _('هشدار: مبلغ از مانده تنخواه بیشتر است!')
                elif po.project and po.amount > project_remaining:
                    budget_message = _('هشدار: مبلغ از مانده پروژه بیشتر است!')

            payment_orders_with_details.append({
                'payment_order': po,
                'previous_actions': previous_actions,
                'next_possible_approvers': next_approvers,
                'tankhah_remaining_after': tankhah_remaining - po.amount if po.status not in ['PAID', 'REJECTED', 'CANCELLED'] else tankhah_remaining,
                'project_remaining_after': project_remaining - po.amount if po.status not in ['PAID', 'REJECTED', 'CANCELLED'] else project_remaining,
                'budget_message': budget_message,
                'tankhah_number': po.tankhah.number if po.tankhah else (po.related_tankhah.number if po.related_tankhah else '-'),
                'factor_numbers': ', '.join(f.number for f in po.related_factors.all()) or '-',
                'org_name': po.organization.name,
                'project_name': po.project.name if po.project else _('بدون پروژه'),
                'stage_name': po.current_stage.name if po.current_stage else _('نامشخص'),
                'created_by_post': po.created_by_post.name if po.created_by_post else '-',
            })

        grouped_by_status = {}
        for item in payment_orders_with_details:
            status = item['payment_order'].get_status_display()
            grouped_by_status.setdefault(status, []).append(item)

        context['payment_orders_data'] = payment_orders_with_details
        context['grouped_by_status'] = grouped_by_status
        context['title'] = _('بررسی دستورات پرداخت')
        context['status_choices'] = PaymentOrder.STATUS_CHOICES
        context['organizations'] = Organization.objects.filter(is_active=True).order_by('name')
        context['projects'] = Project.objects.filter(is_active=True).order_by('name')
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'organization_id': self.request.GET.get('organization_id', ''),
            'project_id': self.request.GET.get('project_id', ''),
        }


        logger.info(f"Context prepared for user {self.request.user.username}, {len(payment_orders_with_details)} payment orders")
        return context
# --------------------------------------------------------------------------
class PaymentOrderReviewView(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/PaymentOrder/payment_order_review.html'
    context_object_name = 'payment_orders_data'
    paginate_by = 10
    permission_codenames = ['budgets.PaymentOrder_view']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی لازم برای مشاهده دستورات پرداخت را ندارید.')

    def get_queryset(self):
        user = self.request.user
        payment_order_ct = ContentType.objects.get_for_model(PaymentOrder)
        queryset = PaymentOrder.objects.select_related(
            'payee', 'tankhah', 'tankhah__organization', 'related_tankhah',
            'organization', 'project', 'current_stage', 'created_by', 'paid_by', 'created_by_post'
        ).prefetch_related(
            Prefetch(
                'related_factors',
                queryset=Factor.objects.select_related('tankhah').prefetch_related('items')
            )
        )

        user_orgs = UserPost.objects.filter(
            user=user, is_active=True, end_date__isnull=True
        ).values_list('post__organization__pk', flat=True)
        if not user_orgs and not user.is_superuser:
            logger.warning(f"No organizations for user {user.username}")
            return queryset.none()
        if user_orgs:
            queryset = queryset.filter(organization__pk__in=user_orgs)

        # فیلترهای جستجو
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(description__icontains=search) |
                Q(payee__name__icontains=search) |
                Q(tankhah__number__icontains=search) |
                Q(related_tankhah__number__icontains=search) |
                Q(related_factors__number__icontains=search)
            ).distinct()

        status = self.request.GET.get('status', '')
        if status in [choice[0] for choice in PaymentOrder.STATUS_CHOICES]:
            queryset = queryset.filter(status=status)

        org_id = self.request.GET.get('organization_id', '')
        if org_id:
            queryset = queryset.filter(organization__id=org_id)
        proj_id = self.request.GET.get('project_id', '')
        if proj_id:
            queryset = queryset.filter(project__id=proj_id)

        # اضافه کردن فاکتورهای تأییدشده بدون دستور پرداخت
        approved_factors = Factor.objects.filter(
            status='APPROVED',
            tankhah__organization__in=user_orgs
        ).exclude(
            id__in=PaymentOrder.objects.filter(
                related_factors__isnull=False
            ).values_list('related_factors__id', flat=True)
        ).select_related('tankhah', 'tankhah__organization', 'tankhah__project')

        # ترکیب فاکتورها و دستورات پرداخت
        queryset = queryset.order_by('-created_at')
        return queryset, approved_factors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_orders, approved_factors = self.get_queryset()
        payment_order_ct = ContentType.objects.get_for_model(PaymentOrder)

        payment_orders_with_details = []
        for po in payment_orders:
            approval_logs = ApprovalLog.objects.filter(
                content_type=payment_order_ct,
                object_id=po.id
            ).select_related('user', 'post', 'post__organization', 'stage').order_by('timestamp')

            previous_actions = [
                {
                    'post_name': log.post.name if log.post else _('نامشخص'),
                    'post_org_name': log.post.organization.name if log.post and log.post.organization else _('نامشخص'),
                    'user_name': log.user.get_full_name() or log.user.username if log.user else _('سیستم'),
                    'action': log.action,
                    'timestamp': log.timestamp,
                    'comment': log.comment or '-',
                    'stage_name': log.stage.name if log.stage else _('نامشخص'),
                }
                for log in approval_logs
            ]

            next_approvers = []
            if po.current_stage and not po.is_locked and po.status not in ['PAID', 'REJECTED', 'CANCELLED']:
                next_approvers = list(StageApprover.objects.filter(
                    stage=po.current_stage,
                    is_active=True
                ).select_related('post', 'post__organization').values(
                    'post__name', 'post__organization__name'
                ).distinct())

            tankhah_remaining = Decimal('0')
            project_remaining = Decimal('0')
            budget_message = ''
            if po.tankhah:
                tankhah_remaining = po.tankhah.budget - po.tankhah.spent
            elif po.related_tankhah:
                tankhah_remaining = po.related_tankhah.budget - po.related_tankhah.spent
            if po.project:
                project_remaining = po.project.budget - po.project.spent
            if po.status not in ['PAID', 'REJECTED', 'CANCELLED']:
                if po.amount > tankhah_remaining:
                    budget_message = _('هشدار: مبلغ از مانده تنخواه بیشتر است!')
                elif po.project and po.amount > project_remaining:
                    budget_message = _('هشدار: مبلغ از مانده پروژه بیشتر است!')

            payment_orders_with_details.append({
                'payment_order': po,
                'previous_actions': previous_actions,
                'next_possible_approvers': next_approvers,
                'tankhah_remaining_after': tankhah_remaining - po.amount if po.status not in ['PAID', 'REJECTED', 'CANCELLED'] else tankhah_remaining,
                'project_remaining_after': project_remaining - po.amount if po.status not in ['PAID', 'REJECTED', 'CANCELLED'] else project_remaining,
                'budget_message': budget_message,
                'tankhah_number': po.tankhah.number if po.tankhah else (po.related_tankhah.number if po.related_tankhah else '-'),
                'factor_numbers': ', '.join(f.number for f in po.related_factors.all()) or '-',
                'org_name': po.organization.name,
                'project_name': po.project.name if po.project else _('بدون پروژه'),
                'project_budget': po.project.budget if po.project else Decimal('0'),
                'project_spent': po.project.spent if po.project else Decimal('0'),
                'stage_name': po.current_stage.name if po.current_stage else _('نامشخص'),
                'created_by_post': po.created_by_post.name if po.created_by_post else '-',
            })

        # اضافه کردن فاکتورهای تأییدشده بدون دستور پرداخت
        approved_factors_with_details = []
        for factor in approved_factors:
            tankhah = factor.tankhah
            project = tankhah.project
            approved_factors_with_details.append({
                'factor': factor,
                'factor_number': factor.number,
                'factor_amount': factor.amount,
                'tankhah_number': tankhah.number,
                'tankhah_budget': tankhah.budget,
                'tankhah_spent': tankhah.spent,
                'project_name': project.name if project else _('بدون پروژه'),
                'project_budget': project.budget if project else Decimal('0'),
                'project_spent': project.spent if project else Decimal('0'),
                'org_name': tankhah.organization.name,
                'status': factor.get_status_display(),
            })

        grouped_by_status = {}
        for item in payment_orders_with_details:
            status = item['payment_order'].get_status_display()
            grouped_by_status.setdefault(status, []).append(item)

        context['payment_orders_data'] = payment_orders_with_details
        context['approved_factors'] = approved_factors_with_details
        context['grouped_by_status'] = grouped_by_status
        context['title'] = _('بررسی فاکتورها و دستورات پرداخت')
        context['status_choices'] = PaymentOrder.STATUS_CHOICES
        context['organizations'] = Organization.objects.filter(is_active=True).order_by('name')
        context['projects'] = Project.objects.filter(is_active=True).order_by('name')
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'organization_id': self.request.GET.get('organization_id', ''),
            'project_id': self.request.GET.get('project_id', ''),
        }

        logger.info(f"Context prepared for user {self.request.user.username}, {len(payment_orders_with_details)} payment orders, {len(approved_factors_with_details)} approved factors")
        return context
# --------------------------------------------------------------------------
class PaymentOrderListView(PermissionBaseView, ListView):
        model = PaymentOrder
        template_name = 'budgets/paymentorder/paymentorder_list.html'
        context_object_name = 'payment_orders'
        permission_required = 'PaymentOrder_view'  # اصلاح به نام مجوز مدل
        paginate_by = 10

        def get_queryset(self):
            queryset = PaymentOrder.objects.filter(
                is_active=True
            ).select_related('tankhah', 'related_tankhah', 'current_stage', 'created_by', 'created_by_post',
                             'organization', 'project', 'payee')
            query = self.request.GET.get('query', '')
            status = self.request.GET.get('status', '')
            if query:
                queryset = queryset.filter(
                    Q(order_number__icontains=query) |
                    Q(description__icontains=query) |
                    Q(payee__name__icontains=query) |
                    Q(tankhah__number__icontains=query) |
                    Q(related_tankhah__number__icontains=query)
                )
            if status:
                queryset = queryset.filter(status=status)
            logger.debug(f"PaymentOrderListView queryset: {queryset.count()} records")
            return queryset.order_by('-created_at')

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['query'] = self.request.GET.get('query', '')
            context['status'] = self.request.GET.get('status', '')
            context['status_choices'] = PaymentOrder.STATUS_CHOICES
            logger.debug(f"PaymentOrderListView context: {context}")
            return context
class PaymentOrderCreateView(PermissionBaseView, CreateView):
    model = PaymentOrder
    form_class = PaymentOrderForm
    template_name = 'budgets/paymentorder/paymentorder_form.html'
    success_url = reverse_lazy('paymentorder_list')

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
    success_url = reverse_lazy('paymentorder_list')

    def form_valid(self, form):
        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دستور پرداخت {form.instance.order_number} با موفقیت به‌روزرسانی شد.')
            return response
class PaymentOrderDeleteView(PermissionBaseView, DeleteView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_confirm_delete.html'
    success_url = reverse_lazy('paymentorder_list')

    def post(self, request, *args, **kwargs):
        payment_order = self.get_object()
        with transaction.atomic():
            payment_order.delete()
            messages.success(request, f'دستور پرداخت {payment_order.order_number} با موفقیت حذف شد.')
        return redirect(self.success_url)
# --------------------------------------------------------------------------
class PaymentOrderDetailView(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    context_object_name = 'action'
    permission_required = 'PaymentOrder_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_post = self.request.user.userpost_set.filter(is_active=True).first()
        context['user_can_sign'] = ApprovalLog.objects.filter(
            action=self.object,
            approver_post=user_post.post if user_post else None,
            is_approved=False
        ).exists()
        context['approval_logs'] = ApprovalLog.objects.filter(
            action=self.object
        ).select_related('approver_user', 'approver_post')
        return context

    def send_notifications(self, entity, action, priority, description):
        from django.contrib.contenttypes.models import ContentType
        entity_type = entity.__class__.__name__.upper()
        rules = NotificationRule.objects.filter(entity_type=entity_type, action=action, is_active=True)
        for rule in rules:
            for post in rule.recipients.all():
                users = CustomUser.objects.filter(userpost__post=post, userpost__is_active=True)
                for user in users:

                    send_notification(self.request.user, users=None, posts=None, verb=action.lower(),
                                      description=description +rule.priority, target=self.object,
                                      entity_type=None, priority='MEDIUM')
                    if rule.channel == 'EMAIL':
                        send_mail(
                            subject=description,
                            message=description,
                            from_email='system@example.com',
                            recipient_list=[user.email],
                            fail_silently=True
                        )
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'{entity_type.lower()}_updates',
                {
                    'type': f'{entity_type.lower()}_update',
                    'message': {
                        'entity_type': entity_type,
                        'id': entity.id,
                        'status': entity.status,
                        'description': description
                    }
                }
            )

    def post(self, request, *args, **kwargs):
        action = self.get_object()
        user_post = request.user.userpost_set.filter(is_active=True).first()
        if not user_post:
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('paymentorder_detail', pk=action.pk)

        approval = ApprovalLog.objects.filter(
            action=action,
            approver_post=user_post.post,
            is_approved=False
        ).first()
        if approval:
            approval.is_approved = True
            approval.approver_user = request.user
            approval.timestamp = timezone.now()
            approval.save()
            messages.success(request, _("دستور پرداخت با موفقیت امضا شد."))
            logger.info(f"User {request.user.username} signed PaymentOrder {action.order_number}")

            approved_signatures = ApprovalLog.objects.filter(action=action, is_approved=True).count()
            if approved_signatures >= action.min_signatures:
                action.status = 'APPROVED'
                action.save()
                treasury_users = CustomUser.objects.filter(
                    userpost__post__name='خزانه‌دار',
                    userpost__is_active=True
                )
                self.send_notifications(
                    entity=action,
                    action='APPROVED',
                    priority='HIGH',
                    description=f"دستور پرداخت {action.order_number} تأیید شده و آماده پرداخت است."
                )
            else:
                # اعلان به امضاکنندگان بعدی
                next_approvers = StageApprover.objects.filter(
                    stage=action.current_stage,
                    is_active=True
                ).exclude(post=user_post.post).values_list('post', flat=True)
                self.send_notifications(
                    entity=action,
                    action='NEEDS_APPROVAL',
                    priority='MEDIUM',
                    description=f"دستور پرداخت {action.order_number} نیاز به امضای شما دارد."
                )
        else:
            messages.error(request, _("شما مجاز به امضای این دستور پرداخت نیستید."))

        return redirect('paymentorder_detail', pk=action.pk)
# --------------------------------------------------------------------------

class PaymentOrderDetailView__(PermissionBaseView, DetailView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    context_object_name = 'action'
    permission_required = 'PaymentOrder_view'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_post = self.request.user.userpost_set.filter(is_active=True).first()
        context['user_can_sign'] = ApprovalLog.objects.filter(
            action=self.object,
            approver_post=user_post.post if user_post else None,
            is_approved=False
        ).exists()
        context['approval_logs'] = ApprovalLog.objects.filter(
            action=self.object
        ).select_related('approver_user', 'approver_post')
        return context

    def post(self, request, *args, **kwargs):
        action = self.get_object()
        user_post = request.user.userpost_set.filter(is_active=True).first()
        if not user_post:
            messages.error(request, "شما پست فعالی ندارید.")
            return redirect('paymentorder_detail', pk=action.pk)

        approval =  ApprovalLog.objects.filter(
            action=action,
            approver_post=user_post.post,
            is_approved=False
        ).first()
        if approval:
            approval.is_approved = True
            approval.approver_user = request.user
            approval.timestamp = timezone.now()
            approval.save()
            messages.success(request, "دستور پرداخت با موفقیت امضا شد.")
            logger.info(f"User {request.user.username} signed PaymentOrder {action.order_number}")

            # بررسی تعداد امضاها
            approved_signatures = ApprovalLog.objects.filter(action=action, is_approved=True).count()
            # approved_signatures = ActionApproval.objects.filter(action=action, is_approved=True).count()
            if approved_signatures >= action.min_signatures:
                action.status = 'APPROVED'
                action.save()
                logger.info(f"PaymentOrder {action.order_number} fully approved.")
                treasury_users = CustomUser.objects.filter(
                    userpost__post__name='خزانه‌دار',
                    userpost__is_active=True
                )
                for user in treasury_users:
                    send_notification(self.request.user, users=None, posts=None, verb='ready_for_payment',
                                      description=f"دستور پرداخت {action.order_number} تأیید شده و آماده پرداخت است.",
                                      target=self.object,
                                      entity_type=None, priority='MEDIUM')
        else:
            messages.error(request, "شما مجاز به امضای این دستور پرداخت نیستید.")

        return redirect('paymentorder_detail', pk=action.pk)
class PaymentOrderDetailView__(PermissionBaseView, DetailView):
    model = TankhahAction
    template_name = 'budgets/paymentorder/paymentorder_detail.html'
    context_object_name = 'action'
    permission_required = 'tankhah.view_paymentorder'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # user_post = self.request.user.userpost_set.filter(is_active=True).first()
        # context['user_can_sign'] = ActionApproval.objects.filter(
        #     action=self.object,
        #     approver_post=user_post.post if user_post else None,
        #     is_approved=False
        # ).exists()
        return context

    def post(self, request, *args, **kwargs):
        action = self.get_object()
        user_post = request.user.userpost_set.filter(is_active=True).first()
        if not user_post:
            messages.error(request, "شما پست فعالی ندارید.")
            return redirect('paymentorder_detail', pk=action.pk)

        # approval = ActionApproval.objects.filter(
        #     action=action,
        #     approver_post=user_post.post,
        #     is_approved=False
        # ).first()
        # if approval:
        #     approval.is_approved = True
        #     approval.approver_user = request.user
        #     approval.timestamp = timezone.now()
        #     approval.save()
        #     messages.success(request, "دستور پرداخت با موفقیت امضا شد.")
        #     logger.info(f"User {request.user.username} signed TankhahAction {action.id}")
        #
        #     # بررسی آیا همه امضاها انجام شده
        #     if not ActionApproval.objects.filter(action=action, is_approved=False).exists():
        #         action.tankhah.status = 'APPROVED'
        #         action.tankhah.save()
        #         logger.info(f"Tankhah {action.tankhah.number} fully approved and ready for payment.")
        #         # اینجا می‌تونی نوتیفیکیشن به خزانه‌دار بفرستی
        # else:
        #     messages.error(request, "شما مجاز به امضای این دستور پرداخت نیستید.")

        return redirect('paymentorder_detail', pk=action.pk)
class PaymentOrderListView___(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_list.html'
    context_object_name = 'payment_orders'
    paginate_by = 10

#-------
# --- PaymentOrder CRUD ---