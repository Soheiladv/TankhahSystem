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


class BudgetTransferView(FormView):
    form_class = BudgetTransferForm
    template_name = 'budgets/BudgetTransfer/transfer_list.html'
    success_url = reverse_lazy('budgetallocation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # ارسال کاربر به فرم برای کوئری منطقی
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        logger.debug(f"source_allocation queryset count: {form.fields['source_allocation'].queryset.count()}")
        logger.debug(f"destination_allocation queryset count: {form.fields['destination_allocation'].queryset.count()}")
        return form

    def form_valid(self, form):
        try:
            return_tx, alloc_tx = form.execute_transfer()
            messages.success(self.request, "جابجایی بودجه با موفقیت انجام شد.")
            return super().form_valid(form)
        except Exception as e:
            logger.error(f"خطا در اجرای جابجایی بودجه: {e}", exc_info=True)
            form.add_error(None, "خطا در اجرای جابجایی بودجه")
            return super().form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "خطا در داده‌های وارد شده، لطفاً اصلاح کنید.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        context['title'] = 'جابجایی بودجه بین تخصیص‌ها'
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