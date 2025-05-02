from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory # Import inlineformset_factory
from django.shortcuts import redirect
from django.views.generic import DetailView

from core.PermissionBase import PermissionBaseView
from core.models import UserPost, WorkflowStage
from tankhah.forms import FactorItemApprovalForm
from tankhah.fun_can_edit_approval import can_edit_approval
from tankhah.models import Factor, FactorItem, ApprovalLog
from django.utils.translation import gettext_lazy as _

import logging
logger = logging.getLogger(__name__)
"""تأیید آیتم‌های فاکتور"""

class FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    # permission_codenames = ['tankhah.FactorItem_approve'] # Use PermissionRequiredMixin's permission_required
    permission_required = 'tankhah.FactorItem_approve' # Standard Django permission
    context_object_name = 'factor' # Use 'factor' for clarity in template
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object # Factor instance is already available
        tankhah = factor.tankhah
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0
        logger = logging.getLogger('factor_approval') # Specific logger

        logger.info(f"[ApproveView-Context] شروع get_context_data برای فاکتور {factor.pk}")

        # --- نشانه گذاری مشاهده ---
        # Ensure mark_approval_seen exists and works correctly
        # if user_level > tankhah.current_stage.order:
        #     try:
        #         mark_approval_seen(self.request, tankhah)
        #         logger.debug(f"[ApproveView-Context] مشاهده تایید برای تنخواه {tankhah.pk} ثبت شد.")
        #     except Exception as e:
        #          logger.error(f"[ApproveView-Context] خطا در mark_approval_seen: {e}")
        # ---

        # --- ایجاد Inline Formset ---
        FactorItemApprovalFormSet = inlineformset_factory(
            Factor,           # Parent model
            FactorItem,       # Child model
            form=FactorItemApprovalForm, # Your approval form
            extra=0,          # Don't show extra forms
            can_delete=False  # Don't allow deleting items here
        )

        # Instantiate the formset
        # Pass POST data if it's a POST request, otherwise None
        # Crucially, pass instance=factor to link it to the parent
        formset = FactorItemApprovalFormSet(
            self.request.POST or None,
            instance=factor,
            prefix='items' # Use a prefix for the formset fields
        )
        context['formset'] = formset
        logger.debug(f"[ApproveView-Context] فرم‌ست ایجاد شد. تعداد فرم‌ها: {len(formset.forms)}")
        # Log formset errors if it's a POST request that failed validation in post()
        if self.request.POST and not formset.is_valid():
             logger.warning(f"[ApproveView-Context] فرم‌ست نامعتبر است. خطاها: {formset.errors}")
             logger.warning(f"[ApproveView-Context] خطاهای غیر فرم فرم‌ست: {formset.non_form_errors()}")

        # --- No need for item_form_pairs anymore ---
        # The template will loop directly through context['formset']

        # --- سایر اطلاعات کانتکست ---
        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=tankhah).select_related('user', 'post', 'stage', 'factor_item').order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah

        # Helper function can_edit_approval assumed to exist
        context['can_edit'] = can_edit_approval(user, tankhah, tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and tankhah.current_stage.order < user_level
        context['workflow_stages'] = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('order')
        context['show_payment_number'] = tankhah.status == 'APPROVED' and not tankhah.payment_number
        # Check if ALL items of THIS factor are approved for final approval trigger
        all_items_approved = all(item.status == 'APPROVED' for item in factor.items.all()) if factor.items.exists() else False
        context['can_final_approve_factor'] = context['can_edit'] and all_items_approved # Can this factor be approved?
        # This seems to check ALL factors of the tankhah, maybe rename for clarity?
        context['can_final_approve_tankhah'] = context['can_edit'] and all(f.status == 'APPROVED' for f in tankhah.factors.all())

        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=tankhah, post__level__gt=user_level,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE'] # Consider FactorItem actions too?
        ).exists()
        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=tankhah, action='STAGE_CHANGE', comment__contains='تأیید نهایی' # Make this more robust? Maybe a dedicated flag?
        ).exists()

        logger.info(f"[ApproveView-Context] وضعیت‌های آیتم فعلی: {[item.status for item in factor.items.all()]}")
        logger.info(f"[ApproveView-Context] پایان get_context_data")
        return context

    def post(self, request, *args, **kwargs):
        logger.info(f"[ApproveView-POST] درخواست POST دریافت شد.")
        self.object = self.get_object() # Set self.object for context rendering on error
        factor = self.object
        tankhah = factor.tankhah
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        logger.debug(f"[ApproveView-POST] کاربر: {user.username}, سطح: {user_level}, حداکثر تغییر: {max_change_level}")
        logger.debug(f"[ApproveView-POST] داده‌های POST: {request.POST}")

        # --- بررسی قفل یا آرشیو بودن و دسترسی ویرایش ---
        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل/آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)
        if not can_edit_approval(user, tankhah, tankhah.current_stage):
            messages.error(request, _('شما دسترسی لازم برای ویرایش در این مرحله را ندارید یا سطح بالاتری اقدام کرده است.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # --- پردازش اقدامات خاص ---
        if 'change_stage' in request.POST:
            # ... (منطق تغییر مرحله دستی - بدون تغییر) ...
            try:
                new_stage_order = int(request.POST.get('new_stage_order'))
                # ... (rest of stage change validation and logic) ...
                if tankhah.current_stage.order >= user_level: raise ValidationError(_('شما نمی‌توانید به مرحله برابر یا بالاتر تغییر دهید.'))
                if new_stage_order > max_change_level: raise ValidationError(_(f"سطح انتخابی ({new_stage_order}) بیشتر از حد مجاز شما ({max_change_level}) است."))
                new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
                if not new_stage: raise ValidationError(_("مرحله انتخاب شده نامعتبر است."))

                with transaction.atomic():
                    old_stage_name = tankhah.current_stage.name
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING' # Reset status on stage change
                    tankhah.save()
                    ApprovalLog.objects.create(
                         tankhah=tankhah, user=user, action='STAGE_CHANGE', stage=new_stage,
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
            # ... (منطق رد کل فاکتور - بدون تغییر) ...
             with transaction.atomic():
                 factor.status = 'REJECTED'
                 factor.save()
                 # Mark all items as rejected too
                 items_updated = FactorItem.objects.filter(factor=factor).update(status='REJECTED')
                 logger.info(f"[ApproveView-POST] فاکتور {factor.pk} و {items_updated} آیتم آن رد شد توسط {user.username}")
                 # Create ONE log for the factor rejection
                 ApprovalLog.objects.create(
                     tankhah=tankhah, factor=factor, user=user, action='REJECT', stage=tankhah.current_stage,
                     comment=_('رد کامل فاکتور'), post=user_post.post if user_post else None
                 )
                 # Maybe create individual item logs if necessary? Depends on requirements.
             messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
             return redirect('dashboard_flows') # Or factor_list?


        if request.POST.get('final_approve'):
             # ... (منطق تایید نهایی تنخواه - بررسی همه فاکتورها) ...
             # Renamed context var to 'can_final_approve_tankhah'
              with transaction.atomic():
                  all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                  if all_factors_approved:
                      # ... (logic to move to next stage or set as PAID) ...
                      current_stage_order = tankhah.current_stage.order
                      next_stage = WorkflowStage.objects.filter(order__gt=current_stage_order).order_by('order').first()
                      if next_stage:
                           # ... (move to next stage logic + log) ...
                           tankhah.current_stage = next_stage; tankhah.status = 'PENDING'; tankhah.save()
                           ApprovalLog.objects.create(tankhah=tankhah, user=user, action='STAGE_CHANGE', stage=next_stage, comment=f"تایید نهایی و انتقال به {next_stage.name}", post=user_post.post if user_post else None)
                           messages.success(request, _(f"تایید نهایی انجام و به مرحله {next_stage.name} منتقل شد."))
                           return redirect('dashboard_flows') # Redirect after successful final approve
                      elif tankhah.current_stage.is_final_stage:
                           payment_number = request.POST.get('payment_number')
                           if payment_number:
                                tankhah.payment_number = payment_number; tankhah.status = 'PAID'; tankhah.save()
                                messages.success(request, _('تنخواه پرداخت شد.'))
                                return redirect('dashboard_flows')
                           else:
                                messages.error(request, _('برای مرحله نهایی، شماره پرداخت الزامی است.'))
                                # Stay on the same page to allow entering payment number
                                return redirect('factor_item_approve', pk=factor.pk)
                      else:
                           messages.error(request, _('مرحله بعدی برای گردش کار تعریف نشده است.'))
                  else:
                       messages.warning(request, _('تمام فاکتورهای این تنخواه باید ابتدا تأیید شوند.'))
              # Redirect back if final approval wasn't successful or possible yet
              return redirect('factor_item_approve', pk=factor.pk)


        # --- پردازش فرم‌ست تایید/رد آیتم‌ها ---
        FactorItemApprovalFormSet = inlineformset_factory(
             Factor, FactorItem, form=FactorItemApprovalForm, extra=0, can_delete=False
        )
        # Pass request.POST and the factor instance to bind the formset
        formset = FactorItemApprovalFormSet(request.POST, instance=factor, prefix='items')

        if formset.is_valid():
            logger.info("[ApproveView-POST] فرم‌ست آیتم‌ها معتبر است.")
            try:
                with transaction.atomic():
                    logger.info("[ApproveView-POST] شروع تراکنش برای ذخیره تغییرات آیتم‌ها...")
                    has_changes = False
                    items_processed_count = 0

                    # Loop through forms in the formset
                    for form in formset:
                        # process only if the form has data submitted for its fields
                        # form.has_changed() might be less reliable if only hidden field changed via JS
                        # Check cleaned_data instead, or if 'action' is present and different
                        if form.cleaned_data: # Check if form has cleaned data
                            item = form.instance # Get the associated FactorItem instance
                            action = form.cleaned_data.get('action')
                            comment = form.cleaned_data.get('comment', '')

                            # Determine the action from bulk buttons if they were checked
                            if request.POST.get('bulk_approve') == 'on': action = 'APPROVED'
                            elif request.POST.get('bulk_reject') == 'on': action = 'REJECTED'

                            # Process only if a valid action is selected and different from current status
                            if action and action != 'NONE' and action != item.status:
                                logger.info(f"[ApproveView-POST] پردازش آیتم {item.id}: اقدام='{action}', وضعیت فعلی='{item.status}'")
                                has_changes = True
                                items_processed_count += 1

                                # ایجاد لاگ قبل از تغییر وضعیت
                                ApprovalLog.objects.create(
                                    tankhah=tankhah, factor_item=item, user=user,
                                    action=action, stage=tankhah.current_stage,
                                    comment=comment, post=user_post.post if user_post else None
                                )

                                # ذخیره تغییر وضعیت آیتم
                                item.status = action
                                # Save the form - this saves the linked instance (item)
                                form.save() # Save the form which saves the item instance
                                logger.info(f"[ApproveView-POST] وضعیت آیتم {item.id} به {action} تغییر یافت و ذخیره شد.")
                            # else: logger.debug(f"Item {item.id}: No action needed (Action: {action}, Status: {item.status})")

                    # --- بروزرسانی وضعیت کلی فاکتور پس از پردازش همه آیتم‌ها ---
                    if has_changes:
                         # Refresh items from DB to get latest statuses
                         factor.refresh_from_db()
                         all_approved = True
                         any_rejected = False
                         items_exist = factor.items.exists()

                         if items_exist:
                             for item in factor.items.all():
                                 if item.status == 'REJECTED':
                                     any_rejected = True
                                     all_approved = False
                                     break # No need to check further if one is rejected
                                 elif item.status != 'APPROVED':
                                     all_approved = False
                         else:
                             all_approved = False # Cannot be approved if no items

                         if any_rejected:
                             new_factor_status = 'PENDING' # Or REJECTED? Decide business logic
                             messages.warning(request, _('برخی ردیف‌ها رد شدند. وضعیت فاکتور به حالت انتظار بازگشت.'))
                             # Optional: Move stage down if rejection happened
                             # ... (logic for stage down) ...
                         elif all_approved and items_exist:
                             new_factor_status = 'APPROVED'
                             messages.success(request, _('تمام ردیف‌های معتبر تأیید شدند. می‌توانید تأیید نهایی را انجام دهید.'))
                         else: # Mix of PENDING and APPROVED, or no items
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

                # --- End Transaction ---

            except Exception as e:
                 logger.error(f"[ApproveView-POST] خطا در حین پردازش فرم‌ست آیتم‌ها: {e}", exc_info=True)
                 messages.error(request, _("خطا در ذخیره‌سازی تغییرات ردیف‌ها."))
                 # Render page again with the invalid formset (errors should be attached)
                 # No need to manually pass formset to context, DetailView handles it
                 return self.render_to_response(self.get_context_data())


            # Redirect back to the same page after successful processing
            return redirect('factor_item_approve', pk=factor.pk)
        else:
            # Formset is invalid, render the page again with errors
            logger.warning(f"[ApproveView-POST] فرم‌ست نامعتبر است.")
            messages.error(request, _('لطفاً خطاهای فرم ردیف‌ها را بررسی کنید.'))
            # Pass the invalid formset to context explicitly for rendering errors
            # Note: get_context_data already created the formset instance with POST data
            # We just need to re-render the template using it.
            context = self.get_context_data() # Re-get context, which now has the invalid formset
            return self.render_to_response(context)
