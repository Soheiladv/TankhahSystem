import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import redirect
from django.contrib import messages

from tanbakh.models import Factor

logger = logging.getLogger(__name__)

def check_permission_and_organization(permissions, check_org=False):
    """
    Decorator for checking permissions and organization access.
    `permissions` can be a string or list of permission codenames.
    """
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            logger.info(f"Checking permissions for user: {request.user}")
            if request.user.is_superuser:
                logger.info("User is superuser. Access granted.")
                return view_func(request, *args, **kwargs)

            # Handle single or multiple permissions
            perms_to_check = [permissions] if isinstance(permissions, str) else permissions
            for perm in perms_to_check:
                user_groups = request.user.groups.all()
                logger.info(f"User groups: {[group.name for group in user_groups]}")
                has_perm = False
                for group in user_groups:
                    group_roles = group.roles.all()
                    logger.info(f"Group {group.name} roles: {[role.name for role in group_roles]}")
                    for role in group_roles:
                        if role.permissions.filter(codename=perm.split('.')[-1]).exists():
                            logger.info(f"Permission {perm} found in role {role.name}. Access granted.")
                            has_perm = True
                            break
                    if has_perm:
                        break
                if not has_perm:
                    logger.warning(f"Access denied for user: {request.user} to permission: {perm}")
                    messages.warning(request, "شما اجازه دسترسی به این بخش را ندارید.")
                    raise PermissionDenied("شما اجازه دسترسی به این صفحه را ندارید.")

            # Check organization if required and applicable
            if check_org and 'pk' in kwargs:
                try:
                    factor = Factor.objects.get(pk=kwargs['pk'])
                    user_orgs = [up.post.organization for up in request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
                    is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
                    if not is_hq_user and factor.tanbakh.project.organization not in user_orgs:
                        logger.warning(f"User {request.user} has no access to organization {factor.tanbakh.project.organization}")
                        messages.warning(request, "شما به این سازمان دسترسی ندارید.")
                        raise PermissionDenied("شما به این سازمان دسترسی ندارید.")
                except Factor.DoesNotExist:
                    logger.warning(f"Factor with pk {kwargs['pk']} not found")
                    messages.warning(request, "فاکتور یافت نشد.")
                    raise PermissionDenied("فاکتور یافت نشد.")

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

class PermissionBaseView(LoginRequiredMixin, View):
    """
    Base class for CBVs with permission and organization checks.
    Use `permission_codenames` for multiple permissions.

    کلاس پایه برای ویوهای کلاس‌محور با چک مجوز و سازمان.
    """
    permission_codenames = []
    check_organization = False  # فعال‌سازی چک سازمان

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"Checking permissions for user: {request.user}")
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("User is superuser. Access granted.")
            return super().dispatch(request, *args, **kwargs)

        # Check each permission
        for perm in self.permission_codenames:
            if not request.user.has_perm(perm):
                user_groups = request.user.groups.all()
                logger.info(f"User groups: {[group.name for group in user_groups]}")
                has_perm = False
                for group in user_groups:
                    group_roles = group.roles.all()
                    logger.info(f"Group {group.name} roles: {[role.name for role in group_roles]}")
                    for role in group_roles:
                        if role.permissions.filter(codename=perm.split('.')[-1]).exists():
                            logger.info(f"Permission {perm} found in role {role.name}. Access granted.")
                            has_perm = True
                            break
                    if has_perm:
                        break
                if not has_perm:
                    if self.check_organization and hasattr(self, 'get_object'):
                        try:
                            obj = self.get_object()
                            user_orgs = [up.post.organization for up in request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
                            is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
                            if not is_hq_user and getattr(obj, 'tanbakh', None) and getattr(obj.tanbakh, 'project', None) and getattr(obj.tanbakh.project, 'organization', None):
                                if obj.tanbakh.project.organization not in user_orgs:
                                    logger.warning(f"User {request.user} has no access to organization {obj.tanbakh.project.organization}")
                                    messages.warning(request, "شما به این سازمان دسترسی ندارید.")
                                    raise PermissionDenied("شما به این سازمان دسترسی ندارید.")
                        except AttributeError:
                            logger.warning(f"Organization check failed for object {obj}")
                            messages.warning(request, "خطا در بررسی دسترسی سازمان.")
                            raise PermissionDenied("خطا در بررسی دسترسی سازمان.")
                    logger.warning(f"Access denied for user: {request.user} to permission: {perm}")
                    return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def handle_no_permission(self):
        messages.warning(self.request, "شما اجازه دسترسی به این بخش را ندارید.")
        return redirect('factor_list')


"""1. برای ویوهای تابع‌محور:"""
# @check_permission_and_organization('tanbakh.a_factor_view', check_org=True)
# def factor_detail_view(request, pk):
#     factor = Factor.objects.get(pk=pk)
#     # ادامه منطق...

"""2. برای ویوهای کلاس‌محور:"""
# from django.utils.decorators import method_decorator
# class FactorDetailView(PermissionBaseView, UpdateView):
#     model = Factor
#     form_class = FactorForm
#     template_name = 'tanbakh/factor_detail.html'
#     context_object_name = 'factor'
#     permission_codename = 'tanbakh.a_factor_view'
#     check_organization = True  # فعال کردن چک سازمان
#     success_url = reverse_lazy('factor_list')
#
#     def get_form_kwargs(self):
#         kwargs = super().get_form_kwargs()
#         kwargs['user'] = self.request.user
#         return kwargs
