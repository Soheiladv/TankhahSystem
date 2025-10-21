from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from budgets.models import BudgetAllocation, BudgetTransaction, Organization, BudgetItem, BudgetPeriod
from accounts.models import CustomUser
from django.contrib.auth.models import Permission, ContentType


class BudgetTransferDateFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        # کاربر تست با دسترسی مشاهده تراکنش بودجه
        self.user = CustomUser.objects.create_user(username='tester', email='tester@example.com', password='pass1234')
        ct = ContentType.objects.get_for_model(BudgetTransaction)
        perm = Permission.objects.get(content_type=ct, codename='BudgetTransaction_view')
        self.user.user_permissions.add(perm)
        self.client.login(username='tester', password='pass1234')
        # حداقل داده‌های لازم برای تخصیص
        org = Organization.objects.create(name='Org A', code='ORG-A', is_active=True)
        period = BudgetPeriod.objects.create(
            name='1404',
            organization=org,
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            total_amount=10000000,
            is_active=True,
        )
        item = BudgetItem.objects.create(code='ITM-1', name='Item 1', organization=org, budget_period=period, is_active=True)
        self.alloc = BudgetAllocation.objects.create(
            organization=org,
            budget_item=item,
            budget_period=period,
            allocated_amount=1000000,
            is_active=True,
        )

        # سه تراکنش با تاریخ‌های متفاوت
        # توجه: timestamp از نوع DateTime است؛ ما به تاریخ روز مختلف نیاز داریم
        base_dt = timezone.now()
        self.t1 = BudgetTransaction.objects.create(allocation=self.alloc, transaction_type='INCREASE', amount=1000, description='d1')
        self.t2 = BudgetTransaction.objects.create(allocation=self.alloc, transaction_type='DECREASE', amount=2000, description='d2')
        self.t3 = BudgetTransaction.objects.create(allocation=self.alloc, transaction_type='INCREASE', amount=3000, description='d3')
        # به‌روزرسانی زمان‌ها پس از ایجاد چون فیلد auto_now_add است
        BudgetTransaction.objects.filter(pk=self.t1.pk).update(timestamp=base_dt - timedelta(days=2))
        BudgetTransaction.objects.filter(pk=self.t2.pk).update(timestamp=base_dt - timedelta(days=1))
        BudgetTransaction.objects.filter(pk=self.t3.pk).update(timestamp=base_dt)
        self.t1.refresh_from_db(); self.t2.refresh_from_db(); self.t3.refresh_from_db()

    def test_filter_by_exact_jalali_date(self):
        # تاریخ جلالی معادل روز t2 را محاسبه می‌کنیم
        from BudgetsSystem.utils import convert_gregorian_to_jalali
        day = (self.t2.timestamp).date()
        jalali_day = convert_gregorian_to_jalali(day)
        # ارسال بازه‌ای که فقط t2 را شامل شود
        url = reverse('budget_transfer:transfer_list')
        resp = self.client.get(url, {'date_from': jalali_day, 'date_to': jalali_day})
        self.assertEqual(resp.status_code, 200)
        page = resp.context['transfers']
        descs = {obj.description for obj in page.object_list}
        self.assertSetEqual(descs, {'d2'})

    def test_filter_by_range_jalali_date(self):
        from BudgetsSystem.utils import convert_gregorian_to_jalali
        d_from = convert_gregorian_to_jalali((self.t1.timestamp).date())
        d_to = convert_gregorian_to_jalali((self.t2.timestamp).date())
        url = reverse('budget_transfer:transfer_list')
        resp = self.client.get(url, {'date_from': d_from, 'date_to': d_to})
        self.assertEqual(resp.status_code, 200)
        page = resp.context['transfers']
        descs = {obj.description for obj in page.object_list}
        self.assertSetEqual(descs, {'d1', 'd2'})


