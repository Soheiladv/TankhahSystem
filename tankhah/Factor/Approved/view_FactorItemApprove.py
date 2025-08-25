#
# فایل: tankhah/Factor/Approved/view_FactorItemApprove.py (نسخه کامل، نهایی و مستند)
#
import logging
from django.forms import inlineformset_factory
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q, Max
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, UpdateView
from django.utils.translation import gettext_lazy as _

# --- Import های پروژه ---
# مدل‌ها
from tankhah.models import Factor, FactorItem, ApprovalLog
from core.models import AccessRule, Post, Transition, Action
from accounts.models import CustomUser
from budgets.models import PaymentOrder
# فرم‌ها
from .from_Approved import FactorItemApprovalForm, FactorApprovalForm
# توابع کمکی
from core.PermissionBase import PermissionBaseView # تابع دسترسی جدید و متمرکز ما
from notificationApp.utils import send_notification
from tankhah.Factor.Approved.fun_can_edit_approval import check_approval_permissions
# ثابت‌ها
from tankhah.constants import ACTION_TYPES, ACTIONS_WITHOUT_STAGE

from django.utils.translation import gettext_lazy as _

import logging
from django.forms import modelformset_factory
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

# --- Import های پروژه ---
# مدل‌های اصلی برنامه
from tankhah.models import Factor, FactorItem, ApprovalLog
# مدل‌های جدید گردش کار
from core.models import Post, Transition, Action, Status, CustomUser
# فرم و توابع کمکی
from .from_Approved import FactorItemApprovalForm
from notificationApp.utils import send_notification
from core.PermissionBase import PermissionBaseView
# --- تنظیمات اولیه ---
logger = logging.getLogger('FactorItemApproveViewLogger')  # لاگر مشخص برای این ویو

