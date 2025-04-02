import logging
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max
from django.views.generic import View, DeleteView
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import DetailView, UpdateView, CreateView, ListView
from tankhah.models import Factor, Tankhah

logger = logging.getLogger(__name__)


def get_lowest_access_level():
    """پیدا کردن پایین سطح کاربر در سازمان"""
    from core.models import WorkflowStage
    lowest_stage = WorkflowStage.objects.order_by('-order').first()  # بالاترین order رو می‌گیره
    return lowest_stage.order if lowest_stage else 1  # اگه هیچ مرحله‌ای نبود، 1 برگردون

def get_initial_stage_order():
    """پیدا کردن مرحله اولیه (مرحله ثبت فاکتور)"""
    from tankhah.models import WorkflowStage
    initial_stage = WorkflowStage.objects.order_by('order').first()  # بالاترین order (مثلاً 5)
    logger.info(f'initial_stage 😎 {initial_stage}')
    return initial_stage.order if initial_stage else 1

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

"""
کلاس پایه برای ویوها با چک مجوز و سازمان.
- permission_codenames: لیست مجوزهای موردنیاز (مثلاً ['app.view_factor'])
- check_organization: آیا دسترسی به سازمان چک بشه یا نه
"""

class PermissionBaseView(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = False

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"شروع dispatch در PermissionBaseView برای {self.__class__.__name__}, کاربر: {request.user}")

        if not request.user.is_authenticated:
            logger.info("کاربر احراز هویت نشده")
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("کاربر سوپروایزر است، دسترسی کامل داده شد")
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames:
            if not self._has_permissions(request.user):
                logger.info(f"مجوزها رد شد: {self.permission_codenames}")
                return self.handle_no_permission()
            logger.info("همه مجوزها تأیید شد")

        if self.check_organization:
            if not self._has_organization_access(request, **kwargs):
                logger.info("چک سازمان رد شد")
                return self.handle_no_permission()
            logger.info("چک سازمان تأیید شد")

        logger.info("همه چک‌ها در PermissionBaseView تأیید شد")
        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        for perm in self.permission_codenames:
            has_perm = user.has_perm(perm)
            logger.info(f"چک مجوز {perm} برای کاربر {user}: {has_perm}")
            if not has_perm:
                return False
        return True

    def _has_organization_access(self, request, **kwargs):
        user_orgs = [up.post.organization for up in
                     request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
        logger.info(f"سازمان‌های کاربر: {user_orgs}")
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        if is_hq_user:
            logger.info("کاربر HQ است، دسترسی کامل")
            return True

        # مدیریت DetailView, UpdateView و DeleteView
        if isinstance(self, (DetailView, UpdateView, DeleteView)):
            try:
                obj = self.get_object()
                org = self._get_organization_from_object(obj)
                logger.info(f"سازمان شیء: {org}")
                if not org or org not in user_orgs:
                    logger.info("سازمان شیء پیدا نشد یا کاربر دسترسی نداره")
                    return False
                return True
            except Exception as e:
                logger.info(f"خطا در گرفتن سازمان از شیء: {str(e)}")
                return False

        # مدیریت ListView
        if isinstance(self, ListView):
            queryset = self.get_queryset()
            tankhah_orgs = set(tankhah.organization for tankhah in queryset if tankhah.organization)
            logger.info(f"سازمان‌های queryset: {tankhah_orgs}")
            if not tankhah_orgs or any(org in user_orgs for org in tankhah_orgs):
                return True
            return False

        # مدیریت CreateView
        if isinstance(self, CreateView):
            if 'tankhah_id' in kwargs:
                try:
                    tankhah = Tankhah.objects.get(id=kwargs['tankhah_id'])
                    org = tankhah.organization
                    logger.info(f"سازمان تنخواه: {org}")
                    if not org or org not in user_orgs:
                        logger.info("سازمان تنخواه پیدا نشد یا کاربر دسترسی نداره")
                        return False
                    return True
                except Tankhah.DoesNotExist:
                    logger.info("تنخواه پیدا نشد")
                    return False
            # اگه tankhah_id نباشه، اجازه می‌دیم فرم باز شه و توی فرم سازمان چک بشه
            logger.info("ایجاد فاکتور بدون tankhah_id، دسترسی موقت داده شد")
            return True

        logger.info("ویو بدون شیء یا فرم، فقط HQ اجازه داره")
        return False

    def _get_organization_from_object(self, obj):
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return obj.tankhah.organization
            elif hasattr(obj, 'organization') and obj.organization:
                return obj.organization
            return None
        except AttributeError:
            return None

    def handle_no_permission(self):
        logger.info("دسترسی رد شد در PermissionBaseView")
        messages.error(self.request, "شما اجازه دسترسی به این بخش را ندارید.")
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
