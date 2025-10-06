from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import PurchaseRequest
from .forms import PurchaseRequestForm
from django.http import JsonResponse
from django.db.models import Q


class PurchaseRequestListView(LoginRequiredMixin, ListView):
    model = PurchaseRequest
    template_name = 'purchase_requests/pr_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        qs = super().get_queryset().select_related('organization', 'project', 'subproject', 'status')
        if self.request.user.is_superuser:
            return qs
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(self.request.user) or []
            return qs.filter(organization_id__in=user_org_ids)
        except Exception:
            return qs.none()


class PurchaseRequestCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseRequest
    form_class = PurchaseRequestForm
    template_name = 'purchase_requests/pr_form.html'
    success_url = reverse_lazy('pr_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class PurchaseRequestDetailView(LoginRequiredMixin, DetailView):
    model = PurchaseRequest
    template_name = 'purchase_requests/pr_detail.html'
    context_object_name = 'request_obj'

    def get_queryset(self):
        qs = super().get_queryset().select_related('organization')
        if self.request.user.is_superuser:
            return qs
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(self.request.user) or []
            return qs.filter(organization_id__in=user_org_ids)
        except Exception:
            return qs.none()


class PurchaseRequestUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseRequest
    form_class = PurchaseRequestForm
    template_name = 'purchase_requests/pr_form.html'
    success_url = reverse_lazy('pr_list')

    def get_queryset(self):
        qs = super().get_queryset().select_related('organization')
        if self.request.user.is_superuser:
            return qs
        try:
            from core.PermissionBase import PermissionBaseView
            temp = PermissionBaseView()
            user_org_ids = temp.get_user_active_organizations(self.request.user) or []
            return qs.filter(organization_id__in=user_org_ids)
        except Exception:
            return qs.none()


class FilterProjectsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            from core.models import Project
            org_id = request.GET.get('org_id')
            if not org_id:
                return JsonResponse({'results': []})
            try:
                base = Project.objects.filter(organizations__id=org_id)
            except Exception:
                base = Project.objects.all()
            active_q = Q()
            if hasattr(Project, 'is_active'):
                active_q &= Q(is_active=True)
            if hasattr(Project, 'end_date'):
                from django.utils import timezone as _tz
                active_q &= Q(end_date__isnull=True) | Q(end_date__gte=_tz.now().date())
            if hasattr(Project, 'due_date'):
                from django.utils import timezone as _tz
                active_q &= Q(due_date__isnull=True) | Q(due_date__gte=_tz.now().date())
            qs = base.filter(active_q).distinct().order_by('name')
            data = [{'id': p.id, 'text': getattr(p, 'name', str(p))} for p in qs]
            return JsonResponse({'results': data})
        except Exception:
            return JsonResponse({'results': []})


class FilterSubProjectsView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            from core.models import SubProject
            project_id = request.GET.get('project_id')
            if not project_id:
                return JsonResponse({'results': []})
            qs = SubProject.objects.filter(project_id=project_id)
            active_q = Q()
            if hasattr(SubProject, 'is_active'):
                active_q &= Q(is_active=True)
            if hasattr(SubProject, 'end_date'):
                from django.utils import timezone as _tz
                active_q &= Q(end_date__isnull=True) | Q(end_date__gte=_tz.now().date())
            if hasattr(SubProject, 'due_date'):
                from django.utils import timezone as _tz
                active_q &= Q(due_date__isnull=True) | Q(due_date__gte=_tz.now().date())
            qs = qs.filter(active_q).order_by('name')
            data = [{'id': sp.id, 'text': getattr(sp, 'name', str(sp))} for sp in qs]
            return JsonResponse({'results': data})
        except Exception:
            return JsonResponse({'results': []})


class PurchaseRequestApproveView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'purchase_requests.purchase_request_approve'

    def post(self, request, pk):
        pr = get_object_or_404(PurchaseRequest, pk=pk)
        try:
            # Try to resolve an approved status in a flexible way
            from core.dynamic_config import DynamicSystemManager
            approved_status = None
            try:
                approved_status = DynamicSystemManager.find_status_by_entity_and_type(
                    DynamicSystemManager.get_entity_type_for_generic(), 'is_final_approve'
                )
            except Exception:
                approved_status = None
            if not approved_status:
                from core.models import Status
                approved_status = Status.objects.filter(code__in=['APPROVED', 'FINAL_APPROVED']).first()
            if not approved_status:
                messages.error(request, 'وضعیت تایید برای درخواست کالا یافت نشد.')
                return redirect('pr_detail', pk=pr.pk)

            pr.status = approved_status
            pr.save(update_fields=['status'])
            messages.success(request, 'درخواست کالا با موفقیت تایید شد.')
        except Exception as e:
            messages.error(request, f'خطا در تایید درخواست: {e}')
        return redirect('pr_detail', pk=pr.pk)


