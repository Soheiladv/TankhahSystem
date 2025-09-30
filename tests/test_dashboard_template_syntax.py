from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest import mock


class DashboardTemplateSyntaxTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='dash_tester', email='dash_tester@example.com', password='secret123')
        # Ensure permissions do not block the dashboard in tests
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        # Patch heavy view methods to avoid DB vendor-specific SQL (e.g., MySQL DATE_FORMAT)
        from reports.dashboard import views as dash_views
        self.patches = [
            mock.patch.object(dash_views.DashboardMainView, 'get_budget_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_tankhah_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_factor_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_payment_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_cost_center_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_budget_return_statistics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_advanced_risk_metrics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_chart_data', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_advanced_budget_metrics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_advanced_tankhah_metrics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_advanced_factor_metrics', return_value={}),
            mock.patch.object(dash_views.DashboardMainView, 'get_advanced_comparatives', return_value={}),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in getattr(self, 'patches', []):
            try:
                p.stop()
            except RuntimeError:
                pass
    def test_dashboard_renders_without_params(self):
        url = reverse('reports_dashboard:main_dashboard')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 200, msg='Dashboard should render without query params'
        )

    def test_dashboard_renders_with_date_params(self):
        url = reverse('reports_dashboard:main_dashboard')
        params = {
            'start_date': '1404/07/01',
            'end_date': '1404/07/07',
        }
        response = self.client.get(url, params)
        self.assertEqual(
            response.status_code, 200, msg='Dashboard should render with Jalali date params'
        )

    def test_dashboard_renders_with_empty_date_params(self):
        url = reverse('reports_dashboard:main_dashboard')
        params = {
            'start_date': '',
            'end_date': '',
        }
        response = self.client.get(url, params)
        self.assertEqual(
            response.status_code, 200, msg='Dashboard should handle empty date params gracefully'
        )


