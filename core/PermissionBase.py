import logging
from unittest import TestCase

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, get_object_or_404
from django.test import RequestFactory
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
    from core.models import WorkflowStage
    initial_stage = WorkflowStage.objects.order_by('order').first()  # بالاترین order (مثلاً 5)
    logger.info(f'initial_stage 😎 {initial_stage}')
    return initial_stage.order if initial_stage else 1


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
class PermissionBaseView(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = False

    def dispatch(self, request, *args, **kwargs):
        """مدیریت دسترسی‌ها"""
        logger.info(f"شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("تلاش دسترسی کاربر احراز هویت‌نشده")
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("کاربر مدیرکل است، دسترسی کامل")
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames and not self._has_permissions(request.user):
            logger.warning(f"کاربر {request.user} مجوزهای لازم را ندارد: {self.permission_codenames}")
            return self.handle_no_permission()

        if self.check_organization and not self._has_organization_access(request, **kwargs):
            logger.warning(f"کاربر {request.user} به سازمان مرتبط دسترسی ندارد")
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        """بررسی مجوزهای کاربر"""
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _get_organization_from_object(self, obj):
        """استخراج سازمان از شیء"""
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return obj.tankhah.project.organization
            elif hasattr(obj, 'organization') and obj.organization:
                return obj.organization
            elif hasattr(obj, 'budget_allocation') and obj.budget_allocation:
                return obj.budget_allocation.organization
            logger.warning(f"سازمان از شیء {obj} استخراج نشد")
            return None
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def _has_organization_access(self, request, **kwargs):
        """بررسی دسترسی کاربر به سازمان"""
        try:
            # cache_key = f"user_orgs_{request.user.id}"
            # from django.core.cache import cache
            # user_orgs = cache.get(cache_key)
            # if not user_orgs:
            #     user_orgs = set(up.post.organization for up in request.user.userpost_set.filter(is_active=True))
            #     for up in request.user.userpost_set.filter(is_active=True):
            #         org = up.post.organization
            #         user_orgs.add(org)
            #         while org.parent_organization:
            #             org = org.parent_organization
            #             user_orgs.add(org)
            #     cache.set(cache_key, user_orgs, 300)  # 5 دقیقه

            # استخراج سازمان‌های کاربر از UserPost
            user_orgs = set()
            if request.user.userpost_set.exists():
                user_orgs = set(up.post.organization for up in request.user.userpost_set.filter(is_active=True))
            logger.info(f"سازمان‌های کاربر: {user_orgs}")

            # بررسی کاربر HQ
            # is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
            is_hq_user = any(org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type) if user_orgs else False
            if is_hq_user:
                logger.info("کاربر HQ است، دسترسی کامل")
                return True

            # افزودن سازمان‌های والد به مجموعه
            for up in request.user.userpost_set.filter(is_active=True):
                org = up.post.organization
                user_orgs.add(org)
                current_org = org
                while current_org.parent_organization:
                    current_org = current_org.parent_organization
                    user_orgs.add(current_org)

            # مدیریت ویوهای مختلف
            if isinstance(self, (DetailView, UpdateView, DeleteView)):
                obj = self.get_object()
                target_org = self._get_organization_from_object(obj)
                if not target_org:
                    logger.warning("سازمان شیء پیدا نشد")
                    return False
                current_org = target_org
                while current_org:
                    if current_org in user_orgs:
                        logger.info(f"دسترسی به سازمان {current_org} تأیید شد")
                        return True
                    current_org = current_org.parent_organization
                logger.warning(f"کاربر به سازمان {target_org} یا والدین آن دسترسی ندارد")
                return False

            if isinstance(self, ListView):
                queryset = self.get_queryset()
                target_orgs = set()
                tankhah_orgs = set()
                for item in queryset:
                    org = self._get_organization_from_object(item)
                    if org:
                        tankhah_orgs.add(org)
                if not target_orgs:
                    logger.info("هیچ سازمانی در لیست یافت نشد، دسترسی تأیید شد")
                    return True
                for target_org in target_orgs:
                    current_org = target_org
                    while current_org:
                        if current_org in user_orgs:
                            logger.info(f"دسترسی به سازمان {current_org.name} در لیست تأیید شد")
                            return True
                        current_org = current_org.parent_organization
                logger.warning("کاربر به هیچ‌یک از سازمان‌های لیست دسترسی ندارد")

                if not tankhah_orgs or any(org in user_orgs for org in tankhah_orgs):
                    logger.info("دسترسی به لیست تأیید شد")
                    return True
                logger.warning("کاربر به هیچ‌یک از سازمان‌های لیست دسترسی ندارد")
                return False

            # مدیریت CreateView
            from core.models import Organization
            if isinstance(self, CreateView):
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    try:
                        target_org = Organization.objects.get(id=organization_id)
                        current_org = target_org
                        while current_org:
                            if current_org in user_orgs:
                                logger.info(f"دسترسی به سازمان {current_org.name} برای ایجاد تأیید شد")
                                return True
                            current_org = current_org.parent_organization
                        logger.warning(f"کاربر به سازمان {target_org.name} برای ایجاد دسترسی ندارد")
                        return False
                    except Organization.DoesNotExist:
                        logger.error(f"سازمان با ID {organization_id} یافت نشد")
                        return False
                logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            # return False

            if isinstance(self, CreateView):
                if 'tankhah_id' in kwargs:
                    try:
                        tankhah = Tankhah.objects.get(id=kwargs['tankhah_id'])
                        target_org = tankhah.project.organization
                        current_org = target_org
                        while current_org:
                            if current_org in user_orgs:
                                logger.info(f"دسترسی به سازمان {current_org} برای ایجاد تأیید شد")
                                return True
                            current_org = current_org.parent_organization
                        logger.warning(f"کاربر به سازمان {target_org} برای ایجاد دسترسی ندارد")
                        return False
                    except Tankhah.DoesNotExist:
                        logger.error(f"تنخواه با ID {kwargs['tankhah_id']} یافت نشد")
                        return False
                # برای فرم‌های بدون tankhah_id (مانند ایجاد تخصیص جدید)
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    from core.models import Organization
                    try:
                        target_org = Organization.objects.get(id=organization_id)
                        current_org = target_org
                        while current_org:
                            if current_org in user_orgs:
                                logger.info(f"دسترسی به سازمان {current_org} برای ایجاد تأیید شد")
                                return True
                            current_org = current_org.parent_organization
                        logger.warning(f"کاربر به سازمان {target_org} برای ایجاد دسترسی ندارد")
                        return False
                    except Organization.DoesNotExist:
                        logger.error(f"سازمان با ID {organization_id} یافت نشد")
                        return False
                logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            return False

        except Exception as e:
            logger.error(f"خطا در بررسی دسترسی سازمان برای کاربر {request.user}: {str(e)}")
            return False

    def handle_no_permission(self):
        """مدیریت عدم دسترسی"""
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('index')

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
class old_PermissionBaseView(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = False

    def dispatch(self, request, *args, **kwargs):
        """مدیریت دسترسی‌ها"""
        logger.info(f"شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("تلاش دسترسی کاربر احراز هویت‌نشده")
            return self.handle_no_permission()

        if request.user.is_superuser:
            logger.info("کاربر مدیرکل است، دسترسی کامل")
            return super().dispatch(request, *args, **kwargs)

        if self.permission_codenames and not self._has_permissions(request.user):
            logger.warning(f"کاربر {request.user} مجوزهای لازم را ندارد: {self.permission_codenames}")
            return self.handle_no_permission()

        if self.check_organization and not self._has_organization_access(request, **kwargs):
            logger.warning(f"کاربر {request.user} به سازمان مرتبط دسترسی ندارد")
            return self.handle_no_permission()


        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        """بررسی مجوزهای کاربر"""
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _get_organization_from_object(self, obj):
        """استخراج سازمان از شیء"""
        try:
            if hasattr(obj, 'tankhah') and obj.tankhah:
                return obj.tankhah.project.organization
            elif hasattr(obj, 'organization') and obj.organization:
                return obj.organization
            elif hasattr(obj, 'budget_allocation') and obj.budget_allocation:
                return obj.budget_allocation.organization
            logger.warning(f"سازمان از شیء {obj} استخراج نشد")
            return None
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None


    def _has_organization_access(self, request, **kwargs):
        # کامنت: گرفتن همه سازمان‌های کاربر با سلسله‌مراتب
        # user_orgs = set()
        """بررسی دسترسی کاربر به سازمان"""
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
from django.utils.translation import gettext_lazy as _
class New_Version_PermissionBaseView(View):
    permission_codename = None
    permission_denied_message = _("شما دسترسی لازم را ندارید.")
    check_organization = False

    def _has_organization_access(self, organization):
        """چک کردن دسترسی کاربر به سازمان"""
        try:
            user_organizations = self.request.user.get_authorized_organizations()
            return user_organizations.filter(pk=organization.pk).exists()
        except AttributeError:
            logger.warning(f"User {self.request.user} has no organization access method")
            return False

    def dispatch(self, request, *args, **kwargs):
        """مدیریت دسترسی‌ها"""
        if not request.user.is_authenticated:
            logger.warning("Unauthenticated user access attempt")
            raise PermissionDenied(self.permission_denied_message)

        if self.permission_codename and not request.user.has_perm(self.permission_codename):
            logger.warning(f"User {request.user} lacks permission {self.permission_codename}")
            raise PermissionDenied(self.permission_denied_message)

        if self.check_organization:
            organization_id = self.kwargs.get('organization_id') or self.kwargs.get('org_id')
            if organization_id:
                from core.models import Organization
                organization = get_object_or_404(Organization, pk=organization_id)
                if not self._has_organization_access(organization):
                    logger.warning(f"User {request.user} lacks access to organization {organization_id}")
                    raise PermissionDenied(self.permission_denied_message)

        return super().dispatch(request, *args, **kwargs)
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

class PermissionBaseViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        from accounts.forms import CustomUser
        self.user = CustomUser.objects.create_user(username='jjj', password='D@d123')
        from core.models import Organization
        self.organization = Organization.objects.create(name='Test Org', code='TST')
        self.view = PermissionBaseView()

    def test_authenticated_user(self):
        request = self.factory.get('/')
        request.user = self.user
        self.view.request = request
        self.assertTrue(self.view.dispatch(request))

    def test_unauthenticated_user(self):
        request = self.factory.get('/')
        request.user = None
        self.view.request = request
        with self.assertRaises(PermissionDenied):
            self.view.dispatch(request)

    def test_organization_access(self):
        request = self.factory.get('/')
        request.user = self.user
        self.view.request = request
        self.view.check_organization = True
        self.view.kwargs = {'organization_id': self.organization.pk}
        with self.assertRaises(PermissionDenied):
            self.view.dispatch(request)



