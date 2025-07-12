from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.forms import inlineformset_factory # Import inlineformset_factory
from django.shortcuts import redirect
from django.views.generic import DetailView

from core.PermissionBase import PermissionBaseView
from core.models import UserPost, WorkflowStage
from tankhah.forms import FactorItemApprovalForm
from tankhah.fun_can_edit_approval import can_edit_approval
from tankhah.models import Factor, FactorItem, ApprovalLog
from django.utils.translation import gettext_lazy as _


from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import redirect
from django.views.generic import DetailView
from core.views import PermissionBaseView
from core.models import UserPost, WorkflowStage
from tankhah.forms import FactorItemApprovalForm
from tankhah.models import Factor, FactorItem, ApprovalLog
from tankhah.fun_can_edit_approval import can_edit_approval
from django.utils.translation import gettext_lazy as _

import logging
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
    permission_required = 'tankhah.FactorItem_approve'
    context_object_name = 'factor'
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def _get_organization_from_object(self, obj):
        try:
            if isinstance(obj, Factor):
                return obj.tankhah.organization
            return super()._get_organization_from_object(obj)
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        logger.info(f"[ApproveView-Context] شروع get_context_data برای فاکتور {factor.pk}")

        formset = FactorItemApprovalFormSet(
            self.request.POST or None,
            instance=factor,
            prefix='items'
        )

        form_log_pairs = []
        for form in formset:
            item = form.instance
            logger.debug(f"[ApproveView-Context] بررسی آیتم: ID={item.id}, Status={item.status}")
            if not item.id:
                logger.warning(f"[ApproveView-Context] آیتم بدون ID یافت شد: {item}")
            latest_log = ApprovalLog.objects.filter(
                factor_item=item,
                action__in=['APPROVE', 'REJECT']
            ).select_related('user', 'post', 'stage').order_by('-timestamp').first()
            form_log_pairs.append((form, latest_log))

        context['form_log_pairs'] = form_log_pairs
        context['formset'] = formset
        context['approval_logs'] = ApprovalLog.objects.filter(
            Q(tankhah=tankhah) | Q(factor=factor)
        ).select_related('user', 'post', 'stage', 'factor_item').order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['can_edit'] = can_edit_approval(user, tankhah, tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and tankhah.current_stage.order < user_level
        context['workflow_stages'] = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('order')
        context['show_payment_number'] = tankhah.status == 'APPROVED' and not tankhah.payment_number
        all_items_approved = all(
            item.status == 'APPROVED' for item in factor.items.all()) if factor.items.exists() else False
        context['can_final_approve_factor'] = context['can_edit'] and all_items_approved
        context['can_final_approve_tankhah'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in tankhah.factors.all())
        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=tankhah, post__level__gt=user_level,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()
        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=tankhah, action='STAGE_CHANGE', comment__contains='تأیید نهایی'
        ).exists()

        logger.info(f"[ApproveView-Context] تعداد جفت‌های فرم-لاگ: {len(form_log_pairs)}")
        logger.info(f"[ApproveView-Context] پایان get_context_data")
        return context

    def post(self, request, *args, **kwargs):
        logger.info(f"[ApproveView-POST] درخواست POST دریافت شد برای فاکتور {self.kwargs.get('pk')}")
        self.object = self.get_object()
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        if not user_post:
            logger.error(f"[ApproveView-POST] کاربر {user.username} هیچ پست فعالی ندارد")
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('factor_item_approve', pk=factor.pk)
        user_level = user_post.post.level
        max_change_level = user_post.post.max_change_level

        logger.debug(f"[ApproveView-POST] کاربر: {user.username}, سطح: {user_level}, حداکثر تغییر: {max_change_level}")
        logger.debug(f"[ApproveView-POST] داده‌های POST: {request.POST}")

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)
        if not can_edit_approval(user, tankhah, tankhah.current_stage):
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا سطح بالاتری اقدام کرده است.'))
            return redirect('factor_item_approve', pk=factor.pk)

        if 'change_stage' in request.POST:
            try:
                new_stage_order = int(request.POST.get('new_stage_order'))
                if tankhah.current_stage.order >= user_level:
                    raise ValidationError(_('شما نمی‌توانید به مرحله برابر یا بالاتر تغییر دهید.'))
                if new_stage_order > max_change_level:
                    raise ValidationError(_(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))
                new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
                if not new_stage:
                    raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))

                with transaction.atomic():
                    old_stage_name = tankhah.current_stage.name
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING'
                    tankhah.save()
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='STAGE_CHANGE',
                        stage=new_stage,
                        comment=f"تغییر مرحله دستی از '{old_stage_name}' به '{new_stage.name}' توسط {user.get_full_name()}",
                        post=user_post.post
                    )
                messages.success(request, _(f"مرحله تنخواه به {new_stage.name} تغییر یافت."))
            except (ValueError, ValidationError, WorkflowStage.DoesNotExist) as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"[ApproveView-POST] خطای ناشناخته در تغییر مرحله: {e}", exc_info=True)
                messages.error(request, _("خطا در تغییر مرحله."))
            return redirect('factor_item_approve', pk=factor.pk)

        if request.POST.get('reject_factor'):
            with transaction.atomic():
                factor.status = 'REJECTED'
                factor.save()
                items_updated = FactorItem.objects.filter(factor=factor).update(status='REJECTED')
                logger.info(f"[ApproveView-POST] فاکتور {factor.pk} و {items_updated} آیتم آن رد شد توسط {user.username}")
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    factor=factor,
                    user=user,
                    action='REJECT',
                    stage=tankhah.current_stage,
                    comment=_('رد کامل فاکتور'),
                    post=user_post.post
                )
            messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
            return redirect('dashboard_flows')

        if request.POST.get('final_approve'):
            with transaction.atomic():
                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    current_stage_order = tankhah.current_stage.order
                    next_stage = WorkflowStage.objects.filter(order__gt=current_stage_order).order_by('order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تأیید نهایی و انتقال به {next_stage.name}",
                            post=user_post.post
                        )
                        messages.success(request, _(f"تأیید نهایی انجام و به مرحله {next_stage.name} منتقل شد."))
                        return redirect('dashboard_flows')
                    elif tankhah.current_stage.is_final_stage:
                        payment_number = request.POST.get('payment_number')
                        if payment_number:
                            tankhah.payment_number = payment_number
                            tankhah.status = 'PAID'
                            tankhah.save()
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                factor=factor,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=tankhah.current_stage,
                                comment=_('تأیید نهایی با شماره پرداخت'),
                                post=user_post.post
                            )
                            messages.success(request, _('تنخواه پرداخت شد.'))
                            return redirect('dashboard_flows')
                        else:
                            messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
                            return redirect('factor_item_approve', pk=factor.pk)
                    else:
                        messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                else:
                    messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
                return redirect('factor_item_approve', pk=factor.pk)

        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')

        if formset.is_valid():
            logger.info("[ApproveView-POST] فرم‌ست آیتم‌ها معتبر است.")
            try:
                with transaction.atomic():
                    logger.info("[ApproveView-POST] شروع تراکنش برای ذخیره تغییرات آیتم‌ها...")
                    has_changes = False
                    items_processed_count = 0

                    try:
                        content_type = ContentType.objects.get_for_model(FactorItem)
                        logger.debug(f"[ApproveView-POST] ContentType برای FactorItem: ID={content_type.id}, app_label={content_type.app_label}, model={content_type.model}")
                    except ContentType.DoesNotExist:
                        logger.error("[ApproveView-POST] ContentType برای FactorItem یافت نشد.")
                        messages.error(request, _("ContentType برای FactorItem یافت نشد."))
                        raise ValidationError(_("ContentType برای FactorItem یافت نشد."))

                    for form in formset:
                        if form.cleaned_data:
                            item = form.instance
                            logger.debug(f"[ApproveView-POST] پردازش آیتم: ID={item.id}, Status={item.status}")
                            if not item.id:
                                logger.error(f"[ApproveView-POST] آیتم بدون ID یافت شد: {item}")
                                messages.error(request, _(f"آیتم نامعتبر یافت شد: {item}"))
                                continue

                            status = form.cleaned_data.get('status')
                            description = form.cleaned_data.get('description', '')

                            if request.POST.get('bulk_approve') == 'on':
                                status = 'APPROVED'
                            elif request.POST.get('bulk_reject') == 'on':
                                status = 'REJECTED'

                            if status and status != 'NONE' and status != item.status:
                                logger.info(f"[ApproveView-POST] پردازش آیتم {item.id}: وضعیت='{status}', وضعیت فعلی='{item.status}'")
                                has_changes = True
                                items_processed_count += 1
                                action = 'APPROVE' if status == 'APPROVED' else 'REJECT' if status == 'REJECTED' else status

                                try:
                                    ApprovalLog.objects.create(
                                        tankhah=tankhah,
                                        factor=factor,
                                        factor_item=item,
                                        user=user,
                                        action=action,
                                        stage=tankhah.current_stage,
                                        comment=description,
                                        post=user_post.post,
                                        content_type=content_type,
                                        object_id=item.id
                                    )
                                    item.status = status
                                    form.save()
                                    logger.info(f"[ApproveView-POST] وضعیت آیتم {item.id} به {status} تغییر یافت و ذخیره شد.")
                                except Exception as e:
                                    logger.error(f"[ApproveView-POST] خطا در ایجاد ApprovalLog برای آیتم {item.id}: {e}", exc_info=True)
                                    messages.error(request, _(f"خطا در ثبت لاگ برای آیتم {item.id}: {str(e)}"))
                                    raise

                    if has_changes:
                        factor.refresh_from_db()
                        all_approved = True
                        any_rejected = False
                        items_exist = factor.items.exists()

                        if items_exist:
                            for item in factor.items.all():
                                if item.status == 'REJECTED':
                                    any_rejected = True
                                    all_approved = False
                                    break
                                elif item.status != 'APPROVED':
                                    all_approved = False
                        else:
                            all_approved = False

                        if any_rejected:
                            new_factor_status = 'PENDING'
                            messages.warning(request, _('برخی ردیف‌ها رد شدند. وضعیت فاکتور به حالت انتظار بازگشت.'))
                        elif all_approved and items_exist:
                            new_factor_status = 'APPROVED'
                            messages.success(request, _('تمام ردیف‌های معتبر تأیید شدند. می‌توانید تأیید نهایی را انجام دهید.'))
                        else:
                            new_factor_status = 'PENDING'
                            if items_exist:
                                messages.warning(request, _('لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.'))
                            else:
                                messages.warning(request, _('هیچ ردیفی برای فاکتور وجود ندارد.'))

                        if factor.status != new_factor_status:
                            factor.status = new_factor_status
                            factor.save(update_fields=['status'])
                            logger.info(f"[ApproveView-POST] وضعیت فاکتور {factor.id} به {new_factor_status} تغییر یافت.")

                        messages.success(request, _('تغییرات در وضعیت ردیف‌ها با موفقیت ثبت شد.'))
                    else:
                        messages.info(request, _('هیچ تغییری برای ثبت وجود نداشت.'))

            except ValidationError as e:
                logger.error(f"[ApproveView-POST] خطای اعتبارسنجی: {e}")
                messages.error(request, str(e))
                return self.render_to_response(self.get_context_data())
            except Exception as e:
                logger.error(f"[ApproveView-POST] خطا در حین پردازش فرم‌ست آیتم‌ها: {e}", exc_info=True)
                messages.error(request, _("خطا در ذخیره‌سازی تغییرات ردیف‌ها."))
                return self.render_to_response(self.get_context_data())

            return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"[ApproveView-POST] فرم‌ست نامعتبر است. خطاها: {formset.errors}")
            messages.error(request, _('لطفاً خطاهای فرم ردیف‌ها را بررسی کنید.'))
            context = self.get_context_data()
            return self.render_to_response(context)




