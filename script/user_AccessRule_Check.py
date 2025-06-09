# اسکریپت دیباگ برای بررسی قوانین دسترسی
# در Django shell اجرا کنید: python manage.py shell
from accounts.models import CustomUser
from tankhah.models import AccessRule,  WorkflowStage
from core.models import UserPost


def debug_access_rules(username="snejate"):
    """
    بررسی قوانین دسترسی برای کاربر مشخص
    """
    user = CustomUser.objects.get(username=username)
    user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()

    if not user_post:
        print(f"❌ کاربر {username} هیچ پست فعالی ندارد")
        return

    print(f"👤 کاربر: {user.get_full_name()} ({username})")
    print(f"📋 پست: {user_post.post}")
    print(f"🏢 سازمان: {user_post.post.organization}")
    print(f"📊 سطح: {user_post.post.level}")
    print(f"🌿 شعبه: {user_post.post.branch or 'هیچ'}")
    print(f"🔧 HQ: {getattr(user, 'is_hq', False)}")
    print(f"🏛️ Core Org: {user_post.post.organization.is_core}")
    print("-" * 50)

    # بررسی تمام مراحل
    stages = WorkflowStage.objects.all().order_by('order')

    for stage in stages:
        print(f"\n📋 مرحله: {stage.name} (order: {stage.order})")

        # قوانین دسترسی برای این مرحله
        rules = AccessRule.objects.filter(
            organization=user_post.post.organization,
            stage=stage,
            is_active=True
        )

        if not rules.exists():
            print("   ❌ هیچ قانون فعالی وجود ندارد")
            continue

        for rule in rules:
            accessible = rule.min_level <= user_post.post.level
            status = "✅" if accessible else "❌"
            print(f"   {status} {rule.action_type} - {rule.entity_type} (min_level: {rule.min_level})")

    print("\n" + "=" * 50)
    print("بررسی قوانین مخصوص FACTORITEM:")

    factoritem_rules = AccessRule.objects.filter(
        organization=user_post.post.organization,
        entity_type='FACTORITEM',
        is_active=True
    ).order_by('stage__order')

    if factoritem_rules.exists():
        for rule in factoritem_rules:
            accessible = rule.min_level <= user_post.post.level
            status = "✅" if accessible else "❌"
            print(f"{status} {rule.stage.name} - {rule.action_type} (min_level: {rule.min_level})")
    else:
        print("❌ هیچ قانون FACTORITEM یافت نشد")


# اجرای دیباگ
debug_access_rules("snejate")