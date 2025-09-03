from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from accounts.models import CustomUser
from core.models import UserPost, EntityType, Transition
from tankhah.Factor.Approved.fun_can_edit_approval import can_edit_approval
from core.models import  WorkflowStage
from tankhah.models import Tankhah, ApprovalLog
from core.views import PermissionBaseView
from .utils import restrict_to_user_organization

from django.views.generic import ListView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from tankhah.models import Tankhah, Factor
from core.models import Post, UserPost, AccessRule, PostAction, Organization
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

from django.views.generic import DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from tankhah.models import Tankhah, Factor, ApprovalLog
from core.models import Post, UserPost, AccessRule, Organization


class TankhahTrackingView1(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_tracking.html'
    context_object_name = 'tankhah'
    permission_required = 'tankhah.Tankhah_view'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_superuser:
            user_orgs = restrict_to_user_organization(user)
            if user_orgs and obj.organization not in user_orgs:
                raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        return obj

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0

        if 'archive' in request.POST and not tankhah.is_archived:
            tankhah.is_archived = True
            tankhah.archived_at = timezone.now()
            tankhah.save()
            messages.success(request, _('تنخواه با موفقیت آرشیو شد.'))

        elif 'change_stage' in request.POST and can_edit_approval(user, tankhah, tankhah.current_stage):
            new_stage_order = int(request.POST.get('new_stage_order'))
            new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
            if new_stage:
                tankhah.current_stage = new_stage
                tankhah.status = 'PENDING' if new_stage.order < tankhah.current_stage.order else tankhah.status
                tankhah.save()
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    user=user,
                    action='STAGE_CHANGE',
                    stage=new_stage,
                    comment=f"تغییر مرحله به {new_stage.name} توسط {user.get_full_name()}",
                    post=user_post.post if user_post else None
                )
                messages.success(request, _(f"مرحله تنخواه به {new_stage.name} تغییر یافت."))

        return redirect('tankhah_tracking', pk=tankhah.pk)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        # user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        # user_level = user_post.post.level if user_post else 0

        # اطلاعات تنخواه
        context['title'] = _('پیگیری تنخواه') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all().prefetch_related('items__approval_logs', 'documents', 'approval_logs')
        context['documents'] = tankhah.documents.all()

        # آپدیت مراحل گردش کار
        workflow_stages = WorkflowStage.objects.order_by('order')  # از 1 به بالا
        current_stage = tankhah.current_stage
        if not current_stage:  # اگر مرحله فعلی تنظیم نشده
            tankhah.current_stage = workflow_stages.first()  # order=1
            tankhah.save()

        # بررسی پیشرفت مراحل
        stages_data = []
        for stage in workflow_stages:
            approvals = ApprovalLog.objects.filter(
                tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post') | ApprovalLog.objects.filter(
                factor__tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post') | ApprovalLog.objects.filter(
                factor_item__factor__tankhah=tankhah,
                stage=stage
            ).select_related('user', 'post')

            is_completed = approvals.filter(action='APPROVE').exists() and stage.order < tankhah.current_stage.order
            # if not is_completed and approvals.filter(action='APPROVE').exists() and stage == tankhah.current_stage:
            #     # انتقال به مرحله بعدی
            #     # next_stage = workflow_stages.filter(order__gt=stage.order).first()
            #     # next_stage = workflow_stages.filter(order__lt=stage.order).order_by('-order').first()
            #     next_stage = workflow_stages.filter(order__gt=stage.order).order_by('order').first()  # از 1 به 2 به 3
            #     if next_stage:
            #         tankhah.current_stage = next_stage
            #         tankhah.save()
            #     elif all(f.status == 'APPROVED' for f in tankhah.factors.all()):
            #         tankhah.status = 'APPROVED'
            #         tankhah.save()

            stages_data.append({
                'name': stage.name,
                'order': stage.order,
                'is_current': stage == tankhah.current_stage,
                'is_completed': is_completed,
                'approvals': approvals,
                'approvers': [
                    f"{approver.post.name} ({userpost.user.get_full_name()})"
                    for approver in stage.stageapprover_set.prefetch_related('post__userpost_set__user').all()
                    for userpost in approver.post.userpost_set.filter(end_date__isnull=True)
                ],
            })
        context['stages'] = stages_data
        context['can_change_stage'] = can_edit_approval(user, tankhah, tankhah.current_stage) and user_level >= 5  # فقط سطح 5 به بالا
        context['workflow_stages'] = workflow_stages

        # چک مجوز تغییر وضعیت فاکتور
        context['can_approve_factor'] = self.request.user.has_perm('tankhah.FactorItem_approve')

        # چک رده بالاتر و ثبت "دیده شدن"
        if user_level > (tankhah.last_stopped_post.level if tankhah.last_stopped_post else 0):
            logs_to_update = ApprovalLog.objects.filter(tankhah=tankhah, seen_by_higher=False).exclude(user=self.request.user)
            if logs_to_update.exists():
                logs_to_update.update(seen_by_higher=True, seen_at=timezone.now())
                lower_users = CustomUser.objects.filter(
                    userpost__post__level__lt=user_level,
                    userpost__end_date__isnull=True
                ).distinct()
        # خلاصه آماری
        factors = tankhah.factors.all()
        context['stats'] = {
            'total_amount': sum(f.amount for f in factors),
            'approved_amount': sum(f.amount for f in factors if f.status == 'APPROVED'),
            'rejected_amount': sum(f.amount for f in factors if f.status == 'REJECTED'),
            'pending_amount': sum(f.amount for f in factors if f.status == 'PENDING'),
        }
        context['can_archive'] = not tankhah.is_archived and self.request.user.has_perm('tankhah.Tankhah_change')

        return context

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای مشاهده این تنخواه را ندارید.'))
        return redirect('factor_list')

