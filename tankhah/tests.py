from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from core.models import Organization, Post, UserPost, Branch
from tankhah.models import Factor, FactorItem, Tankhah, AccessRule, ApprovalLog


class FactorItemApproveViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.organization = Organization.objects.create(code='TEST', name='Test Org')
        self.branch = Branch.objects.create(code='FIN', name='مالی', is_active=True)
        self.post = Post.objects.create(
            name='Test Post',
            organization=self.organization,
            branch=self.branch,
            level=1,
            can_final_approve_factor=True,
            can_final_approve_tankhah=True
        )
        self.user_post = UserPost.objects.create(user=self.user, post=self.post, is_active=True)
        self.access_rule = AccessRule.objects.create(
            organization=self.organization,
            branch='FIN',
            min_level=1 ,
            action_type='APPROVE',
            entity_type='FACTORITEM',
            stage='STAGE1',
            stage_order=1,
            is_active=True,
            is_final_stage=False
        )
        self.tankhah = Tankhah.objects.create(
            organization=self.organization,
            number='T001',
            status='PENDING',
            current_stage=self.access_rule
        )
        self.factor = Factor.objects.create(tankhah=self.tankhah, organization=self.organization
        )
        self.factor_item = FactorItem.objects.create(factor=self.factor, status='PENDING')

    def test_approve_item(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('factor_item_approve', kwargs={'pk': self.factor.pk}), {
            'items-0-status': 'APPROVED',
            'items-0-description': 'Approved',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '1',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000'
        })
        self.factor_item.refresh_from_db()
        self.assertEqual(self.factor_item.status, 'APPROVED')
        self.assertTrue(ApprovalLog.objects.filter(
            factor=self.factor,
            action='APPROVEED',
            user=self.user
        ).exists())

    def test_final_approve(self):
        self.access_rule.is_final_stage = True
        self.access_rule.save()
        self.factor_item.status = 'APPROVEED'
        self.factor_item.save()
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(reverse('factor_item_approve', kwargs={'pk': self.factor.pk}), {
            'final_approve': 'true',
            'payment_number': 'PN123'
        })
        self.tankhah.refresh_from_db()
        self.assertEqual(self.tankhah.status, 'APPROVEED')
        self.assertTrue(ApprovalLog.objects.filter(
            factor=self.factor,
            action='APPROVEED',
            comment='تأیید نهایی تنخواه'
        ).exists())