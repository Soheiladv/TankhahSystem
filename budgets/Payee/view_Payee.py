from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, CreateView
from django.utils.translation import gettext_lazy as _
from django_jalali.db import models as jmodels
import jdatetime
import logging

from budgets.Payee.forms_payee import PayeeForm
from budgets.models import Payee
from core.PermissionBase import PermissionBaseView

logger = logging.getLogger(__name__)

class PayeeListView(PermissionBaseView, ListView):
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    context_object_name = 'payees'
    paginate_by = 10
    permission_required = ['budgets.Payee_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_active=True)
        query = self.request.GET.get('q', '').strip()
        payee_type = self.request.GET.get('payee_type', '').strip()
        entity_type = self.request.GET.get('entity_type', '').strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(family__icontains=query) |
                Q(legal_name__icontains=query) |
                Q(brand_name__icontains=query) |
                Q(national_id__icontains=query) |
                Q(iban__icontains=query)
            )
            logger.info(f"[PayeeListView] جستجو با عبارت: {query}")

        if payee_type:
            queryset = queryset.filter(payee_type=payee_type)
            logger.info(f"[PayeeListView] فیلتر نوع دریافت‌کننده: {payee_type}")

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
            logger.info(f"[PayeeListView] فیلتر نوع شخص: {entity_type}")

        return queryset.order_by('name', 'legal_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'query': self.request.GET.get('q', ''),
            'payee_type': self.request.GET.get('payee_type', ''),
            'entity_type': self.request.GET.get('entity_type', ''),
            'payee_types': Payee.PAYEE_TYPES,
            'entity_types': Payee.ENTITY_TYPES,
        })
        logger.debug(f"[PayeeListView] Context: {context}")
        return context

class PayeeDetailView(PermissionBaseView, DetailView):
    model = Payee
    template_name = 'budgets/payee/payee_detail.html'
    context_object_name = 'payee'
    permission_required = ['budgets.Payee_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payee = self.get_object()
        context.update({
            'title': _('جزئیات دریافت‌کننده'),
            'jalali_created_at': jdatetime.datetime.fromgregorian(datetime=payee.created_at).strftime('%Y/%m/%d %H:%M') if payee.created_at else ''
        })
        return context

class PayeeCreateView(PermissionBaseView, CreateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')
    permission_required = ['budgets.Payee_add']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def validate_national_id(value):
        if not value.isdigit() or len(value) != 10:
            raise ValidationError(_("کد ملی باید 10 رقم باشد."))
        check = int(value[9])
        s = sum(int(value[i]) * (10 - i) for i in range(9)) % 11
        if (s < 2 and check == s) or (s >= 2 and check == 11 - s):
            return value
        raise ValidationError(_("کد ملی نامعتبر است."))

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        national_id = form.cleaned_data.get('national_id')
        entity_type = form.cleaned_data.get('entity_type')

        # بررسی تکرار
        if national_id and Payee.objects.filter(national_id=national_id, entity_type=entity_type).exists():
            form.add_error('national_id', _('دریافت‌کننده‌ای با این کد ملی/شناسه حقوقی قبلاً ثبت شده است.'))
            return self.form_invalid(form)

        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance} با موفقیت ایجاد شد.')
            logger.info(f"[PayeeCreateView] دریافت‌کننده جدید ایجاد شد: {form.instance}")
            return response

    def form_invalid(self, form):
        logger.warning(f"[PayeeCreateView] فرم نامعتبر: {form.errors}")
        return super().form_invalid(form)

class PayeeUpdateView(PermissionBaseView, UpdateView):
    model = Payee
    form_class = PayeeForm
    template_name = 'budgets/payee/payee_form.html'
    success_url = reverse_lazy('payee_list')
    permission_required = ['budgets.Payee_update']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def form_valid(self, form):
        national_id = form.cleaned_data.get('national_id')
        entity_type = form.cleaned_data.get('entity_type')

        # بررسی تکرار به جز خود این نمونه
        if national_id and Payee.objects.filter(
            national_id=national_id,
            entity_type=entity_type
        ).exclude(pk=self.get_object().pk).exists():
            form.add_error('national_id', _('دریافت‌کننده‌ای با این کد ملی/شناسه حقوقی قبلاً ثبت شده است.'))
            return self.form_invalid(form)

        with transaction.atomic():
            response = super().form_valid(form)
            messages.success(self.request, f'دریافت‌کننده {form.instance} با موفقیت به‌روزرسانی شد.')
            logger.info(f"[PayeeUpdateView] دریافت‌کننده به‌روزرسانی شد: {form.instance}")
            return response

    def form_invalid(self, form):
        logger.warning(f"[PayeeUpdateView] فرم نامعتبر: {form.errors}")
        return super().form_invalid(form)

class PayeeDeleteView(PermissionBaseView, DeleteView):
    model = Payee
    template_name = 'budgets/payee/payee_confirm_delete.html'
    success_url = reverse_lazy('payee_list')
    permission_required = ['budgets.Payee_delete']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def post(self, request, *args, **kwargs):
        payee = self.get_object()
        with transaction.atomic():
            payee.delete()
            messages.success(request, f'دریافت‌کننده {payee} با موفقیت حذف شد.')
            logger.info(f"[PayeeDeleteView] دریافت‌کننده حذف شد: {payee}")
        return redirect(self.success_url)


# ================================================================================================
from django.test import TestCase, Client
from django.urls import reverse
from budgets.models import Payee
from django.contrib.auth.models import User

class PayeeCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='root', password='S@123456@1234')
        self.client.login(username='admin', password='D@d123yes')

    def test_create_individual_payee(self):
        response = self.client.post(reverse('payee_create'), {
            'entity_type': 'INDIVIDUAL',
            'payee_type': 'VENDOR',
            'name': 'علی',
            'family': 'رضایی',
            'national_id': '1234567890',
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Payee.objects.filter(national_id='1234567890').exists())

    def test_duplicate_national_id(self):
        Payee.objects.create(
            entity_type='INDIVIDUAL',
            name='علی',
            family='رضایی',
            national_id='1234567890',
            payee_type='VENDOR',
            is_active=True,
            created_by=self.user
        )
        response = self.client.post(reverse('payee_create'), {
            'entity_type': 'INDIVIDUAL',
            'payee_type': 'VENDOR',
            'name': 'محمد',
            'family': 'محمدی',
            'national_id': '1234567890',
            'is_active': True
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "دریافت‌کننده‌ای با این کد ملی/شناسه حقوقی قبلاً ثبت شده است.")