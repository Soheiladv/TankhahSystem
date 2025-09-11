
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext_lazy as _
import logging
from functools import wraps

from core.models import Organization, UserPost

logger = logging.getLogger(__name__)
class PermissionBaseView(View):
    """
    کلاس پایه برای مدیریت دسترسی کاربران به ویوها و اعمال فیلتر سازمانی.
    - بررسی مجوزها بر اساس permission_codenames
    - اعمال فیلتر سازمانی بر اساس UserPost → Post → Organization → is_core
    - اجازه دسترسی کامل به سوپر یوزر، ادمین و سرپرایزر
    """
    permission_codenames = []           # لیست مجوزهای مورد نیاز
    check_organization = False          # آیا فیلتر سازمانی اعمال شود؟
    organization_filter_field = 'organization__id__in'  # فیلد سازمان برای فیلتر queryset

    def get_user_active_organizations(self, user):
        """بازگرداندن لیست id سازمان‌هایی که کاربر به آنها دسترسی دارد"""
        from .models import UserPost, Organization

        # همه پست‌های فعال کاربر
        active_posts = UserPost.objects.filter(user=user, is_active=True, post__is_active=True)

        org_ids = set()
        for up in active_posts:
            org = up.post.organization
            if org:
                org_ids.add(org.id)
                # اگر دفتر مرکزی است، شعبات زیرمجموعه هم اضافه شوند
                if org.is_core:
                    descendants = org.sub_organizations.filter(is_active=True)
                    org_ids.update(desc.id for desc in descendants)

        logger.info(f"[PERM_CHECK] User {user.username} active orgs: {list(org_ids)}")
        return list(org_ids)

    def get_queryset(self):
        user = self.request.user
        model = getattr(self, 'model', None)
        if not model:
            logger.warning("Model not defined in PermissionBaseView.")
            return model.objects.none()  # یا None

        queryset = model._default_manager.all()

        # گرفتن همه پست‌های فعال کاربر
        user_posts = UserPost.objects.filter(user=user, is_active=True).select_related('post__organization')
        user_orgs = set(up.post.organization for up in user_posts if up.post and up.post.organization)

        # اگر کاربر هیچ پست فعالی ندارد → دسترسی ندارد
        if not user_posts.exists():
            logger.warning(f"[PERM_CHECK] User {user.username} has no active posts.")
            return queryset.none()

        # اگر کاربر هر کدام از پست‌هایش دفتر مرکزی باشد → دسترسی کامل
        if any(org.is_core for org in user_orgs):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full access granted.")
            return queryset

        # اعمال فیلتر سازمانی برای کاربران عادی
        if self.check_organization:
            org_ids = [org.id for org in user_orgs]
            if not org_ids:
                logger.warning(f"[PERM_CHECK] User {user.username} has no accessible organizations.")
                return queryset.none()
            queryset = queryset.filter(**{self.organization_filter_field: org_ids})
            logger.info(f"[PERM_CHECK] User {user.username} queryset filtered by orgs: {org_ids}")

        return queryset

    def has_required_permissions(self, user):
        # سوپر یوزر همیشه دسترسی کامل
        if user.is_superuser:
            return True

        # گرفتن سازمان‌های فعال کاربر
        active_posts = UserPost.objects.filter(user=user, is_active=True, post__is_active=True).select_related(
            'post__organization')
        active_orgs = [up.post.organization for up in active_posts if up.post and up.post.organization]

        # اگر سازمان دفتر مرکزی باشد → دسترسی کامل
        if any(org.is_core for org in active_orgs):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full access granted.")
            return True

        # بررسی مجوزهای معمول
        if isinstance(self.permission_codenames, str):
            perms_to_check = [self.permission_codenames]
        else:
            perms_to_check = self.permission_codenames

        user_perms = user.get_all_permissions()
        missing = [p for p in perms_to_check if p not in user_perms]
        if missing:
            logger.warning(f"[PERM_CHECK] User {user.username} missing permissions: {missing}")

        return any(perm in user_perms for perm in perms_to_check)

    def dispatch(self, request, *args, **kwargs):
        """کنترل دسترسی قبل از اجرای ویو"""
        user = request.user
        if not user.is_authenticated:
            logger.warning(f"Unauthorized access attempt by anonymous user to {request.path}.")
            return redirect('login')

        if not self.has_required_permissions(user):
            messages.error(request, _("You do not have permission to access this page."))
            raise PermissionDenied(_("You do not have permission to access this page."))

        logger.info(f"[PERM_CHECK] User {user.username} passed permission check for {request.path}.")
        return super().dispatch(request, *args, **kwargs)
def check_permission_and_organization(permissions, check_org=False):
    """
    Decorator برای بررسی مجوزها و فیلتر سازمانی به صورت داینامیک.
    - مجوزها را با user.has_perm بررسی می‌کند
    - شعبات زیرمجموعه دفتر مرکزی را به صورت داینامیک اضافه می‌کند
    - ادمین، سرپرایزر و سوپر یوزر دسترسی کامل دارند
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                logger.warning(f"Unauthorized access attempt by anonymous user to {request.path}.")
                return redirect('login')

            # اطمینان از اینکه permissions لیست است
            perms_to_check = [permissions] if isinstance(permissions, str) else permissions

            # دسترسی کامل برای سوپر یوزر یا کاربران با نقش ادمین/سرپرایزر
                       # بررسی دسترسی کامل
            from core.models import UserPost
            is_full_access = (
                    user.is_superuser or
                    UserPost.objects.filter(user=user, is_active=True, post__is_active=True,
                                            post__organization__is_core=True).exists()
            )

            if is_full_access:
                logger.info(f"[PERM_CHECK] User {user.username} is admin/supervisor → full access granted.")
            else:
                # بررسی مجوزها
                if not any(user.has_perm(perm) for perm in perms_to_check):
                    logger.warning(f"User {user.username} is missing permissions: {perms_to_check}")
                    raise PermissionDenied(_("You do not have permission to perform this action."))

            # بررسی سازمان‌ها در صورت فعال بودن check_org
            if check_org and not is_full_access:
                from .models import UserPost, Organization

                # سازمان‌های فعال کاربر
                user_orgs = set(
                    UserPost.objects.filter(user=user, is_active=True)
                    .values_list('post__organization_id', flat=True)
                )

                # اضافه کردن زیرمجموعه‌ها اگر دفتر مرکزی باشد
                central_orgs = Organization.objects.filter(id__in=user_orgs, is_core=True, is_active=True)
                all_orgs = set(user_orgs)
                for org in central_orgs:
                    descendants = org.sub_organizations.filter(is_active=True)
                    all_orgs.update([d.id for d in descendants])
                user_orgs = all_orgs

                # بررسی سازمان شیء موردنظر (اگر pk/id موجود باشد)
                obj_id = kwargs.get('pk') or kwargs.get('id')
                model_class = getattr(view_func, 'model', None)
                if obj_id and model_class:
                    obj = get_object_or_404(model_class, pk=obj_id)
                    obj_org_id = None

                    if hasattr(obj, 'organization') and obj.organization:
                        obj_org_id = obj.organization.id
                    elif hasattr(obj, 'tankhah') and hasattr(obj.tankhah, 'organization'):
                        obj_org_id = obj.tankhah.organization.id

                    if obj_org_id and obj_org_id not in user_orgs:
                        logger.warning(f"User {user.username} tried to access org {obj_org_id} without permission.")
                        raise PermissionDenied(_("You do not have permission to access objects from this organization."))

                logger.info(f"[PERM_CHECK] User {user.username} has access to orgs: {user_orgs}")

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator

