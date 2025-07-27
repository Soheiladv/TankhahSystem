from django.test import TestCase
from .models import Post, Branch, Organization
from .forms import PostForm

class PostModelTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(code='TEST', name='Test Org')
        self.branch = Branch.objects.create(code='FIN', name='مالی', is_active=True)
        self.parent_post = Post.objects.create(
            name='Parent Post', organization=self.organization, branch=self.branch, level=1
        )

    def test_level_inheritance(self):
        child_post = Post.objects.create(
            name='Child Post', organization=self.organization, branch=self.branch, parent=self.parent_post
        )
        self.assertEqual(child_post.level, 2)
        self.assertEqual(child_post.max_change_level, 2)

    def test_update_parent_level(self):
        child_post = Post.objects.create(
            name='Child Post', organization=self.organization, branch=self.branch, parent=self.parent_post
        )
        self.parent_post.level = 2
        self.parent_post.save()
        child_post.refresh_from_db()
        self.assertEqual(child_post.level, 3)

class PostFormTest(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(code='TEST', name='Test Org')
        self.branch = Branch.objects.create(code='FIN', name='مالی', is_active=True)
        self.parent_post = Post.objects.create(
            name='Parent Post', organization=self.organization, branch=self.branch, level=1
        )

    def test_form_save(self):
        form_data = {
            'name': 'Test Post',
            'organization': self.organization.id,
            'parent': self.parent_post.id,
            'branch': self.branch.id,
            'is_active': True,
            'max_change_level': 2,
        }
        form = PostForm(data=form_data)
        self.assertTrue(form.is_valid())
        post = form.save()
        self.assertEqual(post.level, 2)