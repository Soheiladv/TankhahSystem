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

# from version_tracker.models import AppVersion
#
# # تست 1: تغییرات Build
# changed_files_build = [
#     'templates/home.html',
#     'static/css/main.css',
#     'app/static/js/app.js'
# ]
# result_build = AppVersion.determine_version_types(changed_files_build)
# print(f"نتیجه تست Build: {result_build} (انتظار: build)")
# assert result_build == 'build', "تست Build ناموفق بود!"
#
# # تست 2: ترکیبی Major + Build
# changed_files_major_build = [
#     'app/models/user.py',
#     'app/templates/user/profile.html'
# ]
# result_major = AppVersion.determine_version_types(changed_files_major_build)
# print(f"نتیجه تست ترکیبی: {result_major} (انتظار: major)")
# assert result_major == 'major', "تست ترکیبی ناموفق بود!"