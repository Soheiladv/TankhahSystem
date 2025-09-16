
"""
سیستم دسترسی بهینه برای BudgetsSystem
موتور تایید دسترسی کاربران بر اساس پریمیژن‌ها، رول‌ها و دسترسی سازمانی

ویژگی‌ها:
- بررسی پریمیژن‌ها و رول‌های سیستم
- کنترل دسترسی سازمانی (دفتر مرکزی → همه شعبات، شعبه → فقط خودش)
- چک دسترسی در هر درخواست ویو
- لاگ‌گذاری کامل و شفاف
- عملکرد بهینه و قابل نگهداری
"""

from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
import logging
from functools import wraps
from typing import List, Union, Optional, Set

from core.models import Organization, UserPost

logger = logging.getLogger(__name__)


class PermissionBaseView(View):
    """
    کلاس پایه بهینه برای مدیریت دسترسی کاربران
    
    ویژگی‌ها:
    - بررسی مجوزها بر اساس permission_codename
    - اعمال فیلتر سازمانی بر اساس UserPost → Post → Organization → is_core
    - اجازه دسترسی کامل به سوپر یوزر و کاربران دفتر مرکزی
    - لاگ‌گذاری کامل و شفاف
    - عملکرد بهینه
    """
    
    # تنظیمات دسترسی
    permission_codename: Union[str, List[str]] = []  # مجوزهای مورد نیاز
    check_organization: bool = False  # آیا فیلتر سازمانی اعمال شود؟
    organization_filter_field: str = 'organization__id__in'  # فیلد سازمان برای فیلتر
    
    # تنظیمات پیام‌ها
    permission_denied_message: str = _("شما دسترسی لازم برای مشاهده این صفحه را ندارید.")
    login_required_message: str = _("لطفاً ابتدا وارد سیستم شوید.")
    
    def get_user_active_organizations(self, user) -> List[int]:
        """
        بازگرداندن لیست ID سازمان‌هایی که کاربر دسترسی دارد
        
        منطق:
        - کاربران دفتر مرکزی: دسترسی به همه سازمان‌ها
        - کاربران شعبات: دسترسی فقط به سازمان خودشان
        """
        if user.is_superuser:
            return list(Organization.objects.filter(is_active=True).values_list('id', flat=True))
        
        active_posts = UserPost.objects.filter(
            user=user, 
            is_active=True, 
            post__is_active=True
        ).select_related('post__organization')
        
        org_ids = set()
        has_core_access = False
        
        for up in active_posts:
            org = up.post.organization
            if org and org.is_active:
                org_ids.add(org.id)
                
                # اگر دفتر مرکزی است، دسترسی کامل
                if org.is_core:
                    has_core_access = True
                    # اضافه کردن همه سازمان‌های فعال
                    all_orgs = Organization.objects.filter(is_active=True).values_list('id', flat=True)
                    org_ids.update(all_orgs)
                    break
                else:
                    # اگر شعبه است، زیرمجموعه‌هایش را هم اضافه کن
                    if org.parent_organization and org.parent_organization.is_core:
                        org_ids.add(org.parent_organization.id)
        
        logger.info(f"[PERM_CHECK] User {user.username} active orgs: {list(org_ids)} (has_core: {has_core_access})")
        return list(org_ids)
    
    def has_required_permissions(self, user) -> bool:
        """
        بررسی اینکه کاربر حداقل یکی از مجوزهای مورد نیاز را دارد
        
        منطق:
        1. سوپر یوزر: دسترسی کامل
        2. کاربران دفتر مرکزی: دسترسی کامل (بر اساس پریمیژن)
        3. کاربران عادی: بررسی پریمیژن‌های خاص
        """
        if user.is_superuser:
            logger.info(f"[PERM_CHECK] User {user.username} is superuser → full access granted.")
            return True
        
        # بررسی دسترسی دفتر مرکزی
        if self._user_has_core_access(user):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full access granted.")
            return True
        
        # بررسی پریمیژن‌های خاص
        perms_to_check = self.permission_codename
        if isinstance(perms_to_check, str):
            perms_to_check = [perms_to_check]
        
        if not perms_to_check:
            logger.warning(f"[PERM_CHECK] No permission_codename defined for {self.__class__.__name__}")
            return False
        
        # نرمال‌سازی پریمیژن‌ها
        normalized_perms = self._normalize_permissions(perms_to_check)
        
        # بررسی پریمیژن‌های کاربر
        user_perms = {p.lower() for p in user.get_all_permissions()}
        has_perm = any(p.lower() in user_perms for p in normalized_perms)
        
        if has_perm:
            logger.info(f"[PERM_CHECK] User {user.username} has required permissions: {normalized_perms}")
        else:
            logger.warning(f"[PERM_CHECK] User {user.username} missing permissions: {normalized_perms}")
        
        return has_perm
    
    def _user_has_core_access(self, user) -> bool:
        """بررسی دسترسی کاربر به دفتر مرکزی"""
        return UserPost.objects.filter(
            user=user,
            is_active=True,
            post__is_active=True,
            post__organization__is_core=True
        ).exists()
    
    def _normalize_permissions(self, permissions: List[str]) -> List[str]:
        """نرمال‌سازی پریمیژن‌ها (اضافه کردن app_label اگر لازم باشد)"""
        normalized = []
        for perm in permissions:
            if '.' not in perm:
                # اگر app_label نداره، از مدل ویو بگیر
                app_label = self._get_app_label_from_view()
                if app_label:
                    perm = f"{app_label}.{perm}"
            normalized.append(perm)
        return normalized
    
    def _get_app_label_from_view(self) -> Optional[str]:
        """دریافت app_label از مدل ویو"""
        if hasattr(self, 'model') and self.model:
            return self.model._meta.app_label
        return None
    
    def get_queryset(self):
        """
        بازگرداندن queryset با اعمال فیلتر سازمانی
        
        منطق:
        - سوپر یوزر: همه داده‌ها
        - کاربران دفتر مرکزی: همه داده‌ها
        - کاربران شعبات: فقط داده‌های سازمان خودشان
        """
        user = self.request.user
        model = getattr(self, 'model', None)
        
        if not model:
            logger.warning(f"[PERM_CHECK] Model not defined in {self.__class__.__name__}")
            from django.db import models
            return models.QuerySet().none()
        
        queryset = model._default_manager.all()
        
        # سوپر یوزر: دسترسی کامل
        if user.is_superuser:
            logger.info(f"[PERM_CHECK] User {user.username} is superuser → full queryset access.")
            return queryset
        
        # کاربران دفتر مرکزی: دسترسی کامل
        if self._user_has_core_access(user):
            logger.info(f"[PERM_CHECK] User {user.username} has core organization → full queryset access.")
            return queryset
        
        # اعمال فیلتر سازمانی
        if self.check_organization:
            user_orgs = self.get_user_active_organizations(user)
            if not user_orgs:
                logger.warning(f"[PERM_CHECK] User {user.username} has no accessible organizations.")
                return queryset.none()
            
            queryset = queryset.filter(**{self.organization_filter_field: user_orgs})
            logger.info(f"[PERM_CHECK] User {user.username} queryset filtered by orgs: {user_orgs}")
        
        return queryset
    
    def dispatch(self, request, *args, **kwargs):
        """
        کنترل دسترسی قبل از اجرای ویو
        
        مراحل:
        1. بررسی احراز هویت
        2. بررسی مجوزها
        3. اجرای ویو اصلی
        """
        user = request.user
        
        # 1. بررسی احراز هویت
        if not user.is_authenticated:
            logger.warning(f"[PERM_CHECK] Unauthorized access attempt by anonymous user to {request.path}")
            messages.error(request, self.login_required_message)
            return redirect('login')
        
        # 2. بررسی مجوزها
        if not self.has_required_permissions(user):
            logger.error(f"[PERM_CHECK] Permission denied for user {user.username} to {request.path}")
            messages.error(request, self.permission_denied_message)
            raise PermissionDenied(self.permission_denied_message)
        
        logger.info(f"[PERM_CHECK] User {user.username} passed permission check for {request.path}")
        return super().dispatch(request, *args, **kwargs)


