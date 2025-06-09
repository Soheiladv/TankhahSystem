from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.forms import forms
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _

from budgets.Budget_Items.frosm_BudgetItem import BudgetItemForm
from budgets.models import BudgetItem, BudgetPeriod

from django.contrib.auth.mixins import PermissionRequiredMixin
import logging

from core.PermissionBase import PermissionBaseView

logger = logging.getLogger(__name__)

class BudgetItemListView(PermissionRequiredMixin, ListView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_list.html'
    context_object_name = 'budget_items'
    paginate_by = 10
    permission_required = 'budgets.view_budgetitem'

    def get_queryset(self):
        queryset = BudgetItem.objects.select_related('budget_period', 'organization')#.order_by('-created_at')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(budget_period__name__icontains=query) |
                Q(organization__name__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست ردیف‌های بودجه')
        context['query'] = self.request.GET.get('q', '')
        return context

class ok_BudgetItemCreateView(PermissionBaseView, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ایجاد شد.')
    permission_required = 'budgets.add_budgetitem'

    def get_form_kwargs(self):
        """افزودن کاربر به kwargs فرم برای محدود کردن انتخاب‌ها"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """تقویت context با عناصر UI پیشرفته"""
        context = super().get_context_data(**kwargs)

        # عنوان صفحه
        context['title'] = _('ایجاد ردیف بودجه جدید')
        context['page_title'] = _('مدیریت ردیف‌های بودجه')
        context['page_subtitle'] = _('ایجاد ردیف بودجه جدید')

        # اطلاعات راهنما
        context['help_texts'] = {
            'budget_period': _('دوره بودجه مربوطه را انتخاب نمایید'),
            'organization': _('سازمان/شعبه مرتبط با این ردیف بودجه'),
            'code': _('کد منحصر به فرد برای ردیف بودجه'),
        }

        # دکمه‌های اکشن
        context['action_buttons'] = [
            {
                'text': _('بازگشت به لیست'),
                'url': reverse_lazy('budgetitem_list'),
                'icon': 'fa fa-arrow-right',
                'class': 'btn btn-light-danger',
            },
            {
                'text': _('ذخیره و ادامه'),
                'type': 'submit',
                'name': 'save_and_continue',
                'icon': 'fa fa-save',
                'class': 'btn btn-light-primary',
            },
            {
                'text': _('ذخیره'),
                'type': 'submit',
                'icon': 'fa fa-check',
                'class': 'btn btn-primary',
            }
        ]

        # فعال کردن اجزای پیشرفته UI
        context['use_card'] = True  # استفاده از کارت بوت استرپ
        context['use_select2'] = True  # فعال کردن select2
        context['use_jalali_datepicker'] = False  # غیرفعال کردن تاریخ‌شمار جلالی
        context['use_form_validation'] = True  # فعال کردن اعتبارسنجی فرم

        return context

    def form_valid(self, form):
        """پردازش پس از ثبت موفق فرم"""
        response = super().form_valid(form)

        # بررسی دکمه ذخیره و ادامه
        if 'save_and_continue' in self.request.POST:
            from django.urls import reverse
            return redirect(reverse('budgetitem_create'))

        return response

    def form_invalid(self, form):
        """پردازش خطاهای فرم با UI پیشرفته"""
        logger.error(f"Form invalid: errors={form.errors.as_json()}")

        # افزودن خطاهای فیلدها به context برای نمایش بهتر
        context = self.get_context_data(form=form)
        context['form_errors'] = [
            {
                'field': field,
                'errors': errors,
                'icon': 'fa fa-exclamation-triangle'
            }
            for field, errors in form.errors.items()
        ]

        return self.render_to_response(context)

    def get_form(self, form_class=None):
        """تنظیمات اضافی برای فرم"""
        form = super().get_form(form_class)

        # افزودن کلاس‌های بوت استرپ به فیلدها
        for field_name, field in form.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'

            if field.required:
                field.widget.attrs['required'] = 'required'
                field.widget.attrs['class'] += ' required-field'

            # تنظیم placeholder برای فیلدهای متنی
            from django import forms
            if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
                if not field.widget.attrs.get('placeholder'):
                    field.widget.attrs['placeholder'] = field.label

        return form
class BudgetItemCreateView(PermissionBaseView, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ایجاد شد.')
    permission_required = 'budgets.budgetitem_add'  # اصلاح نام پرمیشن بر اساس مدل

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': _('ایجاد ردیف بودجه جدید'),
            'page_title': _('مدیریت ردیف‌های بودجه'),
            'page_subtitle': _('ایجاد ردیف بودجه جدید'),
            'help_texts': {
                'budget_period': _('دوره بودجه مربوطه را انتخاب نمایید'),
                'organization': _('سازمان/شعبه مرتبط (اختیاری، به‌طور خودکار از دوره بودجه تنظیم می‌شود)'),
                'code': _('کد منحصر به فرد برای ردیف بودجه'),
                'name': _('نام توصیفی برای ردیف بودجه'),
            },
            'action_buttons': [
                {
                    'text': _('بازگشت به لیست'),
                    'url': reverse_lazy('budgetitem_list'),
                    'icon': 'fa fa-arrow-right',
                    'class': 'btn btn-outline-secondary',
                },
                {
                    'text': _('ذخیره و ادامه'),
                    'type': 'submit',
                    'name': 'save_and_continue',
                    'icon': 'fa fa-save',
                    'class': 'btn btn-outline-primary',
                },
                {
                    'text': _('ذخیره'),
                    'type': 'submit',
                    'icon': 'fa fa-check',
                    'class': 'btn btn-primary',
                },
            ],
            'use_card': True,
            'use_select2': True,
            'use_jalali_datepicker': False,
            'use_form_validation': True,
        })

        # افزودن خطاها به کنتکست
        if 'form' in context and context['form'].errors:
            context['form_errors'] = [
                {'field': field, 'errors': errors, 'icon': 'fa fa-exclamation-triangle'}
                for field, errors in context['form'].errors.items()
            ]
            messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))

        logger.debug(f"BudgetItemCreateView context: {context}")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        if 'save_and_continue' in self.request.POST:
            return redirect(reverse('budgetitem_create'))
        return response

    def form_invalid(self, form):
        logger.error(f"Form invalid: errors={form.errors.as_json()}")
        messages.error(self.request, _('خطایی در ثبت فرم رخ داد. لطفاً فیلدها را بررسی کنید.'))
        return super().form_invalid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name, field in form.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
            if field.required:
                field.widget.attrs['required'] = 'required'
                field.widget.attrs['class'] += ' required-field'
            # if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
            #     field.widget.attrs['placeholder'] = field.label
        return form

"""این ویو سازمان را اجبار کرده است"""
class old_BudgetItemCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ایجاد شد.')
    permission_required = 'budgets.add_budgetitem'

    def get_context_data(self, **kwargs):
        # from core.models import Organization
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد ردیف بودجه جدید')
        context['budget_periods'] = BudgetPeriod.objects.filter(is_active=True).select_related('organization')
        # context['organizations'] = Organization.objects.filter(is_active=True).select_related('org_type')
        return context


    def form_invalid(self, form):
        logger.error(f"Form invalid: errors={form.errors.as_json()}")
        messages.error(self.request, _('لطفاً خطاهای فرم را بررسی کنید.'))
        return super().form_invalid(form)

class BudgetItemUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = BudgetItem
    form_class = BudgetItemForm
    template_name = 'budgets/budgetitem/budgetitem_form.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت ویرایش شد.')
    permission_required = 'budgets.change_budgetitem'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش ردیف بودجه')
        return context

class BudgetItemDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_confirm_delete.html'
    success_url = reverse_lazy('budgetitem_list')
    success_message = _('ردیف بودجه با موفقیت حذف شد.')
    permission_required = 'budgets.delete_budgetitem'

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except models.ProtectedError:
            messages.error(request, _('نمی‌توان ردیف بودجه را حذف کرد چون تخصیص‌هایی به آن وابسته‌اند.'))
            return redirect('budgetitem_list')

class BudgetItemDetailView(PermissionRequiredMixin, DetailView):
    model = BudgetItem
    template_name = 'budgets/budgetitem/budgetitem_detail.html'
    context_object_name = 'budget_item'
    permission_required = 'budgets.view_budgetitem'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات ردیف بودجه')
        return context