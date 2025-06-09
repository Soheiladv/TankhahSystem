import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import Client
from factory import SubFactory, Sequence, LazyAttribute, post_generation
from factory.django import DjangoModelFactory
from core.models import Organization, Post, UserPost, WorkflowStage
from tankhah.models import Tankhah, Factor, FactorItem, StageApprover, ApprovalLog
from accounts.models import CustomUser, MyGroup, Role
from django.utils import timezone

# Factory‌ها
class UserFactory(DjangoModelFactory):
    class Meta:
        model = CustomUser

    username = Sequence(lambda n: f"user_{n}")
    email = LazyAttribute(lambda o: f"{o.username}@example.com")
    password = "testpass123"

class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    code = Sequence(lambda n: f"ORG{n:03d}")
    name = Sequence(lambda n: f"Organization {n}")
    org_type = "COMPLEX"

class PostFactory(DjangoModelFactory):
    class Meta:
        model = Post

    name = Sequence(lambda n: f"Post Level {n}")
    organization = SubFactory(OrganizationFactory)
    level = 1
    is_active = True

    @post_generation
    def set_parent(obj, create, extracted, **kwargs):
        if create and hasattr(obj, 'level') and obj.level > 1:
            parent = Post.objects.filter(level=obj.level - 1, organization=obj.organization).first()
            if parent:
                obj.parent = parent

class UserPostFactory(DjangoModelFactory):
    class Meta:
        model = UserPost

    user = SubFactory(UserFactory)
    post = SubFactory(PostFactory)
    start_date = LazyAttribute(lambda o: timezone.now())

class WorkflowStageFactory(DjangoModelFactory):
    class Meta:
        model = WorkflowStage

    name = Sequence(lambda n: f"Stage {n}")
    order = Sequence(lambda n: n)
    is_active = True

class TankhahFactory(DjangoModelFactory):
    class Meta:
        model = Tankhah

    number = Sequence(lambda n: f"TNKH{n:05d}")
    amount = 1000000
    date = LazyAttribute(lambda o: timezone.now())
    organization = SubFactory(OrganizationFactory)
    created_by = SubFactory(UserFactory)
    current_stage = SubFactory(WorkflowStageFactory)
    status = "DRAFT"

class FactorFactory(DjangoModelFactory):
    class Meta:
        model = Factor

    tankhah = SubFactory(TankhahFactory)
    date = LazyAttribute(lambda o: timezone.now())
    amount = 500000
    description = "Test Factor"
    status = "PENDING"

class FactorItemFactory(DjangoModelFactory):
    class Meta:
        model = FactorItem

    factor = SubFactory(FactorFactory)
    description = "Test Item"
    amount = 500000
    status = "PENDING"
    quantity = 1
    unit_price = 500000

class StageApproverFactory(DjangoModelFactory):
    class Meta:
        model = StageApprover

    stage = SubFactory(WorkflowStageFactory)
    post = SubFactory(PostFactory)
    is_active = True

class MyGroupFactory(DjangoModelFactory):
    class Meta:
        model = MyGroup

    name = Sequence(lambda n: f"Group {n}")

class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    name = Sequence(lambda n: f"Role {n}")
    is_active = True

# فیکسچرها
@pytest.fixture
def client():
    return Client()

@pytest.fixture
def hq_organization():
    return OrganizationFactory(org_type="HQ")

@pytest.fixture
def complex_organization():
    return OrganizationFactory(org_type="COMPLEX")

@pytest.fixture
def users_with_levels(hq_organization, complex_organization):
    users = []
    posts = []
    hq_post = PostFactory(organization=hq_organization, level=0, name="Supervisor")
    posts.append(hq_post)
    current_parent = None
    for level in range(1, 8):
        post = PostFactory(organization=complex_organization, level=level, parent=current_parent)
        posts.append(post)
        current_parent = post
    for level in range(8):
        user = UserFactory()
        post = posts[level]
        UserPostFactory(user=user, post=post)
        users.append(user)
    return users

