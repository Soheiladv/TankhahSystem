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
from tankhah.Factor.NF.view_Nfactor import FactorItemFormSet
from tankhah.forms import FactorItemApprovalForm, FactorApprovalForm

from tankhah.models import Factor, FactorItem, ApprovalLog, StageApprover, create_budget_transaction, FactorHistory, \
    Tankhah
from tankhah.fun_can_edit_approval import can_edit_approval
from django.utils.translation import gettext_lazy as _
import logging
from core.models import Organization
from django.contrib.contenttypes.models import ContentType
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from notifications.signals import notify
logger = logging.getLogger('factor_approval')

# تنظیم لاگ‌گیری با فایل
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
    filename='logs/factor_item_approve.log',
    filemode='a'
)
# 💡 اصلاح: FactorItemApprovalFormSet اکنون تنها از فیلدهای status, description استفاده می‌کند
FactorItemApprovalFormSet = inlineformset_factory(
    Factor,
    FactorItem,
    form=FactorItemApprovalForm,
    fields=('status', 'description', 'comment'), # 💡 اضافه کردن comment اگر در فرم هم هست
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

    def get_object(self, queryset=None):
        # این متد Factor مربوط به pk را برمی‌گرداند
        return get_object_or_404(Factor, pk=self.kwargs['pk'])

    # def post(self, request, *args, **kwargs):
    #     logger.info(
    #         f"[FactorItemApproveView] درخواست POST برای فاکتور {self.kwargs.get('pk')} توسط {request.user.username}")
    #     self.object = self.get_object()
    #     factor = self.object
    #     tankhah = factor.tankhah
    #     user = request.user
    #
    #     # بررسی پست فعال کاربر و سازمان‌های مرتبط
    #     user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()
    #     user_org_ids = set()
    #     for up in user.userpost_set.filter(is_active=True):
    #         org = up.post.organization
    #         user_org_ids.add(org.id)
    #         current_org = org
    #         while current_org.parent_organization:
    #             current_org = current_org.parent_organization
    #             user_org_ids.add(current_org.id)
    #     is_hq_user = any(Organization.objects.filter(id=org_id, is_core=True).exists() for org_id in user_org_ids)
    #
    #     # بررسی مرحله فعلی تنخواه
    #     current_stage = tankhah.current_stage
    #     if not current_stage:
    #         logger.error(f"[FactorItemApproveView] مرحله فعلی برای تنخواه {tankhah.number} تعریف نشده است")
    #         messages.error(request, _("مرحله فعلی تنخواه نامعتبر است."))
    #         return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # بررسی وجود پست فعال
    #     if not user_post and not is_hq_user:
    #         logger.error(f"[FactorItemApproveView] کاربر {user.username} هیچ پست فعالی ندارد")
    #         messages.error(request, _("شما پست فعالی ندارید."))
    #         return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # بررسی دسترسی کاربر
    #     if not can_edit_approval(user, tankhah, current_stage, factor):
    #         logger.warning(f"[FactorItemApproveView] کاربر {user.username} دسترسی لازم برای ویرایش ندارد")
    #         messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید.'))
    #         return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # بررسی قفل بودن تنخواه یا فاکتور
    #     if tankhah.is_locked or tankhah.is_archived or factor.locked:
    #         if is_hq_user:
    #             logger.info(f"[FactorItemApproveView] کاربر {user.username} قفل تنخواه/فاکتور را باز می‌کند")
    #             tankhah.is_locked = False
    #             tankhah.is_archived = False
    #             factor.locked = False
    #             tankhah.save(update_fields=['is_locked', 'is_archived'])
    #             factor.save(update_fields=['locked'])
    #         else:
    #             logger.warning(
    #                 f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است")
    #             messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
    #             return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # پردازش تغییر مرحله
    #     if 'change_stage' in request.POST:
    #         logger.info(f"[FactorItemApproveView] درخواست تغییر مرحله برای فاکتور {factor.pk}")
    #         try:
    #             new_stage_order = int(request.POST.get('new_stage_order'))
    #             stage_change_reason = request.POST.get('stage_change_reason', '').strip()
    #             if not stage_change_reason:
    #                 raise ValidationError(_("توضیحات تغییر مرحله الزامی است."))
    #             max_change_level = user_post.post.max_change_level if user_post else 0
    #             if not is_hq_user and new_stage_order > max_change_level:
    #                 raise ValidationError(
    #                     _(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))
    #
    #             new_stage = AccessRule.objects.filter(
    #                 stage_order=new_stage_order,
    #                 is_active=True,
    #                 entity_type='FACTOR',
    #                 organization=tankhah.organization
    #             ).first()
    #             if not new_stage:
    #                 raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))
    #
    #             if not is_hq_user and user_post:
    #                 has_permission = AccessRule.objects.filter(
    #                     post=user_post.post,
    #                     stage_order=new_stage_order,
    #                     is_active=True,
    #                     entity_type='FACTOR'
    #                 ).exists()
    #                 if not has_permission:
    #                     raise ValidationError(_("شما اجازه ارجاع به این مرحله را ندارید."))
    #
    #             with transaction.atomic():
    #                 tankhah.current_stage = new_stage
    #                 tankhah.status = 'PENDING'
    #                 tankhah._changed_by = user
    #                 tankhah.save(update_fields=['current_stage', 'status'])
    #                 ApprovalLog.objects.create(
    #                     tankhah=tankhah,
    #                     factor=factor,
    #                     user=user,
    #                     action='STAGE_CHANGE',
    #                     stage=new_stage,
    #                     comment=f"تغییر مرحله به {new_stage.stage}: {stage_change_reason}",
    #                     post=user_post.post if user_post else None
    #                 )
    #                 approving_posts = AccessRule.objects.filter(
    #                     stage_order=new_stage.stage_order,
    #                     is_active=True,
    #                     entity_type='FACTOR',
    #                     action_type='APPROVE'
    #                 ).values_list('post', flat=True)
    #                 self.send_notifications(
    #                     entity=factor,
    #                     action='NEEDS_APPROVAL',
    #                     priority='MEDIUM',
    #                     description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {new_stage.stage} دارد.",
    #                     recipients=approving_posts
    #                 )
    #                 messages.success(request, _(f"مرحله فاکتور به {new_stage.stage} تغییر یافت."))
    #             return redirect('factor_item_approve', pk=factor.pk)
    #         except (ValueError, ValidationError) as e:
    #             logger.error(f"[FactorItemApproveView] خطا در تغییر مرحله: {e}", exc_info=True)
    #             messages.error(request, str(e))
    #             return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # پردازش رد کامل فاکتور
    #     if request.POST.get('reject_factor'):
    #         logger.info(f"[FactorItemApproveView] درخواست رد کامل فاکتور {factor.pk}")
    #         try:
    #             rejected_reason = request.POST.get('rejected_reason', '').strip()
    #             if not rejected_reason:
    #                 raise ValidationError(_("دلیل رد فاکتور الزامی است."))
    #             with transaction.atomic():
    #                 factor.status = 'REJECTE' # 💡 یکسان‌سازی
    #                 factor.is_locked = True
    #                 factor.rejected_reason = rejected_reason
    #                 factor._changed_by = user
    #                 if factor.tankhah.spent >= factor.amount:
    #                     factor.tankhah.spent -= factor.amount
    #                     factor.tankhah.save(update_fields=['spent'])
    #                     if factor.tankhah.project:
    #                         factor.tankhah.project.spent -= factor.amount
    #                         factor.tankhah.project.save(update_fields=['spent'])
    #                     logger.info(
    #                         f"[FactorItemApproveView] بودجه {factor.amount} به تنخواه {factor.tankhah.number} عودت داده شد")
    #                 factor.save()
    #                 FactorItem.objects.filter(factor=factor).update(status='REJECTE') # 💡 یکسان‌سازی
    #                 ApprovalLog.objects.create(
    #                     tankhah=tankhah,
    #                     factor=factor,
    #                     user=user,
    #                     action='REJECTE', # 💡 یکسان‌سازی
    #                     stage=current_stage,
    #                     comment=f"رد کامل فاکتور: {rejected_reason}",
    #                     post=user_post.post if user_post else None
    #                 )
    #                 self.send_notifications(
    #                     entity=factor,
    #                     action='REJECTE', # 💡 یکسان‌سازی
    #                     priority='HIGH',
    #                     description=f"فاکتور {factor.number} رد شد. دلیل: {rejected_reason}",
    #                     recipients=[factor.created_by_post] if factor.created_by_post else []
    #                 )
    #                 messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
    #                 return redirect('dashboard_flows')
    #         except Exception as e:
    #             logger.error(f"[FactorItemApproveView] خطا در رد فاکتور: {e}", exc_info=True)
    #             messages.error(request, _("خطا در رد فاکتور."))
    #             return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # پردازش تأیید نهایی
    #     if request.POST.get('final_approve'):
    #         logger.info(f"[FactorItemApproveView] درخواست تأیید نهایی برای فاکتور {factor.pk}")
    #         try:
    #             with transaction.atomic():
    #                 all_factors_approved = all(f.status == 'APPROVE' for f in tankhah.factors.all())
    #                 if not all_factors_approved:
    #                     logger.warning(f"[FactorItemApproveView] همه فاکتورهای تنخواه {tankhah.number} تأیید نشده‌اند")
    #                     messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
    #                     return redirect('factor_item_approve', pk=factor.pk)
    #
    #                 if current_stage.is_final_stage:
    #                     if tankhah.status == 'APPROVE':
    #                         logger.warning(f"[FactorItemApproveView] تنخواه {tankhah.number} قبلاً تأیید نهایی شده است")
    #                         messages.warning(request, _('این تنخواه قبلاً تأیید نهایی شده است.'))
    #                         return redirect('factor_item_approve', pk=factor.pk)
    #
    #                     user_post = user.userpost_set.filter(is_active=True).first()
    #                     if not user_post or not (
    #                             user_post.post.can_final_approve_factor or user_post.post.can_final_approve_tankhah):
    #                         logger.warning(f"[FactorItemApproveView] کاربر {user.username} مجاز به تأیید نهایی نیست")
    #                         messages.error(request, _('شما مجاز به تأیید نهایی فاکتور یا تنخواه نیستید.'))
    #                         return redirect('factor_item_approve', pk=factor.pk)
    #
    #                     payment_number = request.POST.get('payment_number')
    #                     if current_stage.triggers_payment_order and not payment_number:
    #                         logger.error(
    #                             f"[FactorItemApproveView] شماره پرداخت برای تنخواه {tankhah.number} ارائه نشده است")
    #                         messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
    #                         return redirect('factor_item_approve', pk=factor.pk)
    #
    #                     if current_stage.triggers_payment_order:
    #                         self.create_payment_order(factor, user)
    #
    #                     tankhah.status = 'APPROVE'
    #                     tankhah.payment_number = payment_number
    #                     tankhah.is_locked = True
    #                     tankhah._changed_by = user
    #                     tankhah.save(update_fields=['status', 'payment_number', 'is_locked'])
    #                     ApprovalLog.objects.create(
    #                         tankhah=tankhah,
    #                         factor=factor,
    #                         user=user,
    #                         action='APPROVE',
    #                         stage=current_stage,
    #                         comment=_('تأیید نهایی تنخواه'),
    #                         post=user_post.post if user_post else None
    #                     )
    #                     hq_posts = Post.objects.filter(organization__org_type__org_type='HQ')
    #                     self.send_notifications(
    #                         entity=factor,
    #                         action='APPROVE',
    #                         priority='HIGH',
    #                         description=f"فاکتور {factor.number} تأیید نهایی شد و به دفتر مرکزی ارسال شد.",
    #                         recipients=hq_posts
    #                     )
    #                     messages.success(request, _('فاکتور تأیید نهایی شد.'))
    #                     return redirect('dashboard_flows')
    #                 else:
    #                     next_stage = AccessRule.objects.filter(
    #                         stage_order__gt=current_stage.stage_order,
    #                         is_active=True,
    #                         entity_type='FACTOR',
    #                         organization=tankhah.organization
    #                     ).order_by('stage_order').first()
    #                     if not next_stage:
    #                         logger.error(
    #                             f"[FactorItemApproveView] مرحله بعدی برای تنخواه {tankhah.number} تعریف نشده است")
    #                         messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
    #                         return redirect('factor_item_approve', pk=factor.pk)
    #
    #                     approved_reason = request.POST.get('approved_reason', '').strip()
    #                     if not approved_reason:
    #                         raise ValidationError(_("توضیحات تأیید الزامی است."))
    #
    #                     tankhah.current_stage = next_stage
    #                     tankhah.status = 'PENDING'
    #                     tankhah._changed_by = user
    #                     tankhah.save(update_fields=['current_stage', 'status'])
    #                     ApprovalLog.objects.create(
    #                         tankhah=tankhah,
    #                         factor=factor,
    #                         user=user,
    #                         action='STAGE_CHANGE',
    #                         stage=next_stage,
    #                         comment=f"تأیید و انتقال به {next_stage.stage}. توضیحات: {approved_reason}",
    #                         post=user_post.post if user_post else None
    #                     )
    #                     approving_posts = AccessRule.objects.filter(
    #                         stage_order=next_stage.stage_order,
    #                         is_active=True,
    #                         entity_type='FACTOR',
    #                         action_type='APPROVE'
    #                     ).values_list('post', flat=True)
    #                     self.send_notifications(
    #                         entity=factor,
    #                         action='NEEDS_APPROVAL',
    #                         priority='MEDIUM',
    #                         description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.stage} دارد.",
    #                         recipients=approving_posts
    #                     )
    #                     messages.success(request, _(f"تأیید انجام و به مرحله {next_stage.stage} منتقل شد."))
    #                     return redirect('dashboard_flows')
    #         except Exception as e:
    #             logger.error(f"[FactorItemApproveView] خطا در تأیید نهایی: {e}", exc_info=True)
    #             messages.error(request, _("خطا در تأیید نهایی."))
    #             return redirect('factor_item_approve', pk=factor.pk)
    #
    #     # پردازش فرم‌ست آیتم‌ها
    #     # 💡 اصلاح: استفاده از instance=factor برای اطمینان از صحت ارتباط والد-فرزند
    #     formset = FactorItemApprovalFormSet(request.POST, request.FILES, instance=factor, prefix='items')
    #
    #     if formset.is_valid():
    #         logger.info("[FactorItemApproveView] فرم‌ست آیتم‌ها معتبر است")
    #         logger.debug(f"[FactorItemApproveView] داده‌های فرم‌ست: {formset.cleaned_data}")
    #         try:
    #             with transaction.atomic():
    #                 has_changes = False
    #                 items_processed_count = 0
    #                 content_type = ContentType.objects.get_for_model(FactorItem)
    #                 action = None
    #                 log_comment = ''
    #
    #                 # تأیید گروهی
    #                 if request.POST.get('bulk_approve') == 'on':
    #                     approved_reason = request.POST.get('bulk_reason', '').strip()
    #                     if not approved_reason:
    #                         raise ValidationError(_("توضیحات تأیید برای تأیید گروهی الزامی است."))
    #                     for item in factor.items.all():
    #                         if item.status not in ['APPROVE', 'REJECTE']:
    #                             access_rule = AccessRule.objects.filter(
    #                                 organization=user_post.post.organization if user_post else factor.tankhah.organization,
    #                                 stage=current_stage.stage,
    #                                 stage_order=current_stage.stage_order,
    #                                 action_type='APPROVE',
    #                                 entity_type='FACTORITEM',
    #                                 min_level__lte=user_post.post.level if user_post else 0,
    #                                 # 💡 مدیریت branch=None
    #                                 branch=user_post.post.branch if user_post and user_post.post.branch else None,
    #                                 is_active=True
    #                             ).first()
    #                             if not access_rule and not (
    #                                     user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all')):
    #                                 logger.error(
    #                                     f"[FactorItemApproveView] کاربر {user.username} مجاز به APPROVE برای FACTORITEM نیست")
    #                                 raise ValueError(
    #                                     f"کاربر {user.username} مجاز به تأیید برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")
    #
    #                             item.status = 'APPROVE'
    #                             item.description = approved_reason
    #                             item._changed_by = user
    #                             item.save()
    #                             has_changes = True
    #                             items_processed_count += 1
    #                             ApprovalLog.objects.create(
    #                                 tankhah=tankhah,
    #                                 factor=factor,
    #                                 factor_item=item,
    #                                 user=user,
    #                                 action='TEMP_APPROVED' if not current_stage.is_final_stage else 'APPROVE',
    #                                 stage=current_stage,
    #                                 comment=approved_reason,
    #                                 post=user_post.post if user_post else None,
    #                                 content_type=content_type,
    #                                 object_id=item.id,
    #                                 is_temporary=not current_stage.is_final_stage
    #                             )
    #                     action = 'APPROVE'
    #                     log_comment = approved_reason
    #
    #                 # رد گروهی
    #                 elif request.POST.get('bulk_reject') == 'on':
    #                     rejected_reason = request.POST.get('rejected_reason', '').strip()
    #                     if not rejected_reason:
    #                         raise ValidationError(_("دلیل رد برای رد گروهی الزامی است."))
    #                     for item in factor.items.all():
    #                         if item.status not in ['APPROVE', 'REJECTE']:
    #                             access_rule = AccessRule.objects.filter(
    #                                 organization=user_post.post.organization if user_post else factor.tankhah.organization,
    #                                 stage=current_stage.stage,
    #                                 stage_order=current_stage.stage_order,
    #                                 action_type='REJECTE', # 💡 اصلاح: یکسان‌سازی با REJECTE
    #                                 entity_type='FACTORITEM',
    #                                 min_level__lte=user_post.post.level if user_post else 0,
    #                                 # 💡 مدیریت branch=None
    #                                 branch=user_post.post.branch if user_post and user_post.post.branch else None,
    #                                 is_active=True
    #                             ).first()
    #                             if not access_rule and not (
    #                                     user.is_superuser or is_hq_user or user.has_perm('tankhah.Tankhah_view_all')):
    #                                 logger.error(
    #                                     f"[FactorItemApproveView] کاربر {user.username} مجاز به REJECT برای FACTORITEM نیست")
    #                                 raise ValueError(
    #                                     f"کاربر {user.username} مجاز به رد برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")
    #
    #                             item.status = 'REJECTE' # 💡 یکسان‌سازی
    #                             item.description = rejected_reason
    #                             item._changed_by = user
    #                             item.save()
    #                             has_changes = True
    #                             items_processed_count += 1
    #                             ApprovalLog.objects.create(
    #                                 tankhah=tankhah,
    #                                 factor=factor,
    #                                 factor_item=item,
    #                                 user=user,
    #                                 action='TEMP_REJECTED' if not current_stage.is_final_stage else 'REJECTE', # 💡 یکسان‌سازی
    #                                 stage=current_stage,
    #                                 comment=rejected_reason,
    #                                 post=user_post.post if user_post else None,
    #                                 content_type=content_type,
    #                                 object_id=item.id,
    #                                 is_temporary=not current_stage.is_final_stage
    #                             )
    #                     action = 'REJECTE' # 💡 یکسان‌سازی
    #                     log_comment = rejected_reason
    #
    #                 # پردازش آیتم‌های فردی
    #                 else:
    #                     for form in formset:
    #                         if form.cleaned_data and form.has_changed():
    #                             item = form.instance
    #                             if not item.id:
    #                                 logger.error(f"[FactorItemApproveView] آیتم بدون ID یافت شد: {item}")
    #                                 continue
    #                             status = form.cleaned_data.get('status')
    #                             description = form.cleaned_data.get('description', '').strip()
    #                             comment = form.cleaned_data.get('comment', '').strip() # 💡 دریافت comment
    #
    #                             if not status:
    #                                 logger.warning(
    #                                     f"[FactorItemApproveView] وضعیت آیتم {item.id} خالی است، نادیده گرفته می‌شود")
    #                                 continue
    #
    #                             if status == 'REJECTE' and not description: # 💡 یکسان‌سازی
    #                                 raise ValidationError(_("دلیل رد برای آیتم الزامی است."))
    #                             elif status == 'APPROVE' and not description:
    #                                 raise ValidationError(_("توضیحات تأیید برای آیتم الزامی است."))
    #
    #                             if status in ['APPROVE', 'REJECTE']: # 💡 یکسان‌سازی
    #                                 access_rule = AccessRule.objects.filter(
    #                                     organization=user_post.post.organization if user_post else factor.tankhah.organization,
    #                                     stage=current_stage.stage,
    #                                     stage_order=current_stage.stage_order,
    #                                     action_type='APPROVE' if status == 'APPROVE' else 'REJECTE', # 💡 یکسان‌سازی
    #                                     entity_type='FACTORITEM',
    #                                     min_level__lte=user_post.post.level if user_post else 0,
    #                                     # 💡 مدیریت branch=None
    #                                     branch=user_post.post.branch if user_post and user_post.post.branch else None,
    #                                     is_active=True
    #                                 ).first()
    #                                 if not access_rule and not (user.is_superuser or is_hq_user or user.has_perm(
    #                                         'tankhah.Tankhah_view_all')):
    #                                     logger.error(
    #                                         f"[FactorItemApproveView] کاربر {user.username} مجاز به {status} برای FACTORITEM نیست")
    #                                     raise ValueError(
    #                                         f"کاربر {user.username} مجاز به {status} برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")
    #
    #                                 # بررسی اینکه آیا پست قبلاً در این مرحله اقدام کرده است
    #                                 post_has_action = ApprovalLog.objects.filter(
    #                                     factor_item=item,
    #                                     factor=factor,
    #                                     post=user_post.post if user_post else None,
    #                                     stage=current_stage,
    #                                     action__in=['APPROVE', 'REJECTE', 'TEMP_APPROVED', 'TEMP_REJECTED'] # 💡 یکسان‌سازی
    #                                 ).exists()
    #                                 if post_has_action and not (user.is_superuser or is_hq_user):
    #                                     logger.warning(
    #                                         f"[FactorItemApproveView] پست {user_post.post} قبلاً در مرحله {current_stage.stage} اقدام کرده است")
    #                                     continue
    #
    #                                 has_changes = True
    #                                 items_processed_count += 1
    #                                 action = 'TEMP_APPROVED' if status == 'APPROVE' and not current_stage.is_final_stage else 'TEMP_REJECTED' if status == 'REJECTE' and not current_stage.is_final_stage else status
    #                                 ApprovalLog.objects.create(
    #                                     tankhah=tankhah,
    #                                     factor=factor,
    #                                     factor_item=item,
    #                                     user=user,
    #                                     action=action,
    #                                     stage=current_stage,
    #                                     comment=comment, # 💡 استفاده از comment
    #                                     post=user_post.post if user_post else None,
    #                                     content_type=content_type,
    #                                     object_id=item.id,
    #                                     is_temporary=not current_stage.is_final_stage
    #                                 )
    #                                 item.status = status
    #                                 item.description = description
    #                                 item._changed_by = user
    #                                 item.save()
    #                                 logger.info(f"[FactorItemApproveView] وضعیت آیتم {item.id} به {status} تغییر یافت")
    #
    #                 # بررسی وضعیت کلی فاکتور
    #                 all_approved = factor.items.exists() and all(
    #                     item.status == 'APPROVE' for item in factor.items.all())
    #                 any_rejected = any(item.status == 'REJECTE' for item in factor.items.all()) # 💡 یکسان‌سازی
    #                 all_processed = all(item.status in ['APPROVE', 'REJECTE'] for item in factor.items.all()) # 💡 یکسان‌سازی
    #
    #                 if any_rejected:
    #                     factor.status = 'REJECTE' # 💡 یکسان‌سازی
    #                     factor.rejected_reason = log_comment or 'یکی از آیتم‌ها رد شده است'
    #                     factor.is_locked = True
    #                     factor._changed_by = user
    #                     if factor.tankhah.spent >= factor.amount:
    #                         factor.tankhah.spent -= factor.amount
    #                         factor.tankhah.save(update_fields=['spent'])
    #                         if factor.tankhah.project:
    #                             factor.tankhah.project.spent -= factor.amount
    #                             factor.tankhah.project.save(update_fields=['spent'])
    #                         logger.info(
    #                             f"[FactorItemApproveView] بودجه {factor.amount} به تنخواه {factor.tankhah.number} عودت داده شد")
    #                     factor.save()
    #                     self.send_notifications(
    #                         entity=factor,
    #                         action='REJECTE', # 💡 یکسان‌سازی
    #                         priority='HIGH',
    #                         description=f"فاکتور {factor.number} به دلیل رد آیتم‌ها رد شد. دلیل: {factor.rejected_reason}",
    #                         recipients=[factor.created_by_post] if factor.created_by_post else []
    #                     )
    #                     messages.warning(request, _('فاکتور به دلیل رد آیتم‌ها رد شد.'))
    #                     return redirect('dashboard_flows')
    #
    #                 elif all_approved:
    #                     factor.status = 'APPROVE'
    #                     factor.is_locked = current_stage.is_final_stage
    #                     factor._changed_by = user
    #                     factor.save()
    #                     if current_stage.auto_advance:
    #                         next_stage = AccessRule.objects.filter(
    #                             stage_order__gt=current_stage.stage_order,
    #                             is_active=True,
    #                             entity_type='FACTOR',
    #                             organization=tankhah.organization
    #                         ).order_by('stage_order').first()
    #                         if next_stage:
    #                             tankhah.current_stage = next_stage
    #                             tankhah.status = 'PENDING'
    #                             tankhah._changed_by = user
    #                             tankhah.save(update_fields=['current_stage', 'status'])
    #                             ApprovalLog.objects.create(
    #                                 tankhah=tankhah,
    #                                 factor=factor,
    #                                 user=user,
    #                                 action='STAGE_CHANGE',
    #                                 stage=next_stage,
    #                                 comment=f"تأیید آیتم‌ها و انتقال به {next_stage.stage}",
    #                                 post=user_post.post if user_post else None
    #                             )
    #                             approving_posts = AccessRule.objects.filter(
    #                                 stage_order=next_stage.stage_order,
    #                                 is_active=True,
    #                                 entity_type='FACTOR',
    #                                 action_type='APPROVE'
    #                             ).values_list('post', flat=True)
    #                             self.send_notifications(
    #                                 entity=factor,
    #                                 action='NEEDS_APPROVAL',
    #                                 priority='MEDIUM',
    #                                 description=f"فاکتور {factor.number} نیاز به تأیید شما در مرحله {next_stage.stage} دارد.",
    #                                 recipients=approving_posts
    #                             )
    #                             messages.success(request, f"فاکتور به مرحله {next_stage.stage} منتقل شد.")
    #                             return redirect('dashboard_flows')
    #                         elif current_stage.is_final_stage and current_stage.triggers_payment_order:
    #                             self.create_payment_order(factor, user)
    #                             messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند و دستور پرداخت ایجاد شد.'))
    #                             return redirect('dashboard_flows')
    #                         else:
    #                             messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند.'))
    #                             return redirect('dashboard_flows')
    #
    #                 elif all_processed:
    #                     factor.status = 'PARTIAL'
    #                     factor._changed_by = user
    #                     factor.save()
    #                     messages.warning(request, 'برخی از ردیف‌ها تأیید یا رد شده‌اند.')
    #                     return redirect('factor_item_approve', pk=factor.pk)
    #
    #                 else:
    #                     factor.status = 'PENDING'
    #                     factor._changed_by = user
    #                     factor.save()
    #                     if 'final_approve' in request.POST or 'change_stage' in request.POST:
    #                         messages.warning(request, 'لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.')
    #                     elif has_changes:
    #                         messages.success(request,
    #                                          'تغییرات ردیف‌ها با موفقیت ثبت شد، اما برخی ردیف‌ها هنوز در انتظار هستند.')
    #                     else:
    #                         ApprovalLog.objects.create(
    #                             tankhah=tankhah,
    #                             factor=factor,
    #                             user=user,
    #                             action='NO_CHANGE',
    #                             stage=current_stage,
    #                             comment='هیچ تغییری اعمال نشد: وضعیت آیتم‌ها مشخص نشده است.',
    #                             post=user_post.post if user_post else None
    #                         )
    #                         messages.error(request, 'لطفاً وضعیت آیتم‌ها را مشخص کنید.')
    #                     return redirect('factor_item_approve', pk=factor.pk)
    #
    #         except Exception as e:
    #             logger.error(f"[FactorItemApproveView] خطا در پردازش فرم‌ست: {e}", exc_info=True)
    #             messages.error(request, f"خطا در ذخیره‌سازی تغییرات ردیف‌ها: {str(e)}")
    #             return self.render_to_response(self.get_context_data(formset=formset))  # ارسال فرم‌ست با خطاها
    #
    #     else:
    #         logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است: {formset.errors}")
    #         error_messages = []
    #         if formset.non_form_errors():
    #             for error in formset.non_form_errors():
    #                 error_messages.append(str(error))
    #         for form in formset:
    #             for field, errors in form.errors.items():
    #                 for error in errors:
    #                     error_messages.append(f"{field}: {error}")
    #         display_errors = " ".join(error_messages) if error_messages else "اطلاعات واردشده معتبر نیستند."
    #         messages.error(request, f"خطا در پردازش فرم. لطفاً اطلاعات واردشده را بررسی کنید: {display_errors}")
    #         return self.render_to_response(self.get_context_data(formset=formset))  # ارسال فرم‌ست با خطاها
    #
    #     return redirect('factor_item_approve', pk=factor.pk)
    # in tankhah/Factor/view_FactorItemApprove.py
    # This complete method replaces the existing post method in your FactorItemApproveView class.

    def post(self, request, *args, **kwargs):
        logger.info(
            f"[FactorItemApproveView] درخواست POST برای فاکتور {self.kwargs.get('pk')} توسط {request.user.username}")
        self.object = self.get_object()
        factor = self.object
        tankhah = factor.tankhah
        user = request.user

        # بررسی پست فعال کاربر و سازمان‌های مرتبط
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

        # بررسی مرحله فعلی
        current_stage = tankhah.current_stage
        if not current_stage:
            logger.error(f"[FactorItemApproveView] مرحله فعلی برای تنخواه {tankhah.number} تعریف نشده است")
            messages.error(request, _("مرحله فعلی تنخواه نامعتبر است."))
            return redirect('factor_item_approve', pk=factor.pk)

        # بررسی دسترسی
        if not can_edit_approval(user, tankhah, current_stage, factor):
            logger.warning(f"[FactorItemApproveView] کاربر {user.username} دسترسی لازم برای ویرایش ندارد")
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا قبلاً اقدام کرده‌اید.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # بررسی قفل بودن
        if tankhah.is_locked or tankhah.is_archived or factor.locked:
            if is_hq_user:
                logger.info(f"[FactorItemApproveView] کاربر {user.username} قفل تنخواه/فاکتور را باز می‌کند")
                tankhah.is_locked = False
                tankhah.is_archived = False
                factor.locked = False
                tankhah.save(update_fields=['is_locked', 'is_archived'])
                factor.save(update_fields=['locked'])
            else:
                logger.warning(
                    f"[FactorItemApproveView] تنخواه {tankhah.number} یا فاکتور {factor.number} قفل/آرشیو شده است")
                messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
                return redirect('factor_item_approve', pk=factor.pk)

        # پردازش تغییر مرحله
        if 'change_stage' in request.POST:
            try:
                new_stage_order = int(request.POST.get('new_stage_order'))
                stage_change_reason = request.POST.get('stage_change_reason', '').strip()
                if not stage_change_reason:
                    raise ValidationError(_("توضیحات تغییر مرحله الزامی است."))
                max_change_level = user_post.post.max_change_level if user_post else 0
                if not is_hq_user and new_stage_order > max_change_level:
                    raise ValidationError(
                        _(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))

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
                        stage=new_stage,
                        comment=f"تغییر مرحله به {new_stage.stage}: {stage_change_reason}",
                        post=user_post.post if user_post else None,
                        is_temporary=False
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

        # پردازش رد کامل فاکتور
        if request.POST.get('reject_factor'):
            logger.info(f"[FactorItemApproveView] درخواست رد کامل فاکتور {factor.pk}")
            try:
                rejected_reason = request.POST.get('bulk_reason', '').strip()
                if not rejected_reason:
                    raise ValidationError(_("دلیل رد فاکتور الزامی است."))
                with transaction.atomic():
                    # بازگشت به مرحله ابتدایی (stage_order=1)
                    first_stage = AccessRule.objects.filter(
                        stage_order=1,
                        is_active=True,
                        entity_type='FACTOR',
                        organization=tankhah.organization
                    ).first()
                    if not first_stage:
                        raise ValidationError(_("مرحله ابتدایی برای این سازمان تعریف نشده است."))

                    factor.status = 'REJECTE'
                    factor.is_locked = True
                    factor.rejected_reason = rejected_reason
                    factor._changed_by = user
                    if factor.tankhah.spent >= factor.amount:
                        factor.tankhah.spent -= factor.amount
                        factor.tankhah.save(update_fields=['spent'])
                        if factor.tankhah.project:
                            factor.tankhah.project.spent -= factor.amount
                            factor.tankhah.project.save(update_fields=['spent'])
                        logger.info(
                            f"[FactorItemApproveView] بودجه {factor.amount} به تنخواه {factor.tankhah.number} عودت داده شد")
                    factor.save()
                    FactorItem.objects.filter(factor=factor).update(status='REJECTE')
                    tankhah.current_stage = first_stage
                    tankhah.status = 'PENDING'
                    tankhah._changed_by = user
                    tankhah.save(update_fields=['current_stage', 'status'])
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor=factor,
                        user=user,
                        action='REJECTE',
                        stage=current_stage,
                        comment=f"رد کامل فاکتور و بازگشت به مرحله ابتدایی: {rejected_reason}",
                        post=user_post.post if user_post else None,
                        is_temporary=False
                    )
                    self.send_notifications(
                        entity=factor,
                        action='REJECTE',
                        priority='HIGH',
                        description=f"فاکتور {factor.number} رد شد و به مرحله ابتدایی بازگشت. دلیل: {rejected_reason}",
                        recipients=[factor.created_by_post] if factor.created_by_post else []
                    )
                    messages.error(request, _('فاکتور رد شد و به مرحله ابتدایی بازگشت.'))
                    return redirect('dashboard_flows')
            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در رد فاکتور: {e}", exc_info=True)
                messages.error(request, _("خطا در رد فاکتور."))
                return redirect('factor_item_approve', pk=factor.pk)

        # پردازش تأیید نهایی
        if request.POST.get('final_approve'):
            logger.info(f"[FactorItemApproveView] درخواست تأیید نهایی برای فاکتور {factor.pk}")
            try:
                with transaction.atomic():
                    all_factors_approved = all(f.status == 'APPROVE' for f in tankhah.factors.all())
                    if not all_factors_approved:
                        logger.warning(f"[FactorItemApproveView] همه فاکتورهای تنخواه {tankhah.number} تأیید نشده‌اند")
                        messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
                        return redirect('factor_item_approve', pk=factor.pk)

                    # بررسی اینکه آیا مرحله فعلی آخرین مرحله است
                    next_stage = AccessRule.objects.filter(
                        stage_order__gt=current_stage.stage_order,
                        is_active=True,
                        entity_type='FACTOR',
                        organization=tankhah.organization
                    ).order_by('stage_order').first()
                    is_final_stage = not next_stage

                    if is_final_stage:
                        if tankhah.status == 'APPROVE':
                            logger.warning(f"[FactorItemApproveView] تنخواه {tankhah.number} قبلاً تأیید نهایی شده است")
                            messages.warning(request, _('این تنخواه قبلاً تأیید نهایی شده است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        if not user_post or not (
                                user_post.post.can_final_approve_factor or user_post.post.can_final_approve_tankhah):
                            logger.warning(f"[FactorItemApproveView] کاربر {user.username} مجاز به تأیید نهایی نیست")
                            messages.error(request, _('شما مجاز به تأیید نهایی فاکتور یا تنخواه نیستید.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        payment_number = request.POST.get('payment_number')
                        if not payment_number:
                            logger.error(
                                f"[FactorItemApproveView] شماره پرداخت برای تنخواه {tankhah.number} ارائه نشده است")
                            messages.error(request, _('برای تأیید نهایی، شماره پرداخت الزامی است.'))
                            return redirect('factor_item_approve', pk=factor.pk)

                        self.create_payment_order(factor, user)
                        tankhah.status = 'APPROVE'
                        tankhah.payment_number = payment_number
                        tankhah.is_locked = True
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['status', 'payment_number', 'is_locked'])
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor=factor,
                            user=user,
                            action='APPROVE',
                            stage=current_stage,
                            comment=_('تأیید نهایی تنخواه'),
                            post=user_post.post if user_post else None,
                            is_temporary=False,
                            is_final_approval=True
                        )
                        hq_posts = Post.objects.filter(organization__org_type__org_type='HQ')
                        self.send_notifications(
                            entity=factor,
                            action='APPROVE',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} تأیید نهایی شد و به دفتر مرکزی ارسال شد.",
                            recipients=hq_posts
                        )
                        messages.success(request, _('فاکتور تأیید نهایی شد.'))
                        return redirect('dashboard_flows')
                    else:
                        approved_reason = request.POST.get('bulk_reason', '').strip()
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
                            stage=next_stage,
                            comment=f"تأیید و انتقال به {next_stage.stage}. توضیحات: {approved_reason}",
                            post=user_post.post if user_post else None,
                            is_temporary=False
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

        # پردازش فرم‌ست آیتم‌ها
        formset = FactorItemApprovalFormSet(request.POST, request.FILES, instance=factor, prefix='items')
        if formset.is_valid():
            logger.info("[FactorItemApproveView] فرم‌ست آیتم‌ها معتبر است")
            logger.debug(f"[FactorItemApproveView] داده‌های فرم‌ست: {formset.cleaned_data}")
            try:
                with transaction.atomic():
                    has_changes = False
                    items_processed_count = 0
                    content_type = ContentType.objects.get_for_model(FactorItem)
                    action = None
                    log_comment = ''

                    # تأیید گروهی
                    if request.POST.get('bulk_approve') == 'on':
                        approved_reason = request.POST.get('bulk_reason', '').strip()
                        is_temporary = request.POST.get('is_temporary') == 'on'
                        for item in factor.items.all():
                            if item.status not in ['APPROVE', 'REJECTE']:
                                access_rule = AccessRule.objects.filter(
                                    organization=user_post.post.organization if user_post else factor.tankhah.organization,
                                    stage=current_stage.stage,
                                    stage_order=current_stage.stage_order,
                                    action_type='APPROVE',
                                    entity_type='FACTORITEM',
                                    min_level__lte=user_post.post.level if user_post else 0,
                                    branch=user_post.post.branch if user_post and user_post.post.branch else None,
                                    is_active=True
                                ).first()
                                if not access_rule and not (user.is_superuser or is_hq_user):
                                    logger.error(
                                        f"[FactorItemApproveView] کاربر {user.username} مجاز به APPROVE برای FACTORITEM نیست")
                                    raise ValueError(
                                        f"کاربر {user.username} مجاز به تأیید برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")

                                # بررسی اینکه آیا این پست قبلاً اقدام کرده
                                post_has_action = ApprovalLog.objects.filter(
                                    factor_item=item,
                                    factor=factor,
                                    post=user_post.post if user_post else None,
                                    stage=current_stage,
                                    action__in=['APPROVE', 'TEMP_APPROVED']
                                ).exists()
                                if post_has_action and not (user.is_superuser or is_hq_user):
                                    logger.warning(
                                        f"[FactorItemApproveView] پست {user_post.post} قبلاً در مرحله {current_stage.stage} برای آیتم {item.id} اقدام کرده است")
                                    continue

                                item.status = 'APPROVE'
                                item.description = approved_reason
                                item._changed_by = user
                                item.save()
                                has_changes = True
                                items_processed_count += 1
                                ApprovalLog.objects.create(
                                    tankhah=tankhah,
                                    factor=factor,
                                    factor_item=item,
                                    user=user,
                                    action='TEMP_APPROVED' if is_temporary else 'APPROVE',
                                    stage=current_stage,
                                    comment=approved_reason,
                                    post=user_post.post if user_post else None,
                                    content_type=content_type,
                                    object_id=item.id,
                                    is_temporary=is_temporary
                                )
                                # ارسال نوتیفیکیشن به پست بعدی
                                next_post = AccessRule.objects.filter(
                                    stage_order=current_stage.stage_order,
                                    entity_type='FACTORITEM',
                                    min_level__gt=user_post.post.level if user_post else 0,
                                    is_active=True,
                                    organization=tankhah.organization
                                ).order_by('min_level').first()
                                if next_post:
                                    self.send_notifications(
                                        entity=factor,
                                        action='NEEDS_APPROVAL',
                                        priority='MEDIUM',
                                        description=f"آیتم {item.id} از فاکتور {factor.number} نیاز به تأیید شما در مرحله {current_stage.stage} دارد.",
                                        recipients=[next_post.post]
                                    )
                        action = 'APPROVE'
                        log_comment = approved_reason

                    # رد گروهی
                    elif request.POST.get('bulk_reject') == 'on':
                        rejected_reason = request.POST.get('bulk_reason', '').strip()
                        if not rejected_reason:
                            raise ValidationError(_("دلیل رد برای رد گروهی الزامی است."))
                        is_temporary = request.POST.get('is_temporary') == 'on'
                        first_stage = AccessRule.objects.filter(
                            stage_order=1,
                            is_active=True,
                            entity_type='FACTOR',
                            organization=tankhah.organization
                        ).first()
                        if not first_stage:
                            raise ValidationError(_("مرحله ابتدایی برای این سازمان تعریف نشده است."))
                        for item in factor.items.all():
                            if item.status not in ['APPROVE', 'REJECTE']:
                                access_rule = AccessRule.objects.filter(
                                    organization=user_post.post.organization if user_post else factor.tankhah.organization,
                                    stage=current_stage.stage,
                                    stage_order=current_stage.stage_order,
                                    action_type='REJECTE',
                                    entity_type='FACTORITEM',
                                    min_level__lte=user_post.post.level if user_post else 0,
                                    branch=user_post.post.branch if user_post and user_post.post.branch else None,
                                    is_active=True
                                ).first()
                                if not access_rule and not (user.is_superuser or is_hq_user):
                                    logger.error(
                                        f"[FactorItemApproveView] کاربر {user.username} مجاز به REJECTE برای FACTORITEM نیست")
                                    raise ValueError(
                                        f"کاربر {user.username} مجاز به رد برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")

                                # بررسی اینکه آیا این پست قبلاً اقدام کرده
                                post_has_action = ApprovalLog.objects.filter(
                                    factor_item=item,
                                    factor=factor,
                                    post=user_post.post if user_post else None,
                                    stage=current_stage,
                                    action__in=['REJECTE', 'TEMP_REJECTED']
                                ).exists()
                                if post_has_action and not (user.is_superuser or is_hq_user):
                                    logger.warning(
                                        f"[FactorItemApproveView] پست {user_post.post} قبلاً در مرحله {current_stage.stage} برای آیتم {item.id} اقدام کرده است")
                                    continue

                                item.status = 'REJECTE'
                                item.description = rejected_reason
                                item._changed_by = user
                                item.save()
                                has_changes = True
                                items_processed_count += 1
                                ApprovalLog.objects.create(
                                    tankhah=tankhah,
                                    factor=factor,
                                    factor_item=item,
                                    user=user,
                                    action='TEMP_REJECTED' if is_temporary else 'REJECTE',
                                    stage=current_stage,
                                    comment=rejected_reason,
                                    post=user_post.post if user_post else None,
                                    content_type=content_type,
                                    object_id=item.id,
                                    is_temporary=is_temporary
                                )
                        # بازگشت به مرحله ابتدایی
                        tankhah.current_stage = first_stage
                        tankhah.status = 'PENDING'
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['current_stage', 'status'])
                        factor.status = 'REJECTE'
                        factor.is_locked = True
                        factor.rejected_reason = rejected_reason
                        factor._changed_by = user
                        if factor.tankhah.spent >= factor.amount:
                            factor.tankhah.spent -= factor.amount
                            factor.tankhah.save(update_fields=['spent'])
                            if factor.tankhah.project:
                                factor.tankhah.project.spent -= factor.amount
                                factor.tankhah.project.save(update_fields=['spent'])
                            logger.info(
                                f"[FactorItemApproveView] بودجه {factor.amount} به تنخواه {factor.tankhah.number} عودت داده شد")
                        factor.save()
                        self.send_notifications(
                            entity=factor,
                            action='REJECTE',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} رد شد و به مرحله ابتدایی بازگشت. دلیل: {rejected_reason}",
                            recipients=[factor.created_by_post] if factor.created_by_post else []
                        )
                        messages.error(request, _('فاکتور رد شد و به مرحله ابتدایی بازگشت.'))
                        return redirect('dashboard_flows')

                    # پردازش آیتم‌های فردی
                    else:
                        for form in formset:
                            if form.cleaned_data and form.has_changed():
                                item = form.instance
                                if not item.id:
                                    logger.error(f"[FactorItemApproveView] آیتم بدون ID یافت شد: {item}")
                                    continue
                                status = form.cleaned_data.get('status')
                                description = form.cleaned_data.get('description', '').strip()
                                comment = form.cleaned_data.get('comment', '').strip()
                                is_temporary = form.cleaned_data.get('is_temporary', False)

                                if not status:
                                    logger.warning(
                                        f"[FactorItemApproveView] وضعیت آیتم {item.id} خالی است، نادیده گرفته می‌شود")
                                    continue

                                # اعتبارسنجی دسترسی
                                if status in ['APPROVE', 'REJECTE']:
                                    access_rule = AccessRule.objects.filter(
                                        organization=user_post.post.organization if user_post else factor.tankhah.organization,
                                        stage=current_stage.stage,
                                        stage_order=current_stage.stage_order,
                                        action_type=status,
                                        entity_type='FACTORITEM',
                                        min_level__lte=user_post.post.level if user_post else 0,
                                        branch=user_post.post.branch if user_post and user_post.post.branch else None,
                                        is_active=True
                                    ).first()
                                    if not access_rule and not (user.is_superuser or is_hq_user):
                                        logger.error(
                                            f"[FactorItemApproveView] کاربر {user.username} مجاز به {status} برای FACTORITEM نیست")
                                        raise ValueError(
                                            f"کاربر {user.username} مجاز به {status} برای ردیف فاکتور نیست - قانون دسترسی یافت نشد")

                                    # بررسی اینکه آیا این پست قبلاً اقدام کرده
                                    post_has_action = ApprovalLog.objects.filter(
                                        factor_item=item,
                                        factor=factor,
                                        post=user_post.post if user_post else None,
                                        stage=current_stage,
                                        action__in=[status, f'TEMP_{status}']
                                    ).exists()
                                    if post_has_action and not (user.is_superuser or is_hq_user):
                                        logger.warning(
                                            f"[FactorItemApproveView] پست {user_post.post} قبلاً در مرحله {current_stage.stage} برای آیتم {item.id} اقدام {status} کرده است")
                                        continue

                                    has_changes = True
                                    items_processed_count += 1
                                    action = f'TEMP_{status}' if is_temporary else status
                                    ApprovalLog.objects.create(
                                        tankhah=tankhah,
                                        factor=factor,
                                        factor_item=item,
                                        user=user,
                                        action=action,
                                        stage=current_stage,
                                        comment=comment or description,
                                        post=user_post.post if user_post else None,
                                        content_type=content_type,
                                        object_id=item.id,
                                        is_temporary=is_temporary
                                    )
                                    item.status = status
                                    item.description = description
                                    item.comment = comment
                                    item._changed_by = user
                                    item.save()
                                    logger.info(f"[FactorItemApproveView] وضعیت آیتم {item.id} به {status} تغییر یافت")

                                    # ارسال نوتیفیکیشن به پست بعدی
                                    if status == 'APPROVE':
                                        next_post = AccessRule.objects.filter(
                                            stage_order=current_stage.stage_order,
                                            entity_type='FACTORITEM',
                                            min_level__gt=user_post.post.level if user_post else 0,
                                            is_active=True,
                                            organization=tankhah.organization
                                        ).order_by('min_level').first()
                                        if next_post:
                                            self.send_notifications(
                                                entity=factor,
                                                action='NEEDS_APPROVAL',
                                                priority='MEDIUM',
                                                description=f"آیتم {item.id} از فاکتور {factor.number} نیاز به تأیید شما در مرحله {current_stage.stage} دارد.",
                                                recipients=[next_post.post]
                                            )

                    # بررسی وضعیت کلی فاکتور
                    all_approved = factor.items.exists() and all(
                        item.status == 'APPROVE' for item in factor.items.all())
                    any_rejected = any(item.status == 'REJECTE' for item in factor.items.all())
                    all_processed = all(item.status in ['APPROVE', 'REJECTE'] for item in factor.items.all())

                    # تعداد پست‌های مجاز در این مرحله
                    required_posts = AccessRule.objects.filter(
                        stage_order=current_stage.stage_order,
                        entity_type='FACTORITEM',
                        action_type='APPROVE',
                        is_active=True,
                        organization=tankhah.organization
                    ).distinct('post').count()
                    approvals_count = ApprovalLog.objects.filter(
                        factor=factor,
                        stage=current_stage,
                        action__in=['APPROVE', 'TEMP_APPROVED']
                    ).distinct('post').count()

                    if any_rejected:
                        first_stage = AccessRule.objects.filter(
                            stage_order=1,
                            is_active=True,
                            entity_type='FACTOR',
                            organization=tankhah.organization
                        ).first()
                        if not first_stage:
                            raise ValidationError(_("مرحله ابتدایی برای این سازمان تعریف نشده است."))
                        factor.status = 'REJECTE'
                        factor.rejected_reason = log_comment or 'یکی از آیتم‌ها رد شده است'
                        factor.is_locked = True
                        factor._changed_by = user
                        if factor.tankhah.spent >= factor.amount:
                            factor.tankhah.spent -= factor.amount
                            factor.tankhah.save(update_fields=['spent'])
                            if factor.tankhah.project:
                                factor.tankhah.project.spent -= factor.amount
                                factor.tankhah.project.save(update_fields=['spent'])
                            logger.info(
                                f"[FactorItemApproveView] بودجه {factor.amount} به تنخواه {factor.tankhah.number} عودت داده شد")
                        factor.save()
                        tankhah.current_stage = first_stage
                        tankhah.status = 'PENDING'
                        tankhah._changed_by = user
                        tankhah.save(update_fields=['current_stage', 'status'])
                        self.send_notifications(
                            entity=factor,
                            action='REJECTE',
                            priority='HIGH',
                            description=f"فاکتور {factor.number} به دلیل رد آیتم‌ها به مرحله ابتدایی بازگشت. دلیل: {factor.rejected_reason}",
                            recipients=[factor.created_by_post] if factor.created_by_post else []
                        )
                        messages.warning(request, _('فاکتور به دلیل رد آیتم‌ها به مرحله ابتدایی بازگشت.'))
                        return redirect('dashboard_flows')

                    elif all_approved and approvals_count >= required_posts:
                        factor.status = 'APPROVE'
                        next_stage = AccessRule.objects.filter(
                            stage_order__gt=current_stage.stage_order,
                            is_active=True,
                            entity_type='FACTOR',
                            organization=tankhah.organization
                        ).order_by('stage_order').first()
                        factor.is_locked = not next_stage  # قفل فقط در مرحله نهایی
                        factor._changed_by = user
                        factor.save()
                        if next_stage:
                            tankhah.current_stage = next_stage
                            tankhah.status = 'PENDING'
                            tankhah._changed_by = user
                            tankhah.save(update_fields=['current_stage', 'status'])
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                factor=factor,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=next_stage,
                                comment=f"تأیید آیتم‌ها و انتقال به {next_stage.stage}",
                                post=user_post.post if user_post else None,
                                is_temporary=False
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
                            messages.success(request, f"فاکتور به مرحله {next_stage.stage} منتقل شد.")
                            return redirect('dashboard_flows')
                        else:
                            self.create_payment_order(factor, user)
                            messages.success(request, _('تمام ردیف‌های فاکتور تأیید شدند و دستور پرداخت ایجاد شد.'))
                            return redirect('dashboard_flows')

                    elif all_processed:
                        factor.status = 'PARTIAL'
                        factor._changed_by = user
                        factor.save()
                        messages.warning(request, 'برخی از ردیف‌ها تأیید یا رد شده‌اند.')
                        return redirect('factor_item_approve', pk=factor.pk)

                    else:
                        factor.status = 'PENDING'
                        factor._changed_by = user
                        factor.save()
                        if 'final_approve' in request.POST or 'change_stage' in request.POST:
                            messages.warning(request, 'لطفاً وضعیت تمام ردیف‌ها را مشخص کنید.')
                        elif has_changes:
                            messages.success(request,
                                             'تغییرات ردیف‌ها با موفقیت ثبت شد، اما برخی ردیف‌ها هنوز در انتظار هستند.')
                        else:
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                factor=factor,
                                user=user,
                                action='NO_CHANGE',
                                stage=current_stage,
                                comment='هیچ تغییری اعمال نشد: وضعیت آیتم‌ها مشخص نشده است.',
                                post=user_post.post if user_post else None,
                                is_temporary=False
                            )
                            messages.error(request, 'لطفاً وضعیت آیتم‌ها را مشخص کنید.')
                        return redirect('factor_item_approve', pk=factor.pk)

            except Exception as e:
                logger.error(f"[FactorItemApproveView] خطا در پردازش فرم‌ست: {e}", exc_info=True)
                messages.error(request, f"خطا در ذخیره‌سازی تغییرات ردیف‌ها: {str(e)}")
                return self.render_to_response(self.get_context_data(formset=formset))

        else:
            logger.warning(f"[FactorItemApproveView] فرم‌ست نامعتبر است: {formset.errors}")
            error_messages = []
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    error_messages.append(str(error))
            for form in formset:
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"ردیف {form.instance.id} - {field}: {error}")
            display_errors = " ".join(error_messages) if error_messages else "اطلاعات واردشده معتبر نیستند."
            messages.error(request, f"خطا در پردازش فرم. لطفاً اطلاعات واردشده را بررسی کنید: {display_errors}")
            return self.render_to_response(self.get_context_data(formset=formset))

        return redirect('factor_item_approve', pk=factor.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tankhah = factor.tankhah
        user = self.request.user

        logger.info(f"[FactorItemApproveView] شروع get_context_data برای فاکتور {factor.pk}")

        # بررسی مرحله فعلی
        current_stage = tankhah.current_stage
        if not current_stage:
            logger.error(f"[FactorItemApproveView] مرحله فعلی برای تنخواه {tankhah.number} تعریف نشده است")
            messages.error(self.request, _("مرحله فعلی تنخواه نامعتبر است."))
            context['can_edit'] = False
            context['can_change_stage'] = False
            context['workflow_stages'] = []
            context['can_final_approve_tankhah'] = False
            context['approval_logs'] = []
            return context

        # بررسی پست فعال کاربر و سازمان‌های مرتبط
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

        # فرم‌ست آیتم‌ها
        formset = FactorItemApprovalFormSet(self.request.POST or None, instance=factor, prefix='items')

        # لود لاگ‌ها برای آیتم‌ها
        item_ids = [form.instance.id for form in formset if form.instance.id]
        latest_logs_map = {}
        if item_ids:
            all_logs = ApprovalLog.objects.filter(
                factor_item_id__in=item_ids,
                factor=factor
            ).select_related('user', 'post', 'stage').order_by('factor_item_id', '-timestamp')
            for log in all_logs:
                if log.factor_item_id and log.factor_item_id not in latest_logs_map:
                    latest_logs_map[log.factor_item_id] = log

        form_log_pairs = [(form, latest_logs_map.get(form.instance.id)) for form in formset]

        # لود لاگ‌های تاریخچه
        approval_logs = ApprovalLog.objects.filter(
            factor=factor
        ).select_related('user', 'post', 'stage').order_by('-timestamp')

        # بررسی دسترسی‌ها
        user_can_edit = can_edit_approval(user, tankhah, current_stage, factor) or is_hq_user
        is_final_stage = current_stage.is_final_stage
        all_tankhah_factors_approved = all(f.status == 'APPROVE' for f in tankhah.factors.all())
        user_level = user_post.post.level if user_post else 0
        higher_approval_exists = ApprovalLog.objects.filter(
            factor=factor,
            stage=current_stage,
            post__level__gt=user_level
        ).exists()
        can_final_approve = user_can_edit and all_tankhah_factors_approved and is_final_stage

        # بررسی پردازش تمام آیتم‌ها
        all_items_processed = all(
            ApprovalLog.objects.filter(
                factor_item=item,
                factor=factor,
                action__in=['APPROVE', 'REJECTE'],
                content_type=ContentType.objects.get_for_model(FactorItem),
                object_id=item.id,
                is_temporary=False
            ).exists() for item in factor.items.all()
        ) if factor.items.exists() else False

        # مراحل مجاز برای تغییر
        allowed_stages = AccessRule.objects.filter(
            is_active=True,
            entity_type='FACTOR',
            organization=tankhah.organization
        ).order_by('stage_order').distinct()

        context.update({
            'formset': formset,
            'form_log_pairs': form_log_pairs,
            'approval_logs': approval_logs,
            'tankhah': tankhah,
            'can_edit': user_can_edit,
            'can_change_stage': user_can_edit and bool(allowed_stages),
            'workflow_stages': allowed_stages,
            'show_payment_number': tankhah.status == 'APPROVE' and not tankhah.payment_number,
            'can_final_approve_tankhah': can_final_approve,
            'higher_approval_changed': higher_approval_exists,
            'all_items_processed': all_items_processed,
            'items_count': factor.items.count(),
        })

        # پیام‌های اطلاع‌رسانی
        if context['items_count'] == 0:
            logger.warning(f"[FactorItemApproveView] هیچ آیتمی برای فاکتور {factor.number} یافت نشد")
            messages.error(self.request, _('هیچ آیتمی برای این فاکتور وجود ندارد.'))
        elif not context['can_edit']:
            logger.warning(f"[FactorItemApproveView] دسترسی برای کاربر {user.username} رد شد")
            messages.error(self.request, _('شما برای ویرایش در این مرحله دسترسی ندارید یا قبلاً اقدام کرده‌اید.'))
        elif context['all_items_processed']:
            logger.info(f"[FactorItemApproveView] تمام آیتم‌های فاکتور {factor.number} پردازش شده‌اند")
            messages.info(self.request,
                          _('تمام آیتم‌های این فاکتور قبلاً پردازش نهایی شده‌اند، اما می‌توانید تاریخچه اقدامات را مشاهده کنید یا مرحله را تغییر دهید.'))

        logger.info(
            f"[FactorItemApproveView] تعداد جفت‌های فرم: {len(form_log_pairs)}, تعداد لاگ‌ها: {len(approval_logs)}")
        return context

    def create_payment_order(self, factor, user):
        logger.info(f"[FactorItemApproveView] شروع ایجاد دستور پرداخت برای فاکتور {factor.pk}")
        try:
            with transaction.atomic():
                initial_po_stage = AccessRule.objects.filter(
                    entity_type='PAYMENT_ORDER',
                    stage_order=1,
                    is_active=True,
                    organization=factor.tankhah.organization
                ).first()
                if not initial_po_stage:
                    logger.error(f"[Stage] مرحله اولیه برای دستور پرداخت یافت نشد")
                    messages.error(self.request, "مرحله اولیه برای دستور کار تعریف یافت نشد.")
                    return

                tankhah_remaining = factor.tankhah.budget - factor.tankhah.spent
                if factor.amount > tankhah_remaining:
                    logger.error(f"[Budget] بودجه تنخواه کافی نیست: {factor.amount} > {tankhah_remaining}")
                    messages.error(self.request, "بودجه کافی نیست.")
                    return

                if factor.tankhah.project:
                    project_remaining = factor.tankhah.project.budget - factor.tankhah.project.spent
                    if factor.amount > project_remaining:
                        logger.error(f"[PROJECT] بودجه پروژه کافی نیست: {factor.amount} > {project_remaining}")
                        messages.error(self.request, "بودجه پروژه کافی نیست.")
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
                    issue_date=timezone.now(),
                    payee=factor.payee or Payee.objects.filter(is_active=True).first(),
                    min_signatures=initial_po_stage.min_signatures or 1,
                    order_number=PaymentOrder().generate_payment_order_number()
                )
                payment_order.related_factors.add(factor)
                payment_order._request = self.request
                payment_order.save()

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

                approving_posts = Post.objects.filter(
                    stage_order=initial_po_stage.stage_order,
                    is_active=True,
                    entity_type='PAYMENT_ORDER',
                    action_type='APPROVE'
                )
                self.send_notifications(
                    entity=factor,
                    action='CREATED',
                    priority='HIGH',
                    description=f"دستور پرداخت برای {payment_order.order_number} فاکتور {factor.number} ایجاد شد.",
                    recipients=approving_posts
                )
                messages.success(self.request, f'دستور پرداخت {payment_order.order_number} ایجاد شد.')
        except Exception as e:
            logger.error(f"[FactorItemApproveView] خطا در ایجاد دستور پرداخت: {e}")
            messages.error(self.request, "خطا در ایجاد دستور پرداخت.")

    @staticmethod
    def send_notifications(self, entity, action, priority, description, recipients=None):
        logger.info(f"ارسال اعلان برای {entity.__class__.__name__} {getattr(entity, 'number', entity.id)}: {action}")
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
            logger.info(f"اعلان به کاربر {user.username} برای {entity_type} {getattr(entity, 'number', '')} ارسال شد")

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
        logger.info(f"اعلان برای {entity_type} {getattr(entity, 'number', '')} با اقدام {action} ارسال شد")