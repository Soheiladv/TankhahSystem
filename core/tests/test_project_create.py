from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Organization, OrganizationType, Project


class ProjectCreateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='admin', is_superuser=True, is_staff=True)
        self.client.login(username='admin', password='admin')

        self.org_type = OrganizationType.objects.create(
            fname='Branch', org_type='BR', is_budget_allocatable=True
        )
        self.org = Organization.objects.create(
            code='B001', name='Branch 001', org_type=self.org_type, is_active=True
        )

    def test_create_project_with_jalali_dates_and_organization(self):
        url = reverse('project_create')
        payload = {
            'name': 'Proj A',
            'code': 'PA-001',
            'priority': 'MEDIUM',
            'organization': str(self.org.id),
            'is_active': 'on',
            'description': 'test',
            'has_subproject': '',
            'subproject_name': '',
            'subproject_description': '',
            'start_date': '1404/01/10',
            'end_date': '1404/02/20',
        }
        resp = self.client.post(url, payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Project.objects.filter(code='PA-001').exists(), msg='Project was not created')
        project = Project.objects.get(code='PA-001')
        self.assertEqual(project.organizations.count(), 1)
        self.assertEqual(project.organizations.first().id, self.org.id)
        self.assertIsNotNone(project.start_date)
        self.assertIsNotNone(project.end_date)

    def test_create_project_rejects_end_before_start(self):
        url = reverse('project_create')
        payload = {
            'name': 'Proj B',
            'code': 'PB-001',
            'priority': 'LOW',
            'organization': str(self.org.id),
            'is_active': 'on',
            'start_date': '1404/02/20',
            'end_date': '1404/01/10',
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        # Should render form with errors
        self.assertContains(resp, 'تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد', status_code=200)
        self.assertFalse(Project.objects.filter(code='PB-001').exists())


