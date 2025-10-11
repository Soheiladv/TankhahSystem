from django.forms import inlineformset_factory
from django.urls import reverse_lazy, reverse
from django.views.generic import   UpdateView
from accounts.models import CustomUser
from budgets.models import PaymentOrder
from core.models import   Status, Post, Status
from notificationApp.utils import send_notification
from tankhah.Factor.Approved.from_Approved import FactorItemApprovalForm, FactorApprovalForm
from tankhah.constants import ACTION_TYPES
from tankhah.models import Factor, FactorItem, ApprovalLog
from tankhah.Factor.Approved.fun_can_edit_approval import can_edit_approval
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from tankhah.views import PermissionBaseView

import logging
logger = logging.getLogger('factor_approval')

# تنظیم لاگ‌گیری با فایل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    filename='logs/factor_item_approve.log',
    filemode='a'
)

"""  ویو برای تأیید فاکتور"""
class FactorApproveView(PermissionBaseView, UpdateView):
        model = Factor
        form_class = FactorApprovalForm  # فرض بر وجود این فرم
        template_name = 'tankhah/factor_approval.html'
        success_url = reverse_lazy('factor_list')
        permission_codename = ['tankhah.factor_view', 'tankhah.factor_update']

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
            context['items'] = self.object.items.all()
            return context

        def form_valid(self, form):
            factor = self.object
            tankhah = factor.tankhah
            user_posts = self.request.user.userpost_set.all()

            if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
                messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
                return self.form_invalid(form)

            with transaction.atomic():
                self.object = form.save()
                all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
                if all_items_approved:
                    factor.status = 'APPROVED'
                    factor.approved_by.add(self.request.user)
                    factor.locked_by_stage = tankhah.current_stage  # قفل برای مراحل بالاتر
                    factor.save()

                    all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                    if all_factors_approved:
                        next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by(
                            '-order').first()
                        if next_stage:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah.save()
                            approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                            if approvers.exists():
                                # notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است',
                                #             target=tankhah)
                                messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                        else:
                            tankhah.status = 'COMPLETED'
                            tankhah.save()
                            messages.success(self.request, _('تنخواه تکمیل شد.'))
                    else:
                        messages.success(self.request, _('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
                else:
                    messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

            return super().form_valid(form)
#  *******************************************************************************************************************
"""تأیید آیتم‌های فاکتور"""
# 💡 اصلاح: FactorItemApprovalFormSet اکنون تنها از فیلدهای status, description استفاده می‌کند
# FactorItemApprovalFormSet = inlineformset_factory(
#     Factor,
#     FactorItem,
#     form=FactorItemApprovalForm,
#     # fields=('status', 'description', 'comment'), # 💡 اضافه کردن comment اگر در فرم هم هست
#     fields=('status', 'comment', 'is_temporary'),  # هم‌راستا با فرم
#     extra=0,
#     can_delete=False
# )

# FormSet به صورت تمیز در سطح ماژول تعریف می‌شود
FactorItemApprovalFormSet = inlineformset_factory(
    Factor, FactorItem, form=FactorItemApprovalForm,
    extra=0, can_delete=False, fields=('status',)
)
ACTIONS_WITHOUT_STAGE = ('VIEW', 'EDIT', 'CREATE', 'DELETE', 'SIGN_PAYMENT')


class FactorItemApproveView(PermissionBaseView, DetailView):
    """
    این ویو، مرکز کنترل اصلی برای مشاهده، تأیید، یا رد ردیف‌های یک فاکتور است.
    تمام منطق‌های گردش کار، دسترسی‌ها و اقدامات کاربر در این کلاس مدیریت می‌شود.
    """
    model = Factor
    template_name = 'tankhah/Approved/factor_item_approve_final.html'
    context_object_name = 'factor'
    permission_codename = ['tankhah.factor_approve']  # پرمیشن کلی برای ورود به این صفحه

    def get_object(self, queryset=None):
        """
        واکشی شیء فاکتور به همراه بهینه‌سازی کوئری‌ها برای جلوگیری از N+1 queries.
        """
        return get_object_or_404(
            self.model.objects.select_related(
                'tankhah__organization', 'created_by'
            ).prefetch_related(
                'items'
            ),
            pk=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        """
        نسخه نهایی و بهینه get_context_data که بهترین ویژگی‌های هر دو نسخه را ترکیب می‌کند.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        current_stage = factor.tankhah.current_stage

        # --- مرحله ۱: بررسی‌های اولیه ---
        if not current_stage:
            messages.error(self.request, _("گردش کار به درستی تعریف نشده است."))
            context.update({'can_edit': False, 'formset': None});
            return context

        # --- مرحله ۲: استخراج دسترسی‌ها و اقدامات مجاز ---

        # پیش‌فرض‌ها
        allowed_actions = []
        can_edit = False
        user_posts_qs = user.userpost_set.filter(is_active=True).select_related('post', 'post__branch')

        # سناریوی ۱: کاربر سوپریوزر است
        if user.is_superuser:
            can_edit = True
            # به سوپریوزر تمام اقدامات ممکن در گردش کار را می‌دهیم
            allowed_actions = [code for code, label in ACTION_TYPES if code not in ACTIONS_WITHOUT_STAGE]
            messages.info(self.request, _("شما به عنوان سوپریوزر دسترسی کامل برای اقدام دارید."))

        # سناریوی ۲: کاربر عادی با پست فعال
        elif user_posts_qs.exists():
            # ابتدا با تابع جامع can_edit_approval چک می‌کنیم که آیا کاربر اصلاً اجازه اقدام دارد یا خیر.
            # این تابع مواردی مانند قفل بودن، اقدام تکراری و ... را بررسی می‌کند.
            can_edit = can_edit_approval(user, factor.tankhah, current_stage, factor)

            # اگر اجازه کلی وجود داشت، حالا لیست دقیق اقدامات را استخراج می‌کنیم.
            if can_edit:
                user_post_ids = list(user_posts_qs.values_list('post_id', flat=True))
                max_user_level = user_posts_qs.aggregate(max_level=Max('post__level'))['max_level'] or 0

                base_query = Q(organization=factor.tankhah.organization, stage_order=current_stage.stage_order,
                               entity_type='FACTORITEM', is_active=True)
                specific_rule = Q(post_id__in=user_post_ids)
                generic_rule = Q(post__isnull=True, min_level__lte=max_user_level)

                branch_conditions = Q()
                for up in user_posts_qs:
                    branch_conditions |= Q(branch=up.post.branch) if up.post.branch else Q(branch__isnull=True)
                generic_rule.add(branch_conditions, Q.AND)

                applicable_rules = AccessRule.objects.filter(base_query & (specific_rule | generic_rule))
                allowed_actions = list(applicable_rules.values_list('action_type', flat=True).distinct())

                # یک بررسی نهایی: ممکن است can_edit_approval به دلیل موانع گردش کار False باشد،
                # اما allowed_actions مقداری پیدا کند. در این حالت، can_edit باید False باقی بماند.
                if not allowed_actions:
                    can_edit = False

        # سناریوی ۳: کاربر عادی بدون پست فعال
        else:
            messages.error(self.request, _("پست فعال برای کاربر یافت نشد."))
            can_edit = False

        if not can_edit and self.request.method == 'GET':
            messages.warning(self.request, _("شما دسترسی لازم برای اقدام در این مرحله را ندارید."))

        # --- مرحله ۳: ساخت فرم‌ست و آماده‌سازی نهایی کانتکست ---
        form_kwargs = {'user': user, 'allowed_actions': allowed_actions}
        formset = FactorItemApprovalFormSet(self.request.POST or None, instance=factor, prefix='items',
                                            form_kwargs=form_kwargs)

        context.update({
            'current_stage': current_stage,
            'formset': formset,
            'can_edit': can_edit,
            'allowed_actions': allowed_actions,
            'bulk_action_enabled': any(a in allowed_actions for a in ['APPROVE', 'REJECT']),
            'approval_history': ApprovalLog.objects.filter(factor=factor).select_related('user', 'post').order_by(
                '-timestamp'),
            'pending_users': self._get_pending_users(factor, current_stage),
            'future_approvers_by_stage': self._get_future_approvers(factor, current_stage),
        })
        return context

    def post(self, request, *args, **kwargs):
        """
        پردازش درخواست POST. این متد مسئول اعتبارسنجی، پردازش اقدامات
        (تکی و گروهی) و پیشبرد گردش کار است.
        """
        self.object = self.get_object()
        context = self.get_context_data()
        formset = context.get('formset')

        if not context.get('can_edit') or not formset:
            messages.error(request, _('شما دسترسی لازم برای ثبت اقدام را ندارید.'))
            return redirect(self.get_success_url())

        # بخش اقدام گروهی را اینجا پردازش می‌کنیم
        post_data = request.POST.copy()
        if 'bulk_status' in post_data and post_data.get('bulk_status'):
            allowed_actions = context.get('allowed_actions', [])
            self._handle_bulk_actions(post_data, self.object, allowed_actions)
            # پس از اعمال مقادیر گروهی، فرم‌ست را با داده‌های جدید می‌سازیم
            formset = FactorItemApprovalFormSet(post_data, instance=self.object, prefix='items',
                                                form_kwargs=context['formset'].form_kwargs)

        if formset.is_valid():
            try:
                with transaction.atomic():
                    action_taken = self._process_formset_actions(formset)
                    if action_taken:
                        self._check_workflow_advancement(self.object, context['current_stage'])
                    else:
                        messages.warning(request, _('هیچ تغییری برای ثبت وجود نداشت.'))
            except Exception as e:
                logger.error(f"Error during POST processing for factor {self.object.pk}: {e}", exc_info=True)
                messages.error(request, _('خطایی در حین پردازش رخ داد. لطفاً دوباره تلاش کنید.'))
            return redirect(self.get_success_url())
        else:
            messages.error(request, _('اطلاعات ارسالی نامعتبر است. لطفاً خطاها را بررسی کنید.'))
            context['formset'] = formset
            return self.render_to_response(context)

    def get_success_url(self):
        """پس از هر اقدام موفق، کاربر به همین صفحه بازگردانده می‌شود."""
        return reverse('factor_item_approve', kwargs={'pk': self.object.pk})

    # --------------------------------------------------------------------------
    # بخش متدهای کمکی (Helper Methods)
    # --------------------------------------------------------------------------

    def _handle_bulk_actions(self, post_data, factor, allowed_actions):
        """
        مقادیر انتخاب شده در فرم اقدام گروهی را به تمام فرم‌های ردیف‌ها اعمال می‌کند.
        """
        bulk_status = post_data.get('bulk_status')
        if not bulk_status or bulk_status not in allowed_actions:
            messages.error(self.request, _('اقدام گروهی انتخاب‌شده غیرمجاز است.'))
            return

        bulk_comment = post_data.get('bulk_comment', '').strip()
        bulk_is_temporary = post_data.get('bulk_is_temporary') == 'on'

        total_forms = int(post_data.get('items-TOTAL_FORMS', 0))
        for i in range(total_forms):
            prefix = f'items-{i}-'
            item_id = post_data.get(prefix + 'id')
            if not item_id: continue

            post_data[prefix + 'status'] = bulk_status
            if bulk_comment:
                post_data[prefix + 'comment'] = bulk_comment
            post_data[prefix + 'is_temporary'] = 'on' if bulk_is_temporary else ''
            post_data[prefix + 'is_bulk_action'] = 'on'

    def _get_pending_users(self, factor, current_stage):
        """
        کاربرانی که در مرحله فعلی هنوز اقدامی ثبت نکرده‌اند را پیدا می‌کند.
        """
        required_posts = set(AccessRule.objects.filter(
            organization=factor.tankhah.organization, stage_order=current_stage.stage_order, entity_type='FACTORITEM'
        ).values_list('post_id', flat=True))

        acted_posts = set(ApprovalLog.objects.filter(
            factor=factor, stage=current_stage
        ).values_list('post_id', flat=True))

        pending_post_ids = required_posts - acted_posts
        return CustomUser.objects.filter(userpost__post_id__in=pending_post_ids, userpost__is_active=True).distinct()

    def _get_future_approvers(self, factor, current_stage):
        """
        لیستی از مراحل بعدی و تأییدکنندگان آن‌ها را برای نمایش در تمپلیت آماده می‌کند.
        """
        future_approvers = []
        future_rules = AccessRule.objects.filter(
            organization=factor.tankhah.organization, entity_type='FACTORITEM',
            stage_order__gt=current_stage.stage_order
        ).order_by('stage_order').values('stage_order', 'stage', 'post_id').distinct()

        stages = {}
        for rule in future_rules:
            if rule['stage_order'] not in stages:
                stages[rule['stage_order']] = {'name': rule['stage'], 'posts': set()}
            stages[rule['stage_order']]['posts'].add(rule['post_id'])

        for order, data in stages.items():
            users = CustomUser.objects.filter(userpost__post_id__in=data['posts'], userpost__is_active=True).distinct()
            if users:
                future_approvers.append({'stage_order': order, 'stage_name': data['name'], 'approvers': users})
        return future_approvers

    def _process_formset_actions(self, formset):
        """
        روی فرم‌های معتبر حلقه زده و اقدامات کاربر را در ApprovalLog ثبت می‌کند.
        """
        action_taken = False
        user = self.request.user
        user_post = user.userpost_set.filter(is_active=True).first().post
        factor = self.object
        current_stage = factor.tankhah.current_stage # این یک شیء کامل AccessRule است

        for form in formset:
            if not form.has_changed() or not form.cleaned_data.get('status'):
                continue

            item = form.instance
            status = form.cleaned_data['status']
            comment = form.cleaned_data['comment']
            is_temporary = form.cleaned_data['is_temporary']

            logger.debug(f"--- Creating/Updating Log for item {item.pk} with action '{status}' in stage '{current_stage.stage}' ---")

            log_entry, created = ApprovalLog.objects.update_or_create(
                factor_item=item,
                post=user_post,
                stage_rule=current_stage, # <--- **اصلاح اصلی و حیاتی**
                defaults={
                    'factor': factor,
                    'user': user,
                    'action': status,
                    'comment': comment,
                    'is_temporary': is_temporary,
                }
            )
            log_status = "created" if created else "updated"
            logger.info(
                f"ApprovalLog {log_status} for item {item.pk}. PK: {log_entry.pk}, Stage Rule PK: {log_entry.stage_rule.pk}")

            if not is_temporary:
                item.status = status
                item.save(update_fields=['status'])

            action_taken = True
        return action_taken

    def _check_workflow_advancement(self, factor, current_stage):
        """
        بررسی می‌کند که آیا گردش کار باید به مرحله بعد برود، رد شود یا منتظر بماند.
        """
        if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, action='REJECT', is_temporary=False).exists():
            self._reject_factor(factor)
            return

        required_post_ids = set(AccessRule.objects.filter(
            organization=factor.tankhah.organization, stage_order=current_stage.stage_order, entity_type='FACTORITEM'
        ).values_list('post_id', flat=True))

        # اگر در این مرحله هیچ تأییدکننده‌ای تعریف نشده باشد، به صورت خودکار به مرحله بعد برو
        if not required_post_ids:
            self._advance_factor_stage(factor, current_stage)
            return

        final_acted_posts = ApprovalLog.objects.filter(
            factor=factor, stage=current_stage, is_temporary=False
        ).values('post_id').annotate(item_count=Count('factor_item_id', distinct=True))

        fully_approved_post_ids = {p['post_id'] for p in final_acted_posts if p['item_count'] == factor.items.count()}

        if required_post_ids.issubset(fully_approved_post_ids):
            self._advance_factor_stage(factor, current_stage)
        else:
            messages.info(self.request, _("اقدام شما ثبت شد. در انتظار تأیید سایر کاربران در این مرحله."))

    def _advance_factor_stage(self, factor, current_stage):
        """
        فاکتور را به مرحله بعدی گردش کار منتقل می‌کند.
        """
        next_stage_rule = AccessRule.objects.filter(
            organization=factor.tankhah.organization, entity_type='FACTORITEM',
            stage_order__gt=current_stage.stage_order
        ).order_by('stage_order').first()

        if next_stage_rule:
            factor.tankhah.current_stage = next_stage_rule
            factor.tankhah.save()
            factor.items.update(status='PENDING_APPROVAL')

            ApprovalLog.objects.create(
                factor=factor, user=self.request.user, action='STAGE_CHANGE',
                stage=next_stage_rule, comment=f"فاکتور به مرحله '{next_stage_rule.stage}' ارسال شد."
            )
            messages.success(self.request, _(f"فاکتور با موفقیت به مرحله '{next_stage_rule.stage}' ارسال شد."))

            next_stage_posts = AccessRule.objects.filter(
                organization=factor.tankhah.organization,
                stage_order=next_stage_rule.stage_order,
                entity_type='FACTORITEM'
            ).values_list('post_id', flat=True).distinct()

            send_notification(
                sender=self.request.user, posts=Post.objects.filter(id__in=next_stage_posts),
                verb=_("برای تأیید ارسال شد"), target=factor,
                description=_(
                    f"فاکتور #{factor.number} برای تأیید در مرحله '{next_stage_rule.stage}' برای شما ارسال شد."),
                entity_type='FACTOR'
            )
        else:
            factor.status = 'APPROVED_FINAL'
            factor.is_locked = True
            factor.save(update_fields=['status', 'is_locked'])

            ApprovalLog.objects.create(
                factor=factor, user=self.request.user, action='APPROVED_FINAL',
                stage=current_stage, comment="فرآیند تأیید فاکتور تکمیل و نهایی شد."
            )
            messages.success(self.request, _("فاکتور به صورت نهایی تأیید شد."))
            self._create_payment_order(factor)

    def _reject_factor(self, factor):
        """
        فاکتور را به صورت نهایی رد کرده و به مرحله اولیه بازمی‌گرداند.
        """
        initial_stage_rule = AccessRule.objects.filter(
            organization=factor.tankhah.organization,
            entity_type='FACTORITEM'
        ).order_by('stage_order').first()

        factor.status = 'REJECT'
        factor.is_locked = True
        factor.save(update_fields=['status', 'is_locked'])

        if initial_stage_rule:
            factor.tankhah.current_stage = initial_stage_rule
            factor.tankhah.save()
            factor.items.update(status='PENDING')
            rejection_comment = _(f"فاکتور رد شد و به مرحله اولیه '{initial_stage_rule.stage}' بازگشت.")
            stage_for_log = initial_stage_rule
        else:
            rejection_comment = _("فاکتور رد شد.")
            stage_for_log = factor.tankhah.current_stage

        ApprovalLog.objects.create(
            factor=factor, user=self.request.user, action='REJECTED_FINAL',
            stage=stage_for_log, comment=rejection_comment
        )
        messages.error(self.request, rejection_comment)

        send_notification(
            sender=self.request.user, users=[factor.created_by], verb=_("رد شد"),
            target=factor, description=_(f"فاکتور #{factor.number} شما رد شد و به مرحله اولیه بازگشت."),
            entity_type='FACTOR'
        )

    def _create_payment_order(self, factor):
        """
        پس از تأیید نهایی، یک دستور پرداخت ایجاد می‌کند.
        """
        po_initial_stage = AccessRule.objects.filter(
            organization=factor.tankhah.organization,
            entity_type='PAYMENT_ORDER'
        ).order_by('stage_order').first()

        if not po_initial_stage:
            messages.warning(self.request, _("گردش کاری برای 'دستور پرداخت' تعریف نشده است. دستور پرداخت ایجاد نشد."))
            logger.warning(
                f"No initial stage for PAYMENT_ORDER in org {factor.tankhah.organization.pk}. PO not created.")
            return

        try:
            payment_order, created = PaymentOrder.objects.get_or_create(
                tankhah=factor.tankhah, related_factors=factor,
                defaults={
                    'amount': factor.amount,
                    'description': _(f"پرداخت خودکار برای فاکتور #{factor.number}"),
                    'organization': factor.tankhah.organization,
                    'project': factor.tankhah.project,
                    'status': 'PENDING_APPROVAL',
                    'created_by': self.request.user,
                    'payee': factor.created_by,
                    'current_stage': po_initial_stage,
                }
            )

            if created:
                messages.success(self.request, _(f"دستور پرداخت برای این فاکتور با موفقیت ایجاد شد."))
                po_approver_posts = AccessRule.objects.filter(
                    organization=factor.tankhah.organization, entity_type='PAYMENT_ORDER',
                    stage_order=po_initial_stage.stage_order
                ).values_list('post_id', flat=True).distinct()

                send_notification(
                    sender=self.request.user, posts=Post.objects.filter(id__in=po_approver_posts),
                    verb=_("برای تأیید ارسال شد"), target=payment_order,
                    description=_(f"دستور پرداخت برای فاکتور #{factor.number} برای تأیید شما ارسال شد."),
                    entity_type='PAYMENT_ORDER'
                )
            else:
                messages.info(self.request, _("دستور پرداخت برای این فاکتور قبلاً ایجاد شده است."))

        except Exception as e:
            logger.error(f"Failed to create PaymentOrder for factor {factor.pk}: {e}", exc_info=True)
            messages.error(self.request, _("خطایی در هنگام ایجاد دستور پرداخت رخ داد."))