@pytest.fixture
def permissions():
    perms = {
        "core_organization_add": Permission.objects.get(codename="Organization_add", content_type__app_label="core"),
        "core_post_add": Permission.objects.get(codename="Post_add", content_type__app_label="core"),
        "core_userpost_add": Permission.objects.get(codename="UserPost_add", content_type__app_label="core"),
        "core_workflowstage_add": Permission.objects.get(codename="WorkflowStage_add", content_type__app_label="core"),
        "tankhah_add": Permission.objects.get(codename="Tankhah_add", content_type__app_label="tankhah"),
        "factor_add": Permission.objects.get(codename="factor_add", content_type__app_label="tankhah"),
        "factor_approve": Permission.objects.get(codename="FactorItem_approve", content_type__app_label="tankhah"),
        "approval_add": Permission.objects.get(codename="Approval_add", content_type__app_label="tankhah"),
        "group_add": Permission.objects.get(codename="add_mygroup", content_type__app_label="accounts"),
        "role_create": Permission.objects.get(codename="create_role", content_type__app_label="accounts"),
        "user_add": Permission.objects.get(codename="add_customuser", content_type__app_label="accounts"),
    }
    return perms

@pytest.mark.django_db
def test_access_levels(client, users_with_levels, permissions, complex_organization):
    urls = {
        "organization_create": reverse("organization_create"),
        "post_create": reverse("post_create"),
        "userpost_create": reverse("userpost_create"),
        "workflow_stage_create": reverse("workflow_stage_create"),
        "tankhah_create": reverse("tankhah_create"),
        "factor_create": reverse("factor_create", kwargs={"Tankhah_id": TankhahFactory(organization=complex_organization).id}),
    }
    access_rules = {
        0: list(urls.keys()),  # سوپروایزر (HQ) به همه دسترسی داره
        1: ["post_create", "userpost_create", "tankhah_create", "factor_create"],
        2: ["userpost_create", "tankhah_create", "factor_create"],
        3: ["tankhah_create", "factor_create"],
        4: ["tankhah_create"],
        5: ["tankhah_create"],
        6: [],
        7: [],
    }

    for level, user in enumerate(users_with_levels):
        client.force_login(user)
        allowed_views = access_rules[level]

        if level == 0:
            user.user_permissions.set(permissions.values())
        elif level == 1:
            user.user_permissions.add(permissions["core_post_add"], permissions["core_userpost_add"],
                                    permissions["tankhah_add"], permissions["factor_add"])
        elif level == 2:
            user.user_permissions.add(permissions["core_userpost_add"], permissions["tankhah_add"],
                                    permissions["factor_add"])
        elif level == 3:
            user.user_permissions.add(permissions["tankhah_add"], permissions["factor_add"])
        elif level == 4:
            user.user_permissions.add(permissions["tankhah_add"])
        elif level == 5:
            user.user_permissions.add(permissions["tankhah_add"])

        print(f"\nTesting access for Level {level}:")
        for view_name, url in urls.items():
            response = client.get(url)
            if view_name in allowed_views:
                assert response.status_code == 200, f"Level {level} should access {view_name}, got {response.status_code}"
                print(f"  ✅ Level {level} can access {view_name}")
            else:
                assert response.status_code in [403, 302], f"Level {level} should not access {view_name}, got {response.status_code}"
                print(f"  ❌ Level {level} cannot access {view_name} (as expected)")

        client.logout()

# تست سلسله‌مراتب درختی
@pytest.mark.django_db
def test_hierarchy_access(client, users_with_levels, complex_organization):
    """
    تست دسترسی کاربران به داده‌های سلسله‌مراتب درختی
    """
    posts = []
    current_parent = None
    for level in range(1, 8):
        post = PostFactory(organization=complex_organization, level=level, parent=current_parent)
        posts.append(post)
        current_parent = post

    # به‌روزرسانی پست کاربران
    for level, user in enumerate(users_with_levels[1:], 1):  # از سطح 1 شروع می‌کنیم
        UserPost.objects.filter(user=user).delete()
        UserPostFactory(user=user, post=posts[level - 1])

    # تست دسترسی به لیست پست‌ها (فرض می‌کنیم post_list دارید)
    for level, user in enumerate(users_with_levels):
        client.force_login(user)
        response = client.get(reverse("post_list"))  # فرض می‌کنیم URL وجود داره
        if level == 0:  # سوپروایزر همه رو می‌بینه
            for post in posts:
                assert post.name in str(response.content), f"Level 0 should see {post.name}"
        elif level <= 6:  # هر سطح فقط خودش و پایین‌ترها رو می‌بینه
            for post_level, post in enumerate(posts, 1):
                if post_level >= level:
                    assert post.name in str(response.content), f"Level {level} should see {post.name}"
                else:
                    assert post.name not in str(response.content), f"Level {level} should not see {post.name}"
        else:  # سطح 7 فقط خودش
            assert posts[6].name in str(response.content), "Level 7 should see only its own post"
            for post in posts[:-1]:
                assert post.name not in str(response.content), f"Level 7 should not see {post.name}"
        client.logout()