from django.test import TestCase
from django.utils import timezone
from accounts.models import CustomUser, AuditLog, ActiveUser, Province, City

class AccountsModelTest(TestCase):
    def test_custom_user_creation(self):
        user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass',
            first_name='Foad',
            last_name='Test'
        )
        self.assertEqual(user.username, 'foad')
        self.assertEqual(user.get_full_name(), 'Foad Test')
        self.assertTrue(user.check_password('testpass'))

    def test_audit_log_creation(self):
        user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass'
        )
        log = AuditLog.objects.create(
            user=user,
            action='create',
            view_name='test_view',
            path='/test/',
            method='POST',
            model_name='TestModel',
            details='Test log'
        )
        self.assertEqual(log.user, user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.model_name, 'TestModel')

    def test_active_user_creation(self):
        user = CustomUser.objects.create_user(
            username='foad',
            email='foad@example.com',
            password='testpass'
        )
        active_user = ActiveUser.objects.create(
            user=user,
            session_key='testsession123',
            user_ip='192.168.1.34',
            user_agent='Mozilla/5.0'
        )
        self.assertEqual(active_user.user, user)
        self.assertEqual(active_user.session_key, 'testsession123')