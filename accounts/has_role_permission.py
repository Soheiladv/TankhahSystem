import logging
logger = logging.getLogger(__name__)

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def has_permission(permission_codename):
    def decorator(view_func):
        @login_required  # اضافه کردن اجبار ورود در سطح دکوراتور
        def _wrapped_view(request, *args, **kwargs):
            # logger.info(f"Checking permissions for user: {request.user}")
            if request.user.is_superuser:
                # logger.info("User is superuser. Access granted.")
                return view_func(request, *args, **kwargs)
                # بررسی گروه‌های کاربر
            user_groups = request.user.groups.all()
            # logger.info(f"User groups: {[group.name for group in user_groups]}")

            for group in user_groups:
                # بررسی نقش‌های هر گروه
                group_roles = group.roles.all()
                # logger.info(f"Group {group.name} roles: {[role.name for role in group_roles]}")

                for role in group_roles:
                    logger.info(f"Checking role: {role.name}")
                    if role.permissions.filter(codename=permission_codename).exists():
                        logger.warning(f"Permission {permission_codename} found👍in role {role.name} of group {group.name}. Access granted.👍")
                        return view_func(request, *args, **kwargs)

                        # فقط WARNING و هدایت
                    logger.warning(f"Access denied for 😒user: {request.user} to permission: {permission_codename}👎")
                    from django.contrib import messages

                    logger.warning(f"Access denied for 😒user: {request.user} to permission: {permission_codename}👎")
                    messages.warning(request, "شما اجازه دسترسی به این بخش را ندارید.")
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("شما اجازه دسترسی به این صفحه را ندارید.")  # به handler403 می‌رود

        return _wrapped_view
    return decorator



    #         for role in request.user.roles.all():  # مستقیم به نقش‌های کاربر دسترسی پیدا می‌کنیم
    #             logger.info(f"Checking role: {role.name}")  # نمایش نام نقش در لاگ
    #             if role.permissions.filter(codename=permission_codename).exists():
    #                 logger.info(f"Permission {permission_codename} found for role {role.name}. Access granted.")
    #                 return view_func(request, *args, **kwargs)
    #
    #         logger.error(f"Permission denied for user: {request.user}")
    #         raise PermissionDenied("شما اجازه دسترسی به این صفحه را ندارید.")
    #
    #     return _wrapped_view
    #
    # return decorator

