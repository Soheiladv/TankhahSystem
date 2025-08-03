import logging
from unittest import TestCase

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, get_object_or_404
from django.test import RequestFactory
from django.views.generic import DetailView, UpdateView, CreateView, ListView
from django.views.generic import View, DeleteView
from django.utils.translation import gettext_lazy as _

from core.models import Organization, PostAction, AccessRule

logger = logging.getLogger(__name__)


def get_lowest_access_level():
    """پیدا کردن پایین سطح کاربر در سازمان"""
    from core.models import WorkflowStage
    lowest_stage = AccessRule.objects.order_by('order').first()  # پایین‌ترین order
    # lowest_stage = WorkflowStage.objects.order_by('-order').first()  # بالاترین order رو می‌گیره
    return lowest_stage.order if lowest_stage else 1  # اگه هیچ مرحله‌ای نبود، 1 برگردون

def get_initial_stage_order():
    """پیدا کردن مرحله اولیه (مرحله ثبت فاکتور)"""
    from core.models import WorkflowStage
    # initial_stage = WorkflowStage.objects.order_by('order').first()  # بالاترین order (مثلاً 5)
    initial_stage = AccessRule.objects.order_by('-order').first()  # بالاترین order
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
            logger.debug(f'perms_to_check is {perms_to_check}')
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
                    user_orgs = set()
                    for up in request.user.userpost_set.filter(is_active=True, end_date__isnull=True):
                        org = up.post.organization
                        user_orgs.add(org)
                        while org.parent_organization:
                            org = org.parent_organization
                            user_orgs.add(org)

                    is_hq_user = (
                        request.user.has_perm('tankhah.Tankhah_view_all') or
                        request.user.is_superuser or
                        any(org.org_type.fname == 'HQ' for org in user_orgs if org.org_type)
                    )
                    if is_hq_user:
                        logger.info("کاربر HQ است، دسترسی کامل")
                        return view_func(request, *args, **kwargs)

                    current_org = target_org
                    while current_org:
                        if current_org in user_orgs:
                            logger.info(f"دسترسی به سازمان {current_org} تأیید شد")
                            return view_func(request, *args, **kwargs)
                        current_org = current_org.parent_organization
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
    check_organization = True
    organization_filter_field = None

    def dispatch(self, request, *args, **kwargs):
        """
        مدیریت دسترسی‌ها برای ویو
        """
        logger.info(f"[PermissionBaseView] شروع dispatch در {self.__class__.__name__} برای کاربر: {request.user}")
        if not request.user.is_authenticated:
            logger.warning("[PermissionBaseView] تلاش دسترسی کاربر احراز هویت‌نشده")
            return self.handle_no_permission()

        # دسترسی کامل برای superuser یا کاربران با مجوز Tankhah_view_all
        if request.user.is_superuser or request.user.has_perm('tankhah.Tankhah_view_all'):
            logger.info("[PermissionBaseView] کاربر superuser یا دارای مجوز Tankhah_view_all است، دسترسی کامل")
            return super().dispatch(request, *args, **kwargs)

        # بررسی مجوزهای تعریف‌شده
        if self.permission_codenames and not self._has_permissions(request.user):
            logger.warning(f"[PermissionBaseView] کاربر {request.user} مجوزهای لازم را ندارد: {self.permission_codenames}")
            return self.handle_no_permission()

        # بررسی دسترسی سازمانی برای ویوهای غیر ListView
        if self.check_organization and not isinstance(self, ListView):
            if not self._has_organization_access(request, **kwargs):
                logger.warning(f"[PermissionBaseView] کاربر {request.user} به سازمان مرتبط دسترسی ندارد")
                return self.handle_no_permission()

            # 💡 NEW: Enforce that any non-superuser must have an active post for POST requests
        if request.method == 'POST' and not request.user.is_superuser:
            if not request.user.userpost_set.filter(is_active=True).exists():
                logger.warning(f"User '{request.user.username}' attempted a POST action without an active post.")
                messages.error(request, _("شما برای انجام این عملیات باید یک پست سازمانی فعال داشته باشید."))
                # Redirect back to the same page or a dashboard
                return redirect(request.path_info)

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        """
        بررسی اینکه آیا کاربر تمام مجوزهای لازم را دارد
        """
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"[PermissionBaseView] کاربر {user} مجوز {perm} را ندارد")
                return False
        logger.debug(f"[PermissionBaseView] کاربر {user} تمام مجوزهای لازم را دارد")
        return True

    def _has_organization_access(self, request, **kwargs):
        """
        بررسی دسترسی کاربر به سازمان مرتبط با شیء یا ویو
        """
        logger = logging.getLogger('organization_access')
        try:
            # جمع‌آوری تمام سازمان‌های مرتبط با پست‌های فعال کاربر
            user_org_ids = set()
            for user_post in request.user.userpost_set.filter(is_active=True):
                org = user_post.post.organization
                user_org_ids.add(org.id)
                current_org = org
                while current_org.parent_organization:
                    current_org = current_org.parent_organization
                    user_org_ids.add(current_org.id)
            logger.debug(f"[PermissionBaseView] سازمان‌های کاربر {request.user}: {user_org_ids}")

            # بررسی کاربران HQ یا superuser یا Tankhah_view_all
            is_hq_user = (
                request.user.is_superuser or
                request.user.has_perm('tankhah.Tankhah_view_all') or
                any(Organization.objects.filter(id=org_id, org_type__org_type='HQ').exists() for org_id in user_org_ids)
            )
            if is_hq_user:
                logger.info("[PermissionBaseView] کاربر HQ یا superuser یا دارای Tankhah_view_all است، دسترسی کامل")
                return True

            # برای DetailView, UpdateView, DeleteView
            if isinstance(self, (DetailView, UpdateView, DeleteView)):
                obj = self.get_object()
                target_org = self._get_organization_from_object(obj)
                if not target_org:
                    logger.warning(f"[PermissionBaseView] سازمان شیء {obj} پیدا نشد")
                    return False

                # بررسی permission factor_approve
                if request.user.has_perm('tankhah.factor_approve'):
                    logger.info(f"[PermissionBaseView] کاربر {request.user} دسترسی factor_approve دارد")
                    return True


                # بررسی دسترسی تأیید با PostAction
                if hasattr(obj, 'stage') and obj.stage:
                    user_posts = request.user.userpost_set.filter(is_active=True)
                    for user_post in user_posts:
                        if PostAction.objects.filter(
                            post=user_post.post,
                            stage=obj.stage,
                            action_type='APPROVED',  # یا EDIT_APPROVAL اگر تعریف شده باشد
                            entity_type=ContentType.objects.get_for_model(obj).model.upper(),
                            is_active=True
                        ).exists():
                            logger.info(f"[PermissionBaseView] دسترسی تأیید برای شیء {obj} تأیید شد")
                            return True

                # بررسی دسترسی سازمانی
                logger.info(f"[PermissionBaseView] بررسی دسترسی به سازمان {target_org.id} برای کاربر {request.user}")
                if target_org.id in user_org_ids:
                    logger.info(f"[PermissionBaseView] دسترسی به سازمان {target_org.id} تأیید شد")
                    return True
                logger.warning(f"[PermissionBaseView] کاربر {request.user} به سازمان {target_org.id} دسترسی ندارد")
                return False

            # برای CreateView
            if isinstance(self, CreateView):
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    target_org = Organization.objects.get(id=organization_id)
                    logger.info(f"[PermissionBaseView] بررسی دسترسی به سازمان {target_org.id} برای ایجاد")
                    if target_org.id in user_org_ids:
                        logger.info(f"[PermissionBaseView] دسترسی به سازمان {target_org.id} برای ایجاد تأیید شد")
                        return True
                    logger.warning(f"[PermissionBaseView] کاربر {request.user} به سازمان {target_org.id} برای ایجاد دسترسی ندارد")
                    return False
                logger.info("[PermissionBaseView] ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            # برای ListView
            if isinstance(self, ListView):
                if not user_org_ids:
                    logger.warning(f"[PermissionBaseView] کاربر {request.user} به هیچ سازمانی دسترسی ندارد")
                    return False
                logger.info(f"[PermissionBaseView] کاربر به سازمان‌های {user_org_ids} دسترسی دارد")
                return True

            logger.warning("[PermissionBaseView] نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            return False
        except Exception as e:
            logger.error(f"[PermissionBaseView] خطا در بررسی دسترسی: {str(e)}", exc_info=True)
            return False

    def _get_organization_from_object(self, obj):
        """
        استخراج سازمان از شیء به‌صورت عمومی
        """
        logger = logging.getLogger('organization_access')
        try:
            if hasattr(obj, 'organization') and obj.organization:
                logger.info(f"[PermissionBaseView] سازمان مستقیم از شیء {obj} استخراج شد: {obj.organization}")
                return obj.organization
            if hasattr(obj, 'tankhah') and obj.tankhah and obj.tankhah.organization:
                logger.info(f"[PermissionBaseView] سازمان از tankhah شیء {obj} استخراج شد: {obj.tankhah.organization}")
                return obj.tankhah.organization
            if hasattr(obj, 'project') and obj.project and obj.project.organizations.exists():
                organization = obj.project.organizations.first()
                logger.info(f"[PermissionBaseView] سازمان از project شیء {obj} استخراج شد: {organization}")
                return organization
            if hasattr(obj, 'post') and obj.post and obj.post.organization:
                logger.info(f"[PermissionBaseView] سازمان از post شیء {obj} استخراج شد: {obj.post.organization}")
                return obj.post.organization
            logger.warning(f"[PermissionBaseView] سازمان از شیء {obj} استخراج نشد")
            return None
        except AttributeError as e:
            logger.error(f"[PermissionBaseView] خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def handle_no_permission(self):
        """
        مدیریت عدم دسترسی
        """
        logger.warning(f"[PermissionBaseView] عدم دسترسی برای کاربر {self.request.user}")
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('index')

    def get_queryset(self):
        """
        فیلتر کوئری‌ست بر اساس سازمان‌های کاربر برای ListView
        """
        qs = super().get_queryset()
        user = self.request.user
        logger.info(f"[PermissionBaseView] دریافت کوئری‌ست برای {self.__class__.__name__}")

        # برای DetailView نیازی به فیلتر نیست
        if isinstance(self, DetailView):
            logger.info(f"[PermissionBaseView] بدون فیلتر سازمانی برای DetailView")
            return qs

        # دسترسی کامل برای superuser یا کاربران با Tankhah_view_all
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info("[PermissionBaseView] بازگشت کوئری‌ست بدون فیلتر برای superuser یا Tankhah_view_all")
            return qs

        # جمع‌آوری سازمان‌های کاربر
        user_org_ids = set()
        for user_post in user.userpost_set.filter(is_active=True):
            org = user_post.post.organization
            user_orgs = {org.id}
            while org.parent_organization:
                org = org.parent_organization
                user_orgs.add(org.id)
            user_org_ids.update(user_orgs)
        logger.debug(f"[PermissionBaseView] سازمان‌های کاربر {user}: {user_org_ids}")

        # بررسی کاربران HQ
        is_hq_user = any(
            Organization.objects.filter(id=org_id, org_type__org_type='HQ').exists()
            for org_id in user_org_ids
        )
        if is_hq_user:
            logger.info("[PermissionBaseView] بازگشت کوئری‌ست بدون فیلتر برای کاربر HQ")
            return qs

        # اگر سازمانی وجود نداشته باشد، کوئری‌ست خالی برگردانده می‌شود
        if not user_org_ids:
            logger.warning(f"[PermissionBaseView] هیچ سازمانی برای کاربر {user.username} پیدا نشد")
            return qs.none()

        # اعمال فیلتر سازمانی
        if self.organization_filter_field:
            filters = {f"{self.organization_filter_field}__in": user_org_ids}
            logger.debug(f"[PermissionBaseView] اعمال فیلتر: {filters}")
            return qs.filter(**filters)

        logger.warning("[PermissionBaseView] فیلد فیلتر سازمانی تعریف نشده، بازگشت کوئری‌ست خالی")
        return qs.none()

# def _get_organization_from_object(self, obj):
    #     """استخراج سازمان از شیء"""
    #     try:
    #         if hasattr(obj, 'tankhah') and obj.tankhah:
    #             return obj.tankhah.project.organization
    #         elif hasattr(obj, 'organization') and obj.organization:
    #             return obj.organization
    #         elif hasattr(obj, 'budget_allocation') and obj.budget_allocation:
    #             return obj.budget_allocation.organization
    #         logger.warning(f"سازمان از شیء {obj} استخراج نشد")
    #         return None
    #     except AttributeError as e:
    #         logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
    #         return None

    # def _has_organization_access(self, request, **kwargs):
    #     """بررسی دسترسی کاربر به سازمان"""
    #     try:
    #         # استخراج سازمان‌های کاربر از UserPost
    #         user_orgs = set()
    #         if request.user.userpost_set.exists():
    #             user_orgs = set(up.post.organization for up in request.user.userpost_set.filter(is_active=True))
    #         logger.info(f"سازمان‌های کاربر: {user_orgs}")
    #
    #         # بررسی کاربر HQ
    #         # is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
    #         is_hq_user = any(org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type) if user_orgs else False
    #         if is_hq_user:
    #             logger.info("کاربر HQ است، دسترسی کامل")
    #             return True
    #
    #         # افزودن سازمان‌های والد به مجموعه
    #         for up in request.user.userpost_set.filter(is_active=True):
    #             org = up.post.organization
    #             user_orgs.add(org)
    #             current_org = org
    #             while current_org.parent_organization:
    #                 current_org = current_org.parent_organization
    #                 user_orgs.add(current_org)
    #
    #         # مدیریت ویوهای مختلف
    #         if isinstance(self, (DetailView, UpdateView, DeleteView)):
    #             obj = self.get_object()
    #             target_org = self._get_organization_from_object(obj)
    #             if not target_org:
    #                 logger.warning("سازمان شیء پیدا نشد")
    #                 return False
    #             current_org = target_org
    #             while current_org:
    #                 if current_org in user_orgs:
    #                     logger.info(f"دسترسی به سازمان {current_org} تأیید شد")
    #                     return True
    #                 current_org = current_org.parent_organization
    #             logger.warning(f"کاربر به سازمان {target_org} یا والدین آن دسترسی ندارد")
    #             return False
    #
    #         if isinstance(self, ListView):
    #             queryset = self.get_queryset()
    #             target_orgs = set()
    #             tankhah_orgs = set()
    #             for item in queryset:
    #                 org = self._get_organization_from_object(item)
    #                 if org:
    #                     tankhah_orgs.add(org)
    #             if not target_orgs:
    #                 logger.info("هیچ سازمانی در لیست یافت نشد، دسترسی تأیید شد")
    #                 return True
    #             for target_org in target_orgs:
    #                 current_org = target_org
    #                 while current_org:
    #                     if current_org in user_orgs:
    #                         logger.info(f"دسترسی به سازمان {current_org.name} در لیست تأیید شد")
    #                         return True
    #                     current_org = current_org.parent_organization
    #             logger.warning("کاربر به هیچ‌یک از سازمان‌های لیست دسترسی ندارد")
    #
    #             if not tankhah_orgs or any(org in user_orgs for org in tankhah_orgs):
    #                 logger.info("دسترسی به لیست تأیید شد")
    #                 return True
    #             logger.warning("کاربر به هیچ‌یک از سازمان‌های لیست دسترسی ندارد")
    #             return False
    #
    #         # مدیریت CreateView
    #         from core.models import Organization
    #         if isinstance(self, CreateView):
    #             organization_id = kwargs.get('organization_id')
    #             if organization_id:
    #                 try:
    #                     target_org = Organization.objects.get(id=organization_id)
    #                     current_org = target_org
    #                     while current_org:
    #                         if current_org in user_orgs:
    #                             logger.info(f"دسترسی به سازمان {current_org.name} برای ایجاد تأیید شد")
    #                             return True
    #                         current_org = current_org.parent_organization
    #                     logger.warning(f"کاربر به سازمان {target_org.name} برای ایجاد دسترسی ندارد")
    #                     return False
    #                 except Organization.DoesNotExist:
    #                     logger.error(f"سازمان با ID {organization_id} یافت نشد")
    #                     return False
    #             logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
    #             return True
    #
    #         logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
    #         # return False
    #
    #         if isinstance(self, CreateView):
    #             if 'tankhah_id' in kwargs:
    #                 from tankhah.models import Tankhah
    #                 try:
    #                     tankhah = Tankhah.objects.get(id=kwargs['tankhah_id'])
    #                     target_org = tankhah.project.organization
    #                     current_org = target_org
    #                     while current_org:
    #                         if current_org in user_orgs:
    #                             logger.info(f"دسترسی به سازمان {current_org} برای ایجاد تأیید شد")
    #                             return True
    #                         current_org = current_org.parent_organization
    #                     logger.warning(f"کاربر به سازمان {target_org} برای ایجاد دسترسی ندارد")
    #                     return False
    #                 except Tankhah.DoesNotExist:
    #                     logger.error(f"تنخواه با ID {kwargs['tankhah_id']} یافت نشد")
    #                     return False
    #             # برای فرم‌های بدون tankhah_id (مانند ایجاد تخصیص جدید)
    #             organization_id = kwargs.get('organization_id')
    #             if organization_id:
    #                 from core.models import Organization
    #                 try:
    #                     target_org = Organization.objects.get(id=organization_id)
    #                     current_org = target_org
    #                     while current_org:
    #                         if current_org in user_orgs:
    #                             logger.info(f"دسترسی به سازمان {current_org} برای ایجاد تأیید شد")
    #                             return True
    #                         current_org = current_org.parent_organization
    #                     logger.warning(f"کاربر به سازمان {target_org} برای ایجاد دسترسی ندارد")
    #                     return False
    #                 except Organization.DoesNotExist:
    #                     logger.error(f"سازمان با ID {organization_id} یافت نشد")
    #                     return False
    #             logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
    #             return True
    #
    #         logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
    #         return False
    #
    #     except Exception as e:
    #         logger.error(f"خطا در بررسی دسترسی سازمان برای کاربر {request.user}: {str(e)}")
    #         return False
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

class PermissionBaseView___(LoginRequiredMixin, View):
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

        # چک کردن سازمان برای ویوهای Detail, Update, Create...
        if self.check_organization and not isinstance(self, ListView):
            if not self._has_organization_access(request, **kwargs):
                return self.handle_no_permission()
        #
        # if self.check_organization and not self._has_organization_access(request, **kwargs):
        #     logger.warning(f"کاربر {request.user} به سازمان مرتبط دسترسی ندارد")
        #     return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        """بررسی مجوزهای کاربر"""
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _has_organization_access(self, request, **kwargs):
        logger = logging.getLogger('organization_access')
        try:
            user_orgs = set()
            for user_post in request.user.userpost_set.filter(is_active=True):#, end_date__isnull=True):
                org = user_post.post.organization
                user_orgs.add(org)
                current_org = org
                while current_org.parent_organization:
                    current_org = current_org.parent_organization
                    user_orgs.add(current_org)

            is_hq_user = any(
                org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type
            ) or request.user.has_perm('tankhah.Tankhah_view_all')
            if is_hq_user:
                logger.info("کاربر HQ است، دسترسی کامل")
                return True

            if isinstance(self, (DetailView, UpdateView, DeleteView)):
                obj = self.get_object()
                target_org = self._get_organization_from_object(obj)
                if not target_org:
                    logger.warning("سازمان شیء پیدا نشد")
                    return False

                # چک دسترسی تأیید (مثل can_edit_approval)
                if hasattr(obj, 'stage') and obj.stage:
                    from core.models import PostAction
                    from django.contrib.contenttypes.models import ContentType
                    user_posts = request.user.userpost_set.filter(is_active=True)#, end_date__isnull=True)
                    for user_post in user_posts:
                        if PostAction.objects.filter(
                                post=user_post.post,
                                stage=obj.stage,
                                action_type='APPROVED',
                                entity_type=ContentType.objects.get_for_model(obj).model.upper(),
                                is_active=True
                        ).exists():
                            logger.info(f"دسترسی تأیید برای {obj} تأیید شد")
                            return True

                current_org = target_org
                while current_org:
                    if current_org in user_orgs:
                        logger.info(f"دسترسی به سازمان {current_org} تأیید شد")
                        return True
                    current_org = current_org.parent_organization
                logger.warning(f"کاربر {request.user} به سازمان {target_org} یا والدین آن دسترسی ندارد")
                return False

            if isinstance(self, ListView):
                if is_hq_user:
                    logger.info("کاربر HQ است، دسترسی به همه آیتم‌های لیست")
                    return True
                queryset = self.get_queryset()
                for item in queryset:
                    org = self._get_organization_from_object(item)
                    if org and org in user_orgs:
                        logger.info(f"دسترسی به سازمان {org} در لیست تأیید شد")
                        return True
                logger.warning("کاربر به هیچ‌یک از سازمان‌های لیست دسترسی ندارد")
                return False

            if isinstance(self, CreateView):
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    from core.models import Organization
                    target_org = Organization.objects.get(id=organization_id)
                    current_org = target_org
                    while current_org:
                        if current_org in user_orgs:
                            logger.info(f"دسترسی به سازمان {current_org} برای ایجاد تأیید شد")
                            return True
                        current_org = current_org.parent_organization
                    logger.warning(f"کاربر به سازمان {target_org} برای ایجاد دسترسی ندارد")
                    return False
                logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            return False
        except Exception as e:
            logger.error(f"خطا در بررسی دسترسی: {str(e)}")
            return False

    def _get_organization_from_object(self, obj):
        """استخراج سازمان از شیء به‌صورت عمومی"""
        logger = logging.getLogger('organization_access')
        try:
            # 1. اگر شیء مستقیماً فیلد organization دارد
            if hasattr(obj, 'organization') and obj.organization:
                logger.info(f"سازمان مستقیم از شیء {obj} استخراج شد: {obj.organization}")
                return obj.organization

            # 2. اگر شیء فیلد organizations (ManyToMany) دارد (مثل Project)
            if hasattr(obj, 'organizations') and obj.organizations.exists():
                # فرض می‌کنیم اولین سازمان مرتبط را برمی‌گردانیم
                # یا می‌توان منطق دیگری برای انتخاب سازمان تعریف کرد
                organization = obj.organizations.first()
                logger.info(f"سازمان از organizations شیء {obj} استخراج شد: {organization}")
                return organization

            # 3. اگر شیء به Tankhah مرتبط است (مثل Factor)
            if hasattr(obj, 'tankhah') and obj.tankhah:
                logger.info(f"سازمان از tankhah شیء {obj} استخراج شد: {obj.tankhah.organization}")
                return obj.tankhah.organization

            # 4. اگر شیء به Project مرتبط است (مثل Tankhah.project)
            if hasattr(obj, 'project') and obj.project:
                if obj.project.organizations.exists():
                    organization = obj.project.organizations.first()
                    logger.info(f"سازمان از project شیء {obj} استخراج شد: {organization}")
                    return organization

            # 5. اگر شیء به Post مرتبط است
            if hasattr(obj, 'post') and obj.post:
                logger.info(f"سازمان از post شیء {obj} استخراج شد: {obj.post.organization}")
                return obj.post.organization

            # 6. اگر هیچ سازمانی پیدا نشد
            logger.warning(f"سازمان از شیء {obj} استخراج نشد")
            return None

        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def handle_no_permission(self):
        """مدیریت عدم دسترسی"""
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('index')

    def check_object_permission(self, request, obj):
        user = request.user
        user_posts = user.userpost_set.filter(is_active=True)
        for user_post in user_posts:
            from core.models import PostAction

            # چک قوانین مرتبط با پست خاص
            if PostAction.objects.filter(
                post=user_post.post,
                stage=obj.stage,
                action_type='APPROVED',
                entity_type=ContentType.objects.get_for_model(obj).model.upper(),
                is_active=True
            ).exists():
                logger.info(f"دسترسی تأیید برای {obj} تأیید شد (قانون مستقیم پست)")
                return True
            # چک قوانین بر اساس min_level
            if PostAction.objects.filter(
                post=user_post.post,
                stage=obj.stage,
                action_type='APPROVE',
                entity_type=ContentType.objects.get_for_model(obj).model.upper(),
                is_active=True,
                min_level__lte=user_post.post.level
            ).exists():
                logger.info(f"دسترسی تأیید برای {obj} تأیید شد (min_level)")
                return True

    def get_queryset(self):
        """
        FIX: این متد در کلاس پایه بازنویسی (override) می‌شود تا به صورت خودکار
        تمام ListView هایی که از آن ارث‌بری می‌کنند را بر اساس دسترسی کاربر فیلتر کند.
        """
        # ابتدا کوئری‌ست اصلی مدل را از کلاس فرزند (مثلا FactorListView) می‌گیرد
        qs = super().get_queryset()
        user = self.request.user

        # برای DetailView نیازی به فیلتر سازمان نیست
        if isinstance(self, DetailView):
            logger.info(f"No organization filtering applied for DetailView: {self.__class__.__name__}")
            return qs

        # اگر کاربر HQ است، تمام نتایج را برمی‌گرداند
        if user.is_hq:
            logger.info("Returning unfiltered queryset for HQ user")
            return qs

        if hasattr(self, 'organization_filter_field') and self.organization_filter_field:
            user_org_ids = user.userpost_set.filter(is_active=True).values_list('post__organization_id', flat=True).distinct()
            logger.debug(f"User organizations: {list(user_org_ids)}")
            if not user_org_ids:
                logger.warning(f"No organizations found for user {user.username}")
                return qs.none()
            filters = {f"{self.organization_filter_field}__in": user_org_ids}
            logger.debug(f"Applying filters: {filters}")
            return qs.filter(**filters)
        logger.warning("No organization filter field defined, returning empty queryset")

        # اگر کاربر عادی است و فیلد فیلتر سازمان تعریف شده است
        # if self.organization_filter_field:
        #     user_org_ids = user.userpost_set.filter(is_active=True).values_list('post__organization_id', flat=True).distinct()
        #     logger.debug(f"User organizations: {list(user_org_ids)}")
        #     # فیلتر داینامیک بر اساس نام فیلدی که در ویو فرزند تعریف شده
        #     if not user_org_ids:
        #         logger.warning(f"No organizations found for user {user.username}")
        #         return qs.none()
        #         # صراحتاً از __in استفاده کنید
        #     filters = {f"{self.organization_filter_field}__in": user_org_ids}
        #     logger.debug(f"Applying filters: {filters}")
        #     return qs.filter(**filters)

        logger.warning("No organization filter field defined, returning empty queryset")
        return qs.none()

class PermissionBaseView__OK(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = True
    organization_filter_field = None

    def dispatch(self, request, *args, **kwargs):
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

        if self.check_organization and not isinstance(self, ListView):
            if not self._has_organization_access(request, **kwargs):
                return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _has_organization_access(self, request, **kwargs):
        logger = logging.getLogger('organization_access')
        try:
            user_orgs = set()
            for user_post in request.user.userpost_set.filter(is_active=True):
                org = user_post.post.organization
                user_orgs.add(org.id)
                current_org = org
                while current_org.parent_organization:
                    current_org = current_org.parent_organization
                    user_orgs.add(current_org.id)

            is_hq_user = (
                request.user.is_superuser or
                request.user.has_perm('tankhah.Tankhah_view_all') or
                any(Organization.objects.get(id=org_id).org_type.fname == 'HQ' for org_id in user_orgs)
            )
            if is_hq_user:
                logger.info("کاربر HQ است، دسترسی کامل")
                return True

            if isinstance(self, (DetailView, UpdateView, DeleteView)):
                obj = self.get_object()
                target_org = self._get_organization_from_object(obj)
                if not target_org:
                    logger.warning("سازمان شیء پیدا نشد")
                    return False
                logger.info(f"بررسی دسترسی به سازمان {target_org.id} برای کاربر {request.user}")
                return target_org.id in user_orgs

            if isinstance(self, CreateView):
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    target_org = Organization.objects.get(id=organization_id)
                    logger.info(f"بررسی دسترسی به سازمان {target_org.id} برای ایجاد")
                    return target_org.id in user_orgs
                logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            return False
        except Exception as e:
            logger.error(f"خطا در بررسی دسترسی: {str(e)}", exc_info=True)
            return False

    def _get_organization_from_object(self, obj):
        logger = logging.getLogger('organization_access')
        try:
            if hasattr(obj, 'organization') and obj.organization:
                logger.info(f"سازمان مستقیم از شیء {obj} استخراج شد: {obj.organization}")
                return obj.organization
            if hasattr(obj, 'tankhah') and obj.tankhah:
                logger.info(f"سازمان از tankhah شیء {obj} استخراج شد: {obj.tankhah.organization}")
                return obj.tankhah.organization
            if hasattr(obj, 'project') and obj.project and obj.project.organizations.exists():
                organization = obj.project.organizations.first()
                logger.info(f"سازمان از project شیء {obj} استخراج شد: {organization}")
                return organization
            logger.warning(f"سازمان از شیء {obj} استخراج نشد")
            return None
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def handle_no_permission(self):
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('index')

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if isinstance(self, DetailView):
            logger.info(f"No organization filtering applied for DetailView: {self.__class__.__name__}")
            return qs
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info("Returning unfiltered queryset for HQ user")
            return qs
        user_org_ids = set()
        for user_post in user.userpost_set.filter(is_active=True):
            org = user_post.post.organization
            user_orgs = {org.id}
            while org.parent_organization:
                org = org.parent_organization
                user_orgs.add(org.id)
            user_org_ids.update(user_orgs)
        if not user_org_ids:
            logger.warning(f"No organizations found for user {user.username}")
            return qs.none()
        if self.organization_filter_field:
            filters = {f"{self.organization_filter_field}": user_org_ids}
            logger.debug(f"Applying filters: {filters}")
            return qs.filter(**filters)
        logger.warning("No organization filter field defined, returning empty queryset")
        return qs.none()

class PermissionBaseView_OK(LoginRequiredMixin, View):
    permission_codenames = []
    check_organization = True
    organization_filter_field = None

    def dispatch(self, request, *args, **kwargs):
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

        if self.check_organization and not isinstance(self, ListView):
            if not self._has_organization_access(request, **kwargs):
                return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)

    def _has_permissions(self, user):
        for perm in self.permission_codenames:
            if not user.has_perm(perm):
                logger.warning(f"کاربر {user} مجوز {perm} را ندارد")
                return False
        return True

    def _has_organization_access(self, request, **kwargs):
        logger = logging.getLogger('organization_access')
        try:
            user_org_ids = set()
            for user_post in request.user.userpost_set.filter(is_active=True):
                org = user_post.post.organization
                user_org_ids.add(org.id)
                current_org = org
                while current_org.parent_organization:
                    current_org = current_org.parent_organization
                    user_org_ids.add(current_org.id)

            # فقط superuser یا کاربران با مجوز Tankhah_view_all دسترسی کامل دارند
            if request.user.is_superuser or request.user.has_perm('tankhah.Tankhah_view_all'):
                logger.info("کاربر superuser یا دارای مجوز Tankhah_view_all است، دسترسی کامل")
                return True

            if isinstance(self, (DetailView, UpdateView, DeleteView)):
                obj = self.get_object()
                target_org = self._get_organization_from_object(obj)
                if not target_org:
                    logger.warning("سازمان شیء پیدا نشد")
                    return False
                logger.info(f"بررسی دسترسی به سازمان {target_org.id} برای کاربر {request.user}")
                return target_org.id in user_org_ids

            if isinstance(self, ListView):
                # حتی برای کاربران HQ، فقط سازمان‌های مرتبط فیلتر می‌شوند
                if not user_org_ids:
                    logger.warning(f"کاربر {request.user} به هیچ سازمانی دسترسی ندارد")
                    return False
                logger.info(f"کاربر به سازمان‌های {user_org_ids} دسترسی دارد")
                return True

            if isinstance(self, CreateView):
                organization_id = kwargs.get('organization_id')
                if organization_id:
                    target_org = Organization.objects.get(id=organization_id)
                    logger.info(f"بررسی دسترسی به سازمان {target_org.id} برای ایجاد")
                    return target_org.id in user_org_ids
                logger.info("ایجاد بدون نیاز به سازمان خاص، دسترسی تأیید شد")
                return True

            logger.warning("نوع ویو پشتیبانی‌نشده برای بررسی سازمان")
            return False
        except Exception as e:
            logger.error(f"خطا در بررسی دسترسی: {str(e)}", exc_info=True)
            return False

    def _get_organization_from_object(self, obj):
        logger = logging.getLogger('organization_access')
        try:
            if hasattr(obj, 'organization') and obj.organization:
                logger.info(f"سازمان مستقیم از شیء {obj} استخراج شد: {obj.organization}")
                return obj.organization
            if hasattr(obj, 'tankhah') and obj.tankhah:
                logger.info(f"سازمان از tankhah شیء {obj} استخراج شد: {obj.tankhah.organization}")
                return obj.tankhah.organization
            if hasattr(obj, 'project') and obj.project and obj.project.organizations.exists():
                organization = obj.project.organizations.first()
                logger.info(f"سازمان از project شیء {obj} استخراج شد: {organization}")
                return organization
            logger.warning(f"سازمان از شیء {obj} استخراج نشد")
            return None
        except AttributeError as e:
            logger.error(f"خطا در استخراج سازمان از شیء {obj}: {str(e)}")
            return None

    def handle_no_permission(self):
        messages.error(self.request, _("شما اجازه دسترسی به این بخش را ندارید."))
        return redirect('index')

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if isinstance(self, DetailView):
            logger.info(f"No organization filtering applied for DetailView: {self.__class__.__name__}")
            return qs

        # فقط superuser یا کاربران با Tankhah_view_all تمام داده‌ها را می‌بینند
        if user.is_superuser or user.has_perm('tankhah.Tankhah_view_all'):
            logger.info("Returning unfiltered queryset for superuser or Tankhah_view_all user")
            return qs

        user_org_ids = set()
        for user_post in user.userpost_set.filter(is_active=True):
            org = user_post.post.organization
            user_orgs = {org.id}
            while org.parent_organization:
                org = org.parent_organization
                user_orgs.add(org.id)
            user_org_ids.update(user_orgs)

        if not user_org_ids:
            logger.warning(f"No organizations found for user {user.username}")
            return qs.none()

        if self.organization_filter_field:
            filters = {f"{self.organization_filter_field}": user_org_ids}
            logger.debug(f"Applying filters: {filters}")
            return qs.filter(**filters)

        logger.warning("No organization filter field defined, returning empty queryset")
        return qs.none()


