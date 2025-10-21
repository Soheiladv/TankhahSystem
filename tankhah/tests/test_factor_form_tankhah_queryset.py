from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, SystemSettings, Status
from django.contrib.auth.models import Permission
from tankhah.models import Tankhah
from budgets.models import BudgetPeriod, BudgetItem, BudgetAllocation


class FactorFormTankhahQuerysetTests(TestCase):
    def setUp(self):
        # System settings - enable ceilings to ensure list is not hidden by remaining filter
        sys = SystemSettings.get_solo()
        sys.tankhah_payment_ceiling_enabled_default = True
        sys.factor_payment_ceiling_enabled_default = True
        sys.lock_period_after_expiry_enforce_on_write_only = True
        sys.save()

        # Org
        self.org = Organization.objects.create(name='هتل لاله سرعین', code='HSarein')

        # Admin
        self.admin = CustomUser.objects.create_user(username='admin_test', email='admin@test.local', password='x')
        self.admin.is_superuser = True
        self.admin.is_staff = True
        self.admin.save()

        # Branch user
        self.user = CustomUser.objects.create_user(username='branch_user', email='branch@test.local', password='x')
        post = Post.objects.create(name='کارشناس مالی', organization=self.org, level=1)
        UserPost.objects.create(user=self.user, post=post, is_active=True, start_date=timezone.now().date())

        # Minimal workflow prerequisite: initial DRAFT status
        self.status_draft = Status.objects.create(
            name='پیش‌نویس',
            code='DRAFT',
            is_initial=True,
            created_by=self.admin,
            description='وضعیت اولیه برای تست'
        )

        # مجوز لازم برای کاربر شعبه
        try:
            perm = Permission.objects.get(codename='factor_add', content_type__app_label='tankhah')
            self.user.user_permissions.add(perm)
        except Permission.DoesNotExist:
            pass

        # Minimal budget chain
        self.bp = BudgetPeriod.objects.create(
            name='دوره تست',
            organization=self.org,
            total_amount=Decimal('1000000'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.item = BudgetItem.objects.create(
            name='ردیف تست',
            budget_period=self.bp,
            code='ITM-TEST',
            organization=self.org,
        )
        # ساخت پروژه ساده برای تخصیص
        from core.models import Project
        self.project = Project.objects.create(name='پروژه تست', code='PRJ-TEST', start_date=timezone.now().date())
        self.alloc = BudgetAllocation.objects.create(
            budget_period=self.bp,
            organization=self.org,
            budget_item=self.item,
            project=self.project,
            allocated_amount=Decimal('100000'),
            allocation_date=timezone.now().date(),
            created_by=self.admin,
        )
        # Tankhah (active...) attached to allocation
        self.tankhah = Tankhah.objects.create(
            number='TNKH-TEST-Sarein-001',
            organization=self.org,
            project=self.project,
            project_budget_allocation=self.alloc,
            amount=Decimal('1000'),
            date=timezone.now(),
            status=self.status_draft,
            is_archived=False,
            canceled=False,
            is_locked=False,
        )

    def test_admin_sees_tankhah_in_create_form(self):
        c = Client()
        c.force_login(self.admin)
        resp = c.get(reverse('Nfactor_create'), HTTP_HOST='localhost')
        self.assertEqual(resp.status_code, 200)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        qs = form.fields['tankhah'].queryset
        self.assertIn(self.tankhah, qs)

    def test_branch_user_sees_tankhah_in_create_form(self):
        c = Client()
        c.force_login(self.user)
        resp = c.get(reverse('Nfactor_create'), HTTP_HOST='localhost')
        self.assertEqual(resp.status_code, 200)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        qs = form.fields['tankhah'].queryset
        self.assertIn(self.tankhah, qs)


