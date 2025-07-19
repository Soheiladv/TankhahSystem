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
from tankhah.models import Factor, FactorItem, ApprovalLog, StageApprover, create_budget_transaction, FactorHistory
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

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        مدیریت درخواست‌های POST برای تأیید/رد آیتم‌های فاکتور، تغییر مرحله، یا تأیید نهایی.
        بودجه فقط در رد یا حذف فاکتور در مرحله ابتدایی آزاد می‌شود.
        """
        logger.info(
            f"[FactorItemApproveView] درخواست POST دریافت شد برای فاکتور {self.kwargs.get('pk')} توسط کاربر {request.user.username}"
        )
        logger.debug(f"[FactorItemApproveView] داده‌های POST: {request.POST}")

        # دریافت فاکتور و تنخواه
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

        # بررسی دسترسی اولیه
        if not user_post and not user.is_hq:
            logger.error(f"[FactorItemApproveView] کاربر {user.username} هیچ پست فعالی ندارد")
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('factor_item_approve', pk=factor.pk)

        # بررسی قفل بودن تنخواه یا فاکتور
        if tankhah.is_locked or tankhah.is_archived or factor.is_locked:
            logger.warning(
                f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است"
            )
            messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # بررسی دسترسی برای ویرایش در مرحله فعلی
        if not can_edit_approval(user, factor, tankhah.current_stage):  # استفاده از tankhah.current_stage
            logger.warning(
                f"[FactorItemApproveView] کاربر {user.username} دسترسی لازم برای ویرایش فاکتور {factor.number} ندارد"
            )
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # مدیریت تغییر مرحله
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
                        _(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است.")
                    )

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
                        is_active=True,
                        entity_type='FACTOR'
                    ).exists()
                    if not has_permission:
                        raise ValidationError(_("شما اجازه ارجاع به این مرحله را ندارید."))

                # آپدیت مرحله تنخواه (فاکتورها از تنخواه پیروی می‌کنند)
                old_stage_name = tankhah.current_stage.name
                tankhah.current_stage = new_stage
                tankhah.status = 'PENDING'
                tankhah.is_locked = (new_stage.order != 1)
                tankhah._changed_by = user
                tankhah.save(update_fields=['current_stage', 'status', 'is_locked'])
                factor.is_locked = (new_stage.order != 1)
                factor.save(update_fields=['is_locked'])

                # ثبت لاگ
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    factor=factor,
                    user=user,
                    action='STAGE_CHANGE',
                    stage=new_stage,
                    comment=f"انتقال به {new_stage.name}. توضیحات: {stage_change_reason}",
                    post=user_post.post if user_post else None
                )

                # ارسال اعلان
                approving_posts = StageApprover.objects.filter(
                    stage=new_stage,
                    is_active=True,
                    entity_type='FACTOR'
                ).values_list('post', flat=True)
                self.send_notifications(
                    entity=factor,
                    action='NEEDS_APPROVAL',
                    priority='MEDIUM',
                    description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {new_stage.name} دارد (توسط {user.username} ارجاع شد).",
                    recipients=approving_posts
                )
                logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} به مرحله {new_stage.name} تغییر یافت")
                messages.success(request, _(f"مرحله فاکتور به {new_stage.name} تغییر یافت."))
                return redirect('factor_item_approve', pk=factor.pk)
            except (ValueError, ValidationError) as e:
                logger.error(f"[FactorItemApproveView] خطا در تغییر مرحله: {e}", exc_info=True)
                messages.error(request, str(e))
                return redirect('factor_item_approve', pk=factor.pk)

        # مدیریت رد کامل فاکتور
        if request.POST.get('reject_factor'):
            logger.info(f"[FactorItemApproveView] درخواست رد کامل فاکتور {factor.pk}")
            try:
                rejected_reason = request.POST.get('rejected_reason', '').strip()
                if not rejected_reason:
                    raise ValidationError(_("دلیل رد فاکتور الزامی است."))

                # آپدیت وضعیت فاکتور
                factor.status = 'REJECTED'
                factor.is_locked = True
                factor.rejected_reason = rejected_reason
                factor._changed_by = user
                factor.save()

                # آپدیت آیتم‌های فاکتور
                items_updated = FactorItem.objects.filter(factor=factor).update(status='REJECTED')

                # ثبت لاگ
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    factor=factor,
                    user=user,
                    action='REJECT',
                    stage=tankhah.current_stage,
                    comment=f"رد کامل فاکتور: {rejected_reason}",
                    post=user_post.post if user_post else None
                )

                # آزاد کردن بودجه فقط در مرحله ابتدایی
                if tankhah.current_stage.order == 1:
                    create_budget_transaction(
                        allocation=tankhah.project_budget_allocation,
                        transaction_type='RETURN',
                        amount=factor.amount,
                        related_obj=factor,
                        created_by=user,
                        description=f"بازگشت بودجه به دلیل رد فاکتور {factor.number} در مرحله ابتدایی",
                        transaction_id=f"TX-FAC-RET-{factor.number}"
                    )
                    tankhah.remaining_budget += factor.amount
                    tankhah.save(update_fields=['remaining_budget'])

                # ثبت تاریخچه
                FactorHistory.objects.create(
                    factor=factor,
                    change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                    changed_by=user,
                    old_data={'status': 'PENDING'},
                    new_data={'status': 'REJECTED'},
                    description=f"فاکتور به دلیل {rejected_reason} رد شد"
                )

                # ارسال اعلان
                self.send_notifications(
                    entity=factor,
                    action='REJECTED',
                    priority='HIGH',
                    description=f"فاکتور {factor.number} رد شد. دلیل: {rejected_reason} (توسط {user.username}).",
                    recipients=[factor.created_by_post] if factor.created_by_post else []
                )
                logger.info(
                    f"[FactorItemApproveView] فاکتور {factor.pk} و {items_updated} آیتم آن رد شد توسط {user.username}"
                )
                messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
                return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در رد فاکتور: {e}", exc_info=True)
                messages.error(request, _("خطا در رد فاکتور."))
                return redirect('factor_item_approve', pk=factor.pk)

        # مدیریت تأیید نهایی
        if request.POST.get('final_approve'):
            logger.info(f"[FactorItemApproveView] درخواست تأیید نهایی برای فاکتور {factor.pk}")
            try:
                # بررسی مرحله آخر
                if tankhah.current_stage.is_final_stage:
                    # بررسی بودجه
                    if factor.amount > tankhah.get_remaining_budget():
                        logger.error(
                            f"[FactorItemApproveView] بودجه تنخواه کافی نیست برای فاکتور {factor.number}"
                        )
                        messages.error(request, _("بودجه تنخواه کافی نیست."))
                        return redirect('factor_item_approve', pk=factor.pk)

                    # بررسی شماره پرداخت
                    payment_number = request.POST.get('payment_number')
                    if tankhah.current_stage.triggers_payment_order and not payment_number:
                        logger.error(
                            f"[FactorItemApproveView] شماره پرداخت برای فاکتور {factor.number} ارائه نشده است"
                        )
                        messages.error(request, _("برای مرحله نهایی، شماره پرداخت الزامی است."))
                        return redirect('factor_item_approve', pk=factor.pk)

                    # آپدیت وضعیت فاکتور
                    factor.status = 'APPROVED'
                    factor.is_locked = True
                    factor._changed_by = user
                    factor.save()

                    # ایجاد دستور پرداخت
                    if tankhah.current_stage.triggers_payment_order:
                        self.create_payment_order(factor, user, payment_number)

                    # ثبت لاگ
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='APPROVE',
                        stage=tankhah.current_stage,
                        comment=_('تأیید نهایی فاکتور'),
                        post=user_post.post if user_post else None
                    )

                    # ثبت تاریخچه
                    FactorHistory.objects.create(
                        factor=factor,
                        change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                        changed_by=user,
                        old_data={'status': 'PENDING'},
                        new_data={'status': 'APPROVED'},
                        description="فاکتور تأیید نهایی شد"
                    )

                    # ارسال اعلان
                    hq_posts = Post.objects.filter(organization__org_type__org_type='HQ')
                    self.send_notifications(
                        entity=factor,
                        action='APPROVED',
                        priority='HIGH',
                        description=f"فاکتور {factor.number} تأیید نهایی شد (توسط {user.username}).",
                        recipients=hq_posts
                    )

                    # بررسی قفل تنخواه
                    all_factors_approved = all(
                        f.status == 'APPROVED' and tankhah.current_stage.is_final_stage
                        for f in tankhah.factors.all()
                    )
                    if all_factors_approved:
                        tankhah.status = 'APPROVED'
                        tankhah.is_locked = True
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['status', 'is_locked'])
                        self.send_notifications(
                            entity=tankhah,
                            action='APPROVED',
                            priority='HIGH',
                            description=f"تنخواه {tankhah.number} قفل شد چون همه فاکتورها تأیید شدند (توسط {user.username}).",
                            recipients=hq_posts
                        )
                        logger.info(f"[FactorItemApproveView] تنخواه {tankhah.number} قفل شد")
                        messages.success(request, _('تنخواه قفل شد چون همه فاکتورها تأیید شدند.'))
                    else:
                        messages.success(request, _('فاکتور تأیید نهایی شد و دستور پرداخت ایجاد شد.'))

                    return redirect('dashboard_flows')
                else:
                    # انتقال به مرحله بعدی
                    approved_reason = request.POST.get('approved_reason', '').strip()
                    if not approved_reason:
                        raise ValidationError(_("توضیحات تأیید الزامی است."))

                    next_stage = WorkflowStage.objects.filter(
                        order__gt=tankhah.current_stage.order,
                        is_active=True,
                        entity_type='FACTOR'
                    ).order_by('order').first()
                    if not next_stage:
                        logger.error(
                            f"[FactorItemApproveView] مرحله بعدی برای فاکتور {factor.number} تعریف نشده است"
                        )
                        messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                    tankhah.current_stage = next_stage
                    tankhah.status = 'PENDING'
                    tankhah.is_locked = (next_stage.order != 1)
                    tankhah._changed_by = user
                    tankhah.save(update_fields=['current_stage', 'status', 'is_locked'])
                    factor.is_locked = (next_stage.order != 1)
                    factor.save(update_fields=['is_locked'])

                    # ثبت لاگ
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='STAGE_CHANGE',
                        stage=next_stage,
                        comment=f"تأیید و انتقال به {next_stage.name}. توضیحات: {approved_reason}",
                        post=user_post.post if user_post else None
                    )

                    # ارسال اعلان
                    approving_posts = StageApprover.objects.filter(
                        stage=next_stage,
                        is_active=True,
                        entity_type='FACTOR'
                    ).values_list('post', flat=True)
                    self.send_notifications(
                        entity=factor,
                        action='NEEDS_APPROVAL',
                        priority='MEDIUM',
                        description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.name} دارد (توسط {user.username}).",
                        recipients=approving_posts
                    )
                    logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} به مرحله {next_stage.name} منتقل شد")
                    messages.success(request, _(f"فاکتور به مرحله {next_stage.name} منتقل شد."))
                    return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در تأیید نهایی: {e}", exc_info=True)
                messages.error(request, _("خطا در تأیید نهایی."))
                return redirect('factor_item_approve', pk=factor.pk)

        # مدیریت فرم‌ست آیتم‌ها
        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')
        if formset.is_valid():
            logger.info("[FactorItemApproveView] فرم‌ست آیتم‌ها معتبر است")
            try:
                has_changes = False
                items_processed_count = 0
                content_type = ContentType.objects.get_for_model(FactorItem)

                for form in formset:
                    logger.debug(
                        f"[FactorItemApproveView] داده‌های فرم برای آیتم {form.instance.id}: {form.cleaned_data}"
                    )
                    if form.cleaned_data:
                        item = form.instance
                        if not item.id:
                            logger.error(f"[FactorItemApproveView] آیتم بدون ID یافت شد: {item}")
                            continue
                        logger.debug(f"[FactorItemApproveView] وضعیت فعلی آیتم {item.id}: {item.status}")
                        status = form.cleaned_data.get('status')
                        description = form.cleaned_data.get('description', '').strip()

                        # مدیریت اقدامات گروهی
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
                            f"[FactorItemApproveView] آیتم {item.id}: status={status}, description={description}"
                        )

                        # ثبت تغییرات آیتم
                        if status and status != 'NONE' and (status != item.status or user.is_superuser or is_hq_user):
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
                            item._changed_by = user
                            item.save()
                            logger.info(f"[FactorItemApproveView] وضعیت آیتم {item.id} به {status} تغییر یافت")

                # بررسی وضعیت فاکتور
                all_approved = factor.items.exists() and all(
                    item.status == 'APPROVED' for item in factor.items.all()
                )
                any_rejected = any(item.status == 'REJECTED' for item in factor.items.all())

                if any_rejected:
                    factor.status = 'REJECTED'
                    factor.rejected_reason = request.POST.get('rejected_reason', 'یکی از آیتم‌ها رد شده است')
                    factor.is_locked = True
                    factor._changed_by = user
                    factor.save()
                    # آزاد کردن بودجه فقط در مرحله ابتدایی
                    if tankhah.current_stage.order == 1:
                        create_budget_transaction(
                            allocation=tankhah.project_budget_allocation,
                            transaction_type='RETURN',
                            amount=factor.amount,
                            related_obj=factor,
                            created_by=user,
                            description=f"بازگشت بودجه به دلیل رد آیتم‌های فاکتور {factor.number} در مرحله ابتدایی",
                            transaction_id=f"TX-FAC-RET-{factor.number}"
                        )
                        tankhah.remaining_budget += factor.amount
                        tankhah.save(update_fields=['remaining_budget'])

                    # ثبت تاریخچه
                    FactorHistory.objects.create(
                        factor=factor,
                        change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                        changed_by=user,
                        old_data={'status': 'PENDING'},
                        new_data={'status': 'REJECTED'},
                        description=f"فاکتور به دلیل رد آیتم‌ها رد شد: {factor.rejected_reason}"
                    )

                    # ارسال اعلان
                    self.send_notifications(
                        entity=factor,
                        action='REJECTED',
                        priority='HIGH',
                        description=f"فاکتور {factor.number} به دلیل رد آیتم‌ها رد شد. دلیل: {factor.rejected_reason} (توسط {user.username}).",
                        recipients=[factor.created_by_post] if factor.created_by_post else []
                    )
                    logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} به دلیل رد آیتم‌ها رد شد")
                    messages.warning(request, _('فاکتور به دلیل رد آیتم‌ها رد شد.'))
                    return redirect('dashboard_flows')
                elif all_approved:
                    factor.status = 'APPROVED'
                    factor.is_locked = True
                    factor._changed_by = user
                    factor.save()
                    # بررسی مرحله بعدی یا ایجاد دستور پرداخت
                    if tankhah.current_stage.is_final_stage:
                        self.create_payment_order(factor, user)
                        # ثبت تاریخچه
                        FactorHistory.objects.create(
                            factor=factor,
                            change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                            changed_by=user,
                            old_data={'status': 'PENDING'},
                            new_data={'status': 'APPROVED'},
                            description="تمام آیتم‌های فاکتور تأیید شدند"
                        )
                        logger.info(f"[FactorItemApproveView] تمام آیتم‌های فاکتور {factor.pk} تأیید شدند")
                        messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند و دستور پرداخت ایجاد شد.'))

                        # بررسی قفل تنخواه
                        all_factors_approved = all(
                            f.status == 'APPROVED' and tankhah.current_stage.is_final_stage
                            for f in tankhah.factors.all()
                        )
                        if all_factors_approved:
                            tankhah.status = 'APPROVED'
                            tankhah.is_locked = True
                            tankhah._changed_by = user
                            tankhah.save(update_fields=['status', 'is_locked'])
                            self.send_notifications(
                                entity=tankhah,
                                action='APPROVED',
                                priority='HIGH',
                                description=f"تنخواه {tankhah.number} قفل شد چون همه فاکتورها تأیید شدند (توسط {user.username}).",
                                recipients=Post.objects.filter(organization__org_type__org_type='HQ')
                            )
                            logger.info(f"[FactorItemApproveView] تنخواه {tankhah.number} قفل شد")
                            messages.success(request, _('تنخواه قفل شد چون همه فاکتورها تأیید شدند.'))
                        return redirect('dashboard_flows')
                    else:
                        next_stage = WorkflowStage.objects.filter(
                            order__gt=tankhah.current_stage.order,
                            is_active=True,
                            entity_type='FACTOR'
                        ).order_by('order').first()
                        if not next_stage:
                            logger.error(
                                f"[FactorItemApproveView] مرحله بعدی برای فاکتور {factor.number} تعریف نشده است"
                            )
                            messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.is_locked = (next_stage.order != 1)
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['current_stage', 'status', 'is_locked'])
                        factor.is_locked = (next_stage.order != 1)
                        factor.save(update_fields=['is_locked'])
                        # ثبت لاگ
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تأیید آیتم‌ها و انتقال به {next_stage.name}",
                            post=user_post.post if user_post else None
                        )
                        # ثبت تاریخچه
                        FactorHistory.objects.create(
                            factor=factor,
                            change_type=FactorHistory.ChangeType.STATUS_CHANGE,
                            changed_by=user,
                            old_data={'status': 'PENDING'},
                            new_data={'status': 'PENDING', 'stage': next_stage.name},
                            description=f"فاکتور به مرحله {next_stage.name} منتقل شد"
                        )
                        # ارسال اعلان
                        approving_posts = StageApprover.objects.filter(
                            stage=next_stage,
                            is_active=True,
                            entity_type='FACTOR'
                        ).values_list('post', flat=True)
                        self.send_notifications(
                            entity=factor,
                            action='NEEDS_APPROVAL',
                            priority='MEDIUM',
                            description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.name} دارد (توسط {user.username}).",
                            recipients=approving_posts
                        )
                        logger.info(
                            f"[FactorItemApproveView] فاکتور {factor.pk} به مرحله {next_stage.name} منتقل شد"
                        )
                        messages.success(request, _(f"فاکتور به مرحله {next_stage.name} منتقل شد."))
                        return redirect('dashboard_flows')
                else:
                    factor.status = 'PENDING'
                    factor._changed_by = user
                    factor.save()
                    logger.info(f"[FactorItemApproveView] فاکتور {factor.pk} در حالت PENDING باقی ماند")
                    messages.warning(request, _('لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.'))
                    return redirect('factor_item_approve', pk=factor.pk)

                if has_changes:
                    logger.info(
                        f"[FactorItemApproveView] وضعیت فاکتور {factor.id} به {factor.status} تغییر یافت، آیتم‌های پردازش‌شده: {items_processed_count}"
                    )
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

    def create_payment_order(self, factor, user, payment_number=None):
        """
        ایجاد دستور پرداخت برای فاکتور تأییدشده در مرحله نهایی.
        بودجه از remaining_budget به spent منتقل می‌شود.
        """
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
                        f"[FactorItemApproveView] مرحله اولیه گردش کار برای دستور پرداخت یافت نشد"
                    )
                    messages.error(self.request, _("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
                    return

                # بررسی بودجه
                tankhah = factor.tankhah
                if factor.amount > tankhah.get_remaining_budget():
                    logger.error(
                        f"[FactorItemApproveView] بودجه تنخواه کافی نیست برای فاکتور {factor.number}"
                    )
                    messages.error(self.request, _("بودجه تنخواه کافی نیست."))
                    return

                # بررسی بودجه پروژه (در صورت وجود)
                if tankhah.project_budget_allocation:
                    project_remaining = tankhah.project_budget_allocation.get_remaining_amount()
                    if factor.amount > project_remaining:
                        logger.error(
                            f"[FactorItemApproveView] بودجه پروژه کافی نیست برای فاکتور {factor.number}"
                        )
                        messages.error(self.request, _("بودجه پروژه کافی نیست."))
                        return

                user_post = user.userpost_set.filter(is_active=True).first()
                # ایجاد دستور پرداخت
                payment_order = PaymentOrder.objects.create(
                    tankhah=tankhah,
                    related_tankhah=tankhah,
                    amount=factor.amount,
                    description=f"پرداخت خودکار برای فاکتور {factor.number} (تنخواه: {tankhah.number})",
                    organization=tankhah.organization,
                    project=tankhah.project,
                    status='DRAFT',
                    created_by=user,
                    created_by_post=user_post.post if user_post else None,
                    current_stage=initial_po_stage,
                    issue_date=timezone.now().date(),
                    payee=factor.payee or Payee.objects.filter(is_active=True).first(),
                    min_signatures=initial_po_stage.min_signatures or 1,
                    order_number=PaymentOrder().generate_payment_order_number(),
                    payment_number=payment_number
                )
                payment_order.related_factors.add(factor)

                # ثبت تراکنش مصرف بودجه
                create_budget_transaction(
                    allocation=tankhah.project_budget_allocation,
                    transaction_type='CONSUMPTION',
                    amount=factor.amount,
                    related_obj=factor,
                    created_by=user,
                    description=f"مصرف بودجه برای دستور پرداخت {payment_order.order_number}",
                    transaction_id=f"TX-PO-CONS-{payment_order.order_number}"
                )
                tankhah.remaining_budget -= factor.amount
                tankhah.save(update_fields=['remaining_budget'])

                # ارسال اعلان
                approving_posts = StageApprover.objects.filter(
                    stage=initial_po_stage,
                    is_active=True,
                    entity_type='PAYMENTORDER'
                ).values_list('post', flat=True)
                self.send_notifications(
                    entity=payment_order,
                    action='CREATED',
                    priority='HIGH',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد (توسط {user.username}).",
                    recipients=approving_posts
                )
                logger.info(
                    f"[FactorItemApproveView] دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد"
                )
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