class TankhahTrackingViewOLDer(PermissionBaseView, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_tracking.html'
    context_object_name = 'tankhah'
    permission_required = 'tankhah.Tankhah_view'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if not user.is_superuser:
            user_orgs = restrict_to_user_organization(user)
            if user_orgs and obj.organization not in user_orgs:
                raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        return obj

    def post(self, request, *args, **kwargs):
        tankhah = self.get_object()
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        if 'archive' in request.POST and not tankhah.is_archived:
            tankhah.is_archived = True
            tankhah.archived_at = timezone.now()
            tankhah.save()
            messages.success(request, _('تنخواه با موفقیت آرشیو شد.'))

        elif 'change_stage' in request.POST and can_edit_approval(user, tankhah, tankhah.current_stage):
            new_stage_order = int(request.POST.get('new_stage_order'))
            if new_stage_order <= max_change_level:
                new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
                if new_stage:
                    tankhah.current_stage = new_stage
                    tankhah.status = 'PENDING' if new_stage.order < tankhah.current_stage.order else tankhah.status
                    tankhah.save()
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        user=user,
                        action='STAGE_CHANGE',
                        stage=new_stage,
                        comment=f"تغییر مرحله به {new_stage.name} توسط {user.get_full_name()}",
                        post=user_post.post if user_post else None
                    )
                    messages.success(request, _(f"مرحله تنخواه به {new_stage.name} تغییر یافت."))

        return redirect('tankhah_tracking', pk=tankhah.pk)

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or user.has_perm('tankhah.view_tankhah'):
            logger.info(f"User {user.username} has global access. Returning all Tankhah objects.")
            self.has_global_access = True
            # ## FIX:  'current_status' به 'status' تغییر کرد
            return Tankhah.objects.all().select_related(
                'status', 'organization', 'project', 'subproject'
            ).prefetch_related(
                Prefetch('factors', queryset=Factor.objects.select_related('status'))
            ).order_by('-created_at')

        self.has_global_access = False
        user_posts = Post.objects.filter(
            userpost__user=user,
            userpost__is_active=True,
            userpost__end_date__isnull=True
        ).distinct()

        if not user_posts.exists():
            logger.warning(f"Regular user {user.username} has no active posts.")
            return Tankhah.objects.none()

        try:
            tankhah_entity_type = EntityType.objects.get(code='TANKHAH')
        except EntityType.DoesNotExist:
            logger.error("EntityType with code 'TANKHAH' does not exist.")
            return Tankhah.objects.none()

        permitted_org_ids = Transition.objects.filter(
            entity_type=tankhah_entity_type,
            allowed_posts__in=user_posts
        ).values_list('organization_id', flat=True).distinct()

        if not permitted_org_ids:
            logger.warning(f"User {user.username} has no Transition permissions for EntityType 'TANKHAH'.")
            return Tankhah.objects.none()

        self.permitted_org_ids = list(permitted_org_ids)

        # ## FIX:  'current_status' به 'status' تغییر کرد
        queryset = Tankhah.objects.filter(
            organization_id__in=self.permitted_org_ids
        ).select_related(
            'status', 'organization', 'project', 'subproject'
        ).prefetch_related(
            Prefetch('factors', queryset=Factor.objects.select_related('status'))
        ).order_by('-created_at')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if self.has_global_access:
            possible_transitions = Transition.objects.filter(
                entity_type__code='TANKHAH', is_active=True
            ).select_related('action', 'to_status')
        else:
            user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True).distinct()
            possible_transitions = Transition.objects.filter(
                entity_type__code='TANKHAH',
                allowed_posts__in=user_posts,
                is_active=True
            ).select_related('action', 'to_status')

        transitions_map = {}
        for t in possible_transitions:
            key = (t.from_status_id, t.organization_id)
            if key not in transitions_map:
                transitions_map[key] = []
            transitions_map[key].append(t)

        tankhahs_processed_data = []
        for tankhah in self.object_list:
            # ## FIX:  'current_status_id' به 'status_id' تغییر کرد
            lookup_key = (tankhah.status_id, tankhah.organization_id)
            available_transitions = transitions_map.get(lookup_key, [])

            # ## FIX:  'current_status' به 'status' تغییر کرد
            is_payment_ready = tankhah.status.is_final_approve if tankhah.status else False

            tankhahs_processed_data.append({
                'tankhah': tankhah,
                'factors': tankhah.factors.all(),
                'available_transitions': available_transitions,
                'is_payment_ready': is_payment_ready,
            })

        context['tankhahs_data'] = tankhahs_processed_data
        context['title'] = _('وضعیت کلی تنخواه‌ها')

        return context


