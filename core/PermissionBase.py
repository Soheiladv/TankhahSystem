
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
    """
    permission_codename = []          # لیست مجوزهای مورد نیاز
    check_organization = False       # آیا فیلتر سازمانی اعمال شود؟
    organization_filter_field = 'organization__id__in'

    def get_user_active_organizations(self, user):
        """بازگرداندن لیست ID سازمان‌هایی که کاربر دسترسی دارد"""
        from .models import UserPost

        active_posts = UserPost.objects.filter(user=user, is_active=True, post__is_active=True)
        org_ids = set()
        for up in active_posts:
            org = getattr(up.post, 'organization', None)
            if org:
                org_ids.add(org.id)
                # اگر دفتر مرکزی است، شعبات زیرمجموعه هم اضافه شوند
                if getattr(org, 'is_core', False):
                    org_ids.update([d.id for d in org.sub_organizations.filter(is_active=True)])
        return list(org_ids)

    def has_required_permissions(self, user):
        """بررسی اینکه کاربر حداقل یکی از پرمیژن‌های مورد نیاز را دارد"""
        if user.is_superuser:
            return True

        perms_to_check = self.permission_codename
        if isinstance(perms_to_check, str):
            perms_to_check = [perms_to_check]

        if not perms_to_check:
            logger.warning(f"No permission_codename defined for {self.__class__.__name__}")
            return False

        # پرمیژن‌های کاربر و فقط بخش بعد از نقطه
        user_perms_short = {p.split('.')[-1].lower() for p in user.get_all_permissions()}
        perms_to_check_short = {p.split('.')[-1].lower() for p in perms_to_check}

        has_perm = any(p in user_perms_short for p in perms_to_check_short)
        logger.info(f"[PERM_CHECK] User: {user.username}, has_required_permissions: {has_perm}")
        return has_perm

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            logger.warning(f"Unauthorized access attempt by anonymous user to {request.path}.")
            return redirect('login')

        if not self.has_required_permissions(user):
            logger.error(f"Permission denied for user {user.username}")
            raise PermissionDenied(_("You do not have permission to access this page."))

        if self.check_organization:
            user_orgs = self.get_user_active_organizations(user)
            logger.info(f"[PERM_CHECK] User {user.username} active orgs: {user_orgs}")

        return super().dispatch(request, *args, **kwargs)


def check_permission_and_organization(permissions=None, check_org=False, model=None):
    """
    Decorator برای چک کردن permission و سازمان روی یک object
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect('login')

            # نرمال‌سازی لیست پرمیژن‌ها
            perms_to_check = [permissions] if isinstance(permissions, str) else (permissions or [])
            norm_perms = []
            for perm in perms_to_check:
                p = perm.lower()
                if '.' not in p and model:
                    app_label = getattr(getattr(model, '_meta', None), 'app_label', '')
                    if app_label:
                        p = f"{app_label}.{p}"
                norm_perms.append(p)

            # چک پرمیژن‌ها
            user_perms = {p.lower() for p in user.get_all_permissions()}
            if not user.is_superuser and norm_perms and not any(p in user_perms for p in norm_perms):
                raise PermissionDenied(_("You do not have permission to perform this action."))

            # چک سازمانی روی object
            if check_org and model:
                from core.models import UserPost, Organization
                user_orgs = set(UserPost.objects.filter(user=user, is_active=True)
                                .values_list('post__organization_id', flat=True))
                # شامل زیرمجموعه‌های دفتر مرکزی
                central_orgs = Organization.objects.filter(id__in=user_orgs, is_core=True, is_active=True)
                for org in central_orgs:
                    user_orgs.update([d.id for d in org.sub_organizations.filter(is_active=True)])

                obj_id = kwargs.get('pk') or kwargs.get('id')
                if obj_id:
                    obj = get_object_or_404(model, pk=obj_id)
                    obj_org_id = getattr(getattr(obj, 'organization', None), 'id', None) or \
                                 getattr(getattr(getattr(obj, 'tankhah', None), 'organization', None), 'id', None)
                    if obj_org_id and obj_org_id not in user_orgs:
                        raise PermissionDenied(_("You do not have permission to access objects from this organization."))

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class _PermissionBaseView(View):
    """
    کلاس پایه برای مدیریت دسترسی کاربران به ویوها و اعمال فیلتر سازمانی.
    - بررسی مجوزها بر اساس permission_codenames
    - اعمال فیلتر سازمانی بر اساس UserPost → Post → Organization → is_core
    - اجازه دسترسی کامل به سوپر یوزر، ادمین و سرپرایزر
    
    ⚠️  توجه: این کلاس با PermissionBaseView تداخل دارد. 
    پیشنهاد می‌شود فقط یکی از این دو کلاس استفاده شود.
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
            from django.db import models
            return models.QuerySet().none()

        queryset = model._default_manager.all()

        # 🔹 اگر سوپر یوزر است → همه داده‌ها بدون فیلتر
        if user.is_superuser:
            logger.info(f"[PERM_CHECK] User {user.username} is superuser → full queryset access.")
            return queryset

        # گرفتن همه پست‌های فعال کاربر
        user_posts = UserPost.objects.filter(user=user, is_active=True).select_related('post__organization')
        user_orgs = set(up.post.organization for up in user_posts if up.post and up.post.organization)

        if not user_posts.exists():
            logger.warning(f"[PERM_CHECK] User {user.username} has no active posts.")
            return queryset.none()

        # اگر یکی از سازمان‌ها دفتر مرکزی بود → دسترسی کامل
        if any(org.is_core for org in user_orgs):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full access granted.")
            return queryset

        # اعمال فیلتر سازمانی
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
        active_posts = UserPost.objects.filter(
            user=user, is_active=True, post__is_active=True
        ).select_related('post__organization')
        active_orgs = [up.post.organization for up in active_posts if up.post and up.post.organization]

        # اگر سازمان دفتر مرکزی باشد → دسترسی کامل
        if any(org.is_core for org in active_orgs):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full access granted.")
            return True

        # بررسی مجوزها
        if isinstance(self.permission_codenames, str):
            perms_to_check = [self.permission_codenames]
        else:
            perms_to_check = self.permission_codenames

        # همه پرمیژن‌های کاربر
        user_perms = {p.lower() for p in user.get_all_permissions()}

        # نرمال‌سازی پرمیژن‌های موردنیاز
        norm_perms = []
        for perm in perms_to_check:
            p = perm.lower()
            if '.' not in p:  # اگر اپ‌نیم نیامده بود
                # اپ ویو فعلی را پیدا کن
                app_label = ''
                if hasattr(self, 'model') and self.model:
                    app_label = self.model._meta.app_label
                if app_label:
                    p = f"{app_label}.{p}"
            norm_perms.append(p)

        missing = [p for p in norm_perms if p not in user_perms]
        if missing:
            logger.warning(f"[PERM_CHECK] User {user.username} missing permissions: {missing}")

        return any(p in user_perms for p in norm_perms)

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

def _check_permission_and_organization(permissions, check_org=False):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                logger.warning(f"Unauthorized access attempt by anonymous user to {request.path}.")
                return redirect('login')

            # نرمال‌سازی لیست پرمیژن‌ها
            perms_to_check = [permissions] if isinstance(permissions, str) else permissions
            perms_to_check = [p.lower() for p in perms_to_check]

            # دسترسی کامل برای سوپر یوزر یا کاربران دفتر مرکزی
            from core.models import UserPost, Organization
            is_full_access = (
                user.is_superuser or
                UserPost.objects.filter(
                    user=user, is_active=True, post__is_active=True,
                    post__organization__is_core=True
                ).exists()
            )

            if not is_full_access:
                # همه پرمیژن‌های کاربر
                user_perms = {p.lower() for p in user.get_all_permissions()}

                # اگر اپ‌نیم داده نشده بود اضافه کن
                norm_perms = []
                for perm in perms_to_check:
                    if '.' not in perm:
                        # اگر ویو مدل دارد، اپ‌نیم همان مدل است
                        model_class = getattr(view_func, 'model', None)
                        app_label = ''
                        if model_class and hasattr(model_class, '_meta'):
                            app_label = model_class._meta.app_label
                        if app_label:
                            perm = f"{app_label}.{perm}"
                    norm_perms.append(perm)

                if not any(p in user_perms for p in norm_perms):
                    logger.warning(f"User {user.username} missing permissions: {norm_perms}")
                    raise PermissionDenied(_("You do not have permission to perform this action."))

            # بررسی سازمان‌ها مثل قبل...
            if check_org and not is_full_access:
                user_orgs = set(
                    UserPost.objects.filter(user=user, is_active=True)
                    .values_list('post__organization_id', flat=True)
                )
                central_orgs = Organization.objects.filter(id__in=user_orgs, is_core=True, is_active=True)
                all_orgs = set(user_orgs)
                for org in central_orgs:
                    descendants = org.sub_organizations.filter(is_active=True)
                    all_orgs.update([d.id for d in descendants])
                user_orgs = all_orgs

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

