from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction, models
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



class PayeeListView(PermissionBaseView,ListView):
    """
    نمایش لیست دریافت‌کنندگان با قابلیت جستجو و صفحه‌بندی.
    """
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    context_object_name = 'payees'
    paginate_by = 15  # تعداد آیتم‌ها در هر صفحه
    permission_codenames = ['budgets.Payee_view']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_queryset(self):
        """
        این متد برای افزودن منطق جستجو به کوئری اصلی بازنویسی شده است.
        """
        # شروع با کوئریست پایه و مرتب‌سازی بر اساس جدیدترین
        queryset = super().get_queryset().order_by('-pk')

        # دریافت عبارت جستجو شده از پارامتر GET
        search_query = self.request.GET.get('q', '').strip()

        if search_query:
            # ساخت یک کوئری پیچیده برای جستجو در چندین فیلد
            # این کوئری تمام موارد زیر را جستجو می‌کند:
            # - نام یا نام خانوادگی برای اشخاص حقیقی
            # - نام حقوقی برای اشخاص حقوقی
            # - کد ملی یا شناسه حقوقی
            # - شماره تلفن
            # - شماره شبا
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(family__icontains=search_query) |
                Q(legal_name__icontains=search_query) |
                Q(national_id__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(iban__icontains=search_query)
            ).distinct()  # جلوگیری از نتایج تکراری

        return queryset

    def get_context_data(self, **kwargs):
        """
        ارسال عبارت جستجو شده به تمپلیت برای نمایش در فرم جستجو.
        """
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context

class __PayeeListView(PermissionBaseView, ListView):
    model = Payee
    template_name = 'budgets/payee/payee_list.html'
    context_object_name = 'payees'
    paginate_by = 10
    # permission_codenames = ['budgets.Payee_view']
    # check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_queryset(self):
        # return Payee.objects.all().order_by('legal_name', 'name', 'family')
        queryset = super().get_queryset()
        user = self.request.user

        # بررسی دسترسی کامل کاربر
        has_full_access = (
            user.is_superuser or
            user.has_perm('budgets.Payee_view') or
            user.userpost_set.filter(
                is_active=True,
                post__organization__org_type__fname='HQ'
            ).exists()
        )

        if not has_full_access:
            # فقط داده‌های فعال برای کاربران محدود
            queryset = queryset.filter(is_active=True)
            logger.info(f"[PayeeListView] فیلتر is_active اعمال شد")
        else:
            logger.info(f"[PayeeListView] کاربر دسترسی کامل دارد - همه Payeeها نمایش داده می‌شوند")

        # اعمال فیلتر جستجو
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
                Q(iban__icontains=query) |
                Q(account_number__icontains=query)
            )
            logger.info(f"[PayeeListView] جستجو: {query} - نتایج: {queryset.count()}")

        if payee_type:
            queryset = queryset.filter(payee_type=payee_type)
            logger.info(f"[PayeeListView] فیلتر نوع دریافت‌کننده: {payee_type}")

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
            logger.info(f"[PayeeListView] فیلتر نوع شخص: {entity_type}")

        # مرتب‌سازی امن
        queryset = queryset.order_by(
            models.Case(
                models.When(legal_name__isnull=False, then=0),
                default=1,
                output_field=models.IntegerField()
            ),
            'legal_name', 'name', 'family'
        )

        logger.info(f"[PayeeListView] تعداد نهایی Payeeها: {queryset.count()}")
        # logger.debug(f"[PayeeListView] SQL نهایی: {queryset.query}")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        total_count = qs.count()

        context.update({
            'query': self.request.GET.get('q', ''),
            'payee_type': self.request.GET.get('payee_type', ''),
            'entity_type': self.request.GET.get('entity_type', ''),
            'payee_types': Payee.PAYEE_TYPES,
            'entity_types': Payee.ENTITY_TYPES,
            'total_count': total_count,
            'has_results': total_count > 0,
        })

        logger.info(f"[PayeeListView] Context آماده شد - تعداد Payeeها: {total_count}")
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