from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from notifications.signals import notify
from accounts.models import CustomUser
from core.models import UserPost
from .fun_can_edit_approval import can_edit_approval
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
                notify.send(
                    self.request.user,
                    recipient=lower_users,
                    verb='تنخواه شما توسط رده بالاتر دیده شد',
                    target=tankhah
                )

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        context['title'] = _('پیگیری تنخواه') + f" - {tankhah.number}"
        context['factors'] = tankhah.factors.all().prefetch_related('items__approval_logs', 'documents', 'approval_logs')
        context['documents'] = tankhah.documents.all()

        workflow_stages = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('-order')
        current_stage = tankhah.current_stage
        if not current_stage:
            tankhah.current_stage = workflow_stages.first()
            tankhah.save()

        stages_data = []
        from django.db.models import Q
        for stage in WorkflowStage.objects.order_by('-order'):
            approvals = ApprovalLog.objects.filter(
                Q(tankhah=tankhah) |
                Q(factor__tankhah=tankhah) |
                Q(factor_item__factor__tankhah=tankhah),
                stage=stage
            ).select_related('user', 'post').filter(post__level__lte=max_change_level)

            is_completed = approvals.filter(action='APPROVE').exists() and stage.order < tankhah.current_stage.order
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
                    if approver.post.level <= max_change_level
                ],
            })
        context['stages'] = stages_data
        context['can_change_stage'] = can_edit_approval(user, tankhah, tankhah.current_stage)
        context['workflow_stages'] = workflow_stages
        context['can_approve_factor'] = self.request.user.has_perm('tankhah.FactorItem_approve') and can_edit_approval(user, tankhah, tankhah.current_stage)
        context['can_archive'] = not tankhah.is_archived and self.request.user.has_perm('tankhah.Tankhah_change')
        return context

#==  وضعیت کلی تنخواه ها
class TankhahStatusView(PermissionBaseView, ListView):
    model = Tankhah
    template_name = 'tankhah/Reports/tankhah_status.html'
    context_object_name = 'tankhahs'
    permission_required = ['tankhah.Tankhah_view']
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_queryset(self):
        user = self.request.user
        # دریافت پست‌های فعال کاربر
        user_posts = Post.objects.filter(
            userpost__user=user,
            userpost__is_active=True,
            userpost__end_date__isnull=True
        )
        if not user_posts.exists():
            logger.warning(f"User {user.username} has no active posts")
            raise PermissionDenied(_('شما پست فعالی ندارید.'))

        # دریافت سازمان‌های مجاز
        user_orgs = Organization.objects.filter(
            Q(post__in=user_posts) | Q(post__userpost__user=user)
        ).distinct()

        # بررسی دسترسی بر اساس AccessRule
        access_rules = AccessRule.objects.filter(
            Q(post__in=user_posts) | Q(min_level__lte=user_posts.first().level, branch=user_posts.first().branch),
            organization__in=user_orgs,
            entity_type__in=['TANKHAH', 'FACTOR'],
            action_type='VIEW',
            is_active=True
        )
        if not access_rules.exists():
            logger.warning(f"User {user.username} lacks access rules for TANKHAH/FACTOR")
            raise PermissionDenied(_('شما اجازه مشاهده تنخواه یا فاکتور را ندارید.'))

        # فیلتر تنخواه‌ها بر اساس سازمان و دسترسی
        queryset = Tankhah.objects.filter(
            organization__in=user_orgs
        ).select_related('current_stage', 'organization', 'project', 'subproject').prefetch_related('factors')

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_posts = Post.objects.filter(userpost__user=user, userpost__is_active=True)
        context['title'] = _('وضعیت تنخواه‌ها و فاکتورها')

        # جمع‌آوری اطلاعات مراحل و وضعیت‌ها
        tankhahs_data = []
        for tankhah in self.object_list:
            factors = tankhah.factors.all()#.select_related('current_stage')
            payment_stage = WorkflowStage.objects.filter(triggers_payment_order=True, is_active=True).first()

            # وضعیت بودجه
            budget_info = {
                'total': tankhah.project.get_total_budget() if tankhah.project else 0,
                'remaining': tankhah.project.get_remaining_budget() if tankhah.project else 0,
            } if hasattr(tankhah, 'project') and tankhah.project else {'total': 0, 'remaining': 0}

            # بررسی دسترسی برای تغییر مرحله یا تأیید
            can_view_details = AccessRule.objects.filter(
                Q(post__in=user_posts) | Q(min_level__lte=user_posts.first().level, branch=user_posts.first().branch),
                organization=tankhah.organization,
                entity_type='TANKHAH',
                action_type='VIEW',
                is_active=True
            ).exists()

            tankhahs_data.append({
                'tankhah': tankhah,
                'current_stage': tankhah.current_stage,
                'status': tankhah.status,
                # 'factors': [
                #     {
                #         'factor': factor,
                #         'current_stage': factor.current_stage,
                #         'status': factor.status
                #     } for factor in factors
                # ],
                'budget': budget_info,
                'can_view_details': can_view_details,
                'is_payment_ready': payment_stage and tankhah.current_stage == payment_stage and tankhah.status == 'APPROVED'
            })

        context['tankhahs_data'] = tankhahs_data
        context['workflow_stages'] = WorkflowStage.objects.filter(is_active=True).order_by('order')
        return context

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