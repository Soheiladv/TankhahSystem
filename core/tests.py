# from django.test import TestCase
# from django.utils import timezone
# from core.models import Organization, Project, Post, UserPost, WorkflowStage
# from accounts.models import CustomUser
#
# class CoreModelTest(TestCase):
#     def setUp(self):
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='HQ')
#         self.project = Project.objects.create(
#             name='Test Project',
#             code='TPRJ',
#             start_date=timezone.now().date()
#         )
#         self.project.organizations.add(self.org)
#         self.post = Post.objects.create(name='Manager', organization=self.org)
#
#     def test_organization_creation(self):
#         org = Organization.objects.create(name='New Org', code='NEW', org_type='COMPLEX')
#         self.assertEqual(org.name, 'New Org')
#         self.assertEqual(org.code, 'NEW')
#         self.assertEqual(org.org_type, 'COMPLEX')
#
#     def test_project_creation(self):
#         project = Project.objects.create(
#             name='Another Project',
#             code='ANP',
#             start_date=timezone.now().date(),
#             priority='HIGH'
#         )
#         project.organizations.add(self.org)
#         self.assertEqual(project.name, 'Another Project')
#         self.assertEqual(project.code, 'ANP')
#         self.assertEqual(project.priority, 'HIGH')
#         self.assertIn(self.org, project.organizations.all())
#
#     def test_post_creation(self):
#         post = Post.objects.create(
#             name='Supervisor',
#             organization=self.org,
#             level=2,
#             branch='OPS'
#         )
#         self.assertEqual(post.name, 'Supervisor')
#         self.assertEqual(post.organization, self.org)
#         self.assertEqual(post.level, 1)
#         self.assertEqual(post.branch, 'OPS')
#
#     def test_user_post_creation(self):
#         user_post = UserPost.objects.create(user=self.user, post=self.post)
#         self.assertEqual(user_post.user, self.user)
#         self.assertEqual(user_post.post, self.post)
#
#     def test_workflow_stage_creation(self):
#         stage = WorkflowStage.objects.create(name='Test Stage', order=2)
#         self.assertEqual(stage.name, 'Test Stage')
#         self.assertEqual(stage.order, 2)
# #-------------------------------
# from django.test import TestCase, Client
# from django.urls import reverse
# from django.utils import timezone
# from django.contrib.auth import get_user_model
# from core.models import Organization, Project, Post, WorkflowStage, UserPost
# from core.views import (
#     DashboardView_flows_1, OrganizationListView, OrganizationCreateView,
#     ProjectListView, ProjectCreateView, PostListView, WorkflowStageListView
# )
# from tankhah.models import Tankhah, StageApprover
# from accounts.models import CustomUser
#
# CustomUser = get_user_model()
#
#
# class CoreViewsTest(TestCase):
#     def setUp(self):
#         # تنظیمات اولیه
#         self.client = Client()
#
#         # ایجاد کاربر با پرمیشن‌ها
#         self.user = CustomUser.objects.create_user(
#             username='foad',
#             email='foad@example.com',
#             password='testpass'
#         )
#         self.user.user_permissions.add(
#             *self.user.user_permissions.model.objects.filter(
#                 codename__in=[
#                     'DashboardView_flows_view', 'Organization_view', 'Organization_add',
#                     'Project_view', 'Project_add', 'Post_view', 'WorkflowStage_view'
#                 ]
#             )
#         )
#
#         # سازمان تست
#         self.org = Organization.objects.create(name='Test Org', code='TST', org_type='COMPLEX')
#
#         # پست تست
#         self.post = Post.objects.create(name='Manager', organization=self.org, level=1)
#         UserPost.objects.create(user=self.user, post=self.post)
#
#         # مرحله گردش کار
#         self.stage = WorkflowStage.objects.create(name='HQ_INITIAL', order=1)
#         StageApprover.objects.create(post=self.post, stage=self.stage)
#
#         # پروژه تست
#         self.project = Project.objects.create(
#             name='Test Project',
#             code='TPRJ',
#             start_date=timezone.now().date(),
#             budget=1000000
#         )
#         self.project.organizations.add(self.org)
#
#         # تنخواه تست
#         self.tankhah = Tankhah.objects.create(
#             amount=500000,
#             date=timezone.now(),
#             organization=self.org,
#             created_by=self.user,
#             current_stage=self.stage,
#             status='PENDING'
#         )
#
#     def test_organization_list_view(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('organization_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/organization_list.html')
#         self.assertIn('organizations', response.context)
#         self.assertQuerysetEqual(
#             response.context['organizations'],
#             Organization.objects.all(),
#             transform=lambda x: x
#         )
#
#         # تست جستجو
#         response = self.client.get(reverse('organization_list'), {'q': 'TST'})
#         self.assertContains(response, 'Test Org')
#
#     def test_organization_create_view_get(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('organization_create'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/organization_form.html')
#         self.assertIn('form', response.context)
#
#     def test_project_create_view_post(self):
#         from persiantools.jdatetime import JalaliDate
#         self.client.login(username='foad', password='testpass')
#
#         jalali_date = JalaliDate(1404, 1, 17).to_gregorian()  # تبدیل جلالی به میلادی
#         data = {
#             'name': 'New Project',
#             'code': 'NPRJ',
#             'organizations': [self.org.id],
#             'start_date': jalali_date.strftime('%Y-%m-%d'),  # اصلاح تبدیل تاریخ
#             'budget': 2000000,
#             'priority': 'HIGH',
#             'is_active': True
#         }
#         response = self.client.post(reverse('project_create'), data)
#         self.assertEqual(response.status_code, 302)
#         self.assertTrue(Project.objects.filter(code='NPRJ').exists())  # اصلاح مقدار بررسی
#         self.assertRedirects(response, reverse('project_list'))
#
#
#     def test_project_list_view(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('project_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/project_list.html')
#         self.assertIn('projects', response.context)
#         self.assertQuerysetEqual(
#             response.context['projects'],
#             Project.objects.all(),
#             transform=lambda x: x
#         )
#
#     def test_project_create_view_get(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('project_create'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/project_form.html')
#         self.assertIn('form', response.context)
#
#     def test_project_create_view_post(self):
#         self.client.login(username='foad', password='testpass')
#         jalali_date = '1404/01/17'  # تاریخ نمونه جلالی
#         data = {
#             'name': 'New Project',
#             'code': 'NPRJ',
#             'organizations': [self.org.id],
#             'start_date': jalali_date,
#             'budget': 2000000,
#             'priority': 'HIGH',
#             'is_active': True
#         }
#         response = self.client.post(reverse('project_create'), data)
#
#         self.assertEqual(response.status_code, 302)
#         self.assertTrue(Project.objects.filter(code='NPRJ').exists())
#         self.assertRedirects(response, reverse('project_list'))
#
#     def test_post_list_view(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('post_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/post/post_list.html')
#         self.assertIn('posts', response.context)
#         self.assertQuerysetEqual(
#             response.context['posts'],
#             Post.objects.all(),
#             transform=lambda x: x
#         )
#         # تست مرتب‌سازی
#         response = self.client.get(reverse('post_list'), {'sort': 'desc'})
#         self.assertEqual(response.context['current_sort'], 'desc')
#
#     def test_workflow_stage_list_view(self):
#         self.client.login(username='foad', password='testpass')
#         response = self.client.get(reverse('workflow_stage_list'))
#
#         self.assertEqual(response.status_code, 200)
#         self.assertTemplateUsed(response, 'core/workflow_stage/workflow_stage_list.html')
#         self.assertIn('stages', response.context)
#         self.assertQuerysetEqual(
#             response.context['stages'],
#             WorkflowStage.objects.all(),
#             transform=lambda x: x
#         )
#
#     def tearDown(self):
#         # پاکسازی بعد از تست
#         self.client.logout()
#
#
# from django.test import TestCase
# from core.models import Post, WorkflowStage
#
# class PostAccessRuleFormTest(TestCase):
#     def setUp(self):
#         self.post = Post.objects.create(name="تست", organization_id=1, is_active=True)
#         self.stage = WorkflowStage.objects.create(name="تست مرحله", is_active=True)
#
#     def test_sign_payment_validation(self):
#         data = {
#             f"post_{self.post.id}_rule_FACTOR_SIGN_PAYMENT": "on",
#             f"post_{self.post.id}_rule_FACTOR_SIGN_PAYMENT_stage": self.stage.id,
#             f"post_{self.post.id}_level": 2,
#         }
#         from core.AccessRule.forms_accessrule import PostAccessRuleForm
#         form = PostAccessRuleForm(data=data)
#         self.assertTrue(form.is_valid(), msg=form.errors.as_json())
#         self.assertIn(f"post_{self.post.id}_rule_FACTOR_SIGN_PAYMENT", form.cleaned_data)
#
#     def test_invalid_action_type(self):
#         data = {
#             f"post_{self.post.id}_rule_FACTOR_SIGN": "on",
#             f"post_{self.post.id}_rule_FACTOR_SIGN_stage": self.stage.id,
#         }
#         from core.AccessRule.forms_accessrule import PostAccessRuleForm
#         form = PostAccessRuleForm(data=data)
#         self.assertFalse(form.is_valid())
#         self.assertIn("نوع اقدام SIGN نامعتبر است.", str(form.errors))