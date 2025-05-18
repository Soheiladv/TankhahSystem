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
from django.utils.translation import gettext_lazy as _
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

    def _has_organization_access(self, request, **kwargs):
        logger = logging.getLogger('organization_access')
        try:
            user_orgs = set()
            for user_post in request.user.userpost_set.filter(is_active=True, end_date__isnull=True):
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
                    user_posts = request.user.userpost_set.filter(is_active=True, end_date__isnull=True)
                    for user_post in user_posts:
                        if PostAction.objects.filter(
                                post=user_post.post,
                                stage=obj.stage,
                                action_type='APPROVE',
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



