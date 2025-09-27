from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from core.models import SystemSettings


class SystemSettingsUpdateUrlTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='pass', is_superuser=True, is_staff=True
        )
        self.client.login(username='admin', password='pass')
        SystemSettings.get_solo()

    def test_update_success_on_pk_2_url(self):
        url = reverse('system_settings_update', kwargs={'pk': 2})
        data = {
            'budget_locked_percentage_default': '11.00',
            'budget_warning_threshold_default': '22.00',
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': '6.00',
            'tankhah_used_statuses': '["PAID", "APPROVED"]',
            'tankhah_accessible_organizations': '[1, 2, 3]',
            'tankhah_payment_ceiling_default': '500000.00',
            'tankhah_payment_ceiling_enabled_default': 'on',
            'enforce_strict_approval_order': 'on',
            'allow_bypass_org_chart': '',
            'allow_action_without_org_chart': '',
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        # landed dashboard contains عنوان
        self.assertContains(resp, "تنظیمات سیستم")
        s = SystemSettings.get_solo()
        self.assertEqual(s.budget_locked_percentage_default, Decimal('11.00'))
        self.assertEqual(s.budget_warning_threshold_default, Decimal('22.00'))

    def test_update_invalid_shows_error(self):
        url = reverse('system_settings_update', kwargs={'pk': 2})
        data = {
            'budget_locked_percentage_default': 'invalid',
            'budget_warning_threshold_default': '5',
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': '0',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ثبت انجام نشد. لطفاً خطاهای فرم را برطرف کنید.")


