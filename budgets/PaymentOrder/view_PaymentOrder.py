import logging
from decimal import Decimal
from time import timezone

from django.contrib import messages
from django.db import transaction

from accounts.models import CustomUser
from budgets.PaymentOrder.form_PaymentOrder import PaymentOrderForm
from budgets.models import PaymentOrder, generate_payment_order_number, Payee
from core.models import Organization, Project, UserPost, WorkflowStage
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
class TankhahUpdateStatusView__(UpdateView): # باید از PermissionBaseView هم ارث‌بری کند اگر نیاز به چک مجوز دارد
    model = Tankhah
    fields = ['status', 'current_stage'] # فیلدهایی که در فرم تغییر وضعیت تنخواه نمایش داده می‌شوند
    template_name = 'budgets/paymentorder/tankhah_update_status.html' # یک تمپلیت برای فرم تغییر وضعیت تنخواه
    # success_url = reverse_lazy('tankhah:tankhah_list') # یا هر URL دیگری

    def get_success_url(self):
        # بعد از موفقیت، به جزئیات همان تنخواه برگردد یا به لیست تنخواه
        return reverse_lazy('tankhah:tankhah_detail', kwargs={'pk': self.object.pk})


    def form_valid(self, form):
        user = self.request.user
        try:
            with transaction.atomic():
                tankhah = form.save(commit=False) # هنوز در دیتابیس ذخیره نکن

                # اگر created_by در تنخواه ندارید یا می‌خواهید ثبت کننده تغییر وضعیت را نگه دارید:
                # tankhah.last_modified_by = user # یک فیلد فرضی

                tankhah.save() # حالا ذخیره کن
                logger.info(f"Tankhah {tankhah.number} status updated to {tankhah.status} and stage to {tankhah.current_stage.name if tankhah.current_stage else 'None'} by user {user.username}")


                # بررسی شرایط ایجاد خودکار دستور پرداخت
                if tankhah.current_stage and \
                   hasattr(tankhah.current_stage, 'triggers_payment_order') and \
                   tankhah.current_stage.triggers_payment_order and \
                   tankhah.status == 'APPROVED': # یا هر وضعیت دیگری که برای شما منطقی است

                    logger.info(f"Conditions met to auto-create PaymentOrder for Tankhah {tankhah.number}.")

                    # --- منطق تعیین Payee ---
                    # این بخش بسیار مهم است و باید با توجه به ساختار شما پیاده‌سازی شود
                    target_payee = None
                    if hasattr(tankhah, 'payee_beneficiary') and tankhah.payee_beneficiary: # اگر تنخواه مستقیما ذینفع دارد
                        target_payee = tankhah.payee_beneficiary
                    elif tankhah.related_factors.filter(payee__isnull=False).exists(): # اگر فاکتورهای مرتبط payee دارند
                        # اگر همه فاکتورها یک payee دارند، آن را انتخاب کن
                        # در غیر این صورت، یا اولین payee را انتخاب کن یا اجازه ایجاد نده/به کاربر اطلاع بده
                        distinct_payees = tankhah.related_factors.filter(payee__isnull=False).values_list('payee', flat=True).distinct()
                        if len(distinct_payees) == 1:
                            target_payee = Payee.objects.get(pk=distinct_payees[0])
                        else:
                            logger.warning(f"Tankhah {tankhah.number} has factors with multiple or no payees. Cannot auto-determine payee for PaymentOrder.")
                            messages.warning(self.request, _("امکان تعیین خودکار دریافت‌کننده برای دستور پرداخت تنخواه {num} وجود ندارد. لطفاً به صورت دستی ایجاد کنید.").format(num=tankhah.number))
                            # return super().form_valid(form) # ادامه بدون ایجاد PO
                    else:
                        # یک Payee پیش‌فرض یا عمومی اگر هیچ اطلاعاتی نیست (مثلا خود سازمان/فرد تنخواه‌گیر)
                        # این هم باید با منطق شما سازگار باشد
                        # target_payee = Payee.objects.filter(is_default_for_tankhah_settlement=True).first()
                        logger.warning(f"No specific payee found for Tankhah {tankhah.number}. Attempting to use a default or skipping PaymentOrder creation.")
                        # می‌توانید اینجا یک پیام به کاربر بدهید یا اجازه ایجاد ندهید

                    if target_payee:
                        logger.info(f"Target Payee for PaymentOrder: {target_payee}")

                        # یافتن مرحله اولیه گردش کار دستور پرداخت
                        # **مهم:** مطمئن شوید مدل WorkflowStage فیلد entity_type را دارد
                        # و مقداری برای 'PAYMENTORDER' برای آن تعریف کرده‌اید.
                        initial_po_stage = None
                        if hasattr(WorkflowStage, 'entity_type'):
                             initial_po_stage = WorkflowStage.objects.filter(entity_type='PAYMENTORDER', order=1, is_active=True).first()

                        if not initial_po_stage:
                             logger.error("Could not find initial workflow stage for PAYMENTORDER (entity_type='PAYMENTORDER', order=1). PaymentOrder will not be created.")
                             messages.error(self.request, _("خطا: مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
                        else:
                            logger.info(f"Initial stage for new PaymentOrder: {initial_po_stage.name}")
                            # ایجاد دستور پرداخت
                            # تابع generate_payment_order_number باید خارج از مدل PaymentOrder باشد
                            # یا از متد generate_payment_order_number خود نمونه PaymentOrder در save استفاده شود.
                            # برای سادگی، فرض می‌کنیم در save مدل هندل می‌شود اگر order_number خالی باشد.

                            payment_order_instance = PaymentOrder(
                                payee=target_payee,
                                amount=tankhah.amount_to_be_paid, # یا tankhah.amount یا هر فیلد مناسب دیگری
                                description=f"پرداخت/تسویه برای تنخواه شماره {tankhah.number}",
                                related_tankhah=tankhah,
                                organization=tankhah.organization, # سازمان از تنخواه گرفته می‌شود
                                project=tankhah.project, # پروژه از تنخواه گرفته می‌شود
                                status='DRAFT', # یا مرحله اولیه گردش کار
                                created_by=user, # کاربری که باعث این اقدام شده
                                current_stage=initial_po_stage,
                                issue_date=timezone.now().date() # تاریخ صدور امروز
                                # order_number به صورت خودکار در save مدل پر می‌شود
                            )
                            payment_order_instance.save() # این save متد generate_payment_order_number مدل را (اگر در save هست) فراخوانی می‌کند
                                                        # و همچنین payee_account_number و iban را از payee پر می‌کند.

                            if payment_order_instance and payment_order_instance.current_stage:
                                logger.info(
                                    f"PaymentOrder {payment_order_instance.order_number} created and is in stage: {payment_order_instance.current_stage.name}")
                            eligible_users_for_po_action = set()  # استفاده از set برای جلوگیری از ارسال نوتیفیکیشن تکراری به یک کاربر
                            # یافتن پست‌های مجاز برای مرحله فعلی دستور پرداخت
                            # **مهم:** مطمئن شوید مدل StageApprover فیلد entity_type دارد.
                            required_entity_type = 'PAYMENTORDER'  # یا هر مقداری که برای دستور پرداخت در نظر گرفته‌اید

                            approving_posts_query = []
                            if hasattr(StageApprover, 'entity_type'):
                                approving_posts_query = StageApprover.objects.filter(
                                    stage=payment_order_instance.current_stage,
                                    entity_type__iexact=required_entity_type,  # برای case-insensitive
                                    is_active=True
                                ).select_related('post')
                            else:
                                # اگر StageApprover فیلد entity_type ندارد، ممکن است نیاز به منطق دیگری باشد
                                # یا فرض کنید تمام StageApprover های این مرحله برای همه انواع موجودیت‌ها هستند (که ایده‌آل نیست)
                                logger.warning(
                                    f"StageApprover model does not seem to have 'entity_type' field. Notification logic might be inaccurate.")
                                approving_posts_query = StageApprover.objects.filter(
                                    stage=payment_order_instance.current_stage,
                                    is_active=True
                                ).select_related('post')

                            if not approving_posts_query.exists():
                                logger.warning(
                                    f"No active StageApprovers found for stage '{payment_order_instance.current_stage.name}' and entity_type '{required_entity_type}'. Cannot determine recipients for notification.")
                            else:
                                for stage_approver in approving_posts_query:
                                    if stage_approver.post:
                                        # یافتن تمام کاربران فعال منتسب به آن پست
                                        users_in_post = UserPost.objects.filter(
                                            post=stage_approver.post,
                                            is_active=True,
                                            end_date__isnull=True  # کاربر هنوز در این پست فعال است
                                        ).select_related('user')

                                        for user_post_entry in users_in_post:
                                            eligible_users_for_po_action.add(user_post_entry.user)
                                    else:
                                        logger.warning(
                                            f"StageApprover (PK: {stage_approver.pk}) for stage '{payment_order_instance.current_stage.name}' has no associated post.")

                            if eligible_users_for_po_action:
                                logger.info(
                                    f"Found {len(eligible_users_for_po_action)} eligible users for action on PaymentOrder {payment_order_instance.order_number}: {[u.username for u in eligible_users_for_po_action]}")
                                from notifications.signals import \
                                    notify  # یا روش import مناسب برای سیستم نوتیفیکیشن شما

                                for user_to_notify in eligible_users_for_po_action:
                                    if user_to_notify == user:  # به خود ایجاد کننده که همین الان اقدام کرده، نوتیف نده (اگر منطقی است)
                                        # continue # این خط را اگر نمی‌خواهید به ایجاد کننده نوتیف بدهید فعال کنید
                                        pass

                                    try:
                                        notify.send(
                                            sender=user,  # کاربری که باعث ایجاد دستور پرداخت شد (یا یک کاربر سیستمی)
                                            recipient=user_to_notify,
                                            verb=_('دستور پرداخت جدید منتظر اقدام شماست'),
                                            action_object=payment_order_instance,  # خود دستور پرداخت
                                            target=tankhah,  # تنخواهی که باعث ایجاد این دستور پرداخت شد (اختیاری)
                                            description=_(
                                                'دستور پرداخت شماره {po_num} برای تنخواه {tk_num} ایجاد شده و نیاز به بررسی/امضای شما در مرحله "{stage}" دارد.').format(
                                                po_num=payment_order_instance.order_number,
                                                tk_num=tankhah.number,
                                                stage=payment_order_instance.current_stage.name
                                            ),
                                            # level='info', # یا هر سطح دیگری که در سیستم نوتیفیکیشن شما تعریف شده
                                        )
                                        logger.info(
                                            f"Notification sent to {user_to_notify.username} for PaymentOrder {payment_order_instance.order_number}")
                                    except Exception as e:
                                        logger.error(
                                            f"Failed to send notification to {user_to_notify.username} for PaymentOrder {payment_order_instance.order_number}: {e}",
                                            exc_info=True)
                            else:
                                logger.warning(
                                    f"No eligible users found to notify for PaymentOrder {payment_order_instance.order_number} in stage {payment_order_instance.current_stage.name}.")

                            # اگر فاکتورهایی به تنخواه لینک هستند، آنها را به دستور پرداخت هم لینک کنید
                            if tankhah.related_factors.exists(): # فرض related_name='related_factors' برای Factor->Tankhah
                                payment_order_instance.related_factors.set(tankhah.related_factors.all())

                            logger.info(f"PaymentOrder {payment_order_instance.order_number} created successfully for Tankhah {tankhah.number}.")
                            messages.success(self.request, _("دستور پرداخت {po_num} برای تنخواه {tk_num} به صورت خودکار ایجاد شد.").format(po_num=payment_order_instance.order_number, tk_num=tankhah.number))

                            # اینجا می‌توانید نوتیفیکیشن ارسال کنید
                            # notify.send(...)
                    else:
                        logger.warning(f"PaymentOrder NOT created for Tankhah {tankhah.number} due to missing payee.")
                        messages.info(self.request, _("دستور پرداخت برای تنخواه {num} به دلیل عدم تعیین دریافت‌کننده ایجاد نشد.").format(num=tankhah.number))

        except Exception as e:
            logger.error(f"Error in TankhahUpdateStatusView form_valid for tankhah {self.object.pk if self.object else 'None'}: {e}", exc_info=True)
            messages.error(self.request, _("خطایی در پردازش به‌روزرسانی تنخواه رخ داد."))
            # اگر خطا رخ داد، بسته به نوع خطا، ممکن است بخواهید فرم را دوباره نمایش دهید یا به صفحه خطا هدایت کنید
            return self.form_invalid(form) # یا یک HttpResponseServerError

        return super().form_valid(form)

    def get_form_kwargs(self):
        """Pass the user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
class TankhahUpdateStatusView(PermissionBaseView, UpdateView):
    model = Tankhah
    fields = ['status', 'current_stage']
    template_name = 'tankhah/tankhah_update_status.html'
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
                            from notifications.signals import notify
                            notify.send(
                                sender=user,
                                recipient=user_to_notify,
                                verb='needs_approval',
                                action_object=payment_order,
                                target=tankhah,
                                description=f"دستور پرداخت {payment_order.order_number} نیاز به امضای شما دارد."
                            )

                    logger.info(f"PaymentOrder {payment_order.order_number} created for Tankhah {tankhah.number}")
                    messages.success(self.request, f"دستور پرداخت {payment_order.order_number} ایجاد شد.")

        except Exception as e:
            logger.error(f"Error in TankhahUpdateStatusView: {e}", exc_info=True)
            messages.error(self.request, "خطایی در به‌روزرسانی تنخواه رخ داد.")
            return self.form_invalid(form)

        return super().form_valid(form)

from django.contrib.contenttypes.models import ContentType
class PaymentOrderReviewView(PermissionBaseView, ListView):
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

#-------
# --- PaymentOrder CRUD ---
class PaymentOrderListView___(PermissionBaseView, ListView):
    model = PaymentOrder
    template_name = 'budgets/paymentorder/paymentorder_list.html'
    context_object_name = 'payment_orders'
    paginate_by = 10
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
                    from notifications.signals import notify
                    notify.send(
                        sender=request.user,
                        recipient=user,
                        verb='ready_for_payment',
                        action_object=action,
                        description=f"دستور پرداخت {action.order_number} تأیید شده و آماده پرداخت است."
                    )
        else:
            messages.error(request, "شما مجاز به امضای این دستور پرداخت نیستید.")

        return redirect('paymentorder_detail', pk=action.pk)

