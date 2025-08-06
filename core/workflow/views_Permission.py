from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_GET
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from core.PermissionBase import PermissionBaseView
from core.models import Permission, Post, Transition, Organization
from core.workflow.forms_workflow import PermissionForm
from core.workflow.views_workflow import WorkflowAdminRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import permission_required, login_required
from django.http import JsonResponse
from django.shortcuts import render
import json
import logging
logger = logging.getLogger("forms_workflow")


class PermissionListView(ListView):
    model = Permission
    template_name = 'core/workflow/Permission/permission_list.html'
    context_object_name = 'permissions'
    paginate_by = 10
    def get_queryset(self):
        # نمایش مجوزها به تفکیک هر سازمان
        return Permission.objects.select_related(
            'transition__organization',
            'transition__entity_type',
            'transition__from_status',
            'transition__action'
        ).order_by('transition__organization__name', 'transition__entity_type__name', 'transition__from_status__name')
#
    # def get_queryset(self):
    #     queryset = Permission.objects.all().select_related(
    #         'organization', 'on_status'
    #     ).prefetch_related(
    #         'allowed_posts', 'allowed_actions'
    #     ).order_by('organization__name', 'entity_type')
    #
    #     search_query = self.request.GET.get('q', '').strip()
    #     if search_query:
    #         queryset = queryset.filter(
    #             Q(organization__name__icontains=search_query) |
    #             Q(on_status__name__icontains=search_query) |
    #             Q(entity_type__icontains=search_query)
    #         )
    #     return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class PermissionDeleteView(WorkflowAdminRequiredMixin, DeleteView):
    model = Permission
    template_name = 'core/workflow/Permission/permission_confirm_delete.html'
    success_url = reverse_lazy('permission_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("حذف مجوز")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("مجوز با موفقیت حذف شد."))
        return super().delete(request, *args, **kwargs)

@permission_required('Permission_add', raise_exception=True)
def permission_create(request):
    pass
    # """ ویو برای ایجاد یک Permission جدید """
    # if request.method == 'POST':
    #     form = PermissionForm(request.POST)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('permission_list')  # به لیست همه مجوزها ارجاع می‌دهد
    # else:
    #     form = PermissionForm()
    #
    # return render(request, 'core/workflow/Permission/permission_form.html', {'form': form})


@permission_required('Permission_update', raise_exception=True)
def permission_update(request, pk):

    pass
    # """ ویو برای ویرایش یک Permission """
    # permission = get_object_or_404(Permission, pk=pk)
    #
    # # بررسی دسترسی کاربر به مجوز (اختیاری: براساس نیاز شما)
    # if not permission.organization.has_permission(request.user, 'Permission_update'):
    #     return HttpResponseForbidden()
    #
    # if request.method == 'POST':
    #     form = PermissionForm(request.POST, instance=permission)
    #     if form.is_valid():
    #         form.save()
    #         return redirect('permission_detail', pk=permission.pk)  # به جزئیات مجوز ارجاع می‌دهد
    # else:
    #     form = PermissionForm(instance=permission)
    #
    # return render(request, 'core/workflow/Permission/permission_form.html', {'form': form})

def permission_create_update_view(request, pk=None):
    """
    ویو برای ایجاد (Create) و ویرایش (Update) مجوزها.
    """
    instance = get_object_or_404(Permission, pk=pk) if pk else None

    if request.method == 'POST':
        form = PermissionForm(request.POST, instance=instance)
        if form.is_valid():
            permission = form.save(commit=False)
            permission.created_by = request.user  # کاربر فعلی را به عنوان ایجادکننده ثبت کن
            permission.save()
            form.save_m2m()  # برای ذخیره فیلدهای ManyToMany
            # messages.success(request, _('مجوز با موفقیت ذخیره شد.'))
            return redirect('permission_list')  # نام URL لیست مجوزها
    else:
        form = PermissionForm(instance=instance)

    context = {
        'form': form,
        'title': _('ویرایش مجوز') if instance else _('ایجاد مجوز جدید')
    }
    return render(request, 'core/workflow/Permission/permission_form.html', context)


def load_posts_by_transition(request):
    """
    این ویو به درخواست‌های AJAX پاسخ می‌دهد.
    پست‌های مربوط به سازمانِ یک گذار خاص را برمی‌گرداند.
    """
    transition_id = request.GET.get('transition_id')
    posts_data = []

    if transition_id:
        try:
            # با پیدا کردن گذار، به سازمان آن دسترسی پیدا می‌کنیم
            transition = Transition.objects.select_related('organization').get(pk=transition_id)
            organization = transition.organization

            # و تمام پست‌های فعال آن سازمان را می‌گیریم
            posts = Post.objects.filter(organization=organization, is_active=True)
            posts_data = list(posts.values('id', 'name'))

        except Transition.DoesNotExist:
            pass  # اگر گذار پیدا نشد، لیست خالی برمی‌گردد

    return JsonResponse({'posts': posts_data})



# --- ویوی API برای بارگذاری داینامیک پست‌ها ---
@login_required
def load_posts_for_transition_view(request):
    """
    این ویو به درخواست‌های AJAX پاسخ داده و لیستی از پست‌های مرتبط
    با یک گذار خاص را به صورت JSON برمی‌گرداند.
    """
    transition_id = request.GET.get('transition_id')
    logger.debug(f"[load_posts] Received request for transition_id: {transition_id}")

    posts_data = []
    if transition_id:
        try:
            # پیدا کردن گذار و سازمان مرتبط با آن
            transition = Transition.objects.select_related('organization').get(id=transition_id)
            organization = transition.organization

            # پیدا کردن سازمان و تمام زیرمجموعه‌های آن
            orgs_to_include = [organization] + list(organization.sub_organizations.all())

            # واکشی پست‌های مرتبط
            posts = Post.objects.filter(
                organization__in=orgs_to_include, is_active=True
            ).values('id', 'name', 'organization__name')

            posts_data = list(posts)
            logger.debug(f"[load_posts] Found {len(posts_data)} posts for transition {transition_id}.")
        except Transition.DoesNotExist:
            logger.warning(f"[load_posts] Transition with id {transition_id} not found.")
            return JsonResponse({'error': 'Transition not found'}, status=404)

    return JsonResponse({'posts': posts_data})


# --
class PermissionCreateView(  CreateView):
    model = Permission
    # form_class = PermissionForm
    fields = '__all__'
    template_name = 'core/workflow/Permission/permission_form.html'
    success_url = reverse_lazy('permission_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        logger.debug(f"[PermissionCreateView] Passing user to form: {self.request.user}, Type: {type(self.request.user)}, Is authenticated: {self.request.user.is_authenticated}")
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'مجوز با موفقیت ایجاد شد.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'خطا در ایجاد مجوز. لطفاً اطلاعات را بررسی کنید.')
        return super().form_invalid(form)

class PermissionUpdateView(  UpdateView):
    model = Permission
    # form_class = PermissionForm
    template_name = 'core/workflow/Permission/permission_form.html'
    success_url = reverse_lazy('permission_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        logger.debug(f"[PermissionUpdateView] Passing user to form: {self.request.user}, Type: {type(self.request.user)}, Is authenticated: {self.request.user.is_authenticated}")
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'مجوز با موفقیت ویرایش شد.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'خطا در ویرایش مجوز. لطفاً اطلاعات را بررسی کنید.')
        return super().form_invalid(form)

def load_posts(request):
    transition_id = request.GET.get('transition_id')
    logger.debug(f"[load_posts] Loading posts for transition_id: {transition_id}")
    if transition_id:
        try:
            transition = Transition.objects.get(id=transition_id, is_active=True)
            posts = Post.objects.filter(
                organization=transition.organization, is_active=True
            ).select_related('organization').values('id', 'name', 'organization__code')
            logger.debug(f"[load_posts] Found {len(posts)} posts for organization: {transition.organization.id} ({transition.organization.name})")
            return JsonResponse({'posts': list(posts)})
        except Transition.DoesNotExist:
            logger.error(f"[load_posts] Transition {transition_id} not found or inactive")
            return JsonResponse({'posts': []})
    logger.debug("[load_posts] No transition_id provided")
    return JsonResponse({'posts': []})
 


@require_GET
def load_posts(request):
    transition_id = request.GET.get('transition_id')
    if not transition_id:
        return JsonResponse({'posts': []})

    try:
        transition = Transition.objects.get(id=transition_id, is_active=True)
        posts = Post.objects.filter(
            organization=transition.organization, is_active=True
        ).values('id', 'name', 'organization__code')
        return JsonResponse({'posts': list(posts)})
    except Transition.DoesNotExist:
        return JsonResponse({'posts': []})