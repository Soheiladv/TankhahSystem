from tankhah.models import Tanbakh, Factor, FactorItem, TanbakhDocument, ApprovalLog, StageApprover
from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from tankhah.models import Tanbakh, TanbakhDocument
from core.models import Organization, Project, Post, WorkflowStage
from accounts.models import CustomUser
import jdatetime

class TanbakhModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass'
        )
        self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
        self.project = Project.objects.create(
            name='Test Project',
            code='TPRJ',
            start_date=timezone.now().date()
        )
        self.project.organizations.add(self.org)
        self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
        self.post = Post.objects.create(name='Manager', organization=self.org)

    def test_tanbakh_document_upload(self):
        tanbakh = Tanbakh.objects.create(
            amount=1000000,
            date=timezone.now(),
            organization=self.org,
            created_by=self.user,
            description="With Document",
            current_stage=self.stage
        )
        # شبیه‌سازی یه فایل واقعی
        file_content = b"Test file content"
        uploaded_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")
        doc = TanbakhDocument.objects.create(
            tanbakh=tanbakh,
            document=uploaded_file
        )
        self.assertEqual(doc.tanbakh, tanbakh)
        self.assertIn(tanbakh.number, doc.document.name)
        self.assertTrue(doc.document.name.endswith('.pdf'))


class FactorModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass'
        )
        self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
        self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
        self.tanbakh = Tanbakh.objects.create(
            amount=1000000,
            date=timezone.now(),
            organization=self.org,
            created_by=self.user,
            description="Test Tanbakh",
            current_stage=self.stage
        )

    def test_factor_generate_number(self):
        factor = Factor.objects.create(
            tanbakh=self.tanbakh,
            date=timezone.now(),
            description="Test Factor"
        )
        self.assertTrue(factor.number.startswith(self.tanbakh.number))
        self.assertTrue(factor.number.endswith('F1'))

    def test_factor_multiple_numbers(self):
        factor1 = Factor.objects.create(tanbakh=self.tanbakh, date=timezone.now(), description="Factor 1")
        factor2 = Factor.objects.create(tanbakh=self.tanbakh, date=timezone.now(), description="Factor 2")
        self.assertEqual(factor1.number, f"{self.tanbakh.number}-F1")
        self.assertEqual(factor2.number, f"{self.tanbakh.number}-F2")

    def test_factor_item_creation(self):
        factor = Factor.objects.create(tanbakh=self.tanbakh, date=timezone.now(), description="Test Factor")
        item = FactorItem.objects.create(
            factor=factor,
            description="Item 1",
            amount=50000,
            quantity=2
        )
        self.assertEqual(item.factor, factor)
        self.assertEqual(item.amount, 50000)

class ApprovalLogTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass'
        )
        self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
        self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
        self.post = Post.objects.create(name='Manager', organization=self.org)
        self.tanbakh = Tanbakh.objects.create(
            amount=1000000,
            date=timezone.now(),
            organization=self.org,
            created_by=self.user,
            description="Test Tanbakh",
            current_stage=self.stage
        )

    def test_approval_log_creation(self):
        log = ApprovalLog.objects.create(
            tanbakh=self.tanbakh,
            action='APPROVE',
            stage=self.stage,
            user=self.user,
            comment="Approved by manager",
            post=self.post
        )
        self.assertEqual(log.tanbakh, self.tanbakh)
        self.assertEqual(log.action, 'APPROVE')
        self.assertEqual(log.user, self.user)

class StageApproverTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
        self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
        self.post = Post.objects.create(name='Manager', organization=self.org)

    def test_stage_approver_creation(self):
        approver = StageApprover.objects.create(stage=self.stage, post=self.post)
        self.assertEqual(approver.stage, self.stage)
        self.assertEqual(approver.post, self.post)