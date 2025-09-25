from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from core.models import Organization, Post, UserPost, EntityType, Status, Action, Transition


class FactorDetailViewAllowedActionsTest(TestCase):
    def setUp(self):
        # Users
        self.admin = CustomUser.objects.create_user(username='admin', email='admin@example.com', password='pass', is_superuser=True, is_staff=True)
        self.user = CustomUser.objects.create_user(username='u1', email='u1@example.com', password='pass', is_staff=True)

        # Organization and post
        self.org = Organization.objects.create(code='TEST', name='Test Org')
        self.post = Post.objects.create(name='Approver', organization=self.org, level=1)
        UserPost.objects.create(user=self.user, post=self.post, start_date=timezone.now().date(), is_active=True)

        # Workflow primitives (created_by required on Status/Action)
        self.et, _ = EntityType.objects.get_or_create(code='FACTOR', defaults={'name': 'FACTOR'})
        self.s_draft, _ = Status.objects.get_or_create(code='DRAFT', defaults={'name': 'DRAFT', 'is_initial': True, 'is_active': True, 'created_by': self.admin})
        self.s_pending, _ = Status.objects.get_or_create(code='PENDING_APPROVAL', defaults={'name': 'PENDING_APPROVAL', 'is_active': True, 'created_by': self.admin})
        self.a_submit, _ = Action.objects.get_or_create(code='SUBMIT', defaults={'name': 'SUBMIT', 'is_active': True, 'created_by': self.admin})

        # Transition: DRAFT --SUBMIT--> PENDING_APPROVAL limited to user's post
        self.tr = Transition.objects.create(
            name='TEST FACTOR: DRAFT --SUBMIT--> PENDING_APPROVAL',
            organization=self.org,
            entity_type=self.et,
            from_status=self.s_draft,
            action=self.a_submit,
            to_status=self.s_pending,
            created_by=self.admin,
            is_active=True,
        )
        self.tr.allowed_posts.set([self.post.id])

        # Factor instance
        # Import locally to avoid heavy app import at module import time
        from tankhah.models import Factor, Tankhah
        self.Tankhah = Tankhah
        self.Factor = Factor

        self.tankhah = self.Tankhah.objects.create(
            title='TNK1',
            organization=self.org,
        )
        self.factor = self.Factor.objects.create(
            tankhah=self.tankhah,
            status=self.s_draft,
            created_by=self.user,
            payee='P1',
            category_id=self.tankhah.project_budget_allocation_id if hasattr(self.tankhah, 'project_budget_allocation_id') else None,
        )

    def test_available_transitions_contains_submit_for_user_post(self):
        self.client.login(username='u1', password='pass')
        url = reverse('factor_detail', args=[self.factor.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        available = resp.context.get('available_transitions')
        # available_transitions is a list of Transition objects
        self.assertIsNotNone(available)
        self.assertTrue(any(t.action.code == 'SUBMIT' and t.from_status_id == self.s_draft.id for t in available))


