# from django.contrib.messages.storage.fallback import FallbackStorage
# from django.urls import reverse
#
# from tankhah.models import Tankhah, Factor, FactorItem, TankhahDocument, ApprovalLog, StageApprover
# from django.test import TestCase, Client, RequestFactory
# from django.utils import timezone
# from django.core.files.uploadedfile import SimpleUploadedFile
# from tankhah.models import Tankhah, TankhahDocument
# from core.models import Organization, Project, Post, WorkflowStage, UserPost
# from accounts.models import CustomUser
# import jdatetime
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.utils import timezone
# from django.contrib.auth.models import Permission
# from django.contrib import messages
# from accounts.models import CustomUser
# from core.models import Organization, WorkflowStage, Post, UserPost
# from tankhah.models import Tankhah
# from tankhah.forms import TankhahForm
# from tankhah.views import TankhahListView
#
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.utils import timezone
# from django.contrib.auth.models import Permission
# from django.db import models
# from accounts.models import CustomUser
# from core.models import Organization, WorkflowStage, Post, UserPost
# from tankhah.models import Tankhah
# import logging
#
# logger = logging.getLogger(__name__)
#
#
#
#
# class TankhahhModelTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.project = Project.objects.create(
#             name='Test Project',
#             code='TPRJ',
#             start_date=timezone.now().date()
#         )
#         self.project.organizations.add(self.org)
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#         self.post = Post.objects.create(name='Manager', organization=self.org)
#
#     def test_tankhah_document_upload(self):
#         tankhah = Tankhah.objects.create(
#             amount=1000000,
#             date=timezone.now(),
#             organization=self.org,
#             created_by=self.user,
#             description="With Document",
#             current_stage=self.stage
#         )
#         # شبیه‌سازی یه فایل واقعی
#         file_content = b"Test file content"
#         uploaded_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
#         doc = TankhahDocument.objects.create(
#             tankhah=tankhah,
#             document=uploaded_file
#         )
#         self.assertEqual(doc.tankhah, tankhah)
#         self.assertIn(tankhah.number, doc.document.name)
#         self.assertTrue(doc.document.name.endswith('.pdf'))
# #----  viwes
# class FactorModelTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#         self.tankhah = Tankhah.objects.create(
#             amount=1000000,
#             date=timezone.now(),
#             organization=self.org,
#             created_by=self.user,
#             description="Test tankhah",
#             current_stage=self.stage
#         )
#
#     def test_factor_generate_number(self):
#         factor = Factor.objects.create(
#             tankhah=self.tankhah,
#             date=timezone.now(),
#             description="Test Factor"
#         )
#         self.assertTrue(factor.number.startswith(self.tankhah.number))
#         self.assertTrue(factor.number.endswith('F1'))
#
#     def test_factor_multiple_numbers(self):
#         factor1 = Factor.objects.create(tankhah=self.tankhah, date=timezone.now(), description="Factor 1")
#         factor2 = Factor.objects.create(tankhah=self.tankhah, date=timezone.now(), description="Factor 2")
#         self.assertEqual(factor1.number, f"{self.tankhah.number}-F1")
#         self.assertEqual(factor2.number, f"{self.tankhah.number}-F2")
#
#     def test_factor_item_creation(self):
#         factor = Factor.objects.create(tankhah=self.tankhah, date=timezone.now(), description="Test Factor")
#         item = FactorItem.objects.create(
#             factor=factor,
#             description="Item 1",
#             unit_price=25000,  # 25000 * 2 = 50000
#             quantity=2
#             # amount رو حذف کن چون محاسباتیه
#         )
#         self.assertEqual(item.amount, 50000)
# class ApprovalLogTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#         self.post = Post.objects.create(name='Manager', organization=self.org)
#         self.tankhah = Tankhah.objects.create(
#             amount=1000000,
#             date=timezone.now(),
#             organization=self.org,
#             created_by=self.user,
#             description="Test Tankhah",
#             current_stage=self.stage
#         )
#
#     def test_approval_log_creation(self):
#         log = ApprovalLog.objects.create(
#             tankhah=self.tankhah,
#             action='APPROVE',
#             stage=self.stage,
#             user=self.user,
#             comment="Approved by manager",
#             post=self.post
#         )
#         self.assertEqual(log.tankhah, self.tankhah)
#         self.assertEqual(log.action, 'APPROVE')
#         self.assertEqual(log.user, self.user)
# class StageApproverTest(TestCase):
#     def setUp(self):
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#         self.post = Post.objects.create(name='Manager', organization=self.org)
#
#     def test_stage_approver_creation(self):
#         approver = StageApprover.objects.create(stage=self.stage, post=self.post)
#         self.assertEqual(approver.stage, self.stage)
#         self.assertEqual(approver.post, self.post)
# class TankhahListViewTest(TestCase):
#     def setUp(self):
#         self.client = Client()
#
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         permission = Permission.objects.get(codename='Tankhah_view', content_type__app_label='tankhah')
#         self.user.user_permissions.add(permission)
#         logger.info(f"Permissions for foad after adding: {list(self.user.get_all_permissions())}")
#
#         self.org = Organization.objects.create(id=3, name='Test Org', code='TST', org_type='HQ')
#         self.post = Post.objects.create(name='Manager', organization=self.org, level=1)
#         UserPost.objects.create(user=self.user, post=self.post)
#
#         self.stage = WorkflowStage.objects.create(id=1, name='HQ_INITIAL', order=1)
#
#         self.tankhah = Tankhah.objects.create(
#             number='TNKH-14040101-HOTELS-Ard-34323242-002',
#             amount=123123.00,
#             date=timezone.datetime(2025, 3, 20, 20, 30),
#             due_date=timezone.datetime(2025, 4, 16, 20, 30),
#             organization=self.org,
#             created_by=self.user,
#             current_stage=self.stage,
#             status='DRAFT',
#             hq_status='PENDING'
#         )
#
#     def test_tankhah_list_view_hq_user(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('tankhah_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'tankhah/tankhah_list.html')
#         self.assertIn('Tankhahs', response.context)
#         self.assertEqual(response.context['Tankhahs'].count(), 1)
#         self.assertContains(response, 'TNKH-14040101-HOTELS-Ard-34323242-002')
#
#     def test_tankhah_list_view_no_permission(self):
#         no_perm_user = CustomUser.objects.create_user(
#             username='noperm',
#             email='noperm@example.com',
#             password='testpass'
#         )
#         self.client.login(username='noperm', password='testpass')
#         response = self.client.get(reverse('tankhah_list'))
#
#         self.assertEqual(response.status_code, 302)
#         self.assertRedirects(response, reverse('factor_list'))
#
#     def tearDown(self):
#         self.client.logout()
# class TankhahListViewTest(TestCase):
#     def setUp(self):
#         self.client = Client()
#
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         permission = Permission.objects.get(codename='tankhah.Tankhah_view', content_type__app_label='tankhah')
#         self.user.user_permissions.add(permission)
#         logger.info(f"Permissions for foad after adding: {list(self.user.get_all_permissions())}")
#
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.post = Post.objects.create(name='Manager', organization=self.org, level=1)
#         UserPost.objects.create(user=self.user, post=self.post)
#
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#
#         self.tankhah = Tankhah.objects.create(
#             number='TNKH-14040101-HOTELS-Ard-34323242-002',
#             amount=123123.00,
#             date='2025-03-20 20:30:00',
#             due_date='2025-04-16 20:30:00',
#             organization=None,  # مثل رکوردت NULL
#             created_by=self.user,
#             current_stage=self.stage,
#             status='DRAFT',
#             hq_status='PENDING'
#         )
#
#     def test_tankhah_list_view_hq_user(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('tankhah_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'tankhah/tankhah_list.html')
#         self.assertIn('Tankhahs', response.context)
#         self.assertEqual(response.context['Tankhahs'].count(), 1)
#         self.assertContains(response, 'TNKH-14040101-HOTELS-Ard-34323242-002')
#
#     def test_tankhah_list_view_non_hq_user(self):
#         non_hq_org = Organization.objects.create(name='Non HQ Org', code='NHQ', org_type='COMPLEX')
#         UserPost.objects.all().delete()
#         UserPost.objects.create(user=self.user,
#                                 post=Post.objects.create(name='Manager', organization=non_hq_org, level=1))
#
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('tankhah_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'tankhah/tankhah_list.html')
#         self.assertIn('Tankhahs', response.context)
#         self.assertEqual(response.context['Tankhahs'].count(), 1)  # چون NULL رو هم نشون می‌ده
#         self.assertContains(response, 'TNKH-14040101-HOTELS-Ard-34323242-002')
#
#     def test_tankhah_list_view_no_permission(self):
#         no_perm_user = CustomUser.objects.create_user(
#             username='noperm',
#             email='noperm@example.com',
#             password='testpass'
#         )
#         self.client.login(username='noperm', password='testpass')
#         response = self.client.get(reverse('tankhah_list'))
#
#         self.assertEqual(response.status_code, 302)
#         self.assertRedirects(response, reverse('factor_list'))
#
#     def tearDown(self):
#         self.client.logout()
# class TankhahDetailViewTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(username='testuser', password='testpass')
#         self.org = Organization.objects.create(name='Test Org')
#         self.stage = WorkflowStage.objects.create(name='Pending', order=1)
#         self.tankhah = Tankhah.objects.create(
#             number='1001',
#             organization=self.org,
#             current_stage=self.stage
#         )
#         # افزودن پرمیشن به کاربر
#         permission = Permission.objects.get(codename='Tankhah_view')
#         self.user.user_permissions.add(permission)
#
#     def test_detail_view_with_permission(self):
#         self.client.force_login(self.user)
#         response = self.client.get(reverse('tankhah_detail', kwargs={'pk': self.tankhah.pk}))
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, self.tankhah.number)
#
#     def test_detail_view_without_permission(self):
#         user_no_perm = CustomUser.objects.create_user(username='noperm', password='testpass')
#         self.client.force_login(user_no_perm)
#         response = self.client.get(reverse('tankhah_detail', kwargs={'pk': self.tankhah.pk}))
#         self.assertEqual(response.status_code, 403)
# class TankhahDeleteViewTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_superuser(username='admin', password='adminpass')
#         self.org = Organization.objects.create(name='Test Org')
#         self.tankhah = Tankhah.objects.create(number='1001', organization=self.org)
#
#     def test_delete_tankhah(self):
#         self.client.force_login(self.user)
#         response = self.client.post(reverse('tankhah_delete', kwargs={'pk': self.tankhah.pk}))
#         self.assertRedirects(response, reverse('tankhah_list'))
#         self.assertFalse(Tankhah.objects.filter(pk=self.tankhah.pk).exists())
# class TankhahApprovalTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(username='approver', password='testpass')
#         self.org = Organization.objects.create(name='Test Org')
#         self.stage1 = WorkflowStage.objects.create(name='Stage1', order=1)
#         self.stage2 = WorkflowStage.objects.create(name='Stage2', order=2)
#
#         # ایجاد پست کاربر با دسترسی تأیید
#         post = Post.objects.create(organization=self.org)
#         StageApprover.objects.create(stage=self.stage1, post=post)
#         UserPost.objects.create(user=self.user, post=post)
#
#         self.tankhah = Tankhah.objects.create(
#             number='1001',
#             organization=self.org,
#             current_stage=self.stage1
#         )
#
#     def test_approve_tankhah(self):
#         self.client.force_login(self.user)
#         response = self.client.get(reverse('tankhah_approve', kwargs={'pk': self.tankhah.pk}))
#         self.tankhah.refresh_from_db()
#         self.assertEqual(self.tankhah.current_stage, self.stage2)
#         self.assertRedirects(response, reverse('dashboard_flows'))
#
#     def test_reject_tankhah(self):
#         self.client.force_login(self.user)
#         response = self.client.get(reverse('tankhah_reject', kwargs={'pk': self.tankhah.pk}))
#         self.tankhah.refresh_from_db()
#         self.assertEqual(self.tankhah.status, 'REJECTED')
#         self.assertRedirects(response, reverse('dashboard_flows'))
# class FinalApprovalTest(TestCase):
#     def setUp(self):
#         self.hq_user = CustomUser.objects.create_user(username='hquser', password='hqpass')
#         self.branch_user = CustomUser.objects.create_user(username='branchuser', password='branchpass')
#         self.hq_org = Organization.objects.create(name='HQ', org_type='HQ')
#         self.branch_org = Organization.objects.create(name='Branch', org_type='BRANCH')
#
#         # ایجاد پست‌ها
#         UserPost.objects.create(user=self.hq_user, post__organization=self.hq_org)
#         UserPost.objects.create(user=self.branch_user, post__organization=self.branch_org)
#
#         self.stage = WorkflowStage.objects.create(name='HQ_FIN', order=5)
#         self.tankhah = Tankhah.objects.create(
#             number='1001',
#             organization=self.branch_org,
#             current_stage=self.stage
#         )
#
#     def test_hq_final_approval(self):
#         self.client.force_login(self.hq_user)
#         response = self.client.post(
#             reverse('tankhah_final_approval', kwargs={'pk': self.tankhah.pk}),
#             {'status': 'PAID'}
#         )
#         self.tankhah.refresh_from_db()
#         self.assertTrue(self.tankhah.is_archived)
#         self.assertRedirects(response, reverse('tankhah_list'))
#
#     def test_branch_user_cannot_final_approve(self):
#         self.client.force_login(self.branch_user)
#         response = self.client.post(
#             reverse('tankhah_final_approval', kwargs={'pk': self.tankhah.pk}),
#             {'status': 'PAID'}
#         )
#         self.assertEqual(response.status_code, 403)
# #------------
# from django.test import TestCase
# from django.core.exceptions import ValidationError
# from budgets.models import BudgetPeriod, BudgetAllocation,  CostCenter
# from tankhah.models import Tankhah
# from core.models import Organization
# from accounts.models import CustomUser
# from decimal import Decimal
#
# class TankhahTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(username='jj', password='D@d123',email='jj@itdc.net')
#         self.org = Organization.objects.create(name='Test Org', code='TST')
#         self.budget_period = BudgetPeriod.objects.create(
#             organization=self.org, name='Test Period', total_amount=1000000,
#             start_date='2025-01-01', end_date='2025-12-31', created_by=self.user
#         )
#         self.budget_allocation = BudgetAllocation.objects.create(
#             budget_period=self.budget_period, organization=self.org,
#             allocated_amount=500000, created_by=self.user
#         )
#         self.cost_center = CostCenter.objects.create(
#             name='Test Center', code='TC001', organization=self.org,
#             budget_allocation=self.budget_allocation, allocated_budget=200000
#         )
#
#     def test_tankhah_creation(self):
#         tankhah = Tankhah.objects.create(
#             organization=self.org, cost_center=self.cost_center,
#             amount=100000, created_by=self.user
#         )
#         self.assertTrue(tankhah.number.startswith('TNK-'))
#         self.assertEqual(tankhah.status, 'DRAFT')
#
#     def test_tankhah_invalid_amount(self):
#         with self.assertRaises(ValidationError):
#             tankhah = Tankhah(
#                 organization=self.org, cost_center=self.cost_center,
#                 amount=300000, created_by=self.user
#             )
#             tankhah.full_clean()
