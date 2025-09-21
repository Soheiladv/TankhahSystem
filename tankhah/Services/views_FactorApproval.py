import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.forms import modelformset_factory
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from tankhah.Services.approval_service import ApprovalService
from tankhah.Services.forms_Approve import FactorItemForm
from tankhah.models import Factor, FactorItem, ApprovalLog
from core.models import  Status, Post, UserPost
from budgets.models import     PaymentOrder  # Assuming PaymentOrder is in models
from tankhah.workflow_service import WorkflowService

logger = logging.getLogger('ApprovalService')

# --   New View Version
class FactorApprovalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    pass
    template_name = 'factor_approval_modern.html'
    permission_required = 'tankhah.view_factor'  # Basic permission to view

    # Override get_permission_required to handle dyna\
    # ic permissions based on action
    def get_permission_required(self):
        if self.request.method == 'POST':
            if 'change_stage' in self.request.POST:
                return ('tankhah.change_accessrule',)  # Permission to change stage
            elif 'final_approve' in self.request.POST or 'save_changes' in self.request.POST:
                return ('tankhah.change_factoritem',)  # Permission to approve/reject items
            elif 'reject_factor' in self.request.POST:
                return ('tankhah.change_factor',)  # Permission to reject the whole factor
        return self.permission_required

    def get_context_data(self, factor, request, formset=None):
        logger.debug(f"FactorApprovalView: Getting context data for factor ID {factor.id}")

        user_post = request.user.userpost_set.filter(is_active=True).first()
        if not user_post:
            messages.error(request, "شما پست فعالی در سازمان ندارید.")
            logger.warning(f"User {request.user.username} has no active post.")

        can_edit = factor.can_approve(request.user)  # Assuming this method exists on Factor
        can_final_approve_tankhah = factor.can_final_approve(request.user)  # Assuming this method exists on Factor

        # Determine if payment number should be shown (example logic)
        # Show if factor is finally approved and user can final approve
        show_payment_number = factor.status == 'APPROVED_FINAL' and can_final_approve_tankhah

        if formset is None:
            FactorItemFormSet = modelformset_factory(FactorItem, form=FactorItemForm, extra=0)
            formset = FactorItemFormSet(queryset=FactorItem.objects.filter(factor=factor))

        form_log_pairs = []
        for form in formset:
            # IMPORTANT: ApprovalLog model only has FK to Factor, not FactorItem.
            # The HTML template expects item-specific logs. This is a logical inconsistency.
            # For now, we pass the latest log for the *factor* to all items.
            # This means the "وضعیت" column in the table will show the overall factor's latest status,
            # not the individual item's specific approval history.
            # A more robust solution would require a FactorItemApprovalLog model or a generic relation on ApprovalLog.
            latest_factor_log = ApprovalLog.objects.filter(
                factor=factor
            ).exclude(action='STAGE_CHANGE').order_by('-timestamp').first()

            form_log_pairs.append((form, latest_factor_log))

        approval_logs = ApprovalLog.objects.filter(factor=factor).order_by('-timestamp')

        workflow_stages = WorkflowService.get_workflow_stages(factor.tankhah.organization)
        stage_info = WorkflowService.get_current_stage_info(factor)

        context = {
            'factor': factor,
            'formset': formset,
            'form_log_pairs': form_log_pairs,
            'approval_logs': approval_logs,
            'can_edit': can_edit,
            'can_final_approve_tankhah': can_final_approve_tankhah,
            'show_payment_number': show_payment_number,
            'workflow_stages': workflow_stages,
            'can_change_stage': request.user.has_perm('tankhah.change_accessrule'),
            # Permission for manual stage change
            'stage_info': stage_info,
            'all_items_processed': factor.all_items_processed(),  # Assuming this method exists on Factor
        }
        logger.debug(f"Context data prepared for factor {factor.id}.")
        return context

    def get(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk)
        logger.info(f"GET request for Factor ID: {pk} by user {request.user.username}")

        if not factor.can_view(request.user):  # Assuming a can_view method on Factor
            logger.warning(f"User {request.user.username} tried to view factor {pk} without permission.")
            raise PermissionDenied("شما دسترسی لازم برای مشاهده این فاکتور را ندارید.")

        context = self.get_context_data(factor, request)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        factor = get_object_or_404(Factor, pk=pk)
        logger.info(f"POST request for Factor ID: {pk} by user {request.user.username}")

        # Check general permission for any POST action on this factor
        if not factor.can_approve(request.user) and not request.user.has_perm('tankhah.change_accessrule'):
            logger.warning(f"User {request.user.username} tried to modify factor {pk} without sufficient permission.")
            raise PermissionDenied("شما دسترسی لازم برای انجام این عملیات را ندارید.")

        FactorItemFormSet = modelformset_factory(FactorItem, form=FactorItemForm, extra=0)
        formset = FactorItemFormSet(request.POST, queryset=FactorItem.objects.filter(factor=factor))

        with transaction.atomic():
            # Handle stage change
            if 'change_stage' in request.POST:
                if not request.user.has_perm('tankhah.change_accessrule'):
                    messages.error(request, "شما دسترسی لازم برای تغییر مرحله را ندارید.")
                    logger.warning(f"User {request.user.username} attempted unauthorized stage change for factor {pk}.")
                    return redirect(request.path_info)

                new_stage_order = request.POST.get('new_stage_order')
                stage_change_reason = request.POST.get('stage_change_reason', '')

                try:
                    new_stage = AccessRule.objects.get(
                        organization=factor.tankhah.organization,
                        entity_type='FACTOR',
                        stage_order=new_stage_order
                    )
                    factor.tankhah.current_stage = new_stage
                    factor.tankhah.save()

                    ApprovalLog.objects.create(
                        factor=factor,
                        action='STAGE_CHANGE',
                        stage=new_stage,
                        user=request.user,
                        post=request.user.userpost_set.filter(is_active=True).first().post,
                        comment=f"تغییر مرحله به صورت دستی به: {new_stage.stage}. دلیل: {stage_change_reason}",
                        content_type=ContentType.objects.get_for_model(factor),
                        object_id=factor.id
                    )
                    messages.success(request, "مرحله گردش کار با موفقیت تغییر یافت.")
                    logger.info(f"Factor {pk} stage changed to {new_stage.stage_order} by {request.user.username}.")
                except AccessRule.DoesNotExist:
                    messages.error(request, "مرحله انتخاب شده نامعتبر است.")
                    logger.error(f"Invalid stage order {new_stage_order} for factor {pk}.")
                except Exception as e:
                    messages.error(request, f"خطا در تغییر مرحله: {e}")
                    logger.exception(f"Error changing stage for factor {pk}.")
                return redirect(request.path_info)

            # Handle bulk actions (reject_factor_full takes precedence)
            reject_factor_full = 'reject_factor' in request.POST
            bulk_approve = 'bulk_approve' in request.POST
            bulk_reject = 'bulk_reject' in request.POST
            is_temporary = 'is_temporary' in request.POST
            bulk_reason = request.POST.get('bulk_reason', '')

            if reject_factor_full:
                if not bulk_reason:
                    messages.error(request, "برای رد کامل فاکتور، ارائه توضیحات اجباری است.")
                    logger.warning(
                        f"User {request.user.username} attempted full rejection of factor {pk} without reason.")
                    context = self.get_context_data(factor, request, formset)
                    return render(request, self.template_name, context)

                try:
                    ApprovalService.reject_factor(request.user, factor, bulk_reason)
                    messages.success(request, "فاکتور با موفقیت رد و بودجه آزاد شد.")
                    logger.info(f"Factor {pk} fully rejected by {request.user.username}.")
                    return redirect(reverse_lazy('dashboard_flows'))  # Redirect to a list or dashboard
                except PermissionDenied as e:
                    messages.error(request, str(e))
                    logger.warning(f"Permission denied for user {request.user.username} to reject factor {pk}.")
                except Exception as e:
                    messages.error(request, f"خطا در رد کامل فاکتور: {e}")
                    logger.exception(f"Error during full rejection of factor {pk}.")
                context = self.get_context_data(factor, request, formset)
                return render(request, self.template_name, context)

            if formset.is_valid():
                logger.debug(f"Formset is valid for factor {pk}.")

                # Process individual items (update their status/comment based on formset)
                for form in formset:
                    item = form.save(commit=False)
                    # The status and comment fields are part of the form, so they are already handled by form.save()
                    # We just need to ensure they are saved to the database.
                    item.save()
                    logger.debug(f"FactorItem {item.id} updated.")

                # Determine the overall action based on buttons clicked or bulk switches
                overall_action = None
                if 'final_approve' in request.POST:
                    overall_action = 'FINAL_APPROVE'
                elif 'save_changes' in request.POST:
                    overall_action = 'SAVE_CHANGES'

                # Override with bulk actions if active
                if bulk_approve:
                    overall_action = 'BULK_APPROVE'
                elif bulk_reject:
                    overall_action = 'BULK_REJECT'
                    if not bulk_reason:
                        messages.error(request, "برای رد گروهی، ارائه توضیحات اجباری است.")
                        context = self.get_context_data(factor, request, formset)
                        return render(request, self.template_name, context)

                try:
                    if overall_action in ['FINAL_APPROVE', 'SAVE_CHANGES', 'BULK_APPROVE']:
                        ApprovalService.approve_factor(
                            request.user,
                            factor,
                            comment=bulk_reason if bulk_reason else "تأیید آیتم‌ها",
                            is_temporary=is_temporary
                        )
                        messages.success(request, "تغییرات با موفقیت ذخیره و تأیید شد.")
                        logger.info(f"Factor {pk} items processed and factor approved by {request.user.username}.")

                        if overall_action == 'FINAL_APPROVE':
                            factor.consume_budget()  # Consume budget upon final approval
                            factor.status = 'APPROVED_FINAL'  # Set status to final approved
                            factor.save()
                            messages.success(request, "فاکتور به صورت نهایی تأیید و بودجه مصرف شد.")
                            logger.info(f"Factor {pk} finally approved and budget consumed by {request.user.username}.")

                            # Handle payment number if applicable
                            if 'payment_number' in request.POST:
                                payment_number = request.POST.get('payment_number')
                                if payment_number:
                                    PaymentOrder.objects.create(
                                        factor=factor,
                                        payment_number=payment_number,
                                        created_by=request.user  # Assuming created_by for transaction
                                    )
                                    messages.success(request, "شماره پرداخت ثبت شد.")
                                    logger.info(f"Payment number {payment_number} recorded for factor {pk}.")
                                else:
                                    messages.warning(request, "شماره پرداخت وارد نشد.")
                                    logger.warning(f"Payment number not provided for factor {pk}.")

                    elif overall_action == 'BULK_REJECT':
                        ApprovalService.reject_factor(request.user, factor, bulk_reason)
                        messages.success(request, "فاکتور با موفقیت رد و بودجه آزاد شد.")
                        logger.info(f"Factor {pk} rejected by {request.user.username}.")
                        return redirect(reverse_lazy('dashboard_flows'))  # Redirect after rejection

                except PermissionDenied as e:
                    messages.error(request, str(e))
                    logger.warning(f"Permission denied for user {request.user.username} to approve/reject factor {pk}.")
                except Exception as e:
                    messages.error(request, f"خطا در پردازش فاکتور: {e}")
                    logger.exception(f"Error processing factor {pk} by {request.user.username}.")

                return redirect(request.path_info)  # Redirect to refresh the page
            else:
                logger.warning(f"Formset is invalid for factor {pk}. Errors: {formset.errors}")
                messages.error(request, "لطفاً خطاهای فرم را برطرف کنید.")
                context = self.get_context_data(factor, request, formset)
                return render(request, self.template_name, context)