from django.db.models.query import Prefetch
# ==========================================#==  وضعیت کلی تنخواه ها
class TankhahStatusView(PermissionBaseView, ListView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_status.html'
    context_object_name = 'tankhahs'
    permission_codenames = ['tankhah.Tankhah_view']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_queryset(self):
        """
        ساده‌سازی شده: این متد دیگر دسترسی را کنترل نمی‌کند.
        PermissionBaseView ابتدا کاربران را بر اساس پرمیشن و سازمان فیلتر می‌کند.
        این متد فقط کوئری فیلتر شده را دریافت کرده و آن را برای نمایش بهینه می‌کند.
        """
        # queryset ابتدا توسط PermissionBaseView بر اساس سازمان‌های مجاز کاربر فیلتر می‌شود
        queryset = super().get_queryset()

        # لیست فیلدهای مورد نیاز برای بهینه‌سازی
        select_related_fields = [
            'status', 'organization', 'project', 'subproject',
            'project_budget_allocation',
            'project_budget_allocation__budget_period',
            'project_budget_allocation__budget_item'
        ]
        prefetch_related_fields = [
            Prefetch('factors', queryset=Factor.objects.select_related('status'))
        ]

        # اعمال بهینه‌سازی‌ها و مرتب‌سازی نهایی
        return queryset.select_related(*select_related_fields).prefetch_related(*prefetch_related_fields).order_by(
            '-created_at')

        #
        # # ## FIX: استثنای دسترسی فقط برای Superuser ##
        # # اگر کاربر، ادمین کل سیستم باشد، تمام تنخواه‌ها را بدون هیچ فیلتر دیگری مشاهده می‌کند.
        # if user.is_superuser:
        #     logger.info(f"User {user.username} is a superuser. Returning all Tankhah objects.")
        #     self.has_global_access = True
        #     return Tankhah.objects.all().select_related(*select_related_fields).prefetch_related(
        #         *prefetch_related_fields).order_by('-created_at')
        #
        # # --- اگر کاربر superuser نباشد، منطق دسترسی دقیق بر اساس Post اجرا می‌شود ---
        # self.has_global_access = False
        # user_posts = Post.objects.filter(
        #     userpost__user=user, userpost__is_active=True, userpost__end_date__isnull=True
        # ).distinct()
        #
        # if not user_posts.exists():
        #     logger.warning(f"Regular user {user.username} has no active posts.")
        #     return Tankhah.objects.none()
        #
        # try:
        #     tankhah_entity_type = EntityType.objects.get(code='TANKHAH')
        # except EntityType.DoesNotExist:
        #     logger.error("EntityType with code 'TANKHAH' does not exist.")
        #     return Tankhah.objects.none()
        #
        # permitted_org_ids = Transition.objects.filter(
        #     entity_type=tankhah_entity_type,
        #     allowed_posts__in=user_posts
        # ).values_list('organization_id', flat=True).distinct()
        #
        # if not permitted_org_ids:
        #     logger.warning(f"User {user.username} has no Transition permissions for EntityType 'TANKHAH'.")
        #     return Tankhah.objects.none()
        #
        # # این خط برای get_context_data لازم نیست چون check_organization در PermissionBaseView
        # # به صورت خودکار کوئری را فیلتر می‌کند.
        # # self.permitted_org_ids = list(permitted_org_ids)
        #
        # queryset = Tankhah.objects.filter(
        #     organization_id__in=permitted_org_ids
        # ).select_related(*select_related_fields).prefetch_related(*prefetch_related_fields).order_by('-created_at')
        #
        # return queryset
    def get_context_data(self, **kwargs):
        """
        ساده‌سازی شده: این متد دیگر دسترسی کاربر را برای هر اقدام بررسی نمی‌کند.
        بلکه تمام اقدامات ممکن برای هر وضعیت را واکشی کرده و به تمپلیت می‌دهد.
        تمپلیت می‌تواند بر اساس نیاز، دکمه‌ها را نمایش دهد یا مخفی کند.
        """
        context = super().get_context_data(**kwargs)

        # واکشی تمام گذارهای ممکن برای موجودیت تنخواه در یک کوئری
        possible_transitions = Transition.objects.filter(
            entity_type__code='TANKHAH', is_active=True
        ).select_related('action', 'to_status')

        # ساخت یک دیکشنری برای دسترسی سریع به اقدامات هر وضعیت
        transitions_map = {}
        for t in possible_transitions:
            key = (t.from_status_id, t.organization_id)
            if key not in transitions_map:
                transitions_map[key] = []
            transitions_map[key].append(t)

        tankhahs_processed_data = []
        for tankhah in self.object_list:
            lookup_key = (tankhah.status_id, tankhah.organization_id)
            available_transitions = transitions_map.get(lookup_key, [])
            is_payment_ready = tankhah.status.is_final_approve if tankhah.status else False

            tankhahs_processed_data.append({
                'tankhah': tankhah,
                'factors': tankhah.factors.all(),
                'available_transitions': available_transitions,
                'is_payment_ready': is_payment_ready,
            })

        context['tankhahs_data'] = tankhahs_processed_data
        context['title'] = _('وضعیت کلی تنخواه‌ها')

        return context

    # def get_context_data(self, **kwargs):
    #     # متد get_context_data نیازی به تغییر ندارد و با هر دو حالت (superuser و کاربر عادی)
    #     # به درستی کار می‌کند.
    #     context = super().get_context_data(**kwargs)
    #     user = self.request.user
    #
    #     # تشخیص اینکه کاربر مدیر است یا نه، از get_queryset به اینجا منتقل می‌شود
    #     has_global_access = hasattr(self, 'has_global_access') and self.has_global_access
    #
    #     if has_global_access:
    #         possible_transitions = Transition.objects.filter(
    #             entity_type__code='TANKHAH', is_active=True
    #         ).select_related('action', 'to_status')
    #     else:
    #         user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True).distinct()
    #         possible_transitions = Transition.objects.filter(
    #             entity_type__code='TANKHAH',
    #             allowed_posts__in=user_posts,
    #             is_active=True
    #         ).select_related('action', 'to_status')
    #
    #     transitions_map = {}
    #     for t in possible_transitions:
    #         key = (t.from_status_id, t.organization_id)
    #         if key not in transitions_map:
    #             transitions_map[key] = []
    #         transitions_map[key].append(t)
    #
    #     tankhahs_processed_data = []
    #     for tankhah in self.object_list:
    #         lookup_key = (tankhah.status_id, tankhah.organization_id)
    #         available_transitions = transitions_map.get(lookup_key, [])
    #         is_payment_ready = tankhah.status.is_final_approve if tankhah.status else False
    #
    #         tankhahs_processed_data.append({
    #             'tankhah': tankhah,
    #             'factors': tankhah.factors.all(),
    #             'available_transitions': available_transitions,
    #             'is_payment_ready': is_payment_ready,
    #         })
    #
    #     context['tankhahs_data'] = tankhahs_processed_data
    #     context['title'] = _('وضعیت کلی تنخواه‌ها')
    #
    #     return context



# ==========================================

class old__TankhahApprovalTimelineView(PermissionRequiredMixin, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_approval_timeline.html'
    context_object_name = 'tankhah'
    permission_required = ['tankhah.Tankhah_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True)

        # بررسی دسترسی بر اساس AccessRule
        access_rules = AccessRule.objects.filter(
            Q(post__in=user_posts) | Q(min_level__lte=user_posts.first().level, branch=user_posts.first().branch),
            organization=obj.organization,
            entity_type='TANKHAH',
            action_type='VIEW',
            is_active=True
        )
        if not access_rules.exists() and not user.is_superuser:
            logger.warning(f"User {user.username} lacks access به تنخواه {obj.number}")
            raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        user = self.request.user
        user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True)

        # اطلاعات تنخواه
        context['title'] = _(':توجه خطاها را اصلاح کنید') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all()#.select_related('current_stage')

        # دریافت تمام مراحل فعال
        stages = WorkflowStage.objects.filter(is_active=True).order_by('order')

        # دریافت تأییدهای تنخواه و فاکتورها
        tankhah_approvals = ApprovalLog.objects.filter(
            tankhah=tankhah
        ).select_related('user', 'post', 'stage').order_by('created_at')

        factor_approvals = {
            factor.id: ApprovalLog.objects.filter(
                factor=factor
            ).select_related('user', 'post', 'stage').order_by('created_at')
            for factor in context['factors']
        }

        # ساخت خط زمانی
        timeline_data = []
        for stage in stages:
            # تأییدهای تنخواه برای این مرحله
            stage_tankhah_approvals = tankhah_approvals.filter(stage=stage)
            # تأییدهای فاکتورها برای این مرحله
            stage_factor_approvals = [
                {
                    'factor': factor,
                    'approvals': factor_approvals.get(factor.id, []).filter(stage=stage)
                }
                for factor in context['factors']
            ]

            timeline_data.append({
                'stage': stage,
                'is_current': stage == tankhah.current_stage,
                'tankhah_approvals': [
                    {
                        'action': approval.action,
                        'user': approval.user.get_full_name() if approval.user else 'Unknown',
                        'post': approval.post.name if approval.post else 'Unknown',
                        'date': approval.created_at,
                        'comment': approval.comment or 'بدون توضیح'
                    } for approval in stage_tankhah_approvals
                ],
                'factors': [
                    {
                        'factor_number': f['factor'].number,
                        'approvals': [
                            {
                                'action': approval.action,
                                'user': approval.user.get_full_name() if approval.user else 'Unknown',
                                'post': approval.post.name if approval.post else 'Unknown',
                                'date': approval.created_at,
                                'comment': approval.comment or 'بدون توضیح'
                            } for approval in f['approvals']
                        ]
                    } for f in stage_factor_approvals
                ]
            })

        context['timeline_data'] = timeline_data
        context['budget_info'] = {
            'total': tankhah.project.get_total_budget() if hasattr(tankhah, 'project') and tankhah.project else 0,
            'remaining': tankhah.project.get_remaining_budget() if hasattr(tankhah, 'project') and tankhah.project else 0
        }
        context['can_create_payment'] = AccessRule.objects.filter(
            Q(post__in=user_posts) | Q(min_level__lte=user_posts.first().level, branch=user_posts.first().branch),
            organization=tankhah.organization,
            entity_type='PAYMENTORDER',
            action_type='APPROVE',
            is_active=True
        ).exists() and tankhah.status == 'APPROVED' and tankhah.current_stage.triggers_payment_order

        return context


class TankhahApprovalTimelineView(PermissionRequiredMixin, DetailView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_approval_timeline.html'
    context_object_name = 'tankhah'
    permission_required = ['tankhah.Tankhah_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز نیست')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # اگر کاربر سوپریوزر است، دسترسی کامل بده
        if user.is_superuser:
            logger.debug(f"[TankhahApprovalTimelineView] Superuser {user.username} accessing tankhah {obj.number}")
            return obj

        # استعلام پست‌های فعال کاربر
        user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True)

        # بررسی دسترسی بر اساس AccessRule
        if user_posts.exists():
            access_rules = AccessRule.objects.filter(
                Q(post__in=user_posts) |
                Q(
                    min_level__lte=user_posts.first().level,
                    branch=user_posts.first().branch
                ),
                organization=obj.organization,
                entity_type='TANKHAH',
                action_type='VIEW',
                is_active=True
            )
            if not access_rules.exists():
                logger.warning(f"User {user.username} lacks access به تنخواه {obj.number}")
                raise PermissionDenied(_('شما به این تنخواه دسترسی ندارید.'))
        else:
            logger.warning(f"User {user.username} has no active posts, denying access to tankhah {obj.number}")
            raise PermissionDenied(_('شما به هیچ پستی متصل نیستید و نمی‌توانید به این تنخواه دسترسی داشته باشید.'))

        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        user = self.request.user

        # اطلاعات تنخواه
        context['title'] = _(':توجه خطاها را اصلاح کنید') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all().select_related('locked_by_stage')

        # دریافت تمام مراحل فعال
        stages = WorkflowStage.objects.filter(is_active=True).order_by('order')

        # دریافت تأییدهای تنخواه و فاکتورها
        tankhah_approvals = ApprovalLog.objects.filter(
            tankhah=tankhah
        ).select_related('user', 'post', 'stage').order_by('timestamp')

        factor_approvals = {
            factor.id: ApprovalLog.objects.filter(
                factor=factor
            ).select_related('user', 'post', 'stage').order_by('timestamp')
            for factor in context['factors']
        }

        # ساخت خط زمانی
        timeline_data = []
        for stage in stages:
            stage_tankhah_approvals = tankhah_approvals.filter(stage=stage)
            stage_factor_approvals = [
                {
                    'factor': factor,
                    'approvals': factor_approvals.get(factor.id, []).filter(stage=stage)
                }
                for factor in context['factors']
            ]

            timeline_data.append({
                'stage': stage,
                'is_current': stage == tankhah.current_stage,
                'tankhah_approvals': [
                    {
                        'action': approval.action,
                        'user': approval.user.get_full_name() if approval.user else 'Unknown',
                        'post': approval.post.name if approval.post else 'Unknown',
                        'date': approval.timestamp,
                        'comment': approval.comment or 'بدون توضیح'
                    } for approval in stage_tankhah_approvals
                ],
                'factors': [
                    {
                        'factor_number': f['factor'].number,
                        'approvals': [
                            {
                                'action': approval.action,
                                'user': approval.user.get_full_name() if approval.user else 'Unknown',
                                'post': approval.post.name if approval.post else 'Unknown',
                                'date': approval.timestamp,
                                'comment': approval.comment or 'بدون توضیح'
                            } for approval in f['approvals']
                        ]
                    } for f in stage_factor_approvals
                ]
            })

        context['timeline_data'] = timeline_data
        context['budget_info'] = {
            'total': tankhah.project.get_total_budget() if tankhah.project else 0,
            'remaining': tankhah.project.get_remaining_budget() if tankhah.project else 0
        }

        # بررسی امکان ایجاد پرداخت
        can_create_payment = False
        user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True)
        if user.is_superuser:
            can_create_payment = tankhah.status == 'APPROVED' and tankhah.current_stage and tankhah.current_stage.triggers_payment_order
        elif user_posts.exists():
            can_create_payment = (
                AccessRule.objects.filter(
                    Q(post__in=user_posts) |
                    Q(
                        min_level__lte=user_posts.first().level,
                        branch=user_posts.first().branch
                    ),
                    organization=tankhah.organization,
                    entity_type='PAYMENT_ORDER',
                    action_type='APPROVE',
                    is_active=True
                ).exists()
                and tankhah.status == 'APPROVED'
                and tankhah.current_stage and tankhah.current_stage.triggers_payment_order
            )

        context['can_create_payment'] = can_create_payment
        logger.debug(f"[TankhahApprovalTimelineView] Context prepared for tankhah {tankhah.number}, can_create_payment: {can_create_payment}")

        return context