class FactorItemApproveView____(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_required = 'tankhah.FactorItem_approve'
    context_object_name = 'factor'
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def _get_organization_from_object(self, obj):
        """استخراج سازمان برای Factor"""
        try:
            if isinstance(obj, Factor):
                return obj.tankhah.organization
            return super()._get_organization_from_object(obj)
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0
        logger = logging.getLogger('factor_approval')

        logger.info(f"[ApproveView-Context] شروع get_context_data برای فاکتور {factor.pk}")

        formset = FactorItemApprovalFormSet(
            self.request.POST or None,
            instance=factor,
            prefix='items'
        )

        # ایجاد لیست جفت‌های (form, latest_log)
        form_log_pairs = []
        for form in formset:
            item = form.instance
            latest_log = ApprovalLog.objects.filter(
                factor_item=item,
                action__in=['APPROVE', 'REJECT']
            ).select_related('user', 'post', 'stage').order_by('-timestamp').first()
            form_log_pairs.append((form, latest_log))

        context['form_log_pairs'] = form_log_pairs
        context['formset'] = formset
        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=tankhah).select_related('user', 'post', 'stage','factor_item').order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['can_edit'] = can_edit_approval(user, tankhah, tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and tankhah.current_stage.order < user_level
        context['workflow_stages'] = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('order')
        context['show_payment_number'] = tankhah.status == 'APPROVED' and not tankhah.payment_number
        all_items_approved = all(
            item.status == 'APPROVED' for item in factor.items.all()) if factor.items.exists() else False
        context['can_final_approve_factor'] = context['can_edit'] and all_items_approved
        context['can_final_approve_tankhah'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in tankhah.factors.all())
        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=tankhah, post__level__gt=user_level,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()
        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=tankhah, action='STAGE_CHANGE', comment__contains='تأیید نهایی'
        ).exists()

        logger.info(f"[ApproveView-Context] تعداد جفت‌های فرم-لاگ: {len(form_log_pairs)}")
        logger.info(f"[ApproveView-Context] پایان get_context_data")
        return context

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger('factor_approval')
        logger.info(f"[ApproveView-POST] درخواست POST دریافت شد.")
        self.object = self.get_object()
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        logger.debug(f"[ApproveView-POST] کاربر: {user.username}, سطح: {user_level}, حداکثر تغییر: {max_change_level}")
        logger.debug(f"[ApproveView-POST] داده‌های POST: {request.POST}")

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)
        if not can_edit_approval(user, tankhah, tankhah.current_stage):
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا سطح بالاتری اقدام کرده است.'))
            return redirect('factor_item_approve', pk=factor.pk)

        if 'change_stage' in request.POST:
            try:
                new_stage_order = int(request.POST.get('new_stage_order'))
                if tankhah.current_stage.order >= user_level:
                    raise ValidationError(_('شما نمی‌توانید به مرحله برابر یا بالاتر تغییر دهید.'))
                if new_stage_order > max_change_level:
                    raise ValidationError(_(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))
                new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
                if not new_stage:
                    raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))

                with transaction.atomic():
                    old_stage_name = tankhah.current_stage.name
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING'
                    tankhah.save()

                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        user=user,
                        action='STAGE_CHANGE',
                        stage=new_stage,
                        comment=f"تغییر مرحله دستی از '{old_stage_name}' به '{new_stage.name}' توسط {user.get_full_name()}",
                        post=user_post.post if user_post else None
                    )

                messages.success(request, _(f"مرحله تنخواه به {new_stage.name} تغییر یافت."))
            except (ValueError, ValidationError, WorkflowStage.DoesNotExist) as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"[ApproveView-POST] خطای ناشناخته در تغییر مرحله: {e}", exc_info=True)
                messages.error(request, _("خطا در تغییر مرحله."))
            return redirect('factor_item_approve', pk=factor.pk)

        if request.POST.get('reject_factor'):
            with transaction.atomic():
                factor.status = 'REJECTED'
                factor.save()
                items_updated = FactorItem.objects.filter(factor=factor).update(status='REJECTED')
                logger.info(f"[ApproveView-POST] فاکتور {factor.pk} و {items_updated} آیتم آن رد شد توسط {user.username}")
                ApprovalLog.objects.create(
                    tankhah=tankhah, factor=factor, user=user, action='REJECT', stage=tankhah.current_stage,
                    comment=_('رد کامل فاکتور'), post=user_post.post if user_post else None
                )
            messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
            return redirect('dashboard_flows')

        if request.POST.get('final_approve'):
            with transaction.atomic():
                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    current_stage_order = tankhah.current_stage.order
                    next_stage = WorkflowStage.objects.filter(order__gt=current_stage_order).order_by('order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تایید نهایی و انتقال به {next_stage.name}",
                            post=user_post.post if user_post else None
                        )
                        messages.success(request, _(f"تایید نهایی انجام و به مرحله {next_stage.name} منتقل شد."))
                        return redirect('dashboard_flows')
                    elif tankhah.current_stage.is_final_stage:
                        payment_number = request.POST.get('payment_number')
                        if payment_number:
                            tankhah.payment_number = payment_number
                            tankhah.status = 'PAID'
                            tankhah.save()
                            messages.success(request, _('تنخواه پرداخت شد.'))
                            return redirect('dashboard_flows')
                        else:
                            messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
                            return redirect('factor_item_approve', pk=factor.pk)
                    else:
                        messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                else:
                    messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
                return redirect('factor_item_approve', pk=factor.pk)

        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')

        if formset.is_valid():
            logger.info("[ApproveView-POST] فرم‌ست آیتم‌ها معتبر است.")
            try:
                with transaction.atomic():
                    logger.info("[ApproveView-POST] شروع تراکنش برای ذخیره تغییرات آیتم‌ها...")
                    has_changes = False
                    items_processed_count = 0

                    for form in formset:
                        if form.cleaned_data:
                            item = form.instance
                            status = form.cleaned_data.get('status')  # تغییر از action به status
                            description = form.cleaned_data.get('description', '')

                            if request.POST.get('bulk_approve') == 'on':
                                status = 'APPROVE'
                            elif request.POST.get('bulk_reject') == 'on':
                                status = 'REJECT'

                            if status and status != 'NONE' and status != item.status:
                                logger.info(f"[ApproveView-POST] پردازش آیتم {item.id}: وضعیت='{status}', وضعیت فعلی='{item.status}'")
                                has_changes = True
                                items_processed_count += 1
                                # نگاشت status به action برای ApprovalLog
                                action = 'APPROVE' if status == 'APPROVED' else 'REJECT' if status == 'REJECTED' else status

                                ApprovalLog.objects.create(
                                    tankhah=tankhah,
                                    factor_item=item,
                                    user=user,
                                    action=action,
                                    stage=tankhah.current_stage,
                                    comment=description,
                                    post=user_post.post if user_post else None,
                                    content_type=ContentType.objects.get_for_model(FactorItem),
                                    object_id=item.id
                                )
                                item.status = status
                                form.save()
                                logger.info(f"[ApproveView-POST] وضعیت آیتم {item.id} به {status} تغییر یافت و ذخیره شد.")

                    if has_changes:
                        factor.refresh_from_db()
                        all_approved = True
                        any_rejected = False
                        items_exist = factor.items.exists()

                        if items_exist:
                            for item in factor.items.all():
                                if item.status == 'REJECT':
                                    any_rejected = True
                                    all_approved = False
                                    break
                                elif item.status != 'APPROVE':
                                    all_approved = False
                        else:
                            all_approved = False

                        if any_rejected:
                            new_factor_status = 'PENDING'
                            messages.warning(request, _('برخی ردیف‌ها رد شدند. وضعیت فاکتور به حالت انتظار بازگشت.'))
                        elif all_approved and items_exist:
                            new_factor_status = 'APPROVED'
                            messages.success(request, _('تمام ردیف‌های معتبر تأیید شدند. می‌توانید تأیید نهایی را انجام دهید.'))
                        else:
                            new_factor_status = 'PENDING'
                            if items_exist:
                                messages.warning(request, _('لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.'))
                            else:
                                messages.warning(request, _('هیچ ردیفی برای فاکتور وجود ندارد.'))

                        if factor.status != new_factor_status:
                            factor.status = new_factor_status
                            factor.save(update_fields=['status'])
                            logger.info(f"[ApproveView-POST] وضعیت فاکتور {factor.id} به {new_factor_status} تغییر یافت.")

                        messages.success(request, _('تغییرات در وضعیت ردیف‌ها با موفقیت ثبت شد.'))
                    else:
                        messages.info(request, _('هیچ تغییری برای ثبت وجود نداشت.'))

            except Exception as e:
                logger.error(f"[ApproveView-POST] خطا در حین پردازش فرم‌ست آیتم‌ها: {e}", exc_info=True)
                messages.error(request, _("خطا در ذخیره‌سازی تغییرات ردیف‌ها."))
                return self.render_to_response(self.get_context_data())

            return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"[ApproveView-POST] فرم‌ست نامعتبر است.")
            messages.error(request, _('لطفاً خطاهای فرم ردیف‌ها را بررسی کنید.'))
            context = self.get_context_data()
            return self.render_to_response(context)
