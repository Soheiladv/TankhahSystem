# budgets/views.py
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.db import transaction

from budgets.BudgetReturn.froms_BudgetTransferForm import BudgetTransferForm, BudgetReturnForm
from budgets.models import BudgetAllocation
import logging
from core.PermissionBase import PermissionBaseView
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class BudgetTransferView(PermissionBaseView, FormView):
    form_class = BudgetTransferForm
    template_name = 'budgets/ReturnTransfer/budget_transfer_form.html' # تمپلیت شما
    success_url = reverse_lazy('budgetallocation_list') # یا URL مناسب دیگر
    permission_codenames = ['budgets.BudgetTransfer'] # دسترسی لازم (مطمئن شوید این پرمیشن وجود دارد)
    check_organization = False # یا True اگر لازم است

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        logger.debug(f"BudgetTransferView: Passing user {self.request.user.username} to form.")
        return kwargs

    def form_valid(self, form):
        logger.info(f"BudgetTransferView: Form is valid for user {self.request.user.username}. Attempting transfer.")
        try:
            return_tx, alloc_tx = form.execute_transfer() # فراخوانی متد اجرای انتقال

            messages.success(
                self.request,
                _("جابجایی بودجه از تخصیص پروژه '{}' به '{}' به مبلغ {:,} ریال با موفقیت انجام شد.").format(
                    form.cleaned_data['source_allocation'].project.name, # نمایش نام پروژه
                    form.cleaned_data['destination_allocation'].project.name,
                    form.cleaned_data['amount']
                )
            )
            logger.info(
                f"Budget transferred successfully by {self.request.user.username}: "
                f"{form.cleaned_data['amount']} from PBA {form.cleaned_data['source_allocation'].pk} "
                f"to PBA {form.cleaned_data['destination_allocation'].pk}."
            )
            return super().form_valid(form)

        except ValidationError as e:
            logger.warning(f"BudgetTransferView: Validation error during transfer execution - {e}")
            # اضافه کردن خطاها به فرم تا در تمپلیت نمایش داده شوند
            if hasattr(e, 'message_dict'):
                for field, errors_list in e.message_dict.items():
                    for error_msg in errors_list:
                        form.add_error(field if field != '__all__' else None, error_msg)
            elif hasattr(e, 'messages'):
                 for error_msg in e.messages:
                      form.add_error(None, error_msg)
            else:
                form.add_error(None, str(e))
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"BudgetTransferView: Unexpected error during transfer execution - {e}", exc_info=True)
            messages.error(self.request, _("خطای پیش‌بینی نشده‌ای در هنگام جابجایی بودجه رخ داد."))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جابجایی بودجه بین تخصیص‌های پروژه')
        context['operation_type'] = 'transfer'
        logger.debug(f"BudgetTransferView: Context data prepared for user {self.request.user.username}")
        return context



class BudgetReturnView(PermissionBaseView, FormView):
    form_class = BudgetReturnForm
    template_name = 'budgets/ReturnTransfer/budget_management.html'
    permission_codenames = ['budgets.BudgetReturn']
    check_organization = False

    def get_allocation(self):
        logger.debug(f"[{self.request.user.username}] Getting allocation with ID: {self.kwargs['allocation_id']}")
        try:
            logger.debug(f"[{self.request.user.username}] Querying BudgetAllocation")
            allocation = BudgetAllocation.objects.select_related(
                'budget_allocation__budget_period',
                'project',
                'budget_allocation__organization'
            ).get(
                pk=self.kwargs['allocation_id'],
                is_active=True,
                is_locked=False
            )
            logger.debug(f"[{self.request.user.username}] Allocation found: {allocation.id}")
            return allocation
        except BudgetAllocation.DoesNotExist:
            logger.error(f"[{self.request.user.username}] Allocation not found or inactive: {self.kwargs['allocation_id']}")
            raise Http404(_('تخصیص بودجه یافت نشد یا غیرفعال است.'))
        except Exception as e:
            logger.error(f"[{self.request.user.username}] Error getting allocation: {str(e)}")
            raise Http404(_('خطا در دریافت اطلاعات تخصیص بودجه'))

    def get_form_kwargs(self):
        logger.debug(f"[{self.request.user.username}] Getting form kwargs")
        kwargs = super().get_form_kwargs()
        logger.debug(f"[{self.request.user.username}] Getting allocation for form")
        kwargs['allocation'] = self.get_allocation()
        logger.debug(f"[{self.request.user.username}] Setting user in form kwargs: {self.request.user}")
        kwargs['user'] = self.request.user
        logger.debug(f"[{self.request.user.username}] Form kwargs prepared: {kwargs}")
        return kwargs

    def form_valid(self, form):
        logger.info(f"[{self.request.user.username}] Form is valid, starting return process")
        try:
            with transaction.atomic():
                logger.debug(f"[{self.request.user.username}] Starting atomic transaction")
                logger.debug(f"[{self.request.user.username}] Attempting to save form")
                transaction_instance = form.save()
                logger.info(f"[{self.request.user.username}] Return successful. Transaction ID: {transaction_instance.transaction_id}")
                messages.success(
                    self.request,
                    _(f"برگشت بودجه با موفقیت انجام شد. شناسه تراکنش: {transaction_instance.transaction_id}")
                )
                logger.info(
                    f"[{self.request.user.username}] Returned {form.cleaned_data['amount']} "
                    f"from allocation {self.get_allocation().id}"
                )
                logger.debug(f"[{self.request.user.username}] Calling super().form_valid")
                return super().form_valid(form)
        except ValidationError as e:
            logger.error(f"[{self.request.user.username}] Validation error during return: {str(e)}")
            logger.debug(f"[{self.request.user.username}] Adding error to form: {e}")
            form.add_error(None, e)
            logger.debug(f"[{self.request.user.username}] Returning form_invalid")
            return self.form_invalid(form)
        except Exception as e:
            logger.error(f"[{self.request.user.username}] Unexpected error during return: {str(e)}")
            messages.error(
                self.request,
                _("خطای غیرمنتظره در انجام عملیات برگشت بودجه رخ داد.")
            )
            logger.debug(f"[{self.request.user.username}] Returning form_invalid due to unexpected error")
            return self.form_invalid(form)

    def get_success_url(self):
        logger.debug(f"[{self.request.user.username}] Getting success URL: {reverse_lazy('project_budget_allocation_detail', kwargs={'pk': self.kwargs['allocation_id']})}")
        return reverse_lazy('project_budget_allocation_detail', kwargs={'pk': self.kwargs['allocation_id']})

    def get_context_data(self, **kwargs):
        logger.debug(f"[{self.request.user.username}] Getting context data")
        context = super().get_context_data(**kwargs)
        logger.debug(f"[{self.request.user.username}] Setting operation in context: return")
        context['operation'] = 'return'
        logger.debug(f"[{self.request.user.username}] Getting allocation for context")
        context['allocation'] = self.get_allocation()
        logger.debug(f"[{self.request.user.username}] Setting title in context: برگشت بودجه")
        context['title'] = _('برگشت بودجه')
        logger.debug(f"[{self.request.user.username}] Context data prepared: {context}")
        return context