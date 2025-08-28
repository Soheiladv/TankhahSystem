import json
import logging
from decimal import Decimal
from time import timezone

from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect
from tankhah.models import Tankhah,  StageApprover
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from core.PermissionBase import  PermissionBaseView
from django.db.models import Q, Sum, F, Count, Prefetch, DecimalField
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic import TemplateView

from core.forms import OrganizationForm, ProjectForm, PostForm, UserPostForm, PostHistoryForm, WorkflowStageForm, \
    SubProjectForm
from core.models import Project, Post, UserPost, PostHistory, AccessRule, SubProject, PostAction
from django.db.models import Sum, Q
from budgets.models import BudgetAllocation, BudgetPeriod, \
    BudgetTransaction  # فرض بر این که BudgetAllocation در budgets است
from budgets.budget_calculations import get_project_total_budget

from django.db.models import Q
from budgets.budget_calculations import get_project_remaining_budget, \
    get_project_used_budget, get_organization_budget
from core.models import Organization
from django.views.generic import ListView

#######################################################################################
# داشبورد آماری تنخواه گردان
"""این ویو استفاده نشده است ولی جدید ترین است"""
class OLD_DashboardView_flows(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_posts = user.userpost_set.filter(is_active=True).select_related('post')
        user_post_ids = [up.post.id for up in user_posts]
        user_orgs = [up.post.organization for up in user_posts] if user_posts else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False

        # گرفتن مراحل گردش کار
        workflow_stages = AccessRule.objects.all().order_by('-order')
        entities_by_stage = {}

        for stage in workflow_stages:
            # تنخواه‌ها در این مرحله
            stage_tankhahs = Tankhah.objects.filter(current_stage=stage)
            if not is_hq_user and not user.is_superuser:
                stage_tankhahs = stage_tankhahs.filter(organization__in=user_orgs)

            # تخصیص‌های بودجه در این مرحله
            stage_budget_allocations = BudgetAllocation.objects.all()#.filter(current_stage=stage)
            if not is_hq_user and not user.is_superuser:
                stage_budget_allocations = stage_budget_allocations.filter(organization__in=user_orgs)

            # بررسی مجوزهای تأیید/رد
            can_approve_tankhah = user.has_perm('tankhah.Tankhah_approve') and any(
                PostAction.objects.filter(
                    post__in=user_post_ids,
                    stage=stage,
                    action_type='APPROVE',
                    entity_type='TANKHAH',
                    is_active=True
                ).exists()
                for p in user_posts
            )
            can_reject_tankhah = user.has_perm('tankhah.Tankhah_reject') and any(
                PostAction.objects.filter(
                    post__in=user_post_ids,
                    stage=stage,
                    action_type='REJECT',
                    entity_type='TANKHAH',
                    is_active=True
                ).exists()
                for p in user_posts
            )
            can_approve_budget = user.has_perm('budgets.BudgetAllocation_approve') and any(
                PostAction.objects.filter(
                    post__in=user_post_ids,
                    stage=stage,
                    action_type='APPROVE',
                    entity_type='BUDGET_ALLOCATION',
                    is_active=True
                ).exists()
                for p in user_posts
            )
            can_reject_budget = user.has_perm('budgets.BudgetAllocation_reject') and any(
                PostAction.objects.filter(
                    post__in=user_post_ids,
                    stage=stage,
                    action_type='REJECT',
                    entity_type='BUDGET_ALLOCATION',
                    is_active=True
                ).exists()
                for p in user_posts
            )

            # تأییدکنندگان مرحله
            approvers = StageApprover.objects.filter(stage=stage, is_active=True).select_related('post')

            # تعیین رنگ و برچسب
            if stage_tankhahs.filter(status='DRAFT').exists():# or stage_budget_allocations.filter(status='DRAFT').exists():
                color_class = 'bg-warning'
                status_label = 'پیش‌نویس'
            elif stage_tankhahs.filter(status='REJECTED').exists(): #or stage_budget_allocations.filter(status='REJECTED').exists():
                color_class = 'bg-danger'
                status_label = 'رد شده'
            elif stage_tankhahs.filter(status='APPROVED').exists() :#or stage_budget_allocations.filter(status='APPROVED').exists():
                color_class = 'bg-success'
                status_label = 'تأیید شده'
            elif stage_tankhahs.filter(status='PAID').exists():
                color_class = 'bg-primary'
                status_label = 'پرداخت شده'
            else:
                color_class = 'bg-info'
                status_label = 'در حال بررسی'

            entities_by_stage[stage] = {
                'tankhah_count': stage_tankhahs.count(),
                'budget_allocation_count': stage_budget_allocations.count(),
                'color_class': color_class,
                'status_label': status_label,
                'tankhahs': stage_tankhahs,
                'budget_allocations': stage_budget_allocations,
                'can_approve_tankhah': can_approve_tankhah,
                'can_reject_tankhah': can_reject_tankhah,
                'can_approve_budget': can_approve_budget,
                'can_reject_budget': can_reject_budget,
                'approvers': [approver.post.name for approver in approvers],
            }

        context['entities_by_stage'] = entities_by_stage
        context['workflow_stages'] = workflow_stages
        return context

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Prefetch
from django.core.cache import cache
from collections import defaultdict
import logging

logger = logging.getLogger("DashboardFlowsView")
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist

#--------------------------------------------------------------

class DashboardView_flows_______(TemplateView):
    template_name = 'core/dashboard_Status_1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cache_key = f"dashboard_flows_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data and not self.request.GET.get('refresh'):
            context.update(cached_data)
            return context

        try:
            user_info = self._get_user_info(user)
            workflow_data = self._get_workflow_data(user_info)
            summary_stats = self._get_summary_stats(user_info)

            context.update({
                'user_info': user_info,
                'workflow_data': workflow_data,
                'summary_stats': summary_stats,
                'page_title': 'داشبورد گردش کار',
            })

            cache.set(cache_key, {
                'user_info': user_info,
                'workflow_data': workflow_data,
                'summary_stats': summary_stats,
            }, 60)  # کاهش زمان کش به 60 ثانیه برای داده‌های پویا

        except DatabaseError as e:
            logger.error(f"خطای پایگاه داده برای کاربر {user.username}: {e}")
            context['error_message'] = "خطا در ارتباط با پایگاه داده"
        except ObjectDoesNotExist as e:
            logger.error(f"داده‌ای برای کاربر {user.username} یافت نشد: {e}")
            context['error_message'] = "داده‌ای یافت نشد"
        except Exception as e:
            logger.error(f"خطای غیرمنتظره برای کاربر {user.username}: {e}")
            context['error_message'] = "خطا در بارگذاری داده‌ها"

        return context

    def _get_user_info(self, user):
        """استخراج اطلاعات کاربر و سازمان‌ها"""
        user_posts = user.userpost_set.filter(
            is_active=True
        ).select_related(
            'post__organization', 'post__branch'
        ).only(
            'post__organization__org_type',
            'post__organization__name',
            'post__level',
            'post__name',
            'post__branch__name'
        )

        user_orgs = list(set(up.post.organization for up in user_posts))
        is_hq_user = any(org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type)

        return {
            'user': user,
            'user_posts': user_posts,
            'user_orgs': user_orgs,
            'is_hq_user': is_hq_user,
            'is_admin': user.is_superuser or is_hq_user,
        }

    def _get_workflow_data(self, user_info):
        """دریافت داده‌های گردش کار بهینه"""
        stages = AccessRule.objects.filter(is_active=True).order_by('stage_order').select_related('post', 'organization', 'branch').distinct()

        workflow_data = []
        for stage in stages:
            stage_data = self._process_stage_data(stage, user_info)
            workflow_data.append(stage_data)

        return workflow_data

    def _process_stage_data(self, stage, user_info):
        """پردازش داده‌های هر مرحله"""
        # استفاده از approval_logs برای تعیین تنخواه‌های مرتبط با مرحله
        base_tankhah_qs = Tankhah.objects.filter(
            approval_logs__stage=stage.stage,
            approval_logs__stage_order=stage.stage_order
        ).distinct()

        base_budget_qs = BudgetAllocation.objects.filter(
            stage=stage.stage,
            stage_order=stage.stage_order
        )

        if not user_info['is_admin']:
            base_tankhah_qs = base_tankhah_qs.filter(organization__in=user_info['user_orgs'])
            base_budget_qs = base_budget_qs.filter(organization__in=user_info['user_orgs'])

        tankhah_stats = base_tankhah_qs.aggregate(
            total=Count('id'),
            draft=Count('id', filter=Q(status='DRAFT')),
            pending=Count('id', filter=Q(status='PENDING')),
            approved=Count('id', filter=Q(status='APPROVED')),
            rejected=Count('id', filter=Q(status='REJECTED')),
            paid=Count('id', filter=Q(status='PAID')),
        )

        permissions = self._get_user_stage_permissions(stage, user_info)

        approvers = []
        if stage.post:
            approvers.append({
                'name': stage.post.name,
                'organization': stage.organization.name,
                'level': stage.post.level,
                'branch': stage.post.branch.name if stage.post.branch else None,
            })

        return {
            'stage': stage,
            'tankhah_stats': tankhah_stats or {'total': 0, 'draft': 0, 'pending': 0, 'approved': 0, 'rejected': 0, 'paid': 0},
            'permissions': permissions,
            'approvers': approvers,
            'recent_items': self._get_recent_items(base_tankhah_qs, base_budget_qs),
        }

    def _determine_stage_status(self, tankhah_stats):
        """تعیین وضعیت و رنگ مرحله"""
        total_items = tankhah_stats['total']

        if total_items == 0:
            return {'class': 'secondary', 'label': 'خالی', 'priority': 0}
        if tankhah_stats['rejected'] > 0:
            return {'class': 'danger', 'label': 'رد شده', 'priority': 4}
        if tankhah_stats['draft'] > 0:
            return {'class': 'warning', 'label': 'پیش‌نویس', 'priority': 3}
        if tankhah_stats['pending'] > 0:
            return {'class': 'info', 'label': 'در انتظار', 'priority': 2}
        if tankhah_stats['paid'] > 0:
            return {'class': 'primary', 'label': 'پرداخت شده', 'priority': 1}
        if tankhah_stats['approved'] > 0:
            return {'class': 'success', 'label': 'تأیید شده', 'priority': 1}
        return {'class': 'info', 'label': 'در حال بررسی', 'priority': 2}

    def _get_user_stage_permissions(self, stage, user_info):
        """بررسی دسترسی‌های کاربر برای هر مرحله"""
        permissions = {
            'can_approve_tankhah': False,
            'can_reject_tankhah': False,
            'can_approve_budget': False,
            'can_reject_budget': False,
            'can_final_approve_tankhah': False,
        }

        if user_info['is_admin']:
            return {key: True for key in permissions.keys()}

        for user_post in user_info['user_posts']:
            if stage.post == user_post.post and stage.organization in user_info['user_orgs']:
                if stage.action_type == 'APPROVE' and user_info['user'].has_perm('tankhah.Tankhah_approve'):
                    permissions['can_approve_tankhah'] = True
                if stage.action_type == 'REJECT' and user_info['user'].has_perm('tankhah.Tankhah_reject'):
                    permissions['can_reject_tankhah'] = True
                if stage.action_type == 'APPROVE' and user_info['user'].has_perm('budgets.BudgetAllocation_approve'):
                    permissions['can_approve_budget'] = True
                if stage.action_type == 'REJECT' and user_info['user'].has_perm('budgets.BudgetAllocation_reject'):
                    permissions['can_reject_budget'] = True
                if stage.is_final_stage and user_post.post.can_final_approve_tankhah:
                    permissions['can_final_approve_tankhah'] = True

        return permissions

    def _get_recent_items(self, tankhah_qs, budget_qs, limit=5):
        """دریافت آیتم‌های اخیر"""
        recent_tankhahs = list(tankhah_qs.order_by('-created_at')[:limit].values(
            'id', 'number', 'amount', 'status', 'created_at', 'organization__name'
        ))
        recent_budgets = list(budget_qs.order_by('-created_at')[:limit].values(
            'id', 'budget_period__name', 'allocated_amount', 'is_locked', 'created_at', 'organization__name'
        ))
        return {
            'tankhahs': recent_tankhahs,
            'budgets': recent_budgets,
        }

    def _get_summary_stats(self, user_info):
        """آمار کلی داشبورد"""
        base_tankhah_qs = Tankhah.objects.all()
        base_budget_qs = BudgetAllocation.objects.all()

        if not user_info['is_admin']:
            base_tankhah_qs = base_tankhah_qs.filter(organization__in=user_info['user_orgs'])
            base_budget_qs = base_budget_qs.filter(organization__in=user_info['user_orgs'])

        return {
            'total_tankhahs': base_tankhah_qs.count(),
            'pending_tankhahs': base_tankhah_qs.filter(status='PENDING').count(),
            'total_budgets': base_budget_qs.count(),
            'pending_budgets': base_budget_qs.filter(is_active=True, is_locked=False).count(),
            'my_tasks': self._get_user_tasks_count(user_info),
        }

    def _get_user_tasks_count(self, user_info):
        """تعداد وظایف کاربر"""
        if user_info['is_admin']:
            return Tankhah.objects.filter(status='PENDING').count()

        task_count = 0
        for stage in AccessRule.objects.filter(is_active=True, organization__in=user_info['user_orgs']):
            if stage.post in [up.post for up in user_info['user_posts']]:
                task_count += Tankhah.objects.filter(
                    status='PENDING',
                    approval_logs__stage=stage.stage,
                    approval_logs__stage_order=stage.stage_order,
                    organization__in=user_info['user_orgs']
                ).distinct().count()

        return task_count

class DashboardView_flows(TemplateView):
    template_name = 'core/dashboard_Status_1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cache_key = f"dashboard_flows_{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data and not self.request.GET.get('refresh'):
            context.update(cached_data)
            return context

        try:
            user_info = self._get_user_info(user)
            workflow_data = self._get_workflow_data(user_info)
            summary_stats = self._get_summary_stats(user_info)

            context.update({
                'user_info': user_info,
                'workflow_data': workflow_data,
                'summary_stats': summary_stats,
                'page_title': 'داشبورد گردش کار',
            })

            cache.set(cache_key, {
                'user_info': user_info,
                'workflow_data': workflow_data,
                'summary_stats': summary_stats,
            }, 60)  # 60 ثانیه کش برای داده‌های پویا

        except DatabaseError as e:
            logger.error(f"خطای پایگاه داده برای کاربر {user.username}: {e}")
            context['error_message'] = "خطا در ارتباط با پایگاه داده"
        except ObjectDoesNotExist as e:
            logger.error(f"داده‌ای برای کاربر {user.username} یافت نشد: {e}")
            context['error_message'] = "داده‌ای یافت نشد"
        except Exception as e:
            logger.error(f"خطای غیرمنتظره برای کاربر {user.username}: {e}")
            context['error_message'] = "خطا در بارگذاری داده‌ها"

        return context

    def _get_user_info(self, user):
        """استخراج اطلاعات کاربر و سازمان‌ها"""
        user_posts = user.userpost_set.filter(
            is_active=True
        ).select_related(
            'post__organization', 'post__branch'
        ).only(
            'post__organization__org_type',
            'post__organization__name',
            'post__level',
            'post__name',
            'post__branch__name'
        )

        user_orgs = list(set(up.post.organization for up in user_posts))
        is_hq_user = any(org.org_type.org_type == 'HQ' for org in user_orgs if org.org_type)

        return {
            'user': user,
            'user_posts': user_posts,
            'user_orgs': user_orgs,
            'is_hq_user': is_hq_user,
            'is_admin': user.is_superuser or is_hq_user,
        }

    def _get_workflow_data(self, user_info):
        """دریافت داده‌های گردش کار بهینه"""
        stages = AccessRule.objects.filter(is_active=True).order_by('stage_order').select_related('post', 'organization', 'branch').distinct()

        workflow_data = []
        for stage in stages:
            stage_data = self._process_stage_data(stage, user_info)
            workflow_data.append(stage_data)

        return workflow_data

    def _process_stage_data(self, stage, user_info):
        """پردازش داده‌های هر مرحله"""
        # به جای approval_logs، از فیلتر کلی بر اساس سازمان و status استفاده می‌کنیم
        base_tankhah_qs = Tankhah.objects.all()
        base_budget_qs = BudgetAllocation.objects.all()

        if not user_info['is_admin']:
            base_tankhah_qs = base_tankhah_qs.filter(organization__in=user_info['user_orgs'])
            base_budget_qs = base_budget_qs.filter(organization__in=user_info['user_orgs'])

        # برای نمایش مراحل، فرض می‌کنیم هر مرحله می‌تونه تنخواه‌های خاصی رو نشون بده
        tankhah_stats = base_tankhah_qs.aggregate(
            total=Count('id'),
            draft=Count('id', filter=Q(status='DRAFT')),
            pending=Count('id', filter=Q(status='PENDING')),
            approved=Count('id', filter=Q(status='APPROVED')),
            rejected=Count('id', filter=Q(status='REJECTED')),
            paid=Count('id', filter=Q(status='PAID')),
        )

        permissions = self._get_user_stage_permissions(stage, user_info)

        approvers = []
        if stage.post:
            approvers.append({
                'name': stage.post.name,
                'organization': stage.organization.name,
                'level': stage.post.level,
                'branch': stage.post.branch.name if stage.post.branch else None,
            })

        return {
            'stage': stage,
            'tankhah_stats': tankhah_stats or {'total': 0, 'draft': 0, 'pending': 0, 'approved': 0, 'rejected': 0, 'paid': 0},
            'permissions': permissions,
            'approvers': approvers,
            'recent_items': self._get_recent_items(base_tankhah_qs, base_budget_qs),
        }

    def _determine_stage_status(self, tankhah_stats):
        """تعیین وضعیت و رنگ مرحله"""
        total_items = tankhah_stats['total']

        if total_items == 0:
            return {'class': 'secondary', 'label': 'خالی', 'priority': 0}
        if tankhah_stats['rejected'] > 0:
            return {'class': 'danger', 'label': 'رد شده', 'priority': 4}
        if tankhah_stats['draft'] > 0:
            return {'class': 'warning', 'label': 'پیش‌نویس', 'priority': 3}
        if tankhah_stats['pending'] > 0:
            return {'class': 'info', 'label': 'در انتظار', 'priority': 2}
        if tankhah_stats['paid'] > 0:
            return {'class': 'primary', 'label': 'پرداخت شده', 'priority': 1}
        if tankhah_stats['approved'] > 0:
            return {'class': 'success', 'label': 'تأیید شده', 'priority': 1}
        return {'class': 'info', 'label': 'در حال بررسی', 'priority': 2}

    def _get_user_stage_permissions(self, stage, user_info):
        """بررسی دسترسی‌های کاربر برای هر مرحله"""
        permissions = {
            'can_approve_tankhah': False,
            'can_reject_tankhah': False,
            'can_approve_budget': False,
            'can_reject_budget': False,
            'can_final_approve_tankhah': False,
        }

        if user_info['is_admin']:
            return {key: True for key in permissions.keys()}

        for user_post in user_info['user_posts']:
            if stage.post == user_post.post and stage.organization in user_info['user_orgs']:
                if stage.action_type == 'APPROVE' and user_info['user'].has_perm('tankhah.Tankhah_approve'):
                    permissions['can_approve_tankhah'] = True
                if stage.action_type == 'REJECT' and user_info['user'].has_perm('tankhah.Tankhah_reject'):
                    permissions['can_reject_tankhah'] = True
                if stage.action_type == 'APPROVE' and user_info['user'].has_perm('budgets.BudgetAllocation_approve'):
                    permissions['can_approve_budget'] = True
                if stage.action_type == 'REJECT' and user_info['user'].has_perm('budgets.BudgetAllocation_reject'):
                    permissions['can_reject_budget'] = True
                if stage.is_final_stage and user_post.post.can_final_approve_tankhah:
                    permissions['can_final_approve_tankhah'] = True

        return permissions

    def _get_recent_items(self, tankhah_qs, budget_qs, limit=5):
        """دریافت آیتم‌های اخیر"""
        recent_tankhahs = list(tankhah_qs.order_by('-created_at')[:limit].select_related('organization').values(
            'id', 'number', 'amount', 'status', 'created_at', 'organization__name'
        ))
        recent_budgets = list(budget_qs.order_by('-created_at')[:limit].select_related('organization').values(
            'id', 'budget_period__name', 'allocated_amount', 'is_locked', 'created_at', 'organization__name'
        ))
        return {
            'tankhahs': recent_tankhahs,
            'budgets': recent_budgets,
        }

    def _get_summary_stats(self, user_info):
        """آمار کلی داشبورد"""
        base_tankhah_qs = Tankhah.objects.all()
        base_budget_qs = BudgetAllocation.objects.all()

        if not user_info['is_admin']:
            base_tankhah_qs = base_tankhah_qs.filter(organization__in=user_info['user_orgs'])
            base_budget_qs = base_budget_qs.filter(organization__in=user_info['user_orgs'])

        tankhah_status_counts = base_tankhah_qs.values('status').annotate(count=Count('id'))
        budget_status_counts = base_budget_qs.values('is_active', 'is_locked').annotate(count=Count('id'))

        return {
            'total_tankhahs': base_tankhah_qs.count(),
            'pending_tankhahs': base_tankhah_qs.filter(status='PENDING').count(),
            'total_budgets': base_budget_qs.count(),
            'pending_budgets': base_budget_qs.filter(is_active=True, is_locked=False).count(),
            'my_tasks': self._get_user_tasks_count(user_info),
            'tankhah_status_counts': list(tankhah_status_counts),
            'budget_status_counts': list(budget_status_counts),
        }

    def _get_user_tasks_count(self, user_info):
        """تعداد وظایف کاربر"""
        if user_info['is_admin']:
            return Tankhah.objects.filter(status='PENDING').count()

        task_count = 0
        for stage in AccessRule.objects.filter(is_active=True, organization__in=user_info['user_orgs']):
            if stage.post in [up.post for up in user_info['user_posts']]:
                task_count += Tankhah.objects.filter(
                    status='PENDING',
                    organization__in=user_info['user_orgs']
                ).count()

        return task_count
#--------------------------------------------------------------

class  new__DashboardView_flows( TemplateView):
    template_name = 'reports/report_Flow_tankhah/dashboard_creative_v2.html'  # نام تمپلیت خلاقانه و جدید

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cache_key = f"dashboard_creative_v2_{user.id}"

        # مدیریت کش
        if not self.request.GET.get('refresh'):
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Returning cached dashboard data for user {user.username}")
                context.update(cached_data)
                return context

        logger.info(f"Generating new dashboard data for user {user.username}")
        try:
            # --- گام ۱: دریافت اطلاعات پایه کاربر ---
            user_info = self._get_user_info(user)
            context['user_info'] = user_info

            # --- گام ۲: آماده‌سازی داده‌های گردش کار (برای برد کانبان) ---
            workflow_data = self._get_workflow_data(user_info)
            context['workflow_data'] = workflow_data

            # --- گام ۳: محاسبه آمار کلی و داده‌های نمودار ---
            # از workflow_data برای برخی محاسبات استفاده می‌کنیم تا کوئری تکراری نزنیم
            summary_stats = self._get_summary_stats(user_info, workflow_data)
            context['summary_stats'] = summary_stats

            # --- گام ۴: تنظیم عنوان صفحه و ذخیره در کش ---
            context['page_title'] = _("مرکز فرماندهی مالی")

            # ذخیره تمام context تولید شده در کش
            # (به جز page_title که می‌توان در هر بار لود تنظیم کرد)
            data_to_cache = {
                'user_info': context['user_info'],
                'workflow_data': context['workflow_data'],
                'summary_stats': context['summary_stats'],
                'page_title': context['page_title'],  # ذخیره عنوان هم اشکالی ندارد
            }
            cache.set(cache_key, data_to_cache, timeout=300)  # کش برای ۵ دقیقه
            logger.info(f"Dashboard data for user {user.username} cached successfully.")

        except DatabaseError as e:
            logger.error(f"Database error loading dashboard for user {user.username}: {e}", exc_info=True)
            context['error_message'] = _("خطایی در ارتباط با پایگاه داده رخ داده است. لطفاً بعداً تلاش کنید.")
        except ObjectDoesNotExist as e:
            logger.error(f"Data not found for dashboard of user {user.username}: {e}", exc_info=True)
            context['error_message'] = _("برخی از داده‌های مورد نیاز برای نمایش داشبورد یافت نشد.")
        except Exception as e:
            logger.error(f"Unexpected error loading dashboard for user {user.username}: {e}", exc_info=True)
            context['error_message'] = _("خطای پیش‌بینی نشده‌ای در بارگذاری داده‌های داشبورد رخ داد.")

        return context

    def _get_user_info(self, user):
        """اطلاعات پایه کاربر، پست‌ها و سازمان‌هایش را واکشی می‌کند."""
        logger.debug(f"_get_user_info for {user.username}")
        # select_related برای بهینه‌سازی دسترسی به سازمان و نوع سازمان
        user_posts = user.userpost_set.filter(is_active=True, end_date__isnull=True).select_related('post',
                                                                                                    'post__organization',
                                                                                                    'post__organization__org_type')
        user_orgs = list(set(up.post.organization for up in user_posts if up.post and up.post.organization))
        is_hq_user = any(org.org_type and org.org_type.org_type == 'HQ' for org in user_orgs)

        return {
            'user': user,
            'user_posts': user_posts,
            'user_orgs': user_orgs,
            'is_hq_user': is_hq_user,
            'is_admin': user.is_superuser or is_hq_user,
        }

    def _get_workflow_data(self, user_info):
        """داده‌های مربوط به هر مرحله گردش کار را برای نمایش کانبان آماده می‌کند."""
        logger.debug(f"_get_workflow_data for {user_info['user'].username}")
        # فقط مراحل فعال تنخواه را در نظر می‌گیریم (با فرض وجود entity_type)
        # و تاییدکنندگان را prefetch می‌کنیم
        stages_qs = AccessRule.objects.filter(is_active=True)
        if hasattr(AccessRule, 'entity_type'):
            stages_qs = stages_qs.filter(entity_type='TANKHAH')

        stages = stages_qs.order_by('order').prefetch_related(
            Prefetch('stageapprover_set',
                     queryset=StageApprover.objects.filter(is_active=True).select_related('post', 'post__organization'),
                     to_attr='active_approvers')
        )

        workflow_data_list = []
        for stage in stages:
            # ۱. ساخت کوئری پایه برای تنخواه‌های این مرحله
            base_tankhah_qs = Tankhah.objects.filter(current_stage=stage)
            if not user_info['is_admin']:
                base_tankhah_qs = base_tankhah_qs.filter(organization__in=user_info['user_orgs'])

            # ۲. محاسبه آمار وضعیت‌ها در این مرحله
            tankhah_stats = base_tankhah_qs.aggregate(
                total=Count('id'),
                draft=Count('id', filter=Q(status='DRAFT')),
                pending=Count('id', filter=Q(status='PENDING')),
                approved=Count('id', filter=Q(status='APPROVED')),
                rejected=Count('id', filter=Q(status='REJECTED')),
                paid=Count('id', filter=Q(status='PAID')),
            )

            # ۳. استخراج تاییدکنندگان از prefetch
            approvers = [
                {
                    'name': approver.post.name,
                    'organization': approver.post.organization.name if approver.post.organization else None,
                }
                for approver in getattr(stage, 'active_approvers', []) if approver.post
            ]

            # ۴. واکشی چند تنخواه اخیر در این مرحله برای نمایش در کارت کانبان
            recent_tankhahs = list(base_tankhah_qs.select_related(
                'organization', 'created_by'
            ).order_by('-updated_at')[:5].values(  # یا created_at
                'id', 'number', 'amount', 'status', 'created_at', 'organization__name', 'created_by__first_name',
                'created_by__username'
            ))

            workflow_data_list.append({
                'stage': stage,
                'tankhah_stats': tankhah_stats,
                # 'permissions': self._get_user_stage_permissions(stage, user_info), # اگر لازم است
                'approvers': approvers,
                'recent_items': {'tankhahs': recent_tankhahs},
            })
        return workflow_data_list

    def _get_summary_stats(self, user_info, workflow_data):
        """آمار کلی داشبورد، KPI ها و داده‌های نمودار را محاسبه می‌کند."""
        logger.debug(f"_get_summary_stats for {user_info['user'].username}")

        # --- ۱. محاسبه KPI های اصلی ---
        # کل بودجه فعال
        total_active_budget_amount = BudgetPeriod.objects.filter(
            is_active=True, is_completed=False
        ).aggregate(
            total=Coalesce(Sum('total_amount'), Decimal('0'), output_field=DecimalField())
        )['total']

        # کل مصرف شده
        total_consumed_amount = BudgetTransaction.objects.filter(
            allocation__budget_period__is_active=True,
            allocation__budget_period__is_completed=False,
            transaction_type='CONSUMPTION'
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0'), output_field=DecimalField())
        )['total']

        # تعداد تنخواه‌های در گردش (در انتظار تایید)
        # این را می‌توانیم از workflow_data جمع بزنیم تا کوئری تکراری نزنیم
        pending_tankhahs_count = sum(stage['tankhah_stats'].get('pending', 0) for stage in workflow_data)

        # تعداد وظایف من (تنخواه‌هایی که در مرحله‌ای هستند که من تاییدکننده آن هستم و منتظرند)
        user_posts_pks = [up.post.pk for up in user_info['user_posts']]
        my_tasks_count = Tankhah.objects.filter(
            status='PENDING',
            current_stage__stageapprover__post__pk__in=user_posts_pks
        ).distinct().count()

        total_remaining_budget = total_active_budget_amount - total_consumed_amount

        # --- ۲. آماده‌سازی داده‌ها برای نمودارهای Sparkline (مثال: روند مصرف ۶ ماه گذشته) ---
        today = timezone.now().date()
        consumption_trend_list = []
        for i in range(5, -1, -1):  # از ۵ ماه قبل تا ماه جاری
            # محاسبه اولین و آخرین روز هر ماه
            from datetime import timedelta
            first_day_of_month = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            next_month = first_day_of_month + timedelta(days=32)
            last_day_of_month = next_month.replace(day=1) - timedelta(days=1)

            monthly_consumption = BudgetTransaction.objects.filter(
                transaction_type='CONSUMPTION',
                timestamp__date__range=(first_day_of_month, last_day_of_month)
            ).aggregate(total=Coalesce(Sum('amount'), Decimal('0')))['total']

            consumption_trend_list.append(float(monthly_consumption))

        # --- ۳. ساخت دیکشنری نهایی آمار ---
        summary_stats = {
            'my_tasks': my_tasks_count,
            'total_budgets': total_active_budget_amount,
            'total_spent_formatted': f"{total_consumed_amount:,.0f}",
            'total_remaining_formatted': f"{total_remaining_budget:,.0f}",
            'total_remaining_percentage': (
                        total_remaining_budget / total_active_budget_amount * 100) if total_active_budget_amount > 0 else 0,
            'pending_tankhahs': pending_tankhahs_count,
            'consumption_trend_data': consumption_trend_list,
            'budget_trend_data': [],  # داده‌های روند بودجه را هم می‌توانید به همین روش محاسبه کنید
        }
        return summary_stats

"""داشبورد روند تنخواه‌گردانی با رنگ‌بندی و وضعیت مراحل"""
class DashboardView_flows_1( TemplateView):
    template_name = 'core/dashboard1.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}
    # permission_codenames = ['core.DashboardView_flows_view']  # تغییر به لیست

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user

        # گرفتن مراحل به ترتیب (پایین به بالا: order=5 تا order=0)
        workflow_stages = AccessRule.objects.all().order_by('-order')
        context['workflow_stages'] = workflow_stages

        # گرفتن پست‌های سازمانی کاربر
        user_posts = self.request.user.userpost_set.all()
        user_post_ids = [up.post.id for up in user_posts]
        logger.info(f"User {self.request.user} posts: {user_post_ids}")

        # دیکشنری برای ذخیره اطلاعات تنخواه‌ها
        Tankhah_by_stage = {}

        for stage in workflow_stages:
            # تنخواه‌ها در این مرحله
            Tankhahs = Tankhah.objects.filter(current_stage=stage)

            # شمارش تنخواه‌ها
            draft_count = Tankhahs.filter(status='DRAFT').count()
            created_by_user_count = Tankhahs.filter(created_by=self.request.user).count()
            rejected_count = Tankhahs.filter(status='REJECTED').count()
            completed_count = Tankhahs.filter(status='COMPLETED').count()

            # تعیین رنگ و برچسب بر اساس مرحله و وضعیت
            if stage.order == 5 and draft_count > 0:  # شروع فرآیند (پایین‌ترین)
                color_class = 'bg-warning'  # نارنجی
                status_label = 'پیش‌نویس (جدید)'
            elif stage.order == 0 and Tankhahs.exists():  # سوپروایزر یا معاون مالی (بالاترین)
                if completed_count > 0:
                    color_class = 'bg-primary'  # آبی
                    status_label = 'تمام‌شده'
                elif rejected_count > 0:
                    color_class = 'bg-danger'  # قرمز
                    status_label = 'رد شده'
                else:
                    color_class = 'bg-info'  # فیروزه‌ای برای در حال بررسی
                    status_label = 'در حال بررسی سوپروایزر'
            elif created_by_user_count > 0:  # ثبت‌شده توسط کاربر
                color_class = 'bg-success'  # سبز
                status_label = 'ثبت‌شده توسط شما'
            elif rejected_count > 0:  # رد شده
                color_class = 'bg-danger'  # قرمز
                status_label = 'رد شده'
            elif completed_count > 0:  # تمام‌شده
                color_class = 'bg-primary'  # آبی
                status_label = 'تمام‌شده'
            else:  # در حال بررسی در مراحل میانی
                color_class = 'bg-secondary'  # خاکستری
                status_label = 'در انتظار بررسی'

            total_count = Tankhahs.count()
            Tankhah_by_stage[stage] = {
                'count': total_count,
                'color_class': color_class,
                'status_label': status_label,
            }
            logger.info(
                f"Stage {stage.name} (order={stage.order}): {total_count} Tankhahs, Color: {color_class}, Status: {status_label}")

        context['Tankhah_by_stage'] = Tankhah_by_stage
        return context

"""یه نسخه دیگه از داشبورد با اطلاعات خلاصه و مجوز تأیید"""
class __DashboardView_flows(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard1.html'  # Adjust this to your actual template path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_posts = user.userpost_set.all()
        user_orgs = [up.post.organization for up in user_posts] if user_posts else []
        is_hq_user = any(org.org_type == 'HQ' for org in user_orgs) if user_orgs else False
        from budgets.models import BudgetPeriod
        budget_periods = BudgetPeriod.objects.filter( is_active=True) #organization=user.organization,
        # notifications = Notification.objects.filter( is_read=False)#recipient=user,
        budget_statuses = []
        # for period in budget_periods:
        #     status, message = period.check_budget_status()
        #     budget_statuses.append({
        #         'name': period.name,
        #         'remaining': period.get_remaining_amount(),
        #         'total': period.total_amount,
        #         'status': status,
        #         'message': message,
        #     })

        context['budget_statuses'] = budget_statuses
        # context['notifications'] = notifications

        # Filter Tankhah objects based on user permissions
        Tankhahs = Tankhah.objects.all()
        if not is_hq_user and not self.request.user.is_superuser:
            Tankhahs = Tankhahs.filter(organization__in=user_orgs)

        # Summary of Tankhah statuses
        context['Tankhah_summary'] = {
            'no_factor': {
                'count': Tankhahs.filter(factors__isnull=True).count(),
                'orgs': list(
                    Tankhahs.filter(factors__isnull=True).values_list('organization__name', flat=True).distinct())
            },
            'registered': {
                'count': Tankhahs.filter(factors__isnull=False).count(),
                'orgs': list(
                    Tankhahs.filter(factors__isnull=False).values_list('organization__name', flat=True).distinct())
            },
            'pending': {
                'count': Tankhahs.filter(status='PENDING').count(),
                'orgs': list(Tankhahs.filter(status='PENDING').values_list('organization__name', flat=True).distinct())
            },
            'archived': {
                'count': Tankhahs.filter(is_archived=True).count(),
                'orgs': list(Tankhahs.filter(is_archived=True).values_list('organization__name', flat=True).distinct())
            }
        }

        # Workflow stages with approvers
        workflow_stages = AccessRule.objects.all().order_by('-order')
        Tankhah_by_stage = {}
        for stage in workflow_stages:
            stage_Tankhahs = Tankhahs.filter(current_stage=stage)
            can_approve = user.has_perm('Tankhah.Tankhah_approve') and any(
                p.post.stageapprover_set.filter(stage=stage).exists() for p in user_posts
            )
            # Use 'post__name' instead of 'post__title'
            approvers = StageApprover.objects.filter(stage=stage).values_list('post__name', flat=True)

            Tankhah_by_stage[stage] = {
                'count': stage_Tankhahs.count(),
                'color_class': 'bg-info' if stage_Tankhahs.filter(status='PENDING').exists() else 'bg-secondary',
                'status_label': 'در انتظار تأیید' if stage_Tankhahs.filter(
                    status='PENDING').exists() else 'بدون تنخواه',
                'Tankhahs': stage_Tankhahs,
                'can_approve': can_approve,
                'approvers': list(approvers),
            }
        context['Tankhah_by_stage'] = Tankhah_by_stage

        return context

#-- داشبورد گزارشات مالی
"""داشبورد مالی با گزارشات آماری و چارت"""

# یه انکودر سفارشی برای تبدیل Decimal به float
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class AllLinksView(PermissionBaseView, TemplateView):
    template_name = 'core/core_index.html'  # تمپلیت Index
    extra_context = {'title': _('همه لینک‌ها')}
    # permission_codename = 'core.Project_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # تعریف دستی لینک‌ها - می‌تونید از URLResolver هم استفاده کنید
        context['links'] = [
            {'name': _('داشبورد'), 'url': 'dashboard', 'icon': 'fas fa-tachometer-alt'},
            {'name': _('لیست سازمان‌ها'), 'url': 'organization_list', 'icon': 'fas fa-building'},
            {'name': _('ایجاد سازمان'), 'url': 'organization_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست پروژه‌ها'), 'url': 'project_list', 'icon': 'fas fa-project-diagram'},
            {'name': _('ایجاد پروژه'), 'url': 'project_create', 'icon': 'fas fa-plus'},
            {'name': _('لیست تنخواه‌ها'), 'url': 'tankhah_list', 'icon': 'fas fa-file-invoice'},
            {'name': _('ایجاد تنخواه'), 'url': 'tankhah_create', 'icon': 'fas fa-plus'},
            {'name': _(' فهرست فاکتور'), 'url': 'factor_list', 'icon': 'fas fa-plus'},
            {'name': _('مدیریت کاربر و سیستم'), 'url': 'accounts:admin_dashboard', 'icon': 'fas fa-user'},
        ]
        return context
#######################################################################################
# سازمان‌ها
class OrganizationListView(PermissionBaseView, ListView):
    model = Organization
    template_name = 'core/organization_list.html'
    context_object_name = 'organizations'
    from django.conf import settings
    paginate_by = getattr(settings, 'ORGANIZATIONS_PER_PAGE', 10)
    permission_codenames = ['core.organization_view']  # اصلاح نام پرمیشن
    check_organization = False  # هلدینگ به همه دسترسی دارد
    extra_context = {'title': _('لیست سازمان‌ها')}

    def get_queryset(self):
        """استخراج کوئری‌ست با فیلترها و بهینه‌سازی"""
        queryset = Organization.objects.select_related('org_type').prefetch_related(
            Prefetch(
                'budget_allocations',
                queryset=BudgetAllocation.objects.filter(is_active=True).select_related(
                    'budget_period', 'budget_item', 'project'
                ).annotate(
                    total_consumed=Sum(
                        'transactions__amount',
                        filter=Q(transactions__transaction_type='CONSUMPTION')
                    )
                )
            )
        ).order_by('id')

        # اعمال فیلترهای جستجو
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(code__icontains=query) |
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

        # فیلتر وضعیت
        is_active = self.request.GET.get('is_active', '')
        if is_active in ('true', 'false'):
            queryset = queryset.filter(is_active=(is_active == 'true'))

        # فیلتر تاریخ
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            try:
                queryset = queryset.filter(budget_allocations__allocation_date__gte=date_from)
            except ValueError:
                messages.error(self.request, _('فرمت تاریخ شروع نامعتبر است.'))
        if date_to:
            try:
                queryset = queryset.filter(budget_allocations__allocation_date__lte=date_to)
            except ValueError:
                messages.error(self.request, _('فرمت تاریخ پایان نامعتبر است.'))

        logger.debug(f"Queryset count: {queryset.count()}")
        return queryset.distinct()

    def get_budget_details(self, organization):
        """محاسبه بودجه‌های تخصیص‌یافته فعال و مصرف‌شده"""
        try:
            allocations = organization.budget_allocations.filter(is_active=True)
            total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
            total_consumed = allocations.aggregate(
                total=Sum('total_consumed')
            )['total'] or Decimal('0')
            remaining_budget = total_allocated - total_consumed

            return {
                'total_allocated': total_allocated,
                'total_consumed': total_consumed,
                'remaining_budget': remaining_budget,
                'project_count': allocations.values('project').distinct().count(),
                'allocation_count': allocations.count(),
                'last_update': allocations.order_by('-allocation_date').first().allocation_date
                               if allocations.exists() else None,
                'status_message': _('فعال') if allocations.exists() else _('بدون تخصیص'),
            }
        except Exception as e:
            logger.error(f"Error calculating budget details for organization {organization.pk}: {str(e)}", exc_info=True)
            return {
                'total_allocated': Decimal('0'),
                'total_consumed': Decimal('0'),
                'remaining_budget': Decimal('0'),
                'project_count': 0,
                'allocation_count': 0,
                'last_update': None,
                'status_message': _('خطا در محاسبه'),
            }

    def get_context_data(self, **kwargs):
        """ساخت کنتکست با داده‌های بودجه"""
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # افزودن فیلترها به کنتکست
        context.update({
            'query': self.request.GET.get('q', ''),
            'is_active': self.request.GET.get('is_active', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        })

        # محاسبه بودجه برای هر سازمان
        organizations = []
        for org in queryset:
            org.budget_details = self.get_budget_details(org)
            organizations.append(org)
            logger.debug(f"Org {org.name}: budget_details={org.budget_details}")

        context['organizations'] = organizations
        context['total_organizations'] = queryset.count()

        logger.info(f"Final context organizations count: {len(organizations)}")
        return context
class OrganizationDetailView(PermissionBaseView, DetailView):
    model = Organization
    template_name = 'core/organization_detail.html'
    context_object_name = 'organization'
    permission_codename =  'core.Organization_view'
    check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('جزئیات سازمان') + f" - {self.object.code}"
        return context
class OrganizationCreateView(PermissionBaseView, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')
    extra_context = {'title': _('ثبت شعبات و دفتر اثلی سازمان')}

    permission_codename =  'core.Organization_add'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد سازمان جدید')
        return context
class OrganizationUpdateView(PermissionBaseView, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')
    permission_codename =  'core.Organization_update'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        messages.success(self.request, _('سازمان با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش سازمان') + f" - {self.object.code}"
        return context
class OrganizationDeleteView(PermissionBaseView, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')
    permission_codename =  'core.Organization_delete'
    check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('سازمان با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# پروژه‌هاچ
class ProjectListView(PermissionBaseView, ListView):
    model = Project
    template_name = 'core/project_list.html'
    context_object_name = 'projects'
    paginate_by = 12
    extra_context = {'title': _('لیست پروژه‌ها')}
    permission_codename = 'core.Project_view'
    check_organization = True

    def get_queryset(self):
        # **این خط را اصلاح کنید:**
        # به جای 'budget_allocations' از 'allocations' استفاده کنید.
        # همچنین، `budget_allocations` در `Sum` هم باید به `allocations` تغییر کنه.
        # اگر 'subprojects__allocated_budget' در مدل SubProject فیلدی با این نام ندارید، این هم خطا می‌دهد.
        # احتمالاً subprojects__budget_allocations__allocated_amount را می‌خواهید.

        queryset = super().get_queryset().prefetch_related(
            'allocations',  # <-- اصلاح شد: از 'allocations' (related_name در BudgetAllocation) استفاده کنید
            'subprojects',  # اگر هنوز این related_name رو دارید
            'tankhah_set'  # از مدل Tankhah (که شما فرستادید)
        )

        # محاسبه مجموع بودجه تخصیص‌یافته به هر پروژه از طریق BudgetAllocation
        # و مجموع تنخواه‌ها
        queryset = queryset.annotate(
            # مجموع allocated_amount از BudgetAllocationهایی که به این پروژه لینک شده‌اند
            # و یا از طریق subproject به این پروژه لینک شده‌اند (اگر هر دو حالت رو نیاز دارید)
            # اگر project_id در BudgetAllocation کافیه، این سطر کافیه
            total_allocated_budget_sum=Sum('allocations__allocated_amount', filter=Q(allocations__is_active=True)),
            # <-- اصلاح شده

            # مجموع بودجه زیرپروژه‌ها: پیچیده‌تر است. اگر subprojects خودشون allocated_budget ندارند
            # باید از طریق BudgetAllocationهای مرتبط با زیرپروژه فیلتر کنید.
            # مثال: Sum('subprojects__budget_allocations__allocated_amount')
            # با فرض اینکه subprojects.budget_allocations related_name به BudgetAllocation هست
            # یا اگر BudgetAllocation مستقیماً به subproject لینک شده:
            # subproject_total_budget=Sum('allocations__allocated_amount', filter=Q(allocations__subproject__isnull=False)),

            # برای ساده‌سازی، فرض می‌کنیم subproject_budget در SubProject نیست و از allocations محاسبه می‌شود:
            # این سطر را حذف کنید یا اصلاح کنید
            # subproject_budget=Sum('subprojects__allocated_budget'),

            # مجموع تنخواه‌ها با وضعیت PAID
            tankhah_total=Sum('tankhah_set__amount', filter=Q(tankhah_set__status='PAID'))  # <-- اصلاح شد
        )

        # ... (بقیه کدهای get_queryset) ...
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(description__icontains=query) |
                Q(allocations__budget_item__name__icontains=query) |  # جستجو در نام ردیف بودجه
                Q(subprojects__name__icontains=query)
            ).distinct()  # distinct برای جلوگیری از تکرار پروژه ها به خاطر join

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset.order_by('-start_date', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت پروژه‌ها')
        context['query'] = self.request.GET.get('q', '')
        context['status'] = self.request.GET.get('status', '')

        # `get_project_total_budget` رو برای هر پروژه صدا می‌زنیم.
        # مطمئن بشید `get_project_total_budget` با ساختار BudgetAllocation جدید سازگار است.
        # (همونطور که در پاسخ قبلی بازنویسی کردیم)
        projects = context['projects']  # اینها QuerySet هایی هستند که annotate شده‌اند
        project_budgets = {project.id: get_project_total_budget(project) for project in projects}
        context['project_budgets'] = project_budgets

        return context
class ProjectDetailView(PermissionBaseView, DetailView):
    model = Project
    template_name = 'core/project_detail.html'
    context_object_name = 'project'
    permission_codename = 'core.Project_view'
    check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tankhahs'] = Tankhah.objects.filter(project=self.object)#.select_related('current_stage')
        context['title'] = _('جزئیات پروژه') + f" - {self.object.code}"
        return context
class ProjectCreateView(PermissionBaseView, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_add'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد پروژه جدید')

        # اطلاعات بودجه شعبه‌ها
        budget_report = {}
        # for org in Organization.objects.filter(org_type__in=['COMPLEX', 'HQ']):
        # context['organizations'] = Organization.objects.filter(is_budget_allocatable=True).values_list('id', flat=True)
        # context['organizations'] = Organization.objects.filter(org_type__is_budget_allocatable=True, is_active=True ).values_list('id', flat=True)
        organizations = Organization.objects.filter(
            org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type')

        for org in organizations:
            total_budget = get_organization_budget(org)
            used_budget = BudgetAllocation.objects.filter(organization=org).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            remaining_budget = total_budget - used_budget
            budget_report[org.id] = {
                'name': org.name,
                'total_budget': total_budget,
                'used_budget': used_budget,
                'remaining_budget': remaining_budget
            }
        context['budget_report'] = budget_report
        context['organizations'] = organizations
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, _('پروژه با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}, data: {form.data}")
        messages.error(self.request, _('خطایی در ثبت پروژه رخ داد. لطفاً اطلاعات را بررسی کنید.'))
        return super().form_invalid(form)
class ProjectUpdateView(PermissionBaseView, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_update'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش پروژه') + f" - {self.object.code}"

        # اطلاعات بودجه شعبه‌ها
        budget_report = {}
        organizations = Organization.objects.filter(
            org_type__is_budget_allocatable=True, is_active=True
        ).select_related('org_type')

        for org in organizations:
            total_budget = get_organization_budget(org)
            used_budget = BudgetAllocation.objects.filter(organization=org).aggregate(
                total=Sum('allocated_amount')
            )['total'] or Decimal('0')
            # برای ویرایش، بودجه فعلی پروژه رو از used_budget کم می‌کنیم
            if self.object.organizations.filter(id=org.id).exists():
                current_allocation = BudgetAllocation.objects.filter(
                    project=self.object, organization=org
                ).aggregate(total=Sum('allocated_amount'))['total'] or Decimal('0')
                used_budget -= current_allocation
            remaining_budget = total_budget - used_budget
            budget_report[org.id] = {
                'name': org.name,
                'total_budget': total_budget,
                'used_budget': used_budget,
                'remaining_budget': remaining_budget
            }
        context['budget_report'] = budget_report
        return context

    def form_valid(self, form):
        form.request = self.request
        messages.success(self.request, _('پروژه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error(f"Form errors: {form.errors.as_json()}")
        messages.error(self.request, _('خطایی در ویرایش پروژه رخ داد. لطفاً اطلاعات را بررسی کنید.'))
        return super().form_invalid(form)
class ProjectDeleteView(PermissionBaseView, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    permission_codename = 'core.Project_delete'
    check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پروژه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
# --------------
#-- روند تنخواه گردانی داشبورد ---

class PostListView(PermissionBaseView, ListView):
    model = Post
    template_name = 'core/post/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10  # Django handles pagination automatically with this setting
    extra_context = {'title': _('لیست پست‌های سازمانی')}
    permission_codenames = ['core.Post_view']

    def get_queryset(self):
        qs = super().get_queryset()

        # --- Search Functionality ---
        search_query = self.request.GET.get('q')
        if search_query:
            logger.info(f"Searching for posts with query: '{search_query}'")
            # Using Q objects for flexible search across multiple fields
            qs = qs.filter(
                Q(name__icontains=search_query) |  # Search by post name
                Q(organization__name__icontains=search_query) |  # Search by organization name
                Q(branch__name__icontains=search_query) |  # Search by branch name
                Q(description__icontains=search_query)  # Search by description
            ).distinct()  # Use .distinct() to avoid duplicate results if a post matches multiple Q conditions

        # --- Sorting Functionality ---
        sort_order = self.request.GET.get('sort', 'asc')  # Default: ascending by level
        if sort_order == 'desc':
            qs = qs.order_by('-level')  # Descending: high to low level
            logger.info("Sorting posts from high to low level")
        else:
            qs = qs.order_by('level')  # Ascending: low to high level
            logger.info("Sorting posts from low to high level")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass the current search query back to the template for display in the search bar
        context['search_query'] = self.request.GET.get('q', '')
        # Pass the current sort order to the template to highlight the active sort option
        context['current_sort'] = self.request.GET.get('sort', 'asc')
        return context

class PostDetailView(PermissionBaseView, DetailView):
    model = Post
    template_name = 'core/post/post_detail.html'
    context_object_name = 'post'
    extra_context = {'title': _('جزئیات پست سازمانی')}
    permission_codename = 'core.Post_view'
    # check_organization = True  # فعال کردن چک سازمان

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from tankhah.models import StageApprover
        context['stages'] = StageApprover.objects.filter(post=self.object).select_related('stage')
        return context

class PostCreateView(PermissionBaseView, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    permission_codenames = ['Post_add']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.changed_by = self.request.user
        messages.success(self.request, _('پست سازمانی با موفقیت ایجاد شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid: {form.errors}")
        messages.error(self.request, _('خطا در ایجاد پست: لطفاً اطلاعات را بررسی کنید.'))
        return super().form_invalid(form)

class PostUpdateView(PermissionBaseView, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'core/post/post_form.html'
    success_url = reverse_lazy('post_list')
    permission_codenames = ['Post_update']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.changed_by = self.request.user
        logger.debug(f"Form data: {self.request.POST}")
        messages.success(self.request, _('پست سازمانی با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.error(f"Form invalid: {form.errors}")
        messages.error(self.request, _('خطا در به‌روزرسانی پست: لطفاً اطلاعات را بررسی کنید.'))
        return super().form_invalid(form)

class PostDeleteView(PermissionBaseView, DeleteView):
    model = Post
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('post_list')
    # permission_required = 'core.Post_delete'
    permission_codename = 'core.Post_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('پست سازمانی با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#     ==================================================
# --- UserPost Views ---
class UserPostListView(PermissionBaseView, ListView):
    """
    ویو برای نمایش لیست اتصالات کاربر به پست با قابلیت جستجو.
    مسئولیت: نمایش، فیلتر کردن، و صفحه‌بندی اتصالات با توجه به مجوزهای کاربر.
    """
    model = UserPost
    template_name = 'core/post/userpost_list.html'
    context_object_name = 'userposts'
    paginate_by = 10
    permission_required = 'core.UserPost_view'

    def get_queryset(self):
        """فیلتر کردن اتصالات بر اساس جستجو و سازمان‌های مجاز"""
        queryset = UserPost.objects.select_related('user', 'post__organization').order_by('-start_date')
        logger.debug(f"[UserPostListView] شروع فیلتر اتصالات برای کاربر '{self.request.user.username}'")

        # اعمال فیلترهای جستجو
        username = self.request.GET.get('username', '').strip()
        post_name = self.request.GET.get('post_name', '').strip()
        organization_id = self.request.GET.get('organization', '').strip()

        if username:
            queryset = queryset.filter(user__username__icontains=username)
            logger.debug(f"[UserPostListView] فیلتر بر اساس نام کاربر: {username}")
        if post_name:
            queryset = queryset.filter(post__name__icontains=post_name)
            logger.debug(f"[UserPostListView] فیلتر بر اساس نام پست: {post_name}")
        if organization_id:
            queryset = queryset.filter(post__organization__id=organization_id)
            logger.debug(f"[UserPostListView] فیلتر بر اساس سازمان: {organization_id}")

        # محدود کردن به سازمان‌های مجاز برای کاربران غیرسوپریوزر
        if not self.request.user.is_superuser:
            user_orgs = {up.post.organization for up in self.request.user.userpost_set.filter(is_active=True)
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            if not user_orgs:
                logger.warning(f"[UserPostListView] کاربر '{self.request.user.username}' به هیچ سازمان شعبه‌ای دسترسی ندارد")
                messages.error(self.request, _("شما به هیچ سازمانی دسترسی ندارید."))
                return queryset.none()
            queryset = queryset.filter(post__organization__in=user_orgs)
            logger.debug(f"[UserPostListView] فیلتر به سازمان‌های شعبه‌ای: {[org.name for org in user_orgs]}")

        logger.debug(f"[UserPostListView] تعداد اتصالات فیلترشده: {queryset.count()}")
        return queryset

    def get_context_data(self, **kwargs):
        """اضافه کردن داده‌های اضافی به context"""
        context = super().get_context_data(**kwargs)
        context['title'] = _("لیست اتصالات کاربر به پست")
        context['organizations'] = Organization.objects.filter(is_active=True).order_by('name')
        return context

    def handle_no_permission(self):
        """مدیریت عدم دسترسی"""
        logger.warning(f"[UserPostListView] کاربر '{self.request.user.username}' مجوز '{self.permission_required}' را ندارد")
        messages.error(self.request, _("شما مجوز مشاهده اتصالات کاربر به پست را ندارید."))
        return super().handle_no_permission()
    #     ==================================================
class UserPostCreateView(PermissionBaseView,  CreateView):
    """
    ویو برای ایجاد اتصال کاربر به پست.
    مسئولیت: مدیریت فرم و بررسی مجوزهای کاربر.
    """
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    permission_required = 'core.UserPost_add'
    check_organization = True

    def get_form_kwargs(self):
        """اضافه کردن request به kwargs فرم"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def has_permission(self):
        """بررسی مجوزهای کاربر"""
        has_perm = super().has_permission()
        if not has_perm:
            logger.warning(f"[UserPostCreateView] کاربر '{self.request.user.username}' مجوز '{self.permission_required}' را ندارد")
            messages.error(self.request, _("شما مجوز ایجاد اتصال کاربر به پست را ندارید."))
            return False
        logger.debug(f"[UserPostCreateView] مجوز تأیید شد برای کاربر '{self.request.user.username}'")
        return True

    def form_valid(self, form):
        """مدیریت فرم معتبر"""
        userpost = form.instance
        logger.info(f"[UserPostCreateView] اتصال کاربر '{userpost.user.username}' به پست '{userpost.post.name}' ایجاد شد")
        messages.success(self.request, _(f"اتصال کاربر '{userpost.user.username}' به پست '{userpost.post.name}' با موفقیت ایجاد شد."))
        return super().form_valid(form)

    def form_invalid(self, form):
        """مدیریت فرم نامعتبر"""
        logger.warning(f"[UserPostCreateView] فرم نامعتبر برای کاربر '{self.request.user.username}': {form.errors}")
        messages.error(self.request, _('خطا در ایجاد اتصال. لطفاً ورودی‌ها را بررسی کنید.'))
        return super().form_invalid(form)
#     ==================================================
class UserPostUpdateView(PermissionBaseView,   UpdateView):
    """
    ویو برای به‌روزرسانی اتصال کاربر به پست.
    مسئولیت: مدیریت فرم و بررسی مجوزهای کاربر.
    """
    model = UserPost
    form_class = UserPostForm
    template_name = 'core/post/userpost_form.html'
    success_url = reverse_lazy('userpost_list')
    permission_required = 'core.UserPost_update'
    check_organization = True

    def get_form_kwargs(self):
        """اضافه کردن request به kwargs فرم"""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def has_permission(self):
        """بررسی مجوزهای کاربر"""
        has_perm = super().has_permission()
        if not has_perm:
            logger.warning(f"[UserPostUpdateView] کاربر '{self.request.user.username}' مجوز '{self.permission_required}' را ندارد")
            messages.error(self.request, _("شما مجوز به‌روزرسانی اتصال کاربر به پست را ندارید."))
            return False

        userpost = self.get_object()
        if not self.request.user.is_superuser:
            user_orgs = {up.post.organization for up in self.request.user.userpost_set.filter(is_active=True)
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            if userpost.post.organization not in user_orgs:
                logger.warning(f"[UserPostUpdateView] کاربر '{self.request.user.username}' به سازمان پست '{userpost.post.organization.name}' دسترسی ندارد")
                messages.error(self.request, _('شما به سازمان این پست دسترسی ندارید.'))
                return False

        logger.debug(f"[UserPostUpdateView] مجوز تأیید شد برای کاربر '{self.request.user.username}'")
        return True

    def form_valid(self, form):
        """مدیریت فرم معتبر"""
        userpost = form.instance
        logger.info(f"[UserPostUpdateView] اتصال کاربر '{userpost.user.username}' به پست '{userpost.post.name}' به‌روزرسانی شد")
        messages.success(self.request, _(f"اتصال کاربر '{userpost.user.username}' به پست '{userpost.post.name}' با موفقیت به‌روزرسانی شد."))
        return super().form_valid(form)

    def form_invalid(self, form):
        """مدیریت فرم نامعتبر"""
        logger.warning(f"[UserPostUpdateView] فرم نامعتبر برای کاربر '{self.request.user.username}': {form.errors}")
        messages.error(self.request, _('خطا در به‌روزرسانی اتصال. لطفاً ورودی‌ها را بررسی کنید.'))
        return super().form_invalid(form)

#     ==================================================
class UserPostDeleteView(PermissionBaseView, DeleteView):
    model = UserPost
    template_name = 'core/post/post_confirm_delete.html'
    success_url = reverse_lazy('userpost_list')
    # permission_required = 'Tankhah.UserPost_delete'
    permission_codename = 'core.UserPost_delete'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('اتصال کاربر به پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#     ==================================================
def search_posts_autocomplete(request):
    """
    ویو برای جستجوی خودکار پست‌ها بر اساس نام، به صورت AJAX.
    """
    # دریافت عبارت جستجو از درخواست
    query = request.GET.get('q', '')

    # دریافت سازمان‌های مجاز برای کاربر جاری
    # این بخش برای اعمال محدودیت دسترسی به پست‌های سازمان‌های خاص است
    user_orgs = set()
    if not request.user.is_superuser:
        user_orgs = {
            up.post.organization for up in request.user.userpost_set.filter(is_active=True)
            if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding
        }

    # فیلتر کردن پست‌ها
    posts = Post.objects.filter(
        Q(name__icontains=query) | Q(code__icontains=query)
    ).order_by('name')

    # اعمال محدودیت سازمان برای کاربران غیرسوپریوزر
    if user_orgs:
        posts = posts.filter(organization__in=user_orgs)

    # تبدیل نتایج به فرمت JSON
    data = [
        {'id': post.id, 'text': f"{post.name} ({post.code})"}
        for post in posts[:10]  # محدود کردن نتایج به ۱۰ مورد
    ]
    return JsonResponse(data, safe=False)

from django.utils.decorators import method_decorator
@method_decorator(login_required, name='dispatch')
class PostSearchAPIView(PermissionBaseView, View):
    """
    API برای جستجوی پست‌ها با پشتیبانی از فیلترهای نام و سازمان.
    مسئولیت: ارائه نتایج جستجو برای Select2 در فرم UserPost.
    """
    permission_required = 'core.UserPost_view'

    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1))
        per_page = 10
        offset = (page - 1) * per_page

        logger.debug(f"[PostSearchAPIView] جستجو برای عبارت: '{query}', صفحه: {page}")

        # فیلتر پایه
        queryset = Post.objects.filter(is_active=True).select_related('organization')

        # محدود کردن به سازمان‌های مجاز برای کاربران غیرسوپریوزر
        if not request.user.is_superuser:
            user_orgs = {up.post.organization for up in request.user.userpost_set.filter(is_active=True)
                         if up.post.organization and not up.post.organization.is_core and not up.post.organization.is_holding}
            if not user_orgs:
                logger.warning(f"[PostSearchAPIView] کاربر '{request.user.username}' به هیچ سازمان شعبه‌ای دسترسی ندارد")
                return JsonResponse({'results': [], 'has_next': False}, status=200)
            queryset = queryset.filter(organization__in=user_orgs)

        # جستجو بر اساس نام پست یا سازمان
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(organization__name__icontains=query)
            )

        # صفحه‌بندی
        total = queryset.count()
        queryset = queryset[offset:offset + per_page]
        has_next = total > offset + per_page

        # فرمت نتایج برای Select2
        results = [
            {
                'id': post.id,
                'name': post.name,
                'organization_name': post.organization.name if post.organization else 'بدون سازمان'
            }
            for post in queryset
        ]

        logger.info(f"[PostSearchAPIView] تعداد نتایج: {len(results)}, صفحه بعدی: {has_next}")
        return JsonResponse({
            'results': results,
            'has_next': has_next
        }, status=200)
#     ==================================================
# --- PostHistory Views ---
class PostHistoryListView(PermissionBaseView, ListView):
    model = PostHistory
    template_name = 'core/post/posthistory_list.html'
    context_object_name = 'histories'
    paginate_by = 10
    extra_context = {'title': _('لیست تاریخچه پست‌ها')}
    permission_codename = 'core.view_posthistory'
    # check_organization = True  # فعال کردن چک سازمان
class PostHistoryCreateView(PermissionBaseView, CreateView):
    model = PostHistory
    form_class = PostHistoryForm
    template_name = 'core/post/posthistory_form.html'
    success_url = reverse_lazy('posthistory_list')
    # permission_required = 'Tankhah.add_posthistory'
    permission_codename = 'core.add_posthistory'
    # check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        form.instance.changed_by = self.request.user
        messages.success(self.request, _('تاریخچه پست با موفقیت ثبت شد.'))
        return super().form_valid(form)
class PostHistoryDeleteView(PermissionBaseView, DeleteView):
    model = PostHistory
    template_name = 'core/post/posthistory_confirm_delete.html'
    success_url = reverse_lazy('posthistory_list')
    # permission_required = 'Tankhah.delete_posthistory'
    permission_codename = 'core.delete_posthistory'
    # check_organization = True  # فعال کردن چک سازمان

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تاریخچه پست با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
# ---- WorkFlow
class WorkflowStageListView(PermissionBaseView, ListView):
    model = AccessRule
    template_name = "core/workflow_stage/workflow_stage_list.html"
    context_object_name = "stages"
    permission_codename = 'WorkflowStage_view'

    def get_queryset(self):
        queryset = super().get_queryset()
        entity_type = self.request.GET.get('entity_type')
        is_active = self.request.GET.get('is_active')

        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        if is_active:
            queryset = queryset.filter(is_active=is_active == 'true')

        return queryset.order_by('order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست مراحل گردش کار')
        logger.info(f"[WorkflowStageListView] نمایش لیست مراحل توسط کاربر {self.request.user.username}")
        return context

class WorkflowStageCreateView(PermissionBaseView, CreateView):
    model = AccessRule
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_codename = 'WorkflowStage_add'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        try:
            logger.info(f"[WorkflowStageCreateView] ایجاد مرحله جدید توسط کاربر {self.request.user.username}: {form.cleaned_data}")
            response = super().form_valid(form)
            messages.success(self.request, _('مرحله با موفقیت ایجاد شد.'))
            return response
        except Exception as e:
            logger.error(f"[WorkflowStageCreateView] خطا در ایجاد مرحله: {e}", exc_info=True)
            messages.error(self.request, _("خطا در ایجاد مرحله: {}".format(str(e))))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('افزودن مرحله جدید')
        context['action'] = 'create'
        return context

class WorkflowStageUpdateView(PermissionBaseView, UpdateView):
    model = AccessRule
    form_class = WorkflowStageForm
    template_name = "core/workflow_stage/workflow_stage_form.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_codename = 'WorkflowStage_update'
    check_organization = True  # فعال کردن چک سازمان

    def form_valid(self, form):
        try:
            logger.info(f"[WorkflowStageUpdateView] به‌روزرسانی مرحله {self.object.pk} توسط کاربر {self.request.user.username}: {form.cleaned_data}")
            response = super().form_valid(form)
            messages.success(self.request, _('مرحله با موفقیت به‌روزرسانی شد.'))
            return response
        except Exception as e:
            logger.error(f"[WorkflowStageUpdateView] خطا در به‌روزرسانی مرحله {self.object.pk}: {e}", exc_info=True)
            messages.error(self.request, _("خطا در به‌روزرسانی مرحله: {}".format(str(e))))
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش مرحله')
        context['action'] = 'update'
        return context

class WorkflowStageDeleteView(PermissionBaseView, DeleteView):
    model = AccessRule
    template_name = "core/workflow_stage/workflow_stage_confirm_delete.html"
    success_url = reverse_lazy("workflow_stage_list")
    permission_codename = 'WorkflowStage_delete'

    def delete(self, request, *args, **kwargs):
        logger.info(f"[WorkflowStageDeleteView] حذف مرحله {self.get_object().pk} توسط کاربر {request.user.username}")
        messages.success(request, _('مرحله با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('حذف مرحله')
        context['stage'] = self.get_object()
        return context

# ---- Sub Project CRUD
class SubProjectListView(PermissionBaseView, ListView):
    model = SubProject
    template_name = 'core/subproject/subproject_list.html'
    context_object_name = 'subprojects'
    paginate_by = 10
    permission_required = 'core.SubProject_view'

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(project__name__icontains=query) |
                Q(description__icontains=query)
            )
        return queryset.order_by('project__name', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('لیست ساب‌پروژه‌ها')
        context['query'] = self.request.GET.get('q', '')
        return context
class SubProjectCreateView(PermissionBaseView, CreateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'core/subproject/subproject_form.html'
    success_url = reverse_lazy('subproject_list')
    permission_required = 'core.SubProject_add'

    def get_initial(self):
        initial = super().get_initial()
        project_id = self.request.GET.get('project')
        if project_id:
            project = Project.objects.get(id=project_id)
            initial['project'] = project
            initial['allocated_budget'] = get_project_remaining_budget(project) / 2  # پیشنهاد نصف بودجه
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد ساب‌پروژه جدید')
        if 'project' in self.get_initial():
            context['project_remaining_budget'] = get_project_remaining_budget(self.get_initial()['project'])
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('ساب‌پروژه با موفقیت ایجاد شد.'))
        return response
class SubProjectUpdateView(PermissionBaseView, UpdateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'core/subproject/subproject_form.html'
    success_url = reverse_lazy('subproject_list')
    permission_required = 'core.SubProject_update'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش ساب‌پروژه') + f" - {self.object.name}"
        context['project_remaining_budget'] = self.object.project.get_remaining_budget()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('ساب‌پروژه با موفقیت به‌روزرسانی شد.'))
        return response
class SubProjectDeleteView(PermissionBaseView, DeleteView):
    model = SubProject
    template_name = 'core/subproject/subproject_confirm_delete.html'
    success_url = reverse_lazy('subproject_list')
    permission_required = 'core.SubProject_delete'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, _('ساب‌پروژه با موفقیت حذف شد.'))
        return response
# تخصیص بودجه به پروژه و زیر پروژه
# budgets/views.py
class BudgetAllocationView(PermissionBaseView, View):
    template_name = 'budgets/budget/budget_allocation.html'
    permission_required = (
        'core.Project_add',
        'core.Project_Budget_allocation_Head_Office',
        'core.Project_Budget_allocation_Branch',
        'core.SubProject_Budget_allocation_Head_Office',
        'core.SubProject_Budget_allocation_Branch'
    )

    def get(self, request, *args, **kwargs):
        projects = Project.objects.all()
        subprojects = SubProject.objects.all()
        organizations = Organization.objects.all()
        context = {
            'projects': projects,
            'subprojects': subprojects,
            'organizations': organizations,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        entity_type = request.POST.get('entity_type')
        budget_amount = Decimal(request.POST.get('budget_amount'))
        organization_id = request.POST.get('organization')

        if not organization_id:
            messages.error(request, _('لطفاً یک سازمان انتخاب کنید.'))
            return redirect('budget_allocation')

        organization = Organization.objects.get(id=organization_id)
        org_budget = get_organization_budget(organization)

        if entity_type == 'project':
            project = Project.objects.get(id=request.POST.get('project'))
            remaining_org_budget = org_budget - get_project_used_budget(project)
            if budget_amount > remaining_org_budget:
                messages.error(request, _('بودجه بیشتر از باقیمانده سازمان است.'))
                return redirect('budget_allocation')
            # اضافه کردن بودجه به allocations پروژه
            allocation = BudgetAllocation.objects.create(
                organization=organization,
                allocated_amount=budget_amount
            )
            project.allocations.add(allocation)
            messages.success(request, _('بودجه به پروژه تخصیص یافت.'))

        elif entity_type == 'subproject':
            subproject = SubProject.objects.get(id=request.POST.get('subproject'))
            if budget_amount > get_project_remaining_budget(subproject.project):
                messages.error(request, _('بودجه بیشتر از باقیمانده پروژه است.'))
                return redirect('budget_allocation')
            subproject.allocated_budget += budget_amount
            subproject.save()
            messages.success(request, _('بودجه به ساب‌پروژه تخصیص یافت.'))

        return redirect('project_list')
