from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import SystemSettings


class SystemSettingsViewsTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='pass'
        )
        self.client.login(username='admin', password='pass')
        # Ensure singleton exists
        self.settings = SystemSettings.get_solo()

    def test_update_valid(self):
        url = reverse('system_settings_update', kwargs={'pk': self.settings.pk})
        payload = {
            'budget_locked_percentage_default': 12.5,
            'budget_warning_threshold_default': 20,
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': 0,
            'tankhah_used_statuses': '[]',
            'tankhah_accessible_organizations': '[]',
            'tankhah_payment_ceiling_default': 0,
            'tankhah_payment_ceiling_enabled_default': False,
            'enforce_strict_approval_order': True,
            'allow_bypass_org_chart': False,
            'allow_action_without_org_chart': False,
        }
        resp = self.client.post(url, data=payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(float(self.settings.budget_locked_percentage_default), 12.5)
        self.assertContains(resp, 'با موفقیت بروزرسانی شد', html=False)

    def test_update_invalid_percentage_shows_errors(self):
        url = reverse('system_settings_update', kwargs={'pk': self.settings.pk})
        payload = {
            'budget_locked_percentage_default': 'abc',  # invalid
            'budget_warning_threshold_default': 20,
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': 0,
            'tankhah_used_statuses': '[]',
            'tankhah_accessible_organizations': '[]',
            'tankhah_payment_ceiling_default': 0,
            'tankhah_payment_ceiling_enabled_default': False,
            'enforce_strict_approval_order': True,
            'allow_bypass_org_chart': False,
            'allow_action_without_org_chart': False,
        }
        resp = self.client.post(url, data=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'لطفاً خطاهای', html=False)

    def test_create_writes_singleton_and_redirects(self):
        # Remove current to simulate fresh create
        SystemSettings.objects.all().delete()
        url = reverse('system_settings_create')
        payload = {
            'budget_locked_percentage_default': 5,
            'budget_warning_threshold_default': 10,
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': 0,
            'tankhah_used_statuses': '[]',
            'tankhah_accessible_organizations': '[]',
            'tankhah_payment_ceiling_default': 0,
            'tankhah_payment_ceiling_enabled_default': False,
            'enforce_strict_approval_order': True,
            'allow_bypass_org_chart': False,
            'allow_action_without_org_chart': False,
        }
        resp = self.client.post(url, data=payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        obj = SystemSettings.objects.first()
        self.assertIsNotNone(obj)
        self.assertEqual(float(obj.budget_locked_percentage_default), 5.0)
        self.assertContains(resp, 'با موفقیت ذخیره شد', html=False)