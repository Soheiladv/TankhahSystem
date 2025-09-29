from django.test import TestCase
from django.urls import reverse

class MainDashboardViewTests(TestCase):
    def test_main_dashboard_renders_ok(self):
        url = reverse('reports_dashboard:main_dashboard')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        for key in ['budget_stats', 'tankhah_stats', 'factor_stats', 'payment_stats', 'chart_data']:
            self.assertIn(key, resp.context, msg=f"missing context key: {key}")
        self.assertContains(resp, 'داشبورد گزارشات بودجه')
        self.assertContains(resp, 'وضعیت تنخواه‌ها')
        self.assertContains(resp, 'مقایسه سازمان/پروژه')

    def test_main_dashboard_accepts_jalali_filters(self):
        url = reverse('reports_dashboard:main_dashboard')
        params = {
            'start_date': '1404/07/01',
            'end_date': '1404/07/07',
        }
        resp = self.client.get(url, params)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'فیلترهای پیشرفته')
