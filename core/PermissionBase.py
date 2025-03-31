import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View
from django.shortcuts import redirect
from django.contrib import messages

from tankhah.models import Factor

logger = logging.getLogger(__name__)

def check_permission_and_organization(permissions, check_org=False):
    """
    دکوراتور برای چک کردن مجوزها و دسترسی به سازمان.
    `permissions` می‌تونه یه رشته یا لیست از کدهای مجوز باشه.
    """
    def decorator(view_func):
        @login_required  # این خط مطمئن می‌شه کاربر لاگین کرده باشه
        def _wrapped_view(request, *args, **kwargs):
            logger.info(f"چک کردن مجوزها برای کاربر: {request.user}")
            # اگه کاربر سوپریوزر باشه، بدون چک کردن بقیه چیزا دسترسی می‌دم
            if request.user.is_superuser:
                logger.info("کاربر سوپریوزره. دسترسی داده شد.")
                return view_func(request, *args, **kwargs)

            # مجوزها رو مدیریت می‌کنه (اگه تک مجوز یا لیست باشه)
            perms_to_check = [permissions] if isinstance(permissions, str) else permissions
            for perm in perms_to_check:
                user_groups = request.user.groups.all()  # همه گروه‌های کاربر رو می‌گیره
                logger.info(f"گروه‌های کاربر: {[group.name for group in user_groups]}")
                has_perm = False  # پرچم برای اینکه بفهمیم مجوز داره یا نه
                for group in user_groups:
                    group_roles = group.roles.all()  # نقش‌های هر گروه رو می‌گیره
                    logger.info(f"نقش‌های گروه {group.name}: {[role.name for role in group_roles]}")
                    for role in group_roles:
                        # چک می‌کنه که آیا مجوز موردنظر توی نقش‌ها هست یا نه
                        if role.permissions.filter(codename=perm.split('.')[-1]).exists():
                            logger.info(f"مجوز {perm} توی نقش {role.name} پیدا شد. دسترسی داده شد.")
                            has_perm = True
                            break
                    if has_perm:
                        break
                # اگه هیچ مجوزی پیدا نشد، خطا می‌ده
                if not has_perm:
                    logger.warning(f"دسترسی برای کاربر {request.user} به مجوز {perm} رد شد")
                    messages.warning(request, "شما اجازه دسترسی به این بخش را ندارید.")
                    raise PermissionDenied("شما اجازه دسترسی به این صفحه را ندارید.")

            # اگه نیاز به چک سازمان باشه و pk توی kwargs باشه
            if check_org and 'pk' in kwargs:
                try:
                    factor = Factor.objects.get(pk=kwargs['pk'])  # فاکتور رو بر اساس pk پیدا می‌کنه
                    # سازمان‌هایی که کاربر بهشون دسترسی داره رو می‌گیره
                    user_orgs = [up.post.organization for up in request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
                    # چک می‌کنه کاربر دفتر مرکزی (HQ) هست یا نه
                    is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
                    # اگه کاربر HQ نباشه و سازمان فاکتور توی لیستش نباشه، خطا می‌ده
                    if not is_hq_user and factor.tanbakh.project.organization not in user_orgs:
                        logger.warning(f"کاربر {request.user} به سازمان {factor.tanbakh.project.organization} دسترسی نداره")
                        messages.warning(request, "شما به این سازمان دسترسی ندارید.")
                        raise PermissionDenied("شما به این سازمان دسترسی ندارید.")
                except Factor.DoesNotExist:
                    logger.warning(f"فاکتور با pk {kwargs['pk']} پیدا نشد")
                    messages.warning(request, "فاکتور یافت نشد.")
                    raise PermissionDenied("فاکتور یافت نشد.")

            return view_func(request, *args, **kwargs)  # اگه همه‌چیز اوکی بود، ویو اجرا می‌شه
        return _wrapped_view
    return decorator

import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger(__name__)

class PermissionBaseView(LoginRequiredMixin, View):
    """
    کلاس پایه برای ویوها با چک مجوز و سازمان.
    - permission_codenames: لیست مجوزهای موردنیاز (مثلاً ['app.view_factor'])
    - check_organization: آیا دسترسی به سازمان چک بشه یا نه
    """
    permission_codenames = []  # مجوزهای موردنیاز
    check_organization = False  # چک سازمان فعال باشه یا نه

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"چک کردن دسترسی برای کاربر: {request.user}")

        # اگه کاربر لاگین نکرده باشه، خطا می‌ده
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # اگه سوپریوزر باشه، مستقیم دسترسی می‌ده
        if request.user.is_superuser:
            logger.info("کاربر سوپریوزره. دسترسی داده شد.")
            return super().dispatch(request, *args, **kwargs)

        # چک مجوزها
        if self.permission_codenames:
            if not self._has_permissions(request.user):
                logger.warning(f"کاربر {request.user} مجوزهای لازم رو نداره: {self.permission_codenames}")
                return self.handle_no_permission()

        # چک سازمان (اگه فعال باشه)
        if self.check_organization:
            if not self._has_organization_access(request, **kwargs):
                logger.warning(f"کاربر {request.user} به سازمان دسترسی نداره")
                return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        """چک می‌کنه که آیا کاربر مجوزهای لازم رو داره یا نه"""
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.info(f"مجوز {perm} برای کاربر {user} پیدا نشد")
                return False
        logger.info(f"همه مجوزها برای کاربر {user} تأیید شد")
        return True

    def _has_organization_access(self, request, **kwargs):
        """چک می‌کنه که آیا کاربر به سازمان دسترسی داره یا نه"""
        user_orgs = [up.post.organization for up in request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # اگه کاربر HQ باشه، به همه سازمان‌ها دسترسی داره
        if is_hq_user:
            logger.info(f"کاربر {request.user} HQ هست و به همه سازمان‌ها دسترسی داره")
            return True

        # اگه ویو شیء داره (مثل DetailView یا UpdateView)
        if hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
                org = self._get_organization_from_object(obj)
                if not org:
                    logger.warning("سازمان از شیء پیدا نشد")
                    return False
                if org not in user_orgs:
                    logger.warning(f"کاربر {request.user} به سازمان {org} دسترسی نداره")
                    return False
                logger.info(f"دسترسی به سازمان {org} برای کاربر {request.user} تأیید شد")
                return True
            except AttributeError:
                logger.warning("خطا در پیدا کردن سازمان از شیء")
                return False

        # اگه ویو شیء نداره (مثل CreateView)، فقط HQ می‌تونه دسترسی داشته باشه
        logger.info(f"ویو بدون شیء: فقط HQ اجازه داره")
        return False  # فقط HQ می‌تونه (مثلاً تنخواه جدید بزنه)

    def _get_organization_from_object(self, obj):
        """سازمان رو از شیء استخراج می‌کنه"""
        try:
            return obj.tankhah.project.organization
        except AttributeError:
            return None

    def handle_no_permission(self):
        """مدیریت عدم دسترسی"""
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
