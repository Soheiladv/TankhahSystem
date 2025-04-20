import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import DetailView, UpdateView, CreateView, ListView
from django.views.generic import View, DeleteView

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

def __check_permission_and_organization_(permissions, check_org=False):
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


def check_permission_and_organization(permissions, check_org=False):
    """
    دکوراتور برای چک کردن مجوزها و دسترسی به سازمان و ادارات داخلی.
    """

    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            logger.info(f"چک کردن مجوزها برای کاربر: {request.user}")
            if request.user.is_superuser:
                logger.info("کاربر سوپریوزر است. دسترسی داده شد.")
                return view_func(request, *args, **kwargs)

            perms_to_check = [permissions] if isinstance(permissions, str) else permissions
            for perm in perms_to_check:
                if not request.user.has_perm(perm):
                    logger.warning(f"دسترسی برای کاربر {request.user} به مجوز {perm} رد شد")
                    messages.warning(request, "شما اجازه دسترسی به این بخش را ندارید.")
                    raise PermissionDenied("شما اجازه دسترسی به این صفحه را ندارید.")

            if check_org and 'pk' in kwargs:
                try:
                    from tankhah.models import Factor
                    factor = Factor.objects.get(pk=kwargs['pk'])
                    target_org = factor.tankhah.project.organization  # سازمان پروژه
                    # همه سازمان‌های کاربر (شامل ادارات داخلی)
                    user_orgs = set()
                    for up in request.user.userpost_set.all():
                        org = up.post.organization
                        user_orgs.add(org)
                        # اضافه کردن همه والدین سازمان تا ریشه
                        while org.parent_organization:
                            org = org.parent_organization
                            user_orgs.add(org)

                    is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
                    if not is_hq_user:
                        # چک کردن دسترسی به سازمان هدف یا والدینش
                        current_org = target_org
                        has_access = False
                        while current_org:
                            if current_org in user_orgs:
                                has_access = True
                                break
                            current_org = current_org.parent_organization
                        if not has_access:
                            logger.warning(f"کاربر {request.user} به سازمان {target_org} یا والدینش دسترسی ندارد")
                            messages.warning(request, "شما به این سازمان دسترسی ندارید.")
                            raise PermissionDenied("شما به این سازمان دسترسی ندارید.")
                except Factor.DoesNotExist:
                    logger.warning(f"فاکتور با pk {kwargs['pk']} پیدا نشد")
                    messages.warning(request, "فاکتور یافت نشد.")
                    raise PermissionDenied("فاکتور یافت نشد.")

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