def check_permission_and_organization(permissions: Union[str, List[str]] = None, 
                                    check_org: bool = False, 
                                    model=None):
    """
    Decorator برای چک کردن permission و سازمان روی یک object
    
    Args:
        permissions: مجوزهای مورد نیاز
        check_org: آیا چک سازمانی انجام شود؟
        model: مدل برای چک سازمانی
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # بررسی احراز هویت
            if not user.is_authenticated:
                logger.warning(f"[PERM_CHECK] Unauthorized access attempt by anonymous user to {request.path}")
                return redirect('login')
            
            # بررسی مجوزها
            if permissions:
                perms_to_check = [permissions] if isinstance(permissions, str) else permissions
                normalized_perms = []
                
                for perm in perms_to_check:
                    p = perm.lower()
                    if '.' not in p and model:
                        app_label = getattr(getattr(model, '_meta', None), 'app_label', '')
                        if app_label:
                            p = f"{app_label}.{p}"
                    normalized_perms.append(p)
                
                # بررسی دسترسی کامل (سوپر یوزر یا دفتر مرکزی)
                has_full_access = (
                    user.is_superuser or
                    UserPost.objects.filter(
                        user=user, is_active=True, post__is_active=True,
                        post__organization__is_core=True
                    ).exists()
                )
                
                if not has_full_access:
                    user_perms = {p.lower() for p in user.get_all_permissions()}
                    if not any(p in user_perms for p in normalized_perms):
                        logger.warning(f"[PERM_CHECK] User {user.username} missing permissions: {normalized_perms}")
                        raise PermissionDenied(_("You do not have permission to perform this action."))
            
            # بررسی دسترسی سازمانی
            if check_org and model and not user.is_superuser:
                user_orgs = set(
                    UserPost.objects.filter(user=user, is_active=True)
                    .values_list('post__organization_id', flat=True)
                )
                
                # اضافه کردن سازمان‌های زیرمجموعه دفتر مرکزی
                central_orgs = Organization.objects.filter(id__in=user_orgs, is_core=True, is_active=True)
                for org in central_orgs:
                    user_orgs.update([d.id for d in org.sub_organizations.filter(is_active=True)])
                
                obj_id = kwargs.get('pk') or kwargs.get('id')
                if obj_id:
                    obj = get_object_or_404(model, pk=obj_id)
                    obj_org_id = (
                        getattr(getattr(obj, 'organization', None), 'id', None) or
                        getattr(getattr(getattr(obj, 'tankhah', None), 'organization', None), 'id', None)
                    )
                    
                    if obj_org_id and obj_org_id not in user_orgs:
                        logger.warning(f"[PERM_CHECK] User {user.username} tried to access org {obj_org_id} without permission")
                        raise PermissionDenied(_("You do not have permission to access objects from this organization."))
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

