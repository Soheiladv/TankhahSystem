from django.test import TestCase
from version_tracker.models import AppVersion

class VersionDetectionTests(TestCase):
    def test_build_changes(self):
        """تست تشخیص تغییرات Build"""
        changed_files = [
            'templates/home.html',
        ]
        result = AppVersion.determine_version_types(changed_files)
        self.assertEqual(result, 'build')

    def test_major_build_combination(self):
        """تست ترکیبی Major + Build"""
        changed_files = [
            'accounts/models.py',
            'accounts/templates/user/login.html'
        ]
        result = AppVersion.determine_version_types(changed_files)
        self.assertEqual(result, 'major')