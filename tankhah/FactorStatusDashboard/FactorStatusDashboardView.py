from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from django.views.generic import ListView
from tankhah.models import Factor, ApprovalLog
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
import logging

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)
class FactorStatusDashboardView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/Reports/factor_status_dashboard.html'
    context_object_name = 'factors_data'
    paginate_by = 10
    permission_codenames = ['tankhah.factor_view']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی لازم برای مشاهده این گزارش را ندارید.')

    def get_queryset(self):
        # کوئری اصلی برای فاکتورها
        queryset = Factor.objects.select_related(
            'tankhah',
            'tankhah__organization',
            'tankhah__project',
            'tankhah__project_budget_allocation',
            'category',
            'created_by'
        ).prefetch_related(
            'approval_logs',
            'items'
        ).annotate(
            total_items=Count('items'),
            approved_items_count=Count('items', filter=Q(items__status='APPROVED')),
            rejected_items_count=Count('items', filter=Q(items__status='REJECTED')),
            pending_items_count=Count('items', filter=Q(items__status='PENDING')),
        )

        # تعریف nearing_expiry برای فاکتورهای نزدیک به انقضا
        expiry_threshold = timezone.now().date() + timedelta(days=7)
        self.nearing_expiry = queryset.filter(
            date__lte=expiry_threshold,
            date__gte=timezone.now().date(),
            status__in=['PENDING', 'APPROVED']
        )

        # اعمال فیلترهای اضافی (جستجو، وضعیت، سازمان)
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(number__icontains=search_query) |
                Q(tankhah__number__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(items__description__icontains=search_query)
            ).distinct()

        status_filter = self.request.GET.get('status', '')
        if status_filter and status_filter in [choice[0] for choice in Factor.STATUS_CHOICES]:
            queryset = queryset.filter(status=status_filter)

        organization_filter_id = self.request.GET.get('organization_id')
        if organization_filter_id:
            queryset = queryset.filter(tankhah__organization__id=organization_filter_id)

        project_filter_id = self.request.GET.get('project_id')
        if project_filter_id:
            queryset = queryset.filter(tankhah__project__id=project_filter_id)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factors_with_details = []

        for factor in context['object_list']:
            previous_actions = [
                {
                    'post_name': log.post.name if log.post else _("نامشخص"),
                    'post_org_name': log.post.organization.name if log.post and log.post.organization else _("نامشخص"),
                    'user_name': log.user.get_full_name() or log.user.username if log.user else _("سیستم"),
                    'action': log.get_action_display(),
                    'timestamp': log.timestamp,
                    'comment': log.comment,
                    'stage_name': log.stage.name if log.stage else _("نامشخص"),
                    'post_branch_class': 'post-branch-finance' if log.post and log.post.branch == 'FIN' else 'post-branch-default'
                } for log in factor.approval_logs.all()
            ]

            factors_with_details.append({
                'factor': factor,
                'previous_actions': previous_actions,
                'item_statuses_summary': {
                    'total': factor.total_items,
                    'approved': factor.approved_items_count,
                    'rejected': factor.rejected_items_count,
                    'pending': factor.pending_items_count,
                },
                'tankhah_name': factor.tankhah.organization.name if factor.tankhah and factor.tankhah.organization else _("نامشخص"),
                'project_name': factor.tankhah.project.name if factor.tankhah and factor.tankhah.project else _("بدون مرکز هزینه"),
            })

        context['factors_data'] = factors_with_details
        context['title'] = _('داشبورد وضعیت فاکتورها')
        context['nearing_expiry_count'] = self.nearing_expiry.count()  # تعداد فاکتورهای نزدیک به انقضا
        from core.models import Organization, Project
        context['organizations_for_filter'] = Organization.objects.filter(is_active=True).order_by('name')
        context['projects_for_filter'] = Project.objects.filter(is_active=True).order_by('name')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_organization_id'] = self.request.GET.get('organization_id', '')
        context['current_project_id'] = self.request.GET.get('project_id', '')

        return context



@login_required
def approve_factor(request, factor_pk):
    try:
        factor = Factor.objects.get(pk=factor_pk)
        # منطق تایید (مثل تغییر status به APPROVED)
        factor.status = 'APPROVED'
        factor.save()
        return JsonResponse({'status': 'success', 'message': 'فاکتور با موفقیت تایید شد.'})
    except Exception as e:
        logger.error(f"Error approving factor {factor_pk}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def reject_factor(request, factor_pk):
    try:
        factor = Factor.objects.get(pk=factor_pk)
        # منطق رد (مثل تغییر status به REJECTED)
        factor.status = 'REJECTED'
        factor.save()
        return JsonResponse({'status': 'success', 'message': 'فاکتور با موفقیت رد شد.'})
    except Exception as e:
        logger.error(f"Error rejecting factor {factor_pk}: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)