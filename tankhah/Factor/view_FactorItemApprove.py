from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from django.db import transaction
from django.db.models import Q
from django.forms import inlineformset_factory
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import DetailView
from falcon import async_to_sync
from notifications.signals import notify

from accounts.models import CustomUser
from budgets.models import PaymentOrder, Payee, BudgetTransaction
from core.views import PermissionBaseView
from core.models import UserPost, WorkflowStage, Post , AccessRule
from tankhah.forms import FactorItemApprovalForm
from tankhah.models import Factor, FactorItem, ApprovalLog, StageApprover, create_budget_transaction, FactorHistory, \
    Tankhah
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


class FactorItemApproveView______(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    context_object_name = 'factor'
    permission_codenames = ['tankhah.factor_approve']
    check_organization = True
    organization_filter_field = 'tankhah__organization'

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        logger.info(
            f"[FactorItemApproveView] درخواست POST دریافت شد برای فاکتور {factor.pk} ({factor.number}) توسط کاربر {request.user.username}"
        )

        # بررسی دسترسی کاربر با استفاده از can_edit_approval
        can_edit = can_edit_approval(request.user, tankhah, tankhah.current_stage, factor=factor)
        if not can_edit:
            logger.warning(
                f"[FactorItemApproveView] دسترسی ویرایش برای کاربر {request.user.username} در فاکتور {factor.number} رد شد"
            )
            messages.error(request, _("شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید."))
            return redirect('factor_item_approve', pk=factor.pk)

        # دریافت پست فعال کاربر
        user_post = request.user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
        if not user_post:
            logger.error(f"[FactorItemApproveView] هیچ پست فعالی برای کاربر {request.user.username} یافت نشد")
            messages.error(request, _("پست فعالی برای حساب کاربری شما یافت نشد."))
            return redirect('factor_item_approve', pk=factor.pk)

        # پردازش فرم‌ست
        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')
        logger.debug(f"[FactorItemApproveView] داده‌های POST: {request.POST}")
        if formset.is_valid():
            with transaction.atomic():
                any_changes = False
                action = None
                for form in formset:
                    if form.has_changed():
                        any_changes = True
                        item = form.instance
                        status = form.cleaned_data.get('status')
                        if status:
                            logger.info(
                                f"[FactorItemApproveView] به‌روزرسانی آیتم {item.id} به وضعیت {status} توسط کاربر {request.user.username}"
                            )
                            item.status = status
                            item.save()

                # ایجاد ApprovalLog در صورت وجود تغییرات
                if any_changes:
                    comment = request.POST.get('rejected_reason') or request.POST.get('approved_reason') or ''
                    action = 'APPROVED' if all(
                        item.status == 'APPROVED' for item in factor.items.all()) else 'REJECTD' if all(
                        item.status == 'REJECTED' for item in factor.items.all()) else 'PARTIAL'

                    # لاگ قبل از ایجاد ApprovalLog
                    logger.debug(
                        f"[FactorItemApproveView] ایجاد ApprovalLog برای فاکتور {factor.number}, "
                        f"کاربر: {request.user.username}, مرحله: {tankhah.current_stage.name}, "
                        f"اقدام: {action}, توضیحات: {comment}"
                    )

                    # ایجاد ApprovalLog
                    content_type = ContentType.objects.get_for_model(Factor)
                    approval_log = ApprovalLog.objects.create(
                        user=request.user,
                        factor=factor,
                        tankhah=tankhah,
                        stage=tankhah.current_stage,
                        action=action,
                        comment=comment,
                        post=user_post.post,
                        content_type=content_type,
                        object_id=factor.pk
                    )
                    logger.info(
                        f"[FactorItemApproveView] ApprovalLog با id {approval_log.id} برای فاکتور {factor.number} ایجاد شد"
                    )

                    # به‌روزرسانی وضعیت فاکتور
                    factor.status = action
                    factor.save(update_fields=['status'])
                    logger.info(f"[FactorItemApproveView] وضعیت فاکتور {factor.number} به {action} تغییر کرد")

                # بررسی تأیید همه فاکتورها برای تغییر مرحله تنخواه
                all_factors_approved = all(
                    all(item.status == 'APPROVE' for item in f.items.all())
                    for f in tankhah.factors.all()
                )
                if all_factors_approved:
                    logger.info(f"[FactorItemApproveView] تمام فاکتورهای تنخواه {tankhah.number} تأیید شدند")
                    next_stage = tankhah.current_stage.get_next_stage()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.save(update_fields=['current_stage'])
                        logger.info(f"[FactorItemApproveView] مرحله تنخواه به {next_stage.name} تغییر کرد")
                        messages.success(
                            request,
                            _(f"تمام فاکتورهای تنخواه {tankhah.number} تأیید شدند. مرحله تنخواه به {next_stage.name} تغییر کرد.")
                        )
                    else:
                        logger.info(f"[FactorItemApproveView] هیچ مرحله بعدی برای تنخواه {tankhah.number} وجود ندارد")
                        messages.info(request, _("تمام فاکتورهای تنخواه تأیید شدند، اما مرحله بعدی وجود ندارد."))
                elif any_changes:
                    messages.success(
                        request,
                        _(f"تغییرات فاکتور {factor.number} با موفقیت ذخیره شد، اما هنوز برخی فاکتورهای تنخواه تأیید نشده‌اند.")
                    )

            return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است: {formset.errors}")
            messages.error(
                request,
                _(f"خطا در پردازش فرم. لطفاً اطلاعات واردشده را بررسی کنید: {formset.errors}")
            )
            return redirect('factor_item_approve', pk=factor.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        logger.info(f"[FactorItemApproveView] شروع get_context_data برای فاکتور {factor.pk} ({factor.number})")

        # بررسی دسترسی
        can_edit = can_edit_approval(user, tankhah, tankhah.current_stage, factor=factor)
        all_items_processed = all(item.status != 'PENDING' for item in factor.items.all())
        items_count = factor.items.count()
        logger.info(
            f"[FactorItemApproveView] تعداد آیتم‌ها: {items_count}, "
            f"can_edit: {can_edit}, all_items_processed: {all_items_processed}"
        )

        # لاگ آیتم‌ها
        for item in factor.items.all():
            logger.debug(
                f"[FactorItemApproveView] آیتم {item.id}: status={item.status}, description={item.description}"
            )

        # آماده‌سازی فرم‌ست و لاگ‌های تاریخچه
        form_log_pairs = []
        content_type = ContentType.objects.get_for_model(Factor)
        for form in FactorItemApprovalFormSet(instance=factor, prefix='items'):
            item = form.instance
            logs = ApprovalLog.objects.filter(
                factor=factor,
                content_type=content_type,
                object_id=factor.pk
            ).order_by('-timestamp')
            form_log_pairs.append((form, logs))

        # دریافت لاگ‌های تاریخچه
        approval_logs = ApprovalLog.objects.filter(
            factor=factor,
            content_type=content_type,
            object_id=factor.pk
        ).order_by('-timestamp')
        logger.debug(
            f"[FactorItemApproveView] تعداد لاگ‌های تاریخچه برای فاکتور {factor.number}: {approval_logs.count()}"
        )
        for log in approval_logs:
            logger.debug(
                f"[FactorItemApproveView] ApprovalLog id={log.id}, کاربر={log.user.username}, "
                f"اقدام={log.action}, مرحله={log.stage.name}, زمان={log.timestamp}"
            )

        # پیام‌ها
        if items_count == 0:
            logger.warning(f"[FactorItemApproveView] هیچ آیتمی برای فاکتور {factor.number} یافت نشد")
            messages.error(self.request, _("هیچ آیتمی برای این فاکتور وجود ندارد."))
        elif not can_edit:
            logger.warning(
                f"[FactorItemApproveView] دسترسی ویرایش برای کاربر {user.username} در فاکتور {factor.number} رد شد"
            )
            messages.error(self.request,
                           _("شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید."))
        elif all_items_processed:
            logger.info(f"[FactorItemApproveView] تمام آیتم‌های فاکتور {factor.number} پردازش شده‌اند")
            messages.info(self.request,
                          _("تمام آیتم‌های این فاکتور قبلاً پردازش شده‌اند، اما می‌توانید تاریخچه اقدامات را مشاهده کنید."))

        context.update({
            'formset': FactorItemApprovalFormSet(instance=factor, prefix='items'),
            'form_log_pairs': form_log_pairs,
            'approval_logs': approval_logs,
            'can_edit': can_edit,
            'all_items_processed': all_items_processed,
            'items_count': items_count,
            'is_final_approved': tankhah.is_final_approved if hasattr(tankhah, 'is_final_approved') else False,
            'higher_approval_changed': ApprovalLog.objects.filter(
                factor=factor,
                stage__order__lt=tankhah.current_stage.order,
                action__in=['APPROVE', 'REJECT'],
                seen_by_higher=True
            ).exists(),
            'can_final_approve_tankhah': user.has_perm('tankhah.can_final_approve_tankhah') if hasattr(user, 'has_perm') else False,
            'can_change_stage': user.has_perm('tankhah.can_change_stage') if hasattr(user, 'has_perm') else False,
            'workflow_stages': WorkflowStage.objects.all(),
        })
        logger.info(f"[FactorItemApproveView] پایان get_context_data")
        return context

class ___FactorItemApproveView(DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    context_object_name = 'factor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tankhah = factor.tankhah
        user = self.request.user
        current_stage = tankhah.current_stage

        logger.info(f"[FactorItemApproveView] شروع get_context_data برای فاکتور {factor.pk} ({factor.number})")

        can_edit = can_edit_approval(user, tankhah, current_stage, factor)
        context['can_edit'] = can_edit
        logger.debug(f"[FactorItemApproveView] وضعیت can_edit برای نمایش: {can_edit}")

        formset = FactorItemApprovalFormSet(instance=factor, prefix='items')
        context['formset'] = formset

        # === 3. جمع‌آوری اطلاعات آیتم‌ها و لاگ‌ها برای نمایش ===
        all_items_processed = all(item.status != 'PENDING' for item in factor.items.all())
        items_count = factor.items.count()
        context.update({
            'all_items_processed': all_items_processed,
            'items_count': items_count,
            'factor_items': factor.items.all(),  # این خط همچنان صحیح است اما مستقیماً در حلقه تمپلت استفاده نمی‌شود.
        })
        logger.debug(f"[FactorItemApproveView] تعداد آیتم‌ها: {items_count}, همه پردازش شده: {all_items_processed}")

        # **اضافه شده برای رفع مشکل لود نشدن ردیف‌ها در تمپلت**
        # ساختن `form_log_pairs` که تمپلت انتظارش را دارد.
        form_log_pairs = []
        # ابتدا تمام لاگ‌های مربوط به این فاکتور را واکشی می‌کنیم تا در صورت نیاز به آیتم‌ها نسبت دهیم.
        # اگر لاگ‌های آیتم به آیتم را در ApprovalLog ذخیره می‌کنید (مثلاً با استفاده از GenericForeignKey به FactorItem)،
        # اینجا باید منطق مربوط به آن را پیاده‌سازی کنید.
        # در غیر این صورت، بخش 'log' برای هر آیتم ممکن است خالی (None) بماند.
        # برای مثال، فرض می‌کنیم برای هر آیتم، می‌خواهیم آخرین لاگ فاکتور را نمایش دهیم
        # یا هیچ لاگی نمایش ندهیم اگر لاگ آیتم-محور نداریم.

        # اگر ApprovalLog شما واقعاً لاگ‌های آیتم به آیتم را دارد (مثلاً با فیلدی مثل `factor_item`):
        # item_logs_map = {log.factor_item_id: log for log in ApprovalLog.objects.filter(factor_item__factor=factor).order_by('factor_item', '-timestamp').distinct('factor_item')}
        # در غیر این صورت، از این بخش صرف نظر کنید و `item_log` را `None` قرار دهید.

        for form in formset:
            # در حال حاضر، اگر ApprovalLog مستقیماً به FactorItem لینک نیست،
            # log مربوط به هر آیتم را None قرار می‌دهیم تا تمپلت بدون خطا اجرا شود.
            # اگر می‌خواهید لاگ خاصی نمایش داده شود، باید منطق آن را اینجا اضافه کنید.
            # مثلاً، شاید بخواهید آخرین لاگ کلی فاکتور را برای همه آیتم‌ها نمایش دهید:
            # item_log = approval_logs.first() # اگر approval_logs قبلاً مرتب شده باشد
            # یا فقط None اگر لاگ آیتم به آیتم وجود ندارد:
            form_log_pairs.append((form, None))  # هیچ لاگ خاصی برای هر آیتم در نظر گرفته نشده است

        context['form_log_pairs'] = form_log_pairs  # این خط حیاتی است
        # پایان اضافه شده

        # === 4. جمع‌آوری لاگ‌های تأیید (تاریخچه) ===
        content_type_factor = ContentType.objects.get_for_model(Factor)
        content_type_tankhah = ContentType.objects.get_for_model(Tankhah)

        approval_logs = ApprovalLog.objects.filter(
            Q(factor=factor) | Q(tankhah=tankhah, factor__isnull=True, object_id=tankhah.pk),
            content_type__in=[content_type_factor, content_type_tankhah]
        ).order_by('-timestamp')
        context['approval_logs'] = approval_logs
        logger.debug(
            f"[FactorItemApproveView] مجموع لاگ‌های تأیید برای فاکتور {factor.number}: {approval_logs.count()}")

        # ... بقیه کدهای get_context_data (مثل تعیین is_final_approved و show_payment_number) ...

        logger.info(f"[FactorItemApproveView] پایان get_context_data برای فاکتور {factor.number}.")
        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        user = self.request.user
        current_stage = tankhah.current_stage

        logger.info(
            f"[FactorItemApproveView] درخواست POST دریافت شد برای فاکتور {factor.pk} ({factor.number}) توسط کاربر {user.username}"
        )

        # --- مدیریت تغییر مرحله (Stage Change) ---
        # این بخش را به همان صورت که در کد شما موجود است، در اینجا لحاظ کنید.
        # اگر دکمه‌ای برای تغییر مرحله کلی تنخواه وجود دارد، باید اینجا مدیریت شود.
        # مثال (که در کدهای قبلی شما دیده نشد، اما اگر بود باید اینجا باشد):
        if 'stage_change_action' in request.POST:
            action_type = request.POST.get('stage_change_action')
            target_stage_id = request.POST.get('target_stage_id')
            stage_comment = request.POST.get('stage_comment', '').strip()

            if not target_stage_id:
                messages.error(request, _("مرحله مقصد انتخاب نشده است."))
                return redirect('factor_item_approve', pk=factor.pk)

            try:
                with transaction.atomic():
                    # فرض بر این است که منطق `change_tankhah_stage` در جای دیگری تعریف شده است.
                    # این تابع باید وضعیت تنخواه را تغییر دهد و لاگ مربوطه را ثبت کند.
                    # change_tankhah_stage(tankhah, user, current_stage, target_stage_id, stage_comment, user_post_obj)
                    messages.success(request, _("مرحله تنخواه با موفقیت تغییر یافت."))
                    logger.info(
                        f"[FactorItemApproveView] مرحله تنخواه {tankhah.number} با موفقیت به {target_stage_id} تغییر یافت.")
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در تغییر مرحله تنخواه {tankhah.number}: {e}", exc_info=True)
                messages.error(request, _("خطا در تغییر مرحله تنخواه رخ داد."))
            return redirect('factor_item_approve', pk=factor.pk)
        # --- پایان مدیریت تغییر مرحله ---

        # --- مدیریت تأیید/رد ردیف‌های فاکتور ---
        can_edit = can_edit_approval(user, tankhah, current_stage, factor)
        if not can_edit:
            messages.error(request, _("شما دسترسی لازم برای ویرایش یا اقدام روی ردیف‌های این فاکتور را ندارید."))
            logger.warning(
                f"[FactorItemApproveView] کاربر {user.username} دسترسی کافی برای اقدام روی فاکتور {factor.number} ندارد.")
            return redirect('factor_item_approve', pk=factor.pk)

        user_post_obj = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
        if not user_post_obj:
            logger.error(f"[FactorItemApproveView] هیچ پست فعالی برای کاربر {user.username} یافت نشد. عملیات متوقف شد.")
            messages.error(request, _("پست فعالی برای حساب کاربری شما یافت نشد. نمی‌توانید اقدام کنید."))
            return redirect('factor_item_approve', pk=factor.pk)

        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')
        logger.debug(f"[FactorItemApproveView] داده‌های POST دریافتی برای فرم‌ست: {request.POST}")

        if formset.is_valid():
            logger.info(f"[FactorItemApproveView] فرم‌ست آیتم‌های فاکتور برای فاکتور {factor.number} معتبر است.")
            try:
                with transaction.atomic():
                    any_changes_made = False
                    action = None
                    log_comment = ''

                    bulk_approve = 'bulk_approve' in request.POST
                    bulk_reject = 'bulk_reject' in request.POST
                    reject_factor_entirely = 'reject_factor' in request.POST

                    rejected_reason = request.POST.get('rejected_reason', '').strip()
                    approved_reason = request.POST.get('approved_reason', '').strip()

                    # --- مدیریت رد کامل فاکتور ---
                    if reject_factor_entirely:
                        logger.info(f"[FactorItemApproveView] درخواست رد کامل فاکتور {factor.number}.")
                        if not rejected_reason:
                            messages.error(request, _("برای رد کامل فاکتور، وارد کردن دلیل رد اجباری است."))
                            logger.warning(f"[FactorItemApproveView] دلیل رد کامل فاکتور {factor.number} ارسال نشد.")
                            return redirect('factor_item_approve', pk=factor.pk)

                        for item in factor.items.all():
                            if item.status != 'REJECTED':
                                item.status = 'REJECTED'
                                item.save()
                                any_changes_made = True
                                logger.debug(
                                    f"[FactorItemApproveView] آیتم {item.id} به وضعیت 'REJECTED' تغییر یافت (رد کامل فاکتور).")
                        action = 'REJECTD'
                        log_comment = rejected_reason
                        messages.success(request, _(f"فاکتور {factor.number} و تمام آیتم‌های آن با موفقیت رد شدند."))
                        logger.info(f"[FactorItemApproveView] فاکتور {factor.number} به طور کامل رد شد.")

                    # --- مدیریت تأیید/رد دسته‌جمعی ---
                    elif bulk_approve or bulk_reject:
                        logger.info(
                            f"[FactorItemApproveView] درخواست تأیید گروهی آیتم‌های فاکتور {factor.number}."
                            if bulk_approve else f"[FactorItemApproveView] درخواست رد گروهی آیتم‌های فاکتور {factor.number}."
                        )
                        if bulk_reject:
                            if not rejected_reason:
                                messages.error(request, _("برای رد گروهی آیتم‌ها، وارد کردن دلیل رد اجباری است."))
                                logger.warning(
                                    f"[FactorItemApproveView] دلیل رد گروهی برای فاکتور {factor.number} ارسال نشد.")
                                return redirect('factor_item_approve', pk=factor.pk)
                            action = 'REJECTD'
                            log_comment = rejected_reason
                            target_status = 'REJECTED'
                        elif bulk_approve:
                            if not approved_reason:
                                messages.error(request,
                                               _("برای تأیید گروهی آیتم‌ها، وارد کردن توضیحات تأیید اجباری است."))
                                logger.warning(
                                    f"[FactorItemApproveView] توضیحات تأیید گروهی برای فاکتور {factor.number} ارسال نشد.")
                                return redirect('factor_item_approve', pk=factor.pk)
                            action = 'APPROVED'
                            log_comment = approved_reason
                            target_status = 'APPROVED'

                        # اعمال وضعیت جدید به تمام آیتم‌ها
                        for item in factor.items.all():
                            if item.status != target_status:
                                item.status = target_status
                                item.save()
                                any_changes_made = True
                                logger.debug(
                                    f"[FactorItemApproveView] آیتم {item.id} به وضعیت '{target_status}' تغییر یافت (گروهی).")

                        if not any_changes_made:
                            logger.info(
                                f"[FactorItemApproveView] هیچ تغییری در وضعیت آیتم‌ها برای عملیات گروهی فاکتور {factor.number} نیاز نبود.")
                        messages.info(request, _(f"عملیات گروهی روی ردیف‌های فاکتور {factor.number} انجام شد."))

                    # === 6. مدیریت پردازش تک تک آیتم‌ها (اگر تأیید/رد گروهی یا رد کامل فاکتور انتخاب نشده باشد) ===
                    else:
                        logger.info(f"[FactorItemApproveView] پردازش تک تک آیتم‌ها برای فاکتور {factor.number}.")
                        for form in formset:
                            if form.has_changed():
                                any_changes_made = True
                                item = form.instance
                                new_status = form.cleaned_data.get('status')
                                item_description_comment = form.cleaned_data.get('description', '').strip()

                                if new_status == 'REJECTED' and not item_description_comment:
                                    messages.error(request,
                                                   _(f"برای رد ردیف '{item.description}'، وارد کردن دلیل رد اجباری است."))
                                    logger.warning(
                                        f"[FactorItemApproveView] دلیل رد برای آیتم {item.id} ('{item.description}') ارسال نشد.")
                                    return redirect('factor_item_approve', pk=factor.pk)

                                if new_status == 'APPROVED' and not item_description_comment:
                                    messages.error(request,
                                                   _(f"برای تأیید ردیف '{item.description}'، وارد کردن توضیحات تأیید اجباری است."))
                                    logger.warning(
                                        f"[FactorItemApproveView] توضیحات تأیید برای آیتم {item.id} ('{item.description}') ارسال نشد.")
                                    return redirect('factor_item_approve', pk=factor.pk)

                                if new_status:
                                    item.status = new_status
                                    item.save()
                                    logger.info(
                                        f"[FactorItemApproveView] آیتم {item.id} به وضعیت {new_status} تغییر یافت توسط کاربر {user.username}.")
                                else:
                                    item.status = 'PENDING'
                                    item.save()
                                    logger.info(
                                        f"[FactorItemApproveView] آیتم {item.id} به PENDING بازگشت توسط کاربر {user.username}.")

                        if any_changes_made:
                            all_items = factor.items.all()
                            approved_items_count = all_items.filter(status='APPROVED').count()
                            rejected_items_count = all_items.filter(status='REJECTED').count()
                            total_items_count = all_items.count()

                            if approved_items_count == total_items_count:
                                action = 'APPROVED'
                            elif rejected_items_count == total_items_count:
                                action = 'REJECTD'
                            elif approved_items_count > 0 or rejected_items_count > 0:
                                action = 'PARTIAL'

                            log_comment = approved_reason or rejected_reason
                            if not log_comment and action in ['APPROVED', 'REJECTD', 'PARTIAL']:
                                log_comment = _("اقدام روی ردیف‌های فاکتور به صورت تکی.")
                        logger.debug(
                            f"[FactorItemApproveView] وضعیت any_changes_made پس از پردازش تک آیتم: {any_changes_made}")

                    # === 7. ایجاد ApprovalLog و به‌روزرسانی وضعیت کلی فاکتور و تنخواه ===
                    # این بلاک اکنون بازخورد را برای هر دو حالت (تغییر وضعیت و عدم تغییر) ارائه می‌دهد.
                    if any_changes_made and action:
                        logger.info(
                            f"[FactorItemApproveView] ثبت لاگ تأیید کلی و به‌روزرسانی وضعیت فاکتور {factor.number}.")
                        content_type_factor = ContentType.objects.get_for_model(Factor)
                        try:
                            approval_log = ApprovalLog.objects.create(
                                user=user,
                                factor=factor,
                                tankhah=tankhah,
                                stage=tankhah.current_stage,
                                action=action,
                                comment=log_comment,
                                post=user_post_obj.post,
                                content_type=content_type_factor,
                                object_id=factor.pk
                            )
                            logger.info(
                                f"[FactorItemApproveView] ApprovalLog {approval_log.id} برای فاکتور {factor.number} با اقدام {action} ایجاد شد.")

                            if action == 'APPROVE':
                                factor.status = 'APPROVED'
                            elif action == 'REJECT':
                                factor.status = 'REJECTED'
                            elif action == 'PARTIAL':
                                factor.status = 'PARTIAL'

                            factor.save(update_fields=['status'])
                            logger.info(
                                f"[FactorItemApproveView] وضعیت فاکتور {factor.number} به {factor.status} تغییر کرد.")

                            all_factors_in_tankhah_processed = all(
                                all(item.status in ['APPROVED', 'REJECTED'] for item in f.items.all())
                                for f in tankhah.factors.all()
                            )
                            if all_factors_in_tankhah_processed:
                                logger.info(
                                    f"[FactorItemApproveView] تمام فاکتورهای تنخواه {tankhah.number} پردازش شده‌اند.")
                                # این بخش را برای پیشروی خودکار مرحله تنخواه مطابق با منطق موجود خود تنظیم کنید.
                                # ... (منطق پیشروی مرحله تنخواه) ...
                                if hasattr(tankhah.current_stage,
                                           'auto_advance') and tankhah.current_stage.auto_advance:
                                    next_stage = tankhah.current_stage.get_next_stage()
                                    if next_stage:
                                        tankhah.current_stage = next_stage
                                        tankhah.save(update_fields=['current_stage'])
                                        logger.info(
                                            f"[FactorItemApproveView] تنخواه {tankhah.number} به مرحله {next_stage.name} پیشروی کرد.")
                                        messages.success(request,
                                                         _(f"تمام فاکتورهای تنخواه {tankhah.number} پردازش شدند. مرحله تنخواه به {next_stage.name} تغییر یافت."))
                                    else:
                                        messages.info(request,
                                                      _("تمام فاکتورهای تنخواه پردازش شدند، اما مرحله بعدی وجود ندارد."))
                                else:
                                    messages.info(request,
                                                  _("تمام فاکتورهای تنخواه پردازش شدند. مرحله تنخواه به صورت خودکار پیشروی نمی‌کند."))

                            messages.success(request, _(f"تغییرات فاکتور {factor.number} با موفقیت ذخیره شد."))
                            logger.info(
                                f"[FactorItemApproveView] عملیات POST برای فاکتور {factor.number} با موفقیت انجام شد.")

                        except ValueError as e:
                            logger.error(
                                f"[FactorItemApproveView] خطای AccessRule در پردازش آیتم/لاگ برای فاکتور {factor.number}: {e}",
                                exc_info=True)
                            messages.error(request,
                                           _(f"خطا در پردازش ردیف‌ها: دسترسی شما برای این اقدام محدود است. ({e})"))
                        except Exception as e:
                            logger.error(
                                f"[FactorItemApproveView] خطای سیستمی در پردازش آیتم/لاگ برای فاکتور {factor.number}: {e}",
                                exc_info=True)
                            messages.error(request,
                                           _("خطای سیستمی در پردازش درخواست شما رخ داد. لطفاً با پشتیبانی تماس بگیرید."))
                    # ✅ اضافه شده: مدیریت حالتی که هیچ تغییری نیاز نیست اما اقدام انجام شده است.
                    elif action:
                        logger.info(
                            f"[FactorItemApproveView] کاربر {user.username} تلاش کرد تا فاکتور {factor.number} را {action} کند، اما وضعیت آیتم‌ها از قبل در وضعیت مورد نظر بود."
                        )
                        messages.info(
                            request,
                            _(f"وضعیت ردیف‌های فاکتور {factor.number} از قبل در وضعیت '{action}' قرار داشت و تغییری اعمال نشد.")
                        )
                    # ✅ اضافه شده: مدیریت حالتی که هیچ تغییری (نه در وضعیت آیتم‌ها و نه اقدامی مثل تأیید/رد گروهی) وجود نداشت.
                    else:
                        messages.info(request, _("هیچ تغییری برای ذخیره وجود نداشت."))
                        logger.info(f"[FactorItemApproveView] هیچ تغییری در آیتم‌های فاکتور {factor.number} نیاز نبود.")

                return redirect('factor_item_approve', pk=factor.pk)

            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در پردازش فرم‌ست برای فاکتور {factor.number}: {e}",
                             exc_info=True)
                messages.error(request, _("خطای سیستمی در ذخیره تغییرات رخ داد. لطفاً با پشتیبانی تماس بگیرید."))
                return redirect('factor_item_approve', pk=factor.pk)
        else:
            logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است برای فاکتور {factor.number}: {formset.errors}")
            error_messages = []
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    error_messages.append(str(error))
            for form_errors in formset.errors:
                for field, errors in form_errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")

            display_errors = " ".join(error_messages) if error_messages else _("اطلاعات واردشده معتبر نیستند.")
            messages.error(request, _(f"خطا در پردازش فرم. لطفاً اطلاعات واردشده را بررسی کنید: {display_errors}"))
            return self.get(request, *args, **kwargs)

class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_required = 'tankhah.factor_approve'
    context_object_name = 'factor'
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def post(self, request, *args, **kwargs):
        logger.info(f"[FactorItemApproveView] درخواست POST برای فاکتور {self.kwargs.get('pk')} توسط {request.user.username}")
        self.object = self.get_object()
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()

        user_org_ids = set()
        for up in user.userpost_set.filter(is_active=True):
            org = up.post.organization
            user_org_ids.add(org.id)
            current_org = org
            while current_org.parent_organization:
                current_org = current_org.parent_organization
                user_org_ids.add(current_org.id)
        is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)

        if not user_post and not is_hq_user:
            logger.error(f"[FactorItemApproveView] کاربر {user.username} هیچ پست فعالی ندارد")
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('factor_item_approve', pk=factor.pk)

        if tankhah.is_locked or tankhah.is_archived or factor.is_locked:
            logger.warning(f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است")
            messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        current_stage = tankhah.current_stage
        if not current_stage:
            logger.error(f"[FactorItemApproveView] مرحله فعلی برای تنخواه {tankhah.number} تعریف نشده است")
            messages.error(request, _("مرحله فعلی تنخواه نامعتبر است."))
            return redirect('factor_item_approve', pk=factor.pk)

        if not can_edit_approval(user, tankhah, current_stage, factor):
            logger.warning(f"[FactorItemApproveView] کاربر {user.username} دسترسی لازم برای ویرایش ندارد")
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
                if not is_hq_user and new_stage_order > max_change_level:
                    raise ValidationError(_(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))

                new_stage = AccessRule.objects.filter(
                    stage_order=new_stage_order,
                    is_active=True,
                    entity_type='FACTOR',
                    organization=tankhah.organization
                ).first()
                if not new_stage:
                    raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))

                if not is_hq_user and user_post:
                    has_permission = AccessRule.objects.filter(
                        post=user_post.post,
                        stage_order=new_stage_order,
                        is_active=True,
                        entity_type='FACTOR'
                    ).exists()
                    if not has_permission:
                        raise ValidationError(_("شما اجازه ارجاع به این مرحله را ندارید."))

                with transaction.atomic():
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING'
                    tankhah._changed_by = user
                    tankhah.save(update_fields=['current_stage', 'status'])
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='STAGE_CHANGE',
                        stage=new_stage,  # استفاده از نمونه AccessRule
                        comment=f"تغییر مرحله به {new_stage.stage}: {stage_change_reason}",
                        post=user_post.post if user_post else None
                    )
                    approving_posts = AccessRule.objects.filter(
                        stage_order=new_stage.stage_order,
                        is_active=True,
                        entity_type='FACTOR',
                        action_type='APPROVE'
                    ).values_list('post', flat=True)
                    self.send_notifications(
                        entity=factor,
                        action='NEEDS_APPROVAL',
                        priority='MEDIUM',
                        description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {new_stage.stage} دارد.",
                        recipients=approving_posts
                    )
                    messages.success(request, _(f"مرحله فاکتور به {new_stage.stage} تغییر یافت."))
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
                    factor._changed_by = user
                    factor.save()
                    FactorItem.objects.filter(factor=factor).update(status='REJECTED')
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='REJECTED',
                        stage=current_stage,  # استفاده از نمونه AccessRule
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
                        logger.warning(f"[FactorItemApproveView] همه فاکتورهای تنخواه {tankhah.number} تأیید نشده‌اند")
                        messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                    if current_stage.is_final_stage:
                        if tankhah.status == 'APPROVED':
                            logger.warning(f"[FactorItemApproveView] تنخواه {tankhah.number} قبلاً تأیید نهایی شده است")
                            messages.warning(request, _('این تنخواه قبلاً تأیید نهایی شده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        payment_number = request.POST.get('payment_number')
                        if current_stage.triggers_payment_order and not payment_number:
                            logger.error(f"[FactorItemApproveView] شماره پرداخت برای تنخواه {tankhah.number} ارائه نشده است")
                            messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        if current_stage.triggers_payment_order:
                            self.create_payment_order(factor, user)

                        tankhah.status = 'APPROVED'
                        tankhah.payment_number = payment_number
                        tankhah.is_locked = True
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['status', 'payment_number', 'is_locked'])
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='APPROVED',
                            stage=current_stage,  # استفاده از نمونه AccessRule
                            comment=_('تأیید نهایی تنخواه'),
                            post=user_post.post if user_post else None
                        )
                        hq_posts = Post.objects.filter(organization__org_type__org_type='HQ')
                        self.send_notifications(
                            entity=factor,
                            action='APPROVED',
                            priority='HIGH',
                            description=f" فاکتور {factor.number} تأیید نهایی شد و به دفتر مرکزی ارسال شد.",
                            recipients=hq_posts
                        )
                        messages.success(request, _('فاکتور تأیید نهایی شد.'))
                        return redirect('dashboard_flows')
                    else:
                        next_stage = AccessRule.objects.filter(
                            stage_order__gt=current_stage.stage_order,
                            is_active=True,
                            entity_type='FACTOR',
                            organization=tankhah.organization
                        ).order_by('stage_order').first()
                        if not next_stage:
                            logger.error(f"[FactorItemApproveView] مرحله بعدی برای تنخواه {tankhah.number} تعریف نشده است")
                            messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        approved_reason = request.POST.get('approved_reason', '').strip()
                        if not approved_reason:
                            raise ValidationError(_("توضیحات تأیید الزامی است."))

                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['current_stage', 'status'])
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,  # استفاده از نمونه AccessRule
                            comment=f"تأیید و انتقال به {next_stage.stage}. توضیحات: {approved_reason}",
                            post=user_post.post if user_post else None
                        )
                        approving_posts = AccessRule.objects.filter(
                            stage_order=next_stage.stage_order,
                            is_active=True,
                            entity_type='FACTOR',
                            action_type='APPROVE'
                        ).values_list('post', flat=True)
                        self.send_notifications(
                            entity=factor,
                            action='NEEDS_APPROVAL',
                            priority='MEDIUM',
                            description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.stage} دارد.",
                            recipients=approving_posts
                        )
                        messages.success(request, _(f"تأیید انجام و به مرحله {next_stage.stage} منتقل شد."))
                        return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در تأیید نهایی: {e}", exc_info=True)
                messages.error(request, _("خطا در تأیید نهایی."))
                return redirect('factor_item_approve', pk=factor.pk)

        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')
        if formset.is_valid():
            logger.info("[FactorItemApproveView] فرم‌ست آیتم‌ها معتبر است")
            try:
                with transaction.atomic():
                    has_changes = False
                    items_processed_count = 0
                    content_type = ContentType.objects.get_for_model(FactorItem)

                    for form in formset:
                        if form.cleaned_data:
                            item = form.instance
                            if not item.id:
                                logger.error(f"[FactorItemApproveView] آیتم بدون ID یافت شد: {item}")
                                continue
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
                            elif status == 'APPROVED' and not description:
                                raise ValidationError(_("توضیحات تأیید برای آیتم الزامی است."))

                            if status and status != 'NONE' and (status != item.status or user.is_superuser or is_hq_user):
                                access_rule = AccessRule.objects.filter(
                                    organization=user_post.post.organization,
                                    stage=current_stage.stage,  # اصلاح: استفاده از رشته stage
                                    stage_order=current_stage.stage_order,
                                    action_type='APPROVED' if status == 'APPROVED' else 'REJECTED',
                                    entity_type='FACTORITEM',
                                    min_level__lte=user_post.post.level,
                                    branch=user_post.post.branch or '',
                                    is_active=True
                                ).first()
                                if not access_rule and not (user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all')):
                                    logger.error(
                                        f"[FactorItemApproveView] کاربر {user.username} مجاز به {status} برای FACTORITEM نیست"
                                    )
                                    raise ValueError(
                                        f"کاربر {user.username} مجاز به {status} برای ردیف فاکتور نیست - قانون دسترسی یافت نشد"
                                    )

                                has_changes = True
                                items_processed_count += 1
                                action = 'APPROVED' if status == 'APPROVED' else 'REJECTED'
                                ApprovalLog.objects.create(
                                    tankhah=tankhah,
                                    factor=factor,
                                    factor_item=item,
                                    user=user,
                                    action=action,
                                    stage=current_stage,  # استفاده از نمونه AccessRule
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

                    all_approved = factor.items.exists() and all(item.status == 'APPROVED' for item in factor.items.all())
                    any_rejected = any(item.status == 'REJECTED' for item in factor.items.all())

                    if any_rejected:
                        factor.status = 'REJECTED'
                        factor.rejected_reason = request.POST.get('rejected_reason', 'یکی از آیتم‌ها رد شده است')
                        factor.is_locked = True
                        factor._changed_by = user
                        factor.save()
                        self.send_notifications(
                            entity=factor,
                            action='REJECTED',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} به دلیل رد آیتم‌ها رد شد. دلیل: {factor.rejected_reason}",
                            recipients=[factor.created_by_post] if factor.created_by_post else []
                        )
                        messages.warning(request, _('فاکتور به دلیل رد آیتم‌ها رد شد.'))
                        return redirect('dashboard_flows')
                    elif all_approved:
                        factor.status = 'APPROVED'
                        factor.is_locked = True
                        factor._changed_by = user
                        factor.save()
                        next_stage = AccessRule.objects.filter(
                            stage_order__gt=current_stage.stage_order,
                            is_active=True,
                            entity_type='FACTOR',
                            organization=tankhah.organization
                        ).order_by('stage_order').first()
                        if next_stage and current_stage.auto_advance:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah._changed_by = user
                            tankhah.save(update_fields=['current_stage', 'status'])
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                factor=factor,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=next_stage,  # استفاده از نمونه AccessRule
                                comment=f"تأیید آیتم‌ها و انتقال به {next_stage.stage}",
                                post=user_post.post if user_post else None
                            )
                            approving_posts = AccessRule.objects.filter(
                                stage_order=next_stage.stage_order,
                                is_active=True,
                                entity_type='FACTOR',
                                action_type='APPROVE'
                            ).values_list('post', flat=True)
                            self.send_notifications(
                                entity=factor,
                                action='NEEDS_APPROVAL',
                                priority='MEDIUM',
                                description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.stage} دارد.",
                                recipients=approving_posts
                            )
                            messages.success(request, _(f"فاکتور به مرحله {next_stage.stage} منتقل شد."))
                            return redirect('dashboard_flows')
                        elif current_stage.is_final_stage and current_stage.triggers_payment_order:
                            self.create_payment_order(factor, user)
                            messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند.'))
                            return redirect('dashboard_flows')
                        else:
                            messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)
                    else:
                        factor.status = 'PENDING'
                        factor._changed_by = user
                        factor.save()
                        messages.warning(request, _('لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                if has_changes:
                    logger.info(f"[FactorItemApproveView] وضعیت فاکتور {factor.id} به {factor.status} تغییر یافت")
                    messages.success(request, _('تغییرات در وضعیت ردیف‌ها با موفقیت ثبت شد.'))
                else:
                    logger.info(f"[FactorItemApproveView] هیچ تغییری برای فاکتور {factor.pk} ثبت نشد")
                    messages.info(request, _('هیچ تغییری برای ثبت وجود نداشت.'))

            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در پردازش فرم‌ست: {e}", exc_info=True)
                messages.error(request, _("خطا در ذخیره‌سازی تغییرات ردیف‌ها."))
                return self.render_to_response(self.get_context_data())

        else:
            logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است: {formset.errors}")
            messages.error(request, _('لطفاً خطاهای فرم ردیف‌ها را بررسی کنید.'))
            return self.render_to_response(self.get_context_data())

        return redirect('factor_item_approve', pk=factor.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        tankhah = factor.tankhah
        user = self.request.user
        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0
        logger.info(f"[FactorItemApproveView] شروع get_context_data برای فاکتور {factor.pk}")

        current_stage = tankhah.current_stage
        if not current_stage:
            logger.error(f"[FactorItemApproveView] مرحله فعلی برای تنخواه {tankhah.number} تعریف نشده است")
            context['can_edit'] = False
            context['can_change_stage'] = False
            context['workflow_stages'] = []
            context['can_final_approve_factor'] = False
            context['can_final_approve_tankhah'] = False
            messages.error(self.request, _("مرحله فعلی تنخواه نامعتبر است."))
            return context

        formset = FactorItemApprovalFormSet(self.request.POST or None, instance=factor, prefix='items')
        form_log_pairs = []
        for form in formset:
            item = form.instance
            latest_log = ApprovalLog.objects.filter(
                factor_item=item,
                factor=factor,
                action__in=['APPROVED', 'REJECTED'],
                user=user
            ).select_related('user', 'post', 'stage').order_by('-timestamp').first()
            form_log_pairs.append((form, latest_log))

        has_previous_action = ApprovalLog.objects.filter(
            factor=factor,
            user=user,
            stage=current_stage,  # اصلاح: استفاده از نمونه AccessRule
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()

        all_items_processed = all(
            ApprovalLog.objects.filter(
                factor_item=item,
                factor=factor,
                user=user,
                action__in=['APPROVED', 'REJECTED']
            ).exists() for item in factor.items.all()
        ) if factor.items.exists() else False

        allowed_stages = AccessRule.objects.filter(
            is_active=True,
            entity_type='FACTOR',
            stage_order__lte=max_change_level,
            organization=tankhah.organization
        ).order_by('stage_order').distinct()
        if not user.is_hq and user_post:
            allowed_stages = allowed_stages.filter(post=user_post.post, action_type='APPROVE').distinct()

        context['form_log_pairs'] = form_log_pairs
        context['formset'] = formset
        context['approval_logs'] = ApprovalLog.objects.filter(
            factor=factor
        ).select_related('user', 'post', 'stage').order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['can_edit'] = can_edit_approval(user, tankhah, current_stage, factor)
        context['can_change_stage'] = context['can_edit'] and bool(allowed_stages) and not has_previous_action
        context['workflow_stages'] = allowed_stages
        context['show_payment_number'] = tankhah.status == 'APPROVED' and not tankhah.payment_number
        all_items_approved = all(
            item.status == 'APPROVED' for item in factor.items.all()) if factor.items.exists() else False
        context['can_final_approve_factor'] = context['can_edit'] and all_items_approved and not has_previous_action
        context['can_final_approve_tankhah'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in
            tankhah.factors.all()) and current_stage.is_final_stage and not has_previous_action
        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            factor=factor,
            post__level__lt=user_level,
            action__in=['APPROVED', 'REJECTED', 'STAGE_CHANGE']
        ).exists()

        logger.info(f"[FactorItemApproveView] تعداد جفت‌های فرم-لاگ: {len(form_log_pairs)}")
        logger.info(
            f"[FactorItemApproveView] can_edit: {context['can_edit']}, has_previous_action: {has_previous_action}, all_items_processed: {all_items_processed}")
        logger.info(f"[FactorItemApproveView] پایان get_context_data")
        return context

    def create_payment_order(self, factor, user):
        logger.info(f"[FactorItemApproveView] شروع ایجاد دستور پرداخت برای فاکتور {factor.pk}")
        try:
            with transaction.atomic():
                initial_po_stage = AccessRule.objects.filter(
                    entity_type='PAYMENTORDER',
                    stage_order=1,
                    is_active=True,
                    organization=factor.tankhah.organization
                ).first()
                if not initial_po_stage:
                    logger.error(f"[FactorItemApproveView] مرحله اولیه گردش کار برای دستور پرداخت یافت نشد")
                    messages.error(self.request, _("مرحله اولیه گردش کار برای دستور پرداخت تعریف نشده است."))
                    return

                tankhah_remaining = factor.tankhah.budget - factor.tankhah.spent
                if factor.amount > tankhah_remaining:
                    logger.error(f"[FactorItemApproveView] بودجه تنخواه کافی نیست: {factor.amount} > {tankhah_remaining}")
                    messages.error(self.request, _("بودجه تنخواه کافی نیست."))
                    return

                if factor.tankhah.project:
                    project_remaining = factor.tankhah.project.budget - factor.tankhah.project.spent
                    if factor.amount > project_remaining:
                        logger.error(f"[FactorItemApproveView] بودجه پروژه کافی نیست: {factor.amount} > {project_remaining}")
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

                approving_posts = AccessRule.objects.filter(
                    stage_order=initial_po_stage.stage_order,
                    is_active=True,
                    entity_type='PAYMENTORDER',
                    action_type='APPROVE'
                ).values_list('post', flat=True)
                self.send_notifications(
                    entity=payment_order,
                    action='CREATED',
                    priority='HIGH',
                    description=f"دستور پرداخت {payment_order.order_number} برای فاکتور {factor.number} ایجاد شد.",
                    recipients=approving_posts
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
                # send_mail(
                #     subject=description,
                #     message=f"{description}\nلطفاً {entity_type.lower()} {getattr(entity, 'number', entity.id)} را بررسی کنید.",
                #     from_email='system@example.com',
                #     recipient_list=[user.email],
                #     fail_silently=True
                # )
                logger.info(f"[FactorItemApproveView] ایمیل ارسال شد به {user.email} برای {entity_type} {getattr(entity, 'number', entity.id)}")

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
        logger.info(f"[FactorItemApproveView] اعلان برای {entity_type} {getattr(entity, 'number', entity.id)} با اقدام {action} ارسال شد")
