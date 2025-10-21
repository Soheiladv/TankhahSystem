from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from core.models import SystemSettings
from budgets.models import BudgetPeriod, BudgetAllocation, BudgetItem
from accounts.models import CustomUser
from core.models import Organization, OrganizationType, Project

from datetime import date


class SystemSettingsFlagsTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST='localhost')
        self.user, _ = CustomUser.objects.get_or_create(username='flag_tester', defaults={'email': 'flag_tester@example.com'})
        self.user.set_password('pass1234')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username='flag_tester', password='pass1234')

        self.org_type, _ = OrganizationType.objects.get_or_create(fname='Branch', defaults={'is_budget_allocatable': True})
        self.org, _ = Organization.objects.get_or_create(
            name='Test Org',
            defaults={'org_type': self.org_type, 'code': 'TST-ORG'}
        )
        if not self.org.code:
            self.org.code = 'TST-ORG'
            self.org.save()
        if not self.org.org_type:
            self.org.org_type = self.org_type
            self.org.save()

        self.project, _ = Project.objects.get_or_create(
            code='P1',
            defaults={
                'name': 'P1',
                'start_date': date(2025, 1, 1),
                'end_date': date(2025, 12, 31),
                'description': 'test',
                'is_active': True,
            }
        )
        self.project.organizations.add(self.org)

        self.period = BudgetPeriod.objects.create(
            organization=self.org,
            name='Period-Flags',
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            total_amount=Decimal('1000000'),
            created_by=self.user,
        )

        self.budget_item = BudgetItem.objects.create(
            budget_period=self.period,
            organization=self.org,
            code='BI-1',
            name='Operating'
        )

        self.allocation = BudgetAllocation.objects.create(
            budget_period=self.period,
            organization=self.org,
            budget_item=self.budget_item,
            project=self.project,
            allocated_amount=Decimal('500000'),
            created_by=self.user,
            is_active=True,
        )

        self.settings = SystemSettings.get_solo()

    def test_lock_period_after_expiry_enforce_on_write_only(self):
        # حالت 1: تنظیم غیرفعال (False) → قفل سراسری پس از انقضا اعمال شود
        self.settings.lock_period_after_expiry_enforce_on_write_only = False
        self.settings.save()
        # شبیه‌سازی انقضای دوره
        self.period.end_date = date(2020, 1, 1)
        self.period.save()
        locked, _ = self.period.is_locked
        self.assertTrue(locked)

        # حالت 2: تنظیم فعال (True) → قفل فقط در عملیات نوشتنی لحاظ شود (نمایش عمومی قفل نشود)
        self.settings.lock_period_after_expiry_enforce_on_write_only = True
        self.settings.save()
        # چون ذخیره‌ی قبلی ممکن است is_active را False کرده باشد، برای سنجش «قفل نمایشی» فقط فیلد را in-memory تنظیم می‌کنیم
        self.period.is_active = True  # بدون save
        locked, _ = self.period.is_locked
        # با سیاست جدید، is_locked عمومی نباید قفل کند
        self.assertFalse(locked)

    def test_allow_tankhah_budget_overrun_in_factor_and_tankhah_forms(self):
        # آماده‌سازی ساده: باقی‌مانده تخصیص را بسیار کم می‌گذاریم
        self.allocation.allocated_amount = Decimal('100')
        self.allocation.save()

        # 1) وقتی اجازه تجاوز غیرفعال است → باید رد شود
        self.settings.allow_tankhah_budget_overrun = False
        self.settings.save()

        from tankhah.Tankhah.forms_tankhah import TankhahForm
        form = TankhahForm(data={
            'organization': self.org.pk,
            'project': self.project.pk,
            'subproject': '',
            'date': '1404/01/10',
            'due_date': '1404/01/20',
            'amount': '1000',  # بیشتر از باقی‌مانده 100
            'letter_number': '',
            'description': 't'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('بیشتر از بودجه باقیمانده', str(form.errors))

        # 2) وقتی اجازه تجاوز فعال است → باید اجازه دهد (خطای بودجه ندهد)
        self.settings.allow_tankhah_budget_overrun = True
        self.settings.save()
        form2 = TankhahForm(data={
            'organization': self.org.pk,
            'project': self.project.pk,
            'subproject': '',
            'date': '1404/01/10',
            'due_date': '1404/01/20',
            'amount': '1000',
            'letter_number': '',
            'description': 't'
        })
        form2.is_valid()
        errors = str(form2.errors)
        self.assertNotIn('بیشتر از بودجه باقیمانده', errors)

    def test_tankhah_payment_ceiling_enforced(self):
        # سقف پیش‌فرض سیستم را کم بگذار تا خطا فعال شود
        self.settings.tankhah_payment_ceiling_enabled_default = True
        self.settings.tankhah_payment_ceiling_default = Decimal('500')
        self.settings.allow_tankhah_budget_overrun = True  # تا خطای مانده مزاحم نشود
        self.settings.save()

        from tankhah.Tankhah.forms_tankhah import TankhahForm
        form = TankhahForm(data={
            'organization': self.org.pk,
            'project': self.project.pk,
            'subproject': '',
            'date': '1404/01/10',
            'due_date': '1404/01/20',
            'amount': '1000',  # بزرگ‌تر از سقف 500
            'letter_number': '',
            'description': 't'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('سقف', str(form.errors))

    def test_tankhah_payment_ceiling_disabled_allows_amount(self):
        # سقف را غیرفعال کن و مانده را کافی قرار بده تا خطایی وجود نداشته باشد
        self.settings.tankhah_payment_ceiling_enabled_default = False
        self.settings.allow_tankhah_budget_overrun = False
        self.settings.save()

        # افزایش مانده تخصیص تا از خطای مانده عبور کنیم
        self.allocation.allocated_amount = Decimal('2000000')
        self.allocation.save()

        from tankhah.Tankhah.forms_tankhah import TankhahForm
        form = TankhahForm(data={
            'organization': self.org.pk,
            'project': self.project.pk,
            'subproject': '',
            'date': '1404/01/10',
            'due_date': '1404/01/20',
            'amount': '1000',  # بزرگ‌تر از سقف قبلی ولی سقف اکنون غیرفعال است
            'letter_number': '',
            'description': 't'
        })
        # باید معتبر باشد یا حداقل خطای «سقف» ندهد
        form.is_valid()
        self.assertNotIn('سقف', str(form.errors))

    def test_factor_overrun_and_ceiling(self):
        # آماده‌سازی تنخواه با مانده کم
        self.allocation.allocated_amount = Decimal('200')
        self.allocation.save()

        from tankhah.models import Tankhah, Factor, ItemCategory
        from tankhah.Factor.forms_Factor import FactorForm
        from core.models import Status

        # ایجاد تنخواه پایه
        draft = Status.objects.filter(is_initial=True).first() or Status.objects.create(
            name='پیش‌نویس', code='DRAFT', is_initial=True, created_by=self.user, description='init'
        )
        tankhah = Tankhah.objects.create(
            number='TNK-T1',
            amount=Decimal('100'),
            organization=self.org,
            project=self.project,
            project_budget_allocation=self.allocation,
            description='t',
            status=draft,
        )
        cat = ItemCategory.objects.create(name='عمومی')

        # سناریو 1: سقف تنخواه سیستم فعال و مبلغ بیشتر از سقف → خطا
        self.settings.tankhah_payment_ceiling_enabled_default = True
        self.settings.tankhah_payment_ceiling_default = Decimal('300')
        self.settings.allow_tankhah_budget_overrun = True  # تا خطای مانده مزاحم نشود
        self.settings.save()

        # ساخت یک فرم آیتم ساختگی مطابق انتظار FactorForm.clean (unit_price/quantity)
        class DummyItemForm:
            def __init__(self, unit_price, quantity, delete=False):
                self._cleaned = {'unit_price': Decimal(str(unit_price)), 'quantity': quantity, 'DELETE': delete}
            def is_valid(self):
                return True
            @property
            def cleaned_data(self):
                return self._cleaned
        item_form = DummyItemForm(unit_price=400, quantity=1)
        form = FactorForm(data={
            'tankhah': tankhah.pk,
            'date': '1404/01/10',
            'amount': '400',
            'description': 'd',
            'is_emergency': False,
            'category': cat.pk,
        }, formset=[item_form], tankhah=tankhah)
        self.assertFalse(form.is_valid())
        self.assertIn('سقف', str(form.errors))

        # سناریو 2: سقف غیرفعال ولی اجازه تجاوز از مانده غیرفعال → با مبلغ بزرگ‌تر از مانده خطا بدهد
        self.settings.tankhah_payment_ceiling_enabled_default = False
        self.settings.allow_tankhah_budget_overrun = False
        self.settings.save()
        item_form2 = DummyItemForm(unit_price=500, quantity=1)
        form2 = FactorForm(data={
            'tankhah': tankhah.pk,
            'date': '1404/01/10',
            'amount': '500',
            'description': 'd',
            'is_emergency': False,
            'category': cat.pk,
        }, formset=[item_form2], tankhah=tankhah)
        self.assertFalse(form2.is_valid())
        self.assertIn('بیشتر از بودجه باقی', str(form2.errors))


