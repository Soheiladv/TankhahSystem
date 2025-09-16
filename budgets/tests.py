from django.test import TestCase
from django.contrib.auth.models import User
from core.models import EntityType, Status, Action, Transition, Post, UserPost, Organization
from budgets.models import PaymentOrder
from django.contrib.contenttypes.models import ContentType

class WorkflowTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(code='ORG1', name='Test Org', is_active=True)
        self.users = [User.objects.create_user(username=f'user{i}', password='test') for i in range(1, 6)]
        self.posts = [
            Post.objects.create(name=name, organization=self.org)
            for name in ['هیئت مدیره بانک', 'مدیر عامل', 'ذیحسابی', 'مدیر حسابداری', 'مسئول رسیدگی']
        ]
        for i, user in enumerate(self.users):
            UserPost.objects.create(user=user, post=self.posts[i], is_active=True)
        self.entity_type = EntityType.objects.create(
            name='دستور پرداخت', code='PAYMENTORDER',
            content_type=ContentType.objects.get(app_label='budgets', model='paymentorder')
        )
        self.statuses = {
            code: Status.objects.create(name=name, code=code, is_initial=(code=='PO_DRAFT'), is_final_approve=(code=='PO_APPROVED'), created_by=self.users[0])
            for code, name in [
                ('PO_DRAFT', 'پیش‌نویس'), ('PO_PENDING_BOARD', 'در انتظار تایید هیئت مدیره'),
                ('PO_PENDING_CEO', 'در انتظار تایید مدیر عامل'), ('PO_PENDING_ACCOUNTANT', 'در انتظار تایید ذیحسابی'),
                ('PO_PENDING_AUDIT', 'در انتظار تایید مدیر حسابداری'), ('PO_PENDING_REVIEW', 'در انتظار تایید مسئول رسیدگی'),
                ('PO_APPROVED', 'تایید شده'), ('PO_REJECTED', 'رد شده')
            ]
        }
        self.actions = {
            code: Action.objects.create(name=name, code=code, created_by=self.users[0])
            for code, name in [
                ('SUBMIT', 'ارسال برای تایید'), ('APPROVE_BOARD', 'تایید هیئت مدیره'),
                ('APPROVE_CEO', 'تایید مدیر عامل'), ('APPROVE_ACCOUNTANT', 'تایید ذیحسابی'),
                ('APPROVE_AUDIT', 'تایید مدیر حسابداری'), ('APPROVE_REVIEW', 'تایید مسئول رسیدگی'),
                ('REJECT', 'رد کردن')
            ]
        }

    def test_workflow_transitions(self):
        payment_order = PaymentOrder.objects.create(
            order_number='PO-TEST', organization=self.org, status=self.statuses['PO_DRAFT'],
            created_by=self.users[0], amount=1000
        )
        transition = Transition.objects.create(
            name='ارسال به هیئت مدیره', entity_type=self.entity_type,
            from_status=self.statuses['PO_DRAFT'], action=self.actions['SUBMIT'],
            to_status=self.statuses['PO_PENDING_BOARD'], organization=self.org, created_by=self.users[0]
        )
        transition.allowed_posts.add(self.posts[0])
        # Test transition
        payment_order.status = self.statuses['PO_PENDING_BOARD']
        payment_order.save()
        self.assertEqual(payment_order.status.code, 'PO_PENDING_BOARD')