"""
کلاس پایه برای ویوها با چک مجوز و سازمان.
- permission_codenames: لیست مجوزهای موردنیاز (مثلاً ['app.view_factor'])
- check_organization: آیا دسترسی به سازمان چک بشه یا نه
"""
class PermissionBaseView__(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = False

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("کاربر احراز هویت نشده")
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("کاربر سوپریوزر است، دسترسی کامل")
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames and not self._has_permissions(request.user):
            logger.warning(f"مجوزها رد شد: {self.permission_codenames}")
            return self.handle_no_permission()

        if self.check_organization and not self._has_organization_access(request, **kwargs):
            logger.warning("چک سازمان رد شد")
            return self.handle_no_permission()

        logger.info("همه چک‌ها تأیید شد")
        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        logger.info(f"کاربر {user} همه مجوزها را دارد")
        return True

    def _get_organization_from_object(self, obj):
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return obj.tankhah.organization
            elif hasattr(obj, 'organization') and obj.organization:
                return obj.organization
            elif hasattr(obj, 'project') and obj.project:
                return obj.project.organizations.first()
            elif hasattr(obj, 'budget_allocation') and obj.budget_allocation:
                return (obj.budget_allocation.organization)
            return None
        except AttributeError:
            return None

    def _has_organization_access(self, request, **kwargs):
        user_orgs = [up.post.organization for up in request.user.userpost_set.all()] if request.user.userpost_set.exists() else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        if is_hq_user:
            logger.info("کاربر HQ است، دسترسی کامل")
            return True

        if isinstance(self, DetailView):
            obj = self.get_object()
            org = self._get_organization_from_object(obj)
            logger.info(f"سازمان شیء: {org}")
            if not org:
                logger.warning("سازمان شیء پیدا نشد")
                return False
            # چک می‌کنیم آیا کاربر توی سازمان تنخواه یا مرحله تأیید دسترسی داره
            if org in user_orgs or any(p.post.stageapprover_set.filter(stage=obj.tankhah.current_stage).exists() for p in request.user.userpost_set.all()):
                return True
            logger.warning(f"کاربر به سازمان {org} یا مرحله فعلی دسترسی ندارد")
            return False

        logger.info("ویو بدون شیء مشخص، دسترسی موقت")
        return True

    def handle_no_permission(self):
        logger.info("دسترسی رد شد در PermissionBaseView")
        messages.error(self.request, "شما اجازه دسترسی به این بخش را ندارید.")
        return redirect('factor_list')

class PermissionBaseView(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = False

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames and not self._has_permissions(request.user):
            return self.handle_no_permission()

        if self.check_organization and not self._has_organization_access(request, **kwargs):
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _get_organization_from_object(self, obj):
        # کامنت: گرفتن سازمان از شیء با توجه به نوع مدل
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return obj.tankhah.project.organization
            elif hasattr(obj, 'organization') and obj.organization:
                return obj.organization
            return None
        except AttributeError:
            return None

    def _has_organization_access(self, request, **kwargs):
        # کامنت: گرفتن همه سازمان‌های کاربر با سلسله‌مراتب
        # user_orgs = set()
        user_orgs = set(up.post.organization for up in
                        request.user.userpost_set.all()) if request.user.userpost_set.exists() else set()
        logger.info(f"سازمان‌های کاربر: 🏠 {user_orgs}")

        # is_hq_user = any(org.org_type == 'HQ' for org in user_orgs)
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
        if is_hq_user:
            logger.info("کاربر HQ است، دسترسی کامل 👍👍👍")
            return True

        for up in request.user.userpost_set.all():
            org = up.post.organization
            user_orgs.add(org)
            while org.parent_organization:
                org = org.parent_organization
                user_orgs.add(org)


        # کامنت: مدیریت ویوهای مختلف با چک سلسله‌مراتب
        if isinstance(self, (DetailView, UpdateView, DeleteView)):
            obj = self.get_object()
            target_org = self._get_organization_from_object(obj)
            logger.info(f"سازمان‌های شیء: {target_org}")
            if not target_org:
                logger.warning("سازمان شیء پیدا نشد 😭")
                return False
            current_org = target_org
            while current_org:
                if current_org in user_orgs:
                    return True
                logger.warning(f"کاربر به هیچ‌کدام از سازمان‌های {current_org} دسترسی ندارد")
                current_org = current_org.parent_organization
            return False

        if isinstance(self, ListView):
            queryset = self.get_queryset()
            tankhah_orgs = set()
            for item in queryset:
                org = self._get_organization_from_object(item)
                if org:
                    tankhah_orgs.add(org)
            if not tankhah_orgs or any(org in user_orgs for org in tankhah_orgs):
                return True
            return False

        if isinstance(self, CreateView):
            if 'tankhah_id' in kwargs:
                from tankhah.models import Tankhah
                tankhah = Tankhah.objects.get(id=kwargs['tankhah_id'])
                target_org = tankhah.project.organization
                current_org = target_org
                while current_org:
                    if current_org in user_orgs:
                        return True
                    logger.warning(f"کاربر به هیچ‌کدام از سازمان‌های {current_org} دسترسی ندارد")
                    current_org = current_org.parent_organization
                return False
            return True  # موقت برای فرم

        return False

    def handle_no_permission(self):
        messages.error(self.request, "شما اجازه دسترسی به این بخش را ندارید.")
        return redirect('index')



"""
توضیحات خط به خط
شروع dispatch: لاگ می‌کنه که ویو شروع شده و کاربر کیه.

چک لاگین: مطمئن می‌شه کاربر لاگین کرده باشه.

چک سوپریوزر: اگه کاربر سوپریوزر باشه، همه‌چیز رو رد می‌کنه و دسترسی می‌ده.

چک مجوزها: اگه permission_codenames تعریف شده باشه، تابع _has_permissions رو صدا می‌زنه.

چک سازمان: اگه check_organization فعال باشه، تابع _has_organization_access رو صدا می‌زنه.

اجرا: اگه همه‌چیز اوکی باشه، ویو رو اجرا می‌کنه.

شروع _has_permissions: لاگ می‌کنه که داریم مجوزها رو برای کاربر چک می‌کنیم.

گرفتن گروه‌ها: همه گروه‌های کاربر رو از MyGroup می‌گیره.

گرفتن نقش‌ها: نقش‌های مستقیم کاربر رو از roles می‌گیره.

حلقه مجوزها: برای هر مجوز توی permission_codenames چک می‌کنه.

چک مستقیم: اول مجوزهای مستقیم کاربر رو از user_permissions چک می‌کنه.

چک نقش‌های مستقیم: بعد نقش‌های مستقیم کاربر رو بررسی می‌کنه.

چک گروه‌ها: اگه هنوز مجوز پیدا نشده، نقش‌های گروه‌ها رو چک می‌کنه.

نتیجه مجوز: اگه یه مجوز پیدا نشد، False برمی‌گردونه.

موفقیت: اگه همه مجوزها پیدا شدن، True برمی‌گردونه.

گرفتن سازمان‌ها: سازمان‌هایی که کاربر بهشون دسترسی داره رو می‌گیره.

چک HQ: چک می‌کنه که کاربر HQ هست یا نه.

دسترسی HQ: اگه HQ باشه، سریع True برمی‌گردونه.

ویوهای جزئی: برای DetailView, UpdateView, و DeleteView سازمان شیء رو چک می‌کنه.

لیست‌ها: برای ListView سازمان‌های توی queryset رو بررسی می‌کنه.

ایجاد: برای CreateView اگه tankhah_id باشه، سازمان تنخواه رو چک می‌کنه.

پیش‌فرض: اگه نوع ویو مشخص نباشه، فقط HQ اجازه داره.

گرفتن سازمان: تابع کمکی برای گرفتن سازمان از شیء.

عدم دسترسی: اگه دسترسی رد بشه، پیام خطا می‌ده و ریدایرکت می‌کنه.


"""
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




"""
کلاس پایه برای ویوها با چک مجوز و سازمان.
- permission_codenames: لیست مجوزهای موردنیاز (مثلاً ['app.view_factor'])
- check_organization: آیا دسترسی به سازمان چک بشه یا نه
"""

class PermissionBaseView3(LoginRequiredMixin, View):
    permission_codenames = []  # لیست مجوزهای مورد نیاز برای ویو (مثلاً ['core.Project_view'])
    check_organization = False  # آیا نیاز به چک کردن دسترسی سازمانی هست یا نه

    def dispatch(self, request, *args, **kwargs):
        logger.info(f"شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("کاربر احراز هویت نشده 😭")
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("کاربر سوپریوزر 😎 است، دسترسی کامل")
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames:
            logger.info(f"🕐 چک کردن مجوزها: {self.permission_codenames}")
            if not self._has_permissions(request.user):
                logger.warning(f"مجوزها رد شد 👎😭: {self.permission_codenames}")
                return self.handle_no_permission()
            logger.info("👍 همه مجوزها تأیید شد")

        if self.check_organization:
            logger.info("🕐 شروع چک سازمان")
            if not self._has_organization_access(request, **kwargs):
                logger.warning("چک سازمان رد شد 👎")
                return self.handle_no_permission()
            logger.info("چک سازمان تأیید شد 👍")

        logger.info("👍 همه چک‌ها تأیید شد")
        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        logger.info(f"چک کردن مجوزها برای کاربر: {user}")
        user_groups = user.groups.all()
        logger.info(f"گروه‌های کاربر: {[group.name for group in user_groups]}")
        user_roles = user.roles.all()
        logger.info(f"نقش‌های مستقیم کاربر: {[role.name for role in user_roles]}")

        for perm in self.permission_codenames:
            has_perm = False
            logger.info(f"چک کردن مجوز: {perm}")
            if perm in [f"{p.content_type.app_label}.{p.codename}" for p in user.user_permissions.all()]:
                logger.info(f"مجوز {perm} به صورت مستقیم توی user_permissions پیدا شد")
                has_perm = True
            else:
                for role in user_roles:
                    if perm in [f"{p.content_type.app_label}.{p.codename}" for p in role.permissions.all()]:
                        logger.info(f"مجوز {perm} توی نقش مستقیم {role.name} پیدا شد")
                        has_perm = True
                        break
                if not has_perm:
                    for group in user_groups:
                        group_roles = group.roles.all()
                        logger.info(f"نقش‌های گروه {group.name}: {[role.name for role in group_roles]}")
                        for role in group_roles:
                            if perm in [f"{p.content_type.app_label}.{p.codename}" for p in role.permissions.all()]:
                                logger.info(f"مجوز {perm} توی نقش {role.name} از گروه {group.name} پیدا شد")
                                has_perm = True
                                break
                        if has_perm:
                            break
            if not has_perm:
                logger.warning(f"کاربر {user} مجوز {perm} رو نداره")
                return False
        logger.info(f"کاربر {user} همه مجوزهای لازم رو داره")
        return True

    def _has_organization_access(self, request, **kwargs):
        # گرفتن سازمان‌هایی که کاربر بهشون دسترسی داره
        user_orgs = set(up.post.organization for up in request.user.userpost_set.all()) if request.user.userpost_set.exists() else set()
        logger.info(f"سازمان‌های کاربر: 🏠 {user_orgs}")

        # چک کردن اینکه کاربر HQ هست یا نه
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
        logger.info(f"کاربر HQ 🏠 است؟ {is_hq_user}")

        # اگه کاربر HQ باشه، دسترسی کامل داره
        if is_hq_user:
            logger.info("کاربر HQ است، دسترسی کامل 👍👍👍")
            return True

        # مدیریت ویوهای مختلف (DetailView, UpdateView, DeleteView)
        if isinstance(self, (DetailView, UpdateView, DeleteView)):
            try:
                obj = self.get_object()
                orgs = self._get_organization_from_object(obj)
                logger.info(f"سازمان‌های شیء: {orgs}")
                if not orgs or not orgs.intersection(user_orgs):
                    logger.info("سازمان شیء پیدا نشد یا کاربر دسترسی نداره 😭")
                    return False
                return True
            except Exception as e:
                logger.info(f"خطا در گرفتن سازمان از شیء 😭: {str(e)}")
                return False

        # مدیریت ListView
        if isinstance(self, ListView):
            queryset = self.get_queryset()
            tankhah_orgs = set()
            for project in queryset:
                tankhah_orgs.update(project.organizations.all())  # جمع‌آوری همه سازمان‌ها از پروژه‌ها
            logger.info(f"سازمان‌های queryset: {tankhah_orgs}")
            if not tankhah_orgs or tankhah_orgs.intersection(user_orgs):
                return True
            return False

        # مدیریت CreateView
        if isinstance(self, CreateView):
            if 'tankhah_id' in kwargs:
                try:
                    tankhah = Tankhah.objects.get(id=kwargs['tankhah_id'])
                    project_orgs = set(tankhah.project.organizations.all())  # سازمان‌های پروژه مرتبط با تنخواه
                    logger.info(f"سازمان‌های تنخواه: {project_orgs}")
                    if not project_orgs or not project_orgs.intersection(user_orgs):
                        logger.info("سازمان تنخواه پیدا نشد یا کاربر دسترسی نداره")
                        return False
                    return True
                except Tankhah.DoesNotExist:
                    logger.info("تنخواه پیدا نشد")
                    return False
            # اگه tankhah_id نباشه، اجازه می‌دیم فرم باز شه و توی فرم سازمان چک بشه
            logger.info("ایجاد فاکتور بدون tankhah_id، دسترسی موقت داده شد")
            return True

        # اگه نوع ویو مشخص نباشه، فقط HQ اجازه داره
        logger.info("ویو بدون شیء یا فرم، فقط HQ اجازه داره")
        return False

    def _get_organization_from_object(self, obj):
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return set([obj.tankhah.organization])
            elif hasattr(obj, 'organizations') and obj.organizations.exists():
                return set(obj.organizations.all())  # برای مدل‌هایی مثل Project
            elif hasattr(obj, 'organization') and obj.organization:
                return set([obj.organization])
            return set()
        except AttributeError:
            logger.error(f"خطا در گرفتن سازمان از شیء: {obj}")
            return set()

    def handle_no_permission(self):
        logger.info("دسترسی رد شد در PermissionBaseView")
        messages.error(self.request, "شما اجازه دسترسی به این بخش را ندارید.")
        return redirect('index')  # تغییر به URL لیست پروژه‌ها


