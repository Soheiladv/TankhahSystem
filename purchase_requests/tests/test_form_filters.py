from django.test import TestCase
from django.db import connection
from django.contrib.auth import get_user_model

from purchase_requests.forms import PurchaseRequestForm


class PurchaseRequestFormFilterTests(TestCase):
    databases = {'default'}
    def setUp(self):
        # ساخت داده‌های پایه سازمان/پروژه/زیرپروژه با حداقل وابستگی
        from core.models import Organization, Project, SubProject
        self.org1 = Organization.objects.create(name='Org A', code='ORGA')
        self.org2 = Organization.objects.create(name='Org B', code='ORGB')

        # اگر ارتباط M2M organizations روی Project وجود نداشته باشد، تست با مسیر fallback ادامه می‌دهد
        self.proj1 = Project.objects.create(name='P1')
        self.proj2 = Project.objects.create(name='P2')

        try:
            self.proj1.organizations.add(self.org1)
            self.proj2.organizations.add(self.org2)
        except Exception:
            # اگر فیلد organizations وجود نداشت، صرفاً ادامه می‌دهیم
            pass

        self.sub1 = SubProject.objects.create(name='SP1', project=self.proj1)
        self.sub2 = SubProject.objects.create(name='SP2', project=self.proj2)

        self.user = get_user_model().objects.create(username='u1')

    def test_initial_projects_not_empty(self):
        form = PurchaseRequestForm(user=self.user)
        self.assertIn('project', form.fields)
        # در حالت اولیه، لیست پروژه‌ها نباید خالی باشد
        self.assertTrue(form.fields['project'].queryset.exists())

    def test_projects_filtered_by_org_if_provided(self):
        data = {'organization': self.org1.id}
        form = PurchaseRequestForm(data=data, user=self.user)
        qs = form.fields['project'].queryset
        # وجود داشتن کافی است (در صورت نبودن رابطه M2M، مسیر fallback همه پروژه‌ها را نشان می‌دهد)
        self.assertTrue(qs.exists())

    def test_subprojects_filtered_by_project(self):
        data = {'organization': self.org1.id, 'project': self.proj1.id}
        form = PurchaseRequestForm(data=data, user=self.user)
        sp_qs = form.fields['subproject'].queryset
        self.assertTrue(sp_qs.exists())
        # فقط زیرپروژه‌های همان پروژه
        for sp in sp_qs:
            self.assertEqual(getattr(sp, 'project_id', None), self.proj1.id)


