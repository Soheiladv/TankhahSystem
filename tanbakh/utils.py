from django.core.exceptions import PermissionDenied
def restrict_to_user_organization(user, obj_organization):
    """چک می‌کند که آیا کاربر به سازمان شیء دسترسی دارد یا در دفتر مرکزی است."""
    user_orgs = [up.post.organization for up in user.userpost_set.all()]
    is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
    if not is_hq_user and obj_organization not in user_orgs:
        raise PermissionDenied("شما به این اطلاعات دسترسی ندارید.")
    return True

