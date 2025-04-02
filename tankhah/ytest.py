from django.utils import timezone

from tankhah.models import Factor, Tankhah, WorkflowStage
from core.models import UserPost, Post, Organization
from django.contrib.auth import get_user_model
User = get_user_model()
from accounts.models import CustomUser
# from time import timezone
from core.PermissionBase import get_lowest_access_level, get_initial_stage_order
user = CustomUser.objects.get(username='Snejate')
org = Organization.objects.get(name='هتل بین المللی لاله سرعین')
initial_stage = WorkflowStage.objects.order_by('-order').first()
tankhah = Tankhah.objects.create(
        organization=org,
        amount=1000000,
        status='DRAFT',
        description='تست حذف',
        created_by=user,
        current_stage=initial_stage
    )
factor = Factor.objects.create(
        tankhah=tankhah,
        date=timezone.now().date(),
        amount=500000,
        description='فاکتور تست',
        status='REJECTED'
    )
    # مطمئن شو سطح کاربر پایین‌ترین باشه
post = Post.objects.create(name='کارمند پایین‌ترین سطح', organization=org, level=get_lowest_access_level())
UserPost.objects.get_or_create(user=user, post=post)
print(f"فاکتور: {factor.number}, وضعیت: {factor.status}, مرحله: {factor.tankhah.current_stage.order}")
print(f"سازمان‌های کاربر: {[up.post.organization for up in user.userpost_set.all()]}")
print(f"سطح کاربر: {user.userpost_set.first().post.level}")
print(f"پایین‌ترین سطح: {get_lowest_access_level()}")
print(f"مرحله اولیه: {get_initial_stage_order()}")



# >>> post = Post.objects.create(name='کارمند پایین‌ترین سطح', organization=org, level=get_lowest_access_level())
# >>> UserPost.objects.get_or_create(user=user, post=post)
# (<UserPost: Snejate - کارمند پایین‌ترین سطح (از 2025-04-01 07:41:24.569809+00:00)>, True)
# >>> print(f"فاکتور: {factor.number}, وضعیت: {factor.status}, مرحله: {factor.tankhah.current_stage.order}")
# فاکتور: TNKH-14040112-HOTELS-Ard-NOPRJ-001-F1, وضعیت: REJECTED, مرحله: 5
# >>> print(f"سازمان‌های کاربر: {[up.post.organization for up in user.userpost_set.all()]}")
# سازمان‌های کاربر: [<Organization: HOTELS-Ard - هتل بین المللی لاله سرعین (COMPLEX)>, <Organization: HOTELS-Ard - هتل بین المللی لاله سرعین (COMPLEX)>]
# >>> print(f"سطح کاربر: {user.userpost_set.first().post.level}")
# سطح کاربر: 5
# >>> print(f"پایین‌ترین سطح: {get_lowest_access_level()}")
# پایین‌ترین سطح: 6
# >>> print(f"مرحله اولیه: {get_initial_stage_order()}")
# مرحله اولیه: 5
# >>>