from channels.layers import get_channel_layer
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils import timezone
from falcon import async_to_sync
from notifications.signals import notify

import core.models
from accounts.models import CustomUser
from budgets.models import PaymentOrder, Payee, BudgetTransaction
from notificationApp.models import NotificationRule
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import DetailView
from core.views import PermissionBaseView
from core.models import UserPost, WorkflowStage, Post
from tankhah.forms import FactorItemApprovalForm
from tankhah.models import Factor, FactorItem, ApprovalLog, StageApprover
from tankhah.fun_can_edit_approval import can_edit_approval
from django.utils.translation import gettext_lazy as _

import logging
from core.models import Organization
logger = logging.getLogger('factor_approval')

# تنظیم لاگ‌گیری با فایل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    filename='logs/factor_item_approve.log',
    filemode='a'
)


FactorItemApprovalFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemApprovalForm,
    fields=('status', 'description'),
    extra=0,
    can_delete=False
)


"""تأیید آیتم‌های فاکتور"""
class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_required = 'tankhah.factor_approve'
    context_object_name = 'factor'
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def post(self, request, *args, **kwargs):
        logger.info(
            f"[FactorItemApproveView] درخواست POST دریافت شد برای فاکتور {self.kwargs.get('pk')} توسط کاربر {request.user.username}")
        logger.debug(f"[FactorItemApproveView] داده‌های POST: {request.POST}")
        self.object = self.get_object()
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()

        # بررسی HQ بودن کاربر
        user_org_ids = set()
        for up in user.userpost_set.filter(is_active=True):
            org = up.post.organization
            user_org_ids.add(org.id)
            current_org = org
            while current_org.parent_organization:
                current_org = current_org.parent_organization
                user_org_ids.add(current_org.id)
        is_hq_user = any(
            Organization.objects.filter(id=org_id, org_type__org_type='HQ').exists()
            for org_id in user_org_ids
        )

        if not user_post and not user.is_hq:
            logger.error(f"[FactorItemApproveView] کاربر {user.username} هیچ پست فعالی ندارد")
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('factor_item_approve', pk=factor.pk)

        if tankhah.is_locked or tankhah.is_archived or factor.is_locked:
            logger.warning(
                f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است")
            messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        if not can_edit_approval(user, tankhah, tankhah.current_stage):
            # logger.warning(f"[FactorItemApproveView] کاربر {user.username} دسترسی لازم برای ویرایش ندارد")
            logger.warning(f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است")
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        if 'change_stage' in request.POST:
            logger.info(f"[FactorItemApproveView] درخواست تغییر مرحله برای فاکتور {factor.pk}")
            try:
                new_stage_order = int(request.POST.get('new_stage_order'))
                stage_change_reason = request.POST.get('stage_change_reason', '').strip()
                if not stage_change_reason:
                    raise ValidationError(_("توضیحات تغییر مرحله الزامی است."))
                max_change_level = user_post.post.max_change_level if user_post else 0
                if not user.is_hq and new_stage_order > max_change_level:
                    raise ValidationError(
                        _(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))

                new_stage = WorkflowStage.objects.filter(
                    order=new_stage_order,
                    is_active=True,
                    entity_type='FACTOR'
                ).first()
                if not new_stage:
                    raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))

                if not user.is_hq and user_post:
                    has_permission = StageApprover.objects.filter(
                        post=user_post.post,
                        stage=new_stage,
                        is_active=True
                    ).exists()
                    if not has_permission:
                        raise ValidationError(_("شما اجازه ارجاع به این مرحله را ندارید."))

                with transaction.atomic():
                    old_stage_name = tankhah.current_stage.name
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING'
                    tankhah._changed_by = user  # برای سیگنال
                    tankhah.save(update_fields=['current_stage', 'status'])
                    approving_posts = StageApprover.objects.filter(
                        stage=new_stage,
                        is_active=True
                    ).values_list('post', flat=True)
                    self.send_notifications(
                        entity=factor,
                        action='NEEDS_APPROVAL',
                        priority='MEDIUM',
                        description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {new_stage.name} دارد.",
                        recipients=approving_posts
                    )
                    logger.info(f"[FactorItemApproveView] مرحله فاکتور {factor.pk} به {new_stage.name} تغییر یافت")
                    messages.success(request, _(f"مرحله فاکتور به {new_stage.name} تغییر یافت."))
                return redirect('factor_item_approve', pk=factor.pk)
            except (ValueError, ValidationError) as e:
                logger.error(f"[FactorItemApproveView] خطا در تغییر مرحله: {e}", exc_info=True)
                messages.error(request, str(e))
                return redirect('factor_item_approve', pk=factor.pk)

        if request.POST.get('reject_factor'):
            logger.info(f"[FactorItemApproveView] درخواست رد کامل فاکتور {factor.pk}")
            try:
                rejected_reason = request.POST.get('rejected_reason', '').strip()
                if not rejected_reason:
                    raise ValidationError(_("دلیل رد فاکتور الزامی است."))
                with transaction.atomic():
                    factor.status = 'REJECTED'
                    factor.is_locked = True
                    factor.rejected_reason = rejected_reason
                    factor._changed_by = user  # برای سیگنال
                    factor.save()
                    items_updated = FactorItem.objects.filter(factor=factor).update(status='REJECTED')
                    logger.info(
                        f"[FactorItemApproveView] فاکتور {factor.pk} و {items_updated} آیتم آن رد شد توسط {user.username}")
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='REJECT',
                        stage=tankhah.current_stage,
                        comment=f"رد کامل فاکتور: {rejected_reason}",
                        post=user_post.post if user_post else None
                    )
                    self.send_notifications(
                        entity=factor,
                        action='REJECTED',
                        priority='HIGH',
                        description=f"فاکتور {factor.number} رد شد. دلیل: {rejected_reason}",
                        recipients=[factor.created_by_post] if factor.created_by_post else []
                    )
                    messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
                    return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در رد فاکتور: {e}", exc_info=True)
                messages.error(request, _("خطا در رد فاکتور."))
                return redirect('factor_item_approve', pk=factor.pk)

        if request.POST.get('final_approve'):
            logger.info(f"[FactorItemApproveView] درخواست تأیید نهایی برای فاکتور {factor.pk}")
            try:
                with transaction.atomic():
                    all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                    if not all_factors_approved:
                        logger.warning(f"[FactorItemApproveView] همه فاکتورهای تنخواه {tankhah.number} تأیید نشده‌اند.")
                        messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                    if tankhah.current_stage.is_final_stage:
                        if tankhah.status == 'APPROVED':
                            logger.warning(
                                f"[FactorItemApproveView] تنخواه {tankhah.number} قبلاً تأیید نهایی شده است.")
                            messages.warning(request, _('این تنخواه قبلاً تأیید نهایی شده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        payment_number = request.POST.get('payment_number')
                        if tankhah.current_stage.triggers_payment_order and not payment_number:
                            logger.error(
                                f"[FactorItemApproveView] شماره پرداخت برای تنخواه {tankhah.number} ارائه نشده است.")
                            messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        if tankhah.current_stage.triggers_payment_order:
                            self.create_payment_order(factor, user)

                        tankhah.status = 'APPROVED'
                        tankhah.payment_number = payment_number
                        tankhah.is_locked = True
                        tankhah._changed_by = user  # برای سیگنال
                        tankhah.save(update_fields=['status', 'payment_number', 'is_locked'])
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='APPROVE',
                            stage=tankhah.current_stage,
                            comment=_('تأیید نهایی تنخواه'),
                            post=user_post.post if user_post else None
                        )
                        hq_posts = Post.objects.filter(organization__org_type__org_type='HQ')
                        self.send_notifications(
                            entity=factor,
                            action='APPROVED',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} تأیید نهایی شد و به دفتر مرکزی ارسال شد.",
                            recipients=hq_posts
                        )
                        logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} تأیید نهایی شد")
                        messages.success(request, _('فاکتور تأیید نهایی شد.'))
                        return redirect('dashboard_flows')
                    else:
                        next_stage = WorkflowStage.objects.filter(
                            order__gt=tankhah.current_stage.order,
                            is_active=True,
                            entity_type='FACTOR'
                        ).order_by('order').first()
                        if not next_stage:
                            logger.error(
                                f"[FactorItemApproveView] مرحله بعدی برای تنخواه {tankhah.number} تعریف نشده است.")
                            messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        approved_reason = request.POST.get('approved_reason', '').strip()
                        if not approved_reason:
                            raise ValidationError(_("توضیحات تأیید الزامی است."))

                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah._changed_by = user  # برای سیگنال
                        tankhah.save(update_fields=['current_stage', 'status'])
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تأیید و انتقال به {next_stage.name}. توضیحات: {approved_reason}",
                            post=user_post.post if user_post else None
                        )
                        approving_posts = StageApprover.objects.filter(
                            stage=next_stage,
                            is_active=True
                        ).values_list('post', flat=True)
                        self.send_notifications(
                            entity=factor,
                            action='NEEDS_APPROVAL',
                            priority='MEDIUM',
                            description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.name} دارد.",
                            recipients=approving_posts
                        )
                        logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} به مرحله {next_stage.name} منتقل شد")
                        messages.success(request, _(f"تأیید انجام و به مرحله {next_stage.name} منتقل شد."))
                        return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در تأیید نهایی: {e}", exc_info=True)
                messages.error(request, _("خطا در تأیید نهایی."))
                return redirect('factor_item_approve', pk=factor.pk)

        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')
        if formset.is_valid():
            logger.info("[FactorItemApproveView] فرم‌ست آیتم‌ها معتبر است.")
            try:
                with transaction.atomic():
                    has_changes = False
                    items_processed_count = 0
                    content_type = ContentType.objects.get_for_model(FactorItem)

                    for form in formset:
                        logger.debug(
                            f"[FactorItemApproveView] داده‌های فرم برای آیتم {form.instance.id}: {form.cleaned_data}")
                        if form.cleaned_data:
                            item = form.instance
                            if not item.id:
                                logger.error(f"[FactorItemApproveView] آیتم بدون ID یافت شد: {item}")
                                continue
                            logger.debug(f"[FactorItemApproveView] وضعیت فعلی آیتم {item.id}: {item.status}")
                            status = form.cleaned_data.get('status')
                            description = form.cleaned_data.get('description', '').strip()

                            if request.POST.get('bulk_approve') == 'on':
                                approved_reason = request.POST.get('approved_reason', '').strip()
                                if not approved_reason:
                                    raise ValidationError(_("توضیحات تأیید برای تأیید گروهی الزامی است."))
                                status = 'APPROVED'
                                description = approved_reason
                            elif request.POST.get('bulk_reject') == 'on':
                                rejected_reason = request.POST.get('rejected_reason', '').strip()
                                if not rejected_reason:
                                    raise ValidationError(_("دلیل رد برای رد گروهی الزامی است."))
                                status = 'REJECTED'
                                description = rejected_reason
                            elif status == 'REJECTED' and not description:
                                raise ValidationError(_("دلیل رد برای آیتم الزامی است."))

                            logger.debug(
                                f"[FactorItemApproveView] آیتم {item.id}: status={status}, description={description}")

                            # برای کاربران HQ یا superuser، حتی اگر status تغییر نکند، لاگ ثبت شود
                            if status and status != 'NONE' and (
                                    status != item.status or user.is_superuser or is_hq_user):
                                has_changes = True
                                items_processed_count += 1
                                action = 'APPROVE' if status == 'APPROVED' else 'REJECT'
                                ApprovalLog.objects.create(
                                    tankhah=tankhah,
                                    factor=factor,
                                    factor_item=item,
                                    user=user,
                                    action=action,
                                    stage=tankhah.current_stage,
                                    comment=description,
                                    post=user_post.post if user_post else None,
                                    content_type=content_type,
                                    object_id=item.id
                                )
                                item.status = status
                                item.description = description
                                item._changed_by = user  # برای سیگنال
                                item.save()
                                logger.info(f"[FactorItemApproveView] وضعیت آیتم {item.id} به {status} تغییر یافت.")

                    # بررسی وضعیت فاکتور حتی اگر هیچ تغییری ثبت نشده باشد
                    all_approved = factor.items.exists() and all(
                        item.status == 'APPROVED' for item in factor.items.all())
                    any_rejected = any(item.status == 'REJECTED' for item in factor.items.all())

                    if any_rejected:
                        factor.status = 'REJECTED'
                        factor.rejected_reason = request.POST.get('rejected_reason', 'یکی از آیتم‌ها رد شده است')
                        factor.is_locked = True
                        factor._changed_by = user  # برای سیگنال
                        factor.save()
                        self.send_notifications(
                            entity=factor,
                            action='REJECTED',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} به دلیل رد آیتم‌ها رد شد. دلیل: {factor.rejected_reason}",
                            recipients=[factor.created_by_post] if factor.created_by_post else []
                        )
                        logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} به دلیل رد آیتم‌ها رد شد")
                        messages.warning(request, _('فاکتور به دلیل رد آیتم‌ها رد شد.'))
                        return redirect('dashboard_flows')
                    elif all_approved:
                        factor.status = 'APPROVED'
                        factor.is_locked = True
                        factor._changed_by = user  # برای سیگنال
                        factor.save()
                        next_stage = WorkflowStage.objects.filter(
                            order__gt=tankhah.current_stage.order,
                            is_active=True,
                            entity_type='FACTOR'
                        ).order_by('order').first()
                        if next_stage and tankhah.current_stage.auto_advance:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah._changed_by = user  # برای سیگنال
                            tankhah.save(update_fields=['current_stage', 'status'])
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                factor=factor,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=next_stage,
                                comment=f"تأیید آیتم‌ها و انتقال به {next_stage.name}",
                                post=user_post.post if user_post else None
                            )
                            approving_posts = StageApprover.objects.filter(
                                stage=next_stage,
                                is_active=True
                            ).values_list('post', flat=True)
                            self.send_notifications(
                                entity=factor,
                                action='NEEDS_APPROVAL',
                                priority='MEDIUM',
                                description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.name} دارد.",
                                recipients=approving_posts
                            )
                            logger.info(
                                f"[FactorItemApproveView] فاکتور {factor.pk} به مرحله {next_stage.name} منتقل شد")
                            messages.success(request, _(f"فاکتور به مرحله {next_stage.name} منتقل شد."))
                            return redirect('dashboard_flows')
                        elif tankhah.current_stage.is_final_stage and tankhah.current_stage.triggers_payment_order:
                            self.create_payment_order(factor, user)
                            logger.info(f"[FactorItemApproveView] تمام آیتم‌های فاکتور {factor.pk} تأیید شدند")
                            messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند.'))
                            return redirect('dashboard_flows')
                        else:
                            logger.error(
                                f"[FactorItemApproveView] مرحله بعدی برای تنخواه {tankhah.number} تعریف نشده است")
                            messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)
                    else:
                        factor.status = 'PENDING'
                        factor._changed_by = user  # برای سیگنال
                        factor.save()
                        logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} در حالت PENDING باقی ماند")
                        messages.warning(request, _('لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                    if has_changes:
                        logger.info(
                            f"[FactorItemApproveView] وضعیت فاکتور {factor.id} به {factor.status} تغییر یافت، آیتم‌های پردازش‌شده: {items_processed_count}")
                        messages.success(request, _('تغییرات در وضعیت ردیف‌ها با موفقیت ثبت شد.'))
                    else:
                        logger.info(f"[FactorItemApproveView] هیچ تغییری برای فاکتور {factor.pk} ثبت نشد")
                        messages.info(request, _('هیچ تغییری برای ثبت وجود نداشت.'))

            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در پردازش فرم‌ست: {e}", exc_info=True)
                messages.error(request, _("خطا در ذخیره‌سازی تغییرات ردیف‌ها."))
                return self.render_to_response(self.get_context_data())

            else:
                logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است. خطاها: {formset.errors}")
                messages.error(request, _('لطفاً خطاهای فرم ردیف‌ها را بررسی کنید.'))
                return self.render_to_response(self.get_context_data())

        return redirect('factor_item_approve', pk=factor.pk)

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"[FactorItemApproveView] شروع dispatch برای کاربر: {request.user.username}, فاکتور: {self.kwargs.get('pk')}")
        return super().dispatch(request, *args, **kwargs)

    def _get_organization_from_object(self, obj):
        try:
            if isinstance(obj, Factor):
                return obj.tankhah.organization
            return super()._get_organization_from_object(obj)
        except AttributeError as e:
            logger.error(f"[FactorItemApproveView] خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0
        logger.info(f"[FactorItemApproveView] شروع get_context_data برای فاکتور {factor.pk}")

        formset = FactorItemApprovalFormSet(
            self.request.POST or None,
            instance=factor,
            prefix='items'
        )

        form_log_pairs = []
        for form in formset:
            item = form.instance
            latest_log = ApprovalLog.objects.filter(
                factor_item=item,
                action__in=['APPROVE', 'REJECT'],
                user=user
            ).select_related('user', 'post', 'stage').order_by('-timestamp').first()
            form_log_pairs.append((form, latest_log))

        # بررسی اقدام قبلی برای فاکتور یا آیتم‌ها
        has_previous_action = ApprovalLog.objects.filter(
            Q(tankhah=tankhah) | Q(factor__tankhah=tankhah),
            user=user,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()

        # بررسی اینکه آیا همه آیتم‌ها قبلاً توسط کاربر اقدام شده‌اند
        all_items_processed = all(
            ApprovalLog.objects.filter(
                factor_item=item,
                user=user,
                action__in=['APPROVE', 'REJECT']
            ).exists() for item in factor.items.all()
        ) if factor.items.exists() else False

        # فیلتر مراحل مجاز برای ارجاع
        allowed_stages = WorkflowStage.objects.filter(
            is_active=True,
            order__lte=max_change_level,
            entity_type='FACTOR'
        ).order_by('order')
        if not user.is_hq and user_post:
            allowed_stages = allowed_stages.filter(
                stageapprover__post=user_post.post,
                stageapprover__is_active=True
            ).distinct()

        context['form_log_pairs'] = form_log_pairs
        context['formset'] = formset
        context['approval_logs'] = ApprovalLog.objects.filter(
            Q(tankhah=tankhah) | Q(factor=factor)
        ).select_related('user', 'post', 'stage', 'factor_item').order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['can_edit'] = can_edit_approval(user, tankhah, tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and bool(allowed_stages) and not has_previous_action
        context['workflow_stages'] = allowed_stages
        context['show_payment_number'] = tankhah.status == 'APPROVED' and not tankhah.payment_number
        all_items_approved = all(
            item.status == 'APPROVED' for item in factor.items.all()) if factor.items.exists() else False
        context['can_final_approve_factor'] = context['can_edit'] and all_items_approved and not has_previous_action
        context['can_final_approve_tankhah'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in tankhah.factors.all()) and tankhah.current_stage.is_final_stage and not has_previous_action

        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level__lt=user_level,  # سطوح بالاتر (عدد کمتر)
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()

        if context['higher_approval_changed']:
            logger.warning(
                f"[FactorItemApproveView] تغییرات توسط سطح بالاتری (سطح < {user_level}) برای تنخواه {tankhah.number} اعمال شده است")


        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=tankhah,
            action='STAGE_CHANGE',
            comment__contains='تأیید نهایی'
        ).exists() or tankhah.status == 'APPROVED'
        context['has_previous_action'] = has_previous_action
        context['all_items_processed'] = all_items_processed

        logger.info(f"[FactorItemApproveView] تعداد جفت‌های فرم-لاگ: {len(form_log_pairs)}")
        logger.info(f"[FactorItemApproveView] can_edit: {context['can_edit']}, has_previous_action: {has_previous_action}, all_items_processed: {all_items_processed}")
        logger.info(f"[FactorItemApproveView] پایان get_context_data")
        return context

    def create_payment_order(self, factor, user):
        logger.info(f"[FactorItemApproveView] شروع ایجاد دستور پرداخت برای فاکتور {factor.pk}")
        try:
            with transaction.atomic():
                initial_po_stage = WorkflowStage.objects.filter(
                    entity_type='PAYMENTORDER',
                    order=1,
                    is_active=True
                ).first()
                if not initial_po_stage:
                    logger.error(
                        f"[FactorItemApproveView] مرحله اولیه گردش کار برای دستور پرداخت برای فاکتور {factor.number} یافت نشد")
                    messages.error(self.request, _("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
                    return

                tankhah_remaining = factor.tankhah.budget - factor.tankhah.spent
                if factor.amount > tankhah_remaining:
                    logger.error(
                        f"[FactorItemApproveView] بودجه تنخواه کافی نیست برای فاکتور {factor.number}: {factor.amount} > {tankhah_remaining}")
                    messages.error(self.request, _("بودجه تنخواه کافی نیست."))
                    return

                if factor.tankhah.project:
                    project_remaining = factor.tankhah.project.budget - factor.tankhah.project.spent
                    if factor.amount > project_remaining:
                        logger.error(
                            f"[FactorItemApproveView] بودجه پروژه کافی نیست برای فاکتور {factor.number}: {factor.amount} > {project_remaining}")
                        messages.error(self.request, _("بودجه پروژه کافی نیست."))
                        return

                user_post = user.userpost_set.filter(is_active=True).first()
                payment_order = PaymentOrder.objects.create(
                    tankhah=factor.tankhah,
                    related_tankhah=factor.tankhah,
                    amount=factor.amount,
                    description=f"پرداخت خودکار برای فاکتور {factor.number} (تنخواه: {factor.tankhah.number})",
                    organization=factor.tankhah.organization,
                    project=factor.tankhah.project,
                    status='DRAFT',
                    created_by=user,
                    created_by_post=user_post.post if user_post else None,
                    current_stage=initial_po_stage,
                    issue_date=timezone.now().date(),
                    payee=factor.payee or Payee.objects.filter(is_active=True).first(),
                    min_signatures=initial_po_stage.min_signatures or 1,
                    order_number=PaymentOrder().generate_payment_order_number()
                )
                payment_order.related_factors.add(factor)

                if factor.tankhah.budget_allocation:
                    BudgetTransaction.objects.create(
                        allocation=factor.tankhah.budget_allocation,
                        transaction_type='CONSUMPTION',
                        amount=factor.amount,
                        related_tankhah=factor.tankhah,
                        description=f"مصرف بودجه برای دستور پرداخت {payment_order.order_number}",
                        created_by=user,
                        transaction_id=f"TX-CONSUMPTION-{payment_order.pk}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                    )

                factor.tankhah.spent += factor.amount
                factor.tankhah.save(update_fields=['spent'])
                if factor.tankhah.project:
                    factor.tankhah.project.spent += factor.amount
                    factor.tankhah.project.save(update_fields=['spent'])

                approving_posts = StageApprover.objects.filter(
                    stage=initial_po_stage,
                    is_active=True
                ).values_list('post', flat=True)
                self.send_notifications(
                    entity=payment_order,
                    action='CREATED',
                    priority='HIGH',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد.",
                    recipients=approving_posts
                )
                logger.info(
                    f"[FactorItemApproveView] دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد")
                messages.success(self.request, f"دستور پرداخت {payment_order.order_number} ایجاد شد.")
        except Exception as e:
            logger.error(f"[FactorItemApproveView] خطا در ایجاد دستور پرداخت: {e}", exc_info=True)
            messages.error(self.request, _("خطا در ایجاد دستور پرداخت."))

    def send_notifications(self, entity, action, priority, description, recipients=None):
        logger.info(f"[FactorItemApproveView] ارسال اعلان برای {entity.__class__.__name__} {getattr(entity, 'number', entity.id)}: {action}")
        entity_type = entity.__class__.__name__.upper()
        content_type = ContentType.objects.get_for_model(entity.__class__)

        recipients = recipients or []
        users = CustomUser.objects.filter(
            userpost__post__in=recipients,
            userpost__is_active=True,
            userpost__post__organization=entity.tankhah.organization if hasattr(entity, 'tankhah') else entity.organization
        ).distinct()

        for user in users:
            notify.send(
                sender=self.request.user,
                recipient=user,
                verb=action.lower(),
                action_object=entity,
                description=description,
                level=priority.lower()
            )
            if user.email:
                send_mail(
                    subject=description,
                    message=f"{description}\nلطفاً {entity_type.lower()} {getattr(entity, 'number', entity.id)} را بررسی کنید.",
                    from_email='system@example.com',
                    recipient_list=[user.email],
                    fail_silently=True
                )
                logger.info(
                    f"[FactorItemApproveView] ایمیل ارسال شد به {user.email} برای {entity_type} {getattr(entity, 'number', entity.id)}")

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
        logger.info(
            f"[FactorItemApproveView] اعلان برای {entity_type} {getattr(entity, 'number', entity.id)} با اقدام {action} ارسال شد")