# تعریف فرم‌ست در سطح ماژول برای خوانایی
FactorItemApprovalFormSet = inlineformset_factory(
    Factor, FactorItem, form=FactorItemApprovalForm,
    extra=0, can_delete=False, fields=('status',)
)
#-------------------------------------------------------
"""  ویو برای تأیید فاکتور"""
class FactorApproveView(PermissionBaseView, UpdateView):
        model = Factor
        form_class = FactorApprovalForm  # فرض بر وجود این فرم
        template_name = 'tankhah/factor_approval.html'
        success_url = reverse_lazy('factor_list')
        permission_codenames = ['tankhah.factor_view', 'tankhah.factor_update']

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['title'] = ('تأیید فاکتور') + f" - {self.object.number}"
            context['items'] = self.object.items.all()
            return context

        def form_valid(self, form):
            factor = self.object
            tankhah = factor.tankhah
            user_posts = self.request.user.userpost_set.all()

            if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
                messages.error(self.request, ('شما مجاز به تأیید در این مرحله نیستید.'))
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
                        next_stage = AccessRule.objects.filter(order__lt=tankhah.current_stage.order).order_by(
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
                            messages.success(self.request, ('تنخواه تکمیل شد.'))
                    else:
                        messages.success(self.request, ('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
                else:
                    messages.warning(self.request, ('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

            return super().form_valid(form)
#-------------------------------------------------------


#-------------------------------------------------------
#  ویو اصلی تایید فامتور
#-------------------------------------------------------
class FactorItemApproveViewOLD(PermissionBaseView, DetailView):
    """
    ویوی مرکزی برای مدیریت فرآیند تأیید ردیف‌های فاکتور.
    این ویو مسئول نمایش اطلاعات، بررسی دسترسی کاربر، پردازش اقدامات (تأیید/رد)
    و پیشبرد فاکتور در چرخه گردش کار است.
    """
    model = Factor
    template_name = 'tankhah/Approved/factor_item_approve_final.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_approve']

    # --------------------------------------------------------------------------
    # ۱. متدهای اصلی View
    # --------------------------------------------------------------------------

    def get_object(self, queryset=None):
        """
        واکشی شیء فاکتور از دیتابیس با بهینه‌سازی کوئری‌ها (select_related/prefetch_related)
        برای جلوگیری از درخواست‌های مکرر به دیتابیس.
        """
        logger.debug(f"--- [GET_OBJECT] Fetching Factor with PK: {self.kwargs['pk']} ---")
        factor = get_object_or_404(
            self.model.objects.select_related('tankhah__organization', 'created_by').prefetch_related('items'),
            pk=self.kwargs['pk']
        )
        logger.info(f"--- [GET_OBJECT] Factor '{factor.number}' fetched successfully. ---")
        return factor

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی تمام داده‌های لازم برای نمایش در تمپلیت. این متد قلب تپنده ویو در درخواست GET است.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        current_stage = factor.tankhah.current_stage

        logger.debug(f"\n{'=' * 20} START: get_context_data (User: {user.username}, Factor: {factor.pk}) {'=' * 20}\n")

        # --- گام ۱: بررسی‌های اولیه و حیاتی ---
        if not current_stage:
            messages.error(self.request, ("گردش کار به درستی تعریف نشده است."))
            context.update({'can_edit': False});
            return context

        # --- گام ۲: بررسی دسترسی کاربر و استخراج اقدامات مجاز ---
        # تمام منطق پیچیده دسترسی به این تابع واحد و شفاف منتقل شده است.
        permissions = check_approval_permissions(user, factor.tankhah, factor, current_stage)
        can_edit = permissions['can_edit']
        allowed_actions = permissions['allowed_actions']

        if not can_edit and self.request.method == 'GET':
            messages.warning(self.request, ("شما دسترسی لازم برای اقدام در این مرحله را ندارید."))

        # --- گام ۳: ساخت فرم‌ست و آماده‌سازی نهایی کانتکست ---
        form_kwargs = {'user': user, 'allowed_actions': allowed_actions}
        formset = FactorItemApprovalFormSet(self.request.POST or None, instance=factor, prefix='items',
                                            form_kwargs=form_kwargs)

        context.update({
            'current_stage': current_stage,
            'formset': formset,
            'can_edit': can_edit,
            'allowed_actions': allowed_actions,
            'bulk_action_enabled': any(a in allowed_actions for a in ['APPROVE', 'REJECT']),
            'approval_history': self._get_approval_history(factor),
            'pending_users': self._get_pending_users(factor, current_stage),
            'future_approvers_by_stage': self._get_future_approvers(factor, current_stage),
        })

        logger.debug(f"\n{'=' * 20} FINISHED: get_context_data {'=' * 20}\n")
        return context

    def post(self, request, *args, **kwargs):
        """
        پردازش درخواست POST برای ثبت اقدامات کاربر.
        """
        self.object = self.get_object()
        # فراخوانی get_context_data برای دسترسی به can_edit و formset
        context = self.get_context_data()
        formset = context.get('formset')

        logger.info(f"--- [POST] Processing action for Factor {self.object.pk} by User '{request.user.username}' ---")

        # بررسی مجدد دسترسی قبل از هرگونه پردازش
        if not context.get('can_edit'):
            logger.warning(f"--- [POST] Access DENIED for User '{request.user.username}' on POST request. ---")
            messages.error(request, ('شما دسترسی لازم برای ثبت اقدام را ندارید.'))
            return redirect(self.get_success_url())

        # اعتبارسنجی فرم‌ست
        if not formset.is_valid():
            logger.warning(f"--- [POST] Formset is invalid. Errors: {formset.errors} ---")
            messages.error(request, ('اطلاعات ارسالی نامعتبر است. لطفاً خطاها را بررسی کنید.'))
            return self.render_to_response(context)  # نمایش مجدد صفحه با خطاها

        try:
            # تمام عملیات دیتابیس در یک تراکنش اتمیک انجام می‌شود
            with transaction.atomic():
                logger.debug("--- [POST] Starting atomic transaction. ---")
                action_taken = self._process_formset_actions(formset)

                if action_taken:
                    # فقط در صورتی که اقدامی ثبت شده باشد، گردش کار را بررسی کن
                    self._check_workflow_advancement(self.object, context['current_stage'])
                    messages.success(request, ('اقدامات با موفقیت ثبت شد.'))
                else:
                    messages.warning(request, ('هیچ تغییری برای ثبت وجود نداشت.'))

        except Exception as e:
            logger.error(f"--- [POST] FATAL: Exception during transaction: {e} ---", exc_info=True)
            messages.error(request, ('خطایی در حین پردازش رخ داد.'))

        return redirect(self.get_success_url())

    def get_success_url(self):
        """پس از هر اقدام، به همین صفحه بازمی‌گردیم."""
        return reverse('factor_item_approve', kwargs={'pk': self.object.pk})

    # --------------------------------------------------------------------------
    # ۲. متدهای کمکی (Helper Methods) برای خوانایی بهتر
    # --------------------------------------------------------------------------

    def _get_approval_history(self, factor):
        """تاریخچه اقدامات ثبت شده برای فاکتور را واکشی می‌کند."""
        return ApprovalLog.objects.filter(factor=factor).select_related('user', 'post', 'stage_rule').order_by(
            '-timestamp')

    def _get_pending_users(self, factor, current_stage):
        """کاربرانی که در مرحله فعلی هنوز اقدامی ثبت نکرده‌اند را پیدا می‌کند."""
        required_posts = set(AccessRule.objects.filter(
            organization=factor.tankhah.organization, stage_order=current_stage.stage_order, entity_type='FACTORITEM'
        ).values_list('post_id', flat=True))

        acted_posts = set(ApprovalLog.objects.filter(
            factor=factor, stage_rule=current_stage
        ).values_list('post_id', flat=True))

        pending_post_ids = required_posts - acted_posts
        return CustomUser.objects.filter(userpost__post_id__in=pending_post_ids, userpost__is_active=True).distinct()

    def _get_future_approvers(self, factor, current_stage):
        """مراحل بعدی گردش کار و تأییدکنندگان آن‌ها را برای نمایش در تمپلیت آماده می‌کند."""
        future_approvers = []
        # از distinct('stage_order') برای گرفتن هر مرحله فقط یک بار استفاده می‌کنیم
        future_stages = AccessRule.objects.filter(
            organization=factor.tankhah.organization, entity_type='FACTORITEM',
            stage_order__gt=current_stage.stage_order
        ).order_by('stage_order').values('stage_order', 'stage').distinct()

        for stage in future_stages:
            posts_in_stage = AccessRule.objects.filter(
                organization=factor.tankhah.organization, entity_type='FACTORITEM', stage_order=stage['stage_order']
            ).values_list('post_id', flat=True)

            users = CustomUser.objects.filter(userpost__post_id__in=posts_in_stage, userpost__is_active=True).distinct()
            if users:
                future_approvers.append(
                    {'stage_order': stage['stage_order'], 'stage_name': stage['stage'], 'approvers': users})
        return future_approvers

    def _process_formset_actions(self, formset):
        """
        روی فرم‌های معتبر و تغییر کرده حلقه زده و اقدامات کاربر را در ApprovalLog ثبت می‌کند.
        """
        action_taken = False
        user = self.request.user
        user_post = user.userpost_set.filter(is_active=True).first().post
        factor = self.object
        current_stage = factor.tankhah.current_stage

        for form in formset:
            if form.has_changed() and form.cleaned_data.get('status'):
                item = form.instance
                status = form.cleaned_data['status']
                comment = form.cleaned_data['comment']
                is_temporary = form.cleaned_data['is_temporary']

                # ایجاد یا آپدیت لاگ برای این اقدام
                ApprovalLog.objects.update_or_create(
                    factor_item=item, post=user_post, stage_rule=current_stage,
                    defaults={
                        'factor': factor, 'user': user, 'action': status,
                        'comment': comment, 'is_temporary': is_temporary,
                    }
                )
                logger.info(f"Log with action '{status}' saved for Item {item.pk} by User '{user.username}'.")

                # اگر اقدام نهایی بود، وضعیت خود ردیف را هم آپدیت کن
                if not is_temporary:
                    item.status = status
                    item.save(update_fields=['status'])

                action_taken = True
        return action_taken

    def _check_workflow_advancement(self, factor, current_stage):
        """
        بررسی می‌کند که آیا گردش کار باید به مرحله بعد برود، رد شود یا منتظر بماند.
        """
        # شرط ۱: اگر یک ردیف به صورت نهایی رد شده، کل فاکتور را رد کن
        if ApprovalLog.objects.filter(factor=factor, stage_rule=current_stage, action='REJECT',
                                      is_temporary=False).exists():
            self._reject_factor(factor);
            return

        # شرط ۲: آیا تمام پست‌های الزامی در این مرحله اقدام نهایی خود را انجام داده‌اند؟
        required_post_ids = set(AccessRule.objects.filter(
            organization=factor.tankhah.organization, stage_order=current_stage.stage_order, entity_type='FACTORITEM'
        ).values_list('post_id', flat=True))

        # اگر در این مرحله هیچ تأییدکننده‌ای تعریف نشده، به صورت خودکار به مرحله بعد برو
        if not required_post_ids:
            self._advance_factor_stage(factor, current_stage);
            return

        # پیدا کردن پست‌هایی که برای "تمام" ردیف‌ها اقدام نهایی کرده‌اند
        final_acted_posts = ApprovalLog.objects.filter(
            factor=factor, stage_rule=current_stage, is_temporary=False
        ).values('post_id').annotate(item_count=Count('factor_item_id', distinct=True))

        fully_approved_post_ids = {p['post_id'] for p in final_acted_posts if p['item_count'] == factor.items.count()}

        # مقایسه
        if required_post_ids.issubset(fully_approved_post_ids):
            logger.info(f"All required posts have approved. Advancing factor {factor.pk} to next stage.")
            self._advance_factor_stage(factor, current_stage)
        else:
            logger.info(f"Factor {factor.pk} is waiting for other approvers in this stage.")
            messages.info(self.request, ("اقدام شما ثبت شد. در انتظار تأیید سایر کاربران در این مرحله."))

    def _advance_factor_stage(self, factor, current_stage):
        """
        فاکتور را به مرحله بعدی گردش کار منتقل می‌کند یا در صورت اتمام، آن را نهایی می‌کند.
        """
        logger.debug(f"Advancing factor {factor.pk} from stage order {current_stage.stage_order}")

        next_stage_rule = AccessRule.objects.filter(
            organization=factor.tankhah.organization, entity_type='FACTORITEM',
            # stage_order__gt=current_stage.stage_order
            stage_order__lt=current_stage.stage_order  # <--- **اصلاح اصلی: کوچکتر از**
        ).order_by('stage_order').first()

        if next_stage_rule:
            factor.tankhah.current_stage = next_stage_rule
            factor.tankhah.save(update_fields=['current_stage'])
            factor.items.update(status='PENDING_APPROVAL')
            messages.success(self.request, (f"فاکتور با موفقیت به مرحله '{next_stage_rule.stage}' ارسال شد."))
            # send_notification(
            #     sender=self.request.user, posts=Post.objects.filter(id__in=po_approver_posts),
            #     verb=("برای تأیید ارسال شد"), target=payment_order,
            #     description=(f"دستور پرداخت برای فاکتور #{factor.number} برای تأیید شما ارسال شد."),
            #     entity_type='PAYMENT_ORDER'
            # )
        else:
            factor.status = 'APPROVED_FINAL'
            factor.is_locked = True
            factor.save(update_fields=['status', 'is_locked'])
            messages.success(self.request, ("فاکتور به صورت نهایی تأیید شد."))
            self._create_payment_order(factor)

    def _reject_factor(self, factor):
        """
        فاکتور را به صورت نهایی رد کرده و به مرحله اولیه بازمی‌گرداند.
        """
        initial_stage_rule = AccessRule.objects.filter(
            organization=factor.tankhah.organization, entity_type='FACTORITEM'
        ).order_by('stage_order').first()

        factor.status = 'REJECT'
        factor.is_locked = True
        factor.save(update_fields=['status', 'is_locked'])

        rejection_comment = ("فاکتور رد شد.")
        if initial_stage_rule:
            factor.tankhah.current_stage = initial_stage_rule
            factor.tankhah.save(update_fields=['current_stage'])
            factor.items.update(status='PENDING_APPROVAL')
            rejection_comment = (f"فاکتور رد شد و به مرحله اولیه '{initial_stage_rule.stage}' بازگشت.")

        messages.error(self.request, rejection_comment)
        # ... (کد کامل ارسال نوتیفیکیشن) ...

    
        send_notification(
            sender=self.request.user, users=[factor.created_by], verb=("رد شد"),
            target=factor, description=(f"فاکتور #{factor.number} شما رد شد و به مرحله اولیه بازگشت."),
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
            messages.warning(self.request, ("گردش کاری برای 'دستور پرداخت' تعریف نشده است. دستور پرداخت ایجاد نشد."))
            logger.warning(
                f"No initial stage for PAYMENT_ORDER in org {factor.tankhah.organization.pk}. PO not created.")
            return

        try:
            payment_order, created = PaymentOrder.objects.get_or_create(
                tankhah=factor.tankhah, related_factors=factor,
                defaults={
                    'amount': factor.amount,
                    'description': (f"پرداخت خودکار برای فاکتور #{factor.number}"),
                    'organization': factor.tankhah.organization,
                    'project': factor.tankhah.project,
                    'status': 'PENDING_APPROVAL',
                    'created_by': self.request.user,
                    'payee': factor.created_by,
                    'current_stage': po_initial_stage,
                }
            )

            if created:
                messages.success(self.request, (f"دستور پرداخت برای این فاکتور با موفقیت ایجاد شد."))
                po_approver_posts = AccessRule.objects.filter(
                    organization=factor.tankhah.organization, entity_type='PAYMENT_ORDER',
                    stage_order=po_initial_stage.stage_order
                ).values_list('post_id', flat=True).distinct()

                send_notification(
                    sender=self.request.user, posts=Post.objects.filter(id__in=po_approver_posts),
                    verb=("برای تأیید ارسال شد"), target=payment_order,
                    description=(f"دستور پرداخت برای فاکتور #{factor.number} برای تأیید شما ارسال شد."),
                    entity_type='PAYMENT_ORDER'
                )
            else:
                messages.info(self.request, ("دستور پرداخت برای این فاکتور قبلاً ایجاد شده است."))

        except Exception as e:
            logger.error(f"Failed to create PaymentOrder for factor {factor.pk}: {e}", exc_info=True)
            messages.error(self.request, ("خطایی در هنگام ایجاد دستور پرداخت رخ داد."))
#  ----------------NEW -------------------------------#

class FactorItemApproveViewdadsasdasdasdasdasd(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Approved/factor_item_approve_final.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_approve']

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی تمام داده‌های لازم برای نمایش در تمپلیت بر اساس معماری داینامیک.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        current_status = factor.status

        logger.debug(
            f"\n{'=' * 20} START: get_context_data (User: {user.username}, Factor: {factor.pk}, Status: {current_status}) {'=' * 20}\n")

        if not current_status:
            messages.error(self.request, _("فاکتور وضعیت مشخصی ندارد."))
            context.update({'can_edit': False});
            return context

        # --- گام ۱: پیدا کردن اقدامات مجاز از مدل Permission ---
        user_posts = user.userpost_set.filter(is_active=True).values('post')

        # کوئری برای پیدا کردن تمام مجوزهای کاربر در وضعیت فعلی
        permissions = Transition.objects.filter(
            transition__organization=factor.tankhah.organization,
            transition__entity_type__code='FACTORITEM',
            transition__from_status=current_status,
            allowed_posts__in=user_posts,
            transition__is_active=True,
            is_active=True
        ).prefetch_related('allowed_actions')

        # استخراج لیست منحصر به فرد اقدامات مجاز
        allowed_actions = list({action for perm in permissions for action in perm.allowed_actions.all()})
        can_edit = bool(allowed_actions)

        logger.info(
            f"Access Check for User '{user.username}': can_edit={can_edit}, allowed_actions={[a.name for a in allowed_actions]}")

        # --- گام ۲: ساخت فرم‌ست و آماده‌سازی نهایی کانتکست ---
        form_kwargs = {'allowed_actions': allowed_actions}
        formset = FactorItemApprovalFormSet(
            self.request.POST or None, queryset=factor.items.all(),
            prefix='items', form_kwargs=form_kwargs
        )

        context.update({
            'current_status': current_status,
            'formset': formset,
            'can_edit': can_edit,
            'allowed_actions': allowed_actions,
            'approval_history': ApprovalLog.objects.filter(factor=factor).select_related('user', 'post',
                                                                                         'action_obj').order_by(
                '-timestamp'),
            'pending_users': self._get_pending_users(factor, current_status),
            'future_approvers': self._get_future_approvers(factor, current_status),
        })

        logger.debug(f"\n{'=' * 20} FINISHED: get_context_data {'=' * 20}\n")
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        formset = context['formset']

        if not context.get('can_edit'):
            messages.error(request, _('شما دسترسی لازم برای ثبت اقدام را ندارید.'))
            return redirect(self.object.get_absolute_url())

        if formset.is_valid():
            try:
                with transaction.atomic():
                    self._process_approval(formset)
            except Exception as e:
                logger.error(f"Error during POST processing: {e}", exc_info=True)
                messages.error(request, _('خطایی در حین پردازش رخ داد.'))
            return redirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(context)

    # --- متدهای کمکی (Helper Methods) ---

    def _process_approval(self, formset):
        """
        منطق اصلی پردازش اقدامات، ثبت لاگ و پیشبرد گردش کار.
        """
        user = self.request.user
        factor = self.object
        current_status = factor.status

        # پیدا کردن اقدام اصلی (فرض می‌کنیم اقدام برای تمام ردیف‌ها یکسان است)
        action_code = next((form.cleaned_data.get('action') for form in formset if form.cleaned_data.get('action')),
                           None)

        if not action_code:
            messages.warning(self.request, _('هیچ اقدامی انتخاب نشده بود.'))
            return

        action_obj = Action.objects.get(code=action_code)

        # ثبت لاگ برای هر ردیف
        user_post = user.userpost_set.filter(is_active=True).first()
        for form in formset:
            if form.cleaned_data.get('action') == action_code:
                ApprovalLog.objects.create(
                    factor_item=form.instance,
                    user=user, post=user_post.post if user_post else None,
                    action_obj=action_obj, status_obj=current_status,
                    comment=form.cleaned_data.get('comment'),
                    is_temporary=form.cleaned_data.get('is_temporary'),
                )

        # --- منطق پیشرفت گردش کار ---
        # آیا تمام پست‌های لازم در این وضعیت اقدام کرده‌اند؟
        permissions_for_status = Transition.objects.filter(transition__from_status=current_status)
        required_posts_pks = set(permissions_for_status.values_list('allowed_posts', flat=True))

        acted_posts_pks = set(
            ApprovalLog.objects.filter(factor=factor, status_obj=current_status).values_list('post_id', flat=True))

        if required_posts_pks.issubset(acted_posts_pks):
            # اگر همه اقدام کرده‌اند، وضعیت فاکتور را تغییر بده
            transition = Transition.objects.get(from_status=current_status, action=action_obj)
            new_status = transition.to_status

            factor.status = new_status
            factor.items.update(status=new_status)
            factor.save(update_fields=['status'])
            messages.success(self.request, _(f"اقدام شما ثبت و فاکتور به وضعیت '{new_status.name}' منتقل شد."))

            # ارسال نوتیفیکیشن برای تأییدکنندگان وضعیت جدید
            self._send_notification_for_new_status(factor, new_status)
        else:
            messages.info(self.request, _("اقدام شما ثبت شد. در انتظار اقدام سایر کاربران."))

    def _get_pending_users(self, factor, current_status):
        """کاربران منتظر در وضعیت فعلی را پیدا می‌کند."""
        permissions = Transition.objects.filter(transition__from_status=current_status)
        required_posts_pks = set(permissions.values_list('allowed_posts', flat=True))
        acted_posts_pks = set(
            ApprovalLog.objects.filter(factor=factor, status_obj=current_status).values_list('post_id', flat=True))

        pending_post_ids = required_posts_pks - acted_posts_pks
        return CustomUser.objects.filter(userpost__post_id__in=pending_post_ids, userpost__is_active=True).distinct()

    def _get_future_approvers(self, factor, current_status):
        """مراحل (وضعیت‌های) بعدی ممکن در گردش کار را پیدا می‌کند."""
        future_approvers = []
        possible_transitions = Transition.objects.filter(
            organization=factor.tankhah.organization,
            entity_type__code='FACTORITEM',
            from_status=current_status
        ).select_related('to_status')

        for trans in possible_transitions:
            permissions = Transition.objects.filter(transition=trans).prefetch_related('allowed_posts')
            approver_posts = {post for perm in permissions for post in perm.allowed_posts.all()}

            users = CustomUser.objects.filter(userpost__post__in=list(approver_posts),
                                              userpost__is_active=True).distinct()
            if users:
                future_approvers.append({'next_status': trans.to_status.name, 'approvers': users})
        return future_approvers

    def _send_notification_for_new_status(self, factor, new_status):
        """نوتیفیکیشن برای تأیییدکنندگان وضعیت جدید ارسال می‌کند."""
        permissions = Transition.objects.filter(transition__from_status=new_status)
        recipient_posts = {post for perm in permissions for post in perm.allowed_posts.all()}

        if recipient_posts:
            send_notification(
                sender=self.request.user, posts=list(recipient_posts),
                verb=_("برای تأیید ارسال شد"), target=factor,
                description=_(f"فاکتور #{factor.number} برای تأیید در وضعیت '{new_status.name}' برای شما ارسال شد."),
                entity_type='FACTOR'
            )


#
# فایل: tankhah/Factor/Approved/view_FactorItemApprove.py (نسخه کامل و نهایی)
#

class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/Approved/factor_item_approve_final.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_approve']

    # --------------------------------------------------------------------------
    # ۱. متدهای اصلی View
    # --------------------------------------------------------------------------

    def get_object(self, queryset=None):
        """
        واکشی شیء فاکتور با بهینه‌سازی کوئری‌ها.
        """
        return get_object_or_404(
            self.model.objects.select_related(
                'tankhah__organization', 'created_by', 'status'  # status یک ForeignKey است
            ).prefetch_related('items'),
            pk=self.kwargs['pk']
        )

    def get_context_data(self, **kwargs):
        """
        آماده‌سازی تمام داده‌های لازم برای نمایش در تمپلیت.
        """
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        current_status_obj = factor.status

        if not current_status_obj:
            messages.error(self.request, _("فاکتور وضعیت مشخصی ندارد."))
            context.update({'can_edit': False});
            return context

        # --- گام ۱: پیدا کردن اقدامات مجاز ---
        user_posts = user.userpost_set.filter(is_active=True).values('post')
        # --- ۱. پیدا کردن گذارهای مجاز ---
        allowed_transitions = Transition.objects.filter(
            organization=factor.tankhah.organization,
            entity_type__code='FACTORITEM',
            from_status=current_status_obj,
            allowed_posts__in=user_posts,
            is_active=True
        ).select_related('action')

        allowed_actions = list({trans.action for trans in allowed_transitions})
        can_edit = bool(allowed_actions)

        if not can_edit and self.request.method == 'GET':
            messages.warning(self.request, _("شما دسترسی لازم برای اقدام در این وضعیت را ندارید."))

        # --- گام ۲: ساخت فرم‌ست ---
        form_kwargs = {'allowed_actions': allowed_actions}
        formset = FactorItemApprovalFormSet(
            self.request.POST or None,
            queryset=factor.items.all(),
            prefix='items',
            form_kwargs=form_kwargs
        )

        context.update({
            'current_status': current_status_obj,
            'formset': formset,
            'can_edit': can_edit,
            'allowed_actions': allowed_actions,
            'approval_history': ApprovalLog.objects.filter(factor=factor).select_related('user', 'post',
                                                                                         'action_obj').order_by(
                '-timestamp'),
            'pending_users': self._get_pending_users(factor, current_status_obj),
            'future_approvers': self._get_future_approvers(factor, current_status_obj),
        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        formset = context['formset']

        if not context.get('can_edit'):
            messages.error(request, _('شما دسترسی لازم برای ثبت اقدام را ندارید.'))
            return redirect(self.object.get_absolute_url())

        if formset.is_valid():
            try:
                with transaction.atomic():
                    self._process_approval(formset)
            except Exception as e:
                logger.error(f"Error during POST processing: {e}", exc_info=True)
                messages.error(request, _('خطایی در حین پردازش رخ داد.'))
            return redirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(context)

    # --------------------------------------------------------------------------
    # ۲. متدهای کمکی (Helper Methods)
    # --------------------------------------------------------------------------

    def _process_approval(self, formset):
        """
        منطق اصلی پردازش اقدامات، ثبت لاگ و پیشبرد گردش کار.
        """
        user = self.request.user
        factor = self.object
        current_status_obj = factor.status

        # پیدا کردن اقدام اصلی (فرض می‌کنیم اقدام برای تمام ردیف‌ها یکسان است)
        action_code = next((form.cleaned_data.get('action') for form in formset if form.cleaned_data.get('action')),
                           None)
        if not action_code:
            messages.warning(self.request, _('هیچ اقدامی انتخاب نشده بود.'));
            return

        action_obj = Action.objects.get(code=action_code)
        # پیدا کردن گذار مربوطه
        transition = Transition.objects.get(
            from_status=current_status_obj,
            action=action_obj,
            organization=factor.tankhah.organization,
            entity_type__code='FACTORITEM'
        )
        # ثبت لاگ برای هر ردیف
        user_post = user.userpost_set.filter(is_active=True).first()
        for form in formset:
            if form.cleaned_data.get('action') == action_code:
                ApprovalLog.objects.create(
                    factor_item=form.instance,
                    user=user,
                    post=user_post.post if user_post else None,
                    action_obj=action_obj,
                    status_obj=current_status_obj,
                    comment=form.cleaned_data.get('comment'),
                    is_temporary=form.cleaned_data.get('is_temporary'),
                    stage_rule=transition
                )

        # --- منطق پیشرفت گردش کار ---
        # آیا تمام پست‌های لازم در این وضعیت اقدام کرده‌اند؟
        transitions_in_status = Transition.objects.filter(from_status=current_status_obj,
                                                          organization=factor.tankhah.organization,
                                                          entity_type__code='FACTORITEM')
        required_posts_pks = {post.pk for trans in transitions_in_status.prefetch_related('allowed_posts') for post in
                              trans.allowed_posts.all()}

        # **اصلاح کلیدی:** به جای status_obj، ما باید لاگ‌ها را بر اساس مرحله (stage_rule) فیلتر کنیم
        # که این مرحله همان گذاری است که وضعیت اولیه آن، وضعیت فعلی ماست.
        acted_posts_pks = set(
            ApprovalLog.objects.filter(
                factor=factor,
                stage_rule__from_status=current_status_obj  # فیلتر بر اساس وضعیت اولیه گذار
            ).values_list('post_id', flat=True)
        )
        if required_posts_pks.issubset(acted_posts_pks):
            new_status = transition.to_status
            factor.status = new_status
            factor.items.update(status=new_status)
            factor.save(update_fields=['status'])
            messages.success(self.request, _(f"فاکتور به وضعیت '{new_status.name}' منتقل شد."))
            self._send_notification_for_new_status(factor, new_status)
        else:
            messages.info(self.request, _("اقدام شما ثبت شد. در انتظار اقدام سایر کاربران."))

    def _get_pending_users(self, factor, current_status_obj):
        """کاربران منتظر در وضعیت فعلی را پیدا می‌کند."""
        transitions_in_status = Transition.objects.filter(
            organization=factor.tankhah.organization, entity_type__code='FACTORITEM', from_status=current_status_obj
        ).prefetch_related('allowed_posts')

        required_posts_pks = {post.pk for trans in transitions_in_status for post in trans.allowed_posts.all()}
        acted_posts_pks = set(
            ApprovalLog.objects.filter(factor=factor, status_obj=current_status_obj).values_list('post_id', flat=True))

        pending_post_ids = required_posts_pks - acted_posts_pks
        return CustomUser.objects.filter(userpost__post_id__in=pending_post_ids, userpost__is_active=True).distinct()

    def _get_future_approvers(self, factor, current_status_obj):
        """مراحل (وضعیت‌های) بعدی ممکن در گردش کار را پیدا می‌کند."""
        future_approvers = []
        possible_transitions = Transition.objects.filter(
            organization=factor.tankhah.organization, entity_type__code='FACTORITEM', from_status=current_status_obj
        ).select_related('to_status').prefetch_related('allowed_posts')

        for trans in possible_transitions:
            approver_posts = trans.allowed_posts.all()
            users = CustomUser.objects.filter(userpost__post__in=list(approver_posts),
                                              userpost__is_active=True).distinct()
            if users:
                future_approvers.append({'next_status': trans.to_status.name, 'approvers': users})
        return future_approvers

    def _send_notification_for_new_status(self, factor, new_status_obj):
        """نوتیفیکیشن برای تأییدکنندگان وضعیت جدید ارسال می‌کند."""
        transitions_from_new_status = Transition.objects.filter(
            organization=factor.tankhah.organization, entity_type__code='FACTORITEM', from_status=new_status_obj
        ).prefetch_related('allowed_posts')

        recipient_posts = {post for trans in transitions_from_new_status for post in trans.allowed_posts.all()}

        if recipient_posts:
            send_notification(
                sender=self.request.user, posts=list(recipient_posts),
                verb=_("برای تأیید ارسال شد"), target=factor,
                description=_(
                    f"فاکتور #{factor.number} برای تأیید در وضعیت '{new_status_obj.name}' برای شما ارسال شد."),
                entity_type='FACTOR'
            )
