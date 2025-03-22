from django.db.models import Q
from django.contrib import messages
import jdatetime
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.db.models import Q

from accounts.has_role_permission import has_permission
from core.models import UserPost, Post, WorkflowStage
from .forms import TanbakhForm, FactorDocumentFormSet
from .models import Tanbakh, StageApprover
import jdatetime
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Factor, ApprovalLog
from .forms import FactorForm, ApprovalForm
from django.utils.translation import gettext_lazy as _
#---
from django.views.generic import TemplateView
from .forms import FactorForm, FactorItemFormSet

import logging
logger = logging.getLogger(__name__)
#-------
# ثبت و ویرایش تنخواه
@method_decorator(has_permission('Tanbakh_add'), name='dispatch')
class TanbakhManageView(LoginRequiredMixin, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_manage.html'
    success_url = reverse_lazy('tanbakh_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _('تنخواه با موفقیت ثبت یا به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('مدیریت تنخواه')
        return context

# تأیید و ویرایش تنخواه
@method_decorator(has_permission('Tanbakh_part_approve'), name='dispatch')
class TanbakhUpdateView(LoginRequiredMixin, UpdateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_manage.html'
    success_url = reverse_lazy('tanbakh_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user_post = self.request.user.userpost_set.filter(post__organization=self.object.organization).first()
        if not user_post or user_post.post.branch != self.object.current_stage:
            messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید.'))
            return self.form_invalid(form)
        next_post = Post.objects.filter(parent=user_post.post, organization=self.object.organization).first() or \
                    Post.objects.filter(organization__org_type='HQ', branch=self.object.current_stage, level=1).first()
        if next_post:
            self.object.last_stopped_post = next_post
        self.object.save()
        messages.success(self.request, _('تنخواه با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ویرایش و تأیید تنخواه') + f" - {self.object.number}"
        return context

#-------
from notifications.signals import notify

@method_decorator(has_permission('Tanbakh_add'), name='dispatch')
class TanbakhCreateView(LoginRequiredMixin, CreateView):
    model = Tanbakh
    form_class = TanbakhForm
    template_name = 'tanbakh/tanbakh_form.html'
    success_url = reverse_lazy('tanbakh_list')

    # def form_valid(self, form):
    #     form.instance.created_by = self.request.user
    #     with transaction.atomic():
    #         response = super().form_valid(form)
    #         ApprovalLog.objects.create(
    #             tanbakh=self.object,
    #             action='APPROVE',
    #             user=self.request.user,
    #             comment="تنخواه ثبت شد"
    #         )
    #         logger.info(f"تنخواه {self.object.number} توسط {self.request.user} ثبت شد.")
    #     messages.success(self.request, _('تنخواه با موفقیت ثبت شد.'))
    #     return response

    def form_valid(self, form):
        response = super().form_valid(form)
        tanbakh = self.object
        first_stage = WorkflowStage.objects.get(order=1)
        tanbakh.current_stage = first_stage
        tanbakh.save()
        # ارسال اعلان به تأییدکنندگان مرحله اول
        from django.conf import settings
        approvers = settings.AUTH_USER_MODEL.objects.filter(userpost__post__stageapprover__stage=first_stage)
        notify.send(self.request.user,recipient=approvers,verb='تنخواه جدیدی ایجاد شد',target=tanbakh)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('ایجاد تنخواه جدید')
        return context


@method_decorator(has_permission('Tanbakh_view'), name='dispatch')
class TanbakhListView(LoginRequiredMixin, ListView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_list.html'
    context_object_name = 'tanbakhs'
    paginate_by = 10
    extra_context = {'title': _('لیست تنخواه‌ها')}

    def get_queryset(self):
        user_posts = self.request.user.userpost_set.all()
        if not user_posts.exists():
            messages.warning(self.request, _('شما به هیچ پستی متصل نیستید.'))
            return Tanbakh.objects.none()  # یا redirect به صفحه تنظیمات کاربر
        orgs = [up.post.organization for up in user_posts]
        print(f"User: {self.request.user}, UserPosts: {user_posts.count()}, Orgs: {orgs}")
        queryset = Tanbakh.objects.filter(organization__in=orgs)
        print(f"Tanbakh Count: {queryset.count()}")
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query) |
                Q(organization__name__icontains=query) |
                Q(project__name__icontains=query, project__isnull=False) |
                Q(status__icontains=query) |
                Q(letter_number__icontains=query)
            )
            print(f"Query: {query}, Results: {queryset.count()}")
            if not queryset.exists():
                messages.info(self.request, _('هیچ تنخواهی با این مشخصات یافت نشد.'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')  # افزودن query به context برای نمایش در تمپلیت
        return context

class TanbakhDetailView(LoginRequiredMixin, DetailView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_detail.html'
    context_object_name = 'tanbakh'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factors'] = self.object.factors.all()
        context['title'] = _('جزئیات تنخواه') + f" - {self.object.number}"
        context['approval_logs'] = ApprovalLog.objects.filter(tanbakh=self.object).order_by('timestamp')
        # تاریخ فعلی برای چاپ
        context['current_date'] = jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')
        # تبدیل تاریخ‌ها به شمسی
        if self.object.date:
            context['jalali_date'] = jdatetime.date.fromgregorian(date=self.object.date).strftime('%Y/%m/%d %H:%M')
        for factor in context['factors']:
            factor.jalali_date = jdatetime.date.fromgregorian(date=factor.date).strftime('%Y/%m/%d %H:%M')
        for approval in context['approval_logs']:
            approval.jalali_date = jdatetime.datetime.fromgregorian(datetime=approval.date).strftime('%Y/%m/%d %H:%M')
        return context

class TanbakhDeleteView(LoginRequiredMixin, DeleteView):
    model = Tanbakh
    template_name = 'tanbakh/tanbakh_confirm_delete.html'
    success_url = reverse_lazy('tanbakh_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تنخواه با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#ویو تأیید:
class TanbakhApproveView(PermissionRequiredMixin, UpdateView):
    model = Tanbakh
    fields = []  # هیچ فیلدی برای ویرایش دستی نیست
    template_name = 'tanbakh/tanbakh_approve.html'
    permission_required = 'tanbakh.Tanbakh_approve'  # نام دقیق مجوز از مدل
    success_url = reverse_lazy('tanbakh_list')  # پس از تأیید به لیست برگردد

    def get_object(self, queryset=None):
        # دریافت شیء تنخواه و اطمینان از وجود آن
        obj = get_object_or_404(Tanbakh, pk=self.kwargs['pk'])
        # بررسی اینکه آیا تنخواه در وضعیت قابل تأیید است
        if obj.status not in ['PENDING', 'DRAFT']:
            messages.error(self.request, _('این تنخواه قابل تأیید نیست زیرا در وضعیت در انتظار نیست.'))
            raise ValueError("تنخواه در وضعیت غیرقابل تأیید")
        return obj

    def form_valid(self, form):
        tanbakh = self.get_object()
        user = self.request.user
        stage = tanbakh.current_stage

        # بررسی مجوز کاربر
        if not StageApprover.objects.filter(stage=stage, post__userpost__user=user).exists():
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            # ثبت لاگ تأیید
            ApprovalLog.objects.create(
                tanbakh=tanbakh,
                user=user,
                action='APPROVE',
                stage=stage,
                comment=form.cleaned_data['comment']
            )
            # انتقال به مرحله بعدی یا تغییر وضعیت
            next_stage = WorkflowStage.objects.filter(order__gt=stage.order).order_by('order').first()
            if next_stage:
                tanbakh.current_stage = next_stage
            else:
                tanbakh.status = 'APPROVED'
            tanbakh.approved_by.add(user)
            tanbakh.save()

        messages.success(self.request, _('تنخواه با موفقیت تأیید👍 شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطایی 😒در تأیید تنخواه رخ داد.'))
        return super().form_invalid(form)


#ویو رد
class TanbakhRejectView(PermissionRequiredMixin, UpdateView):
    model = Tanbakh
    fields = []  # هیچ فیلدی برای ویرایش دستی نیست
    template_name = 'tanbakh/tanbakh_reject.html'
    permission_required = 'tanbakh.Tanbakh_approve'  # نام دقیق مجوز از مدل (می‌تواند متفاوت باشد)
    success_url = reverse_lazy('tanbakh_list')  # پس از رد به لیست برگردد

    def get_object(self, queryset=None):
        # دریافت شیء تنخواه و اطمینان از وجود آن
        obj = get_object_or_404(Tanbakh, pk=self.kwargs['pk'])
        # بررسی اینکه آیا تنخواه در وضعیت قابل رد است
        if obj.status not in ['PENDING', 'DRAFT', 'APPROVED']:
            messages.error(self.request, _('این تنخواه قابل رد نیست زیرا در وضعیت مناسب نیست.'))
            raise ValueError("تنخواه در وضعیت غیرقابل رد")
        return obj

    def form_valid(self, form):
        tanbakh = self.get_object()
        user = self.request.user
        stage = tanbakh.current_stage

        ApprovalLog.objects.create(
            tanbakh=tanbakh,
            user=user,
            action='REJECT',
            stage=stage,
            comment=form.cleaned_data['comment']
        )
        tanbakh.status = 'REJECTED'
        tanbakh.save()
        messages.success(self.request, _('تنخواه با رد 👎 شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطایی 👎در رد تنخواه رخ داد.'))
        return super().form_invalid(form)

###########################################

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tanbakh/tanbakh_dashboard.html'
    extra_context = {'title': _('داشبورد مدیریت تنخواه')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # لینک‌ها بر اساس پرمیشن‌ها
        context['links'] = {
            'tanbakh': [
                {'url': 'tanbakh_list', 'label': _('لیست تنخواه‌ها'), 'icon': 'fas fa-list',
                 'perm': 'tanbakh.Tanbakh_view'},
                {'url': 'tanbakh_create', 'label': _('ایجاد تنخواه'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Tanbakh_add'},
            ],
            'factor': [
                {'url': 'factor_list', 'label': _('لیست فاکتورها'), 'icon': 'fas fa-file-invoice',
                 'perm': 'tanbakh.Factor_view'},
                {'url': 'factor_create', 'label': _('ایجاد فاکتور'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Factor_add'},
            ],
            'approval': [
                {'url': 'approval_list', 'label': _('لیست تأییدات'), 'icon': 'fas fa-check-circle',
                 'perm': 'tanbakh.Approval_view'},
                {'url': 'approval_create', 'label': _('ثبت تأیید'), 'icon': 'fas fa-plus',
                 'perm': 'tanbakh.Approval_add'},
            ],
        }

        # فیلتر کردن لینک‌ها بر اساس دسترسی کاربر
        for section in context['links']:
            context['links'][section] = [link for link in context['links'][section] if user.has_perm(link['perm'])]

        return context

# --- Factor Views ---
@method_decorator(has_permission('Factor_view'), name='dispatch')
class FactorListView(LoginRequiredMixin, ListView):
    model = Factor
    template_name = 'tanbakh/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()  # فیلد جدا برای تاریخ
        if query or date_query:
            filter_conditions = Q()
            if query:
                filter_conditions |= (
                        Q(number__icontains=query) |
                        Q(tanbakh__number__icontains=query) |
                        Q(amount__icontains=query) |
                        Q(description__icontains=query) |
                        Q(status__icontains=query) |
                        Q(items__description__icontains=query) |
                        Q(items__amount__icontains=query) |
                        Q(items__quantity__icontains=query) |
                        Q(items__status__icontains=query)
                )
            if date_query:
                filter_conditions &= Q(date=date_query)  # جستجوی دقیق تاریخ
            queryset = queryset.filter(filter_conditions).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context

@method_decorator(has_permission('Factor_view'), name='dispatch')
class FactorDetailView(LoginRequiredMixin, DetailView):
    model = Factor
    template_name = 'tanbakh/factor_detail.html'
    context_object_name = 'factor'
    extra_context = {'title': _('جزئیات فاکتور')}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['title'] = _('جزئیات فاکتور') + f" - {self.object.number}"
        return context

@method_decorator(has_permission('Factor_add'), name='dispatch')
class FactorCreateView(LoginRequiredMixin, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES)
            context['document_formset'] = FactorDocumentFormSet(self.request.POST, self.request.FILES)
        else:
            context['item_formset'] = FactorItemFormSet()
            context['document_formset'] = FactorDocumentFormSet()
        context['title'] = _('ایجاد فاکتور جدید')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_formset = context['document_formset']
        if item_formset.is_valid() and document_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            document_formset.instance = self.object
            document_formset.save()
            messages.success(self.request, _('فاکتور، اقلام و اسناد آن با موفقیت ثبت شدند.'))
            return super().form_valid(form)
        return self.form_invalid(form)

@method_decorator(has_permission('Factor_update'), name='dispatch')
class FactorUpdateView(LoginRequiredMixin, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tanbakh/factor_form.html'
    success_url = reverse_lazy('factor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object)
            context['document_formset'] = FactorDocumentFormSet(self.request.POST, self.request.FILES, instance=self.object)
        else:
            context['item_formset'] = FactorItemFormSet(instance=self.object)
            context['document_formset'] = FactorDocumentFormSet(instance=self.object)
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        # محاسبه جمع کل
        total_amount = sum(item.amount * item.quantity for item in self.object.items.all())
        context['total_amount'] = total_amount
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        item_formset = context['item_formset']
        document_formset = context['document_formset']
        if item_formset.is_valid() and document_formset.is_valid():
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()
            document_formset.instance = self.object
            document_formset.save()
            messages.success(self.request, _('فاکتور، اقلام و اسناد آن با موفقیت به‌روزرسانی شدند.'))
            return super().form_valid(form)
        return self.form_invalid(form)

@method_decorator(has_permission('Factor_delete'), name='dispatch')
class FactorDeleteView(LoginRequiredMixin, DeleteView):
    model = Factor
    template_name = 'tanbakh/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)

# --- Approval Views ---
@method_decorator(has_permission('Approval_view'), name='dispatch')
class ApprovalListView(LoginRequiredMixin, ListView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('لیست تأییدات')}

@method_decorator(has_permission('Approval_view'), name='dispatch')
class ApprovalDetailView(LoginRequiredMixin, DetailView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}

@method_decorator(has_permission('Approval_add'), name='dispatch')
class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user).first()
        user_level = user_post.post.level if user_post else 0

        if form.instance.tanbakh:
            tanbakh = form.instance.tanbakh
            current_status = tanbakh.status
            branch = form.instance.action

            # بررسی مرحله فعلی (اگر current_stage وجود داشته باشد)
            if hasattr(tanbakh, 'current_stage') and branch != tanbakh.current_stage:
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action:
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tanbakh.status = 'APPROVED'
                    tanbakh.hq_status = 'SENT_TO_HQ'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'OPS'
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tanbakh.hq_status = 'HQ_OPS_APPROVED'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'
                elif branch == 'FIN' and tanbakh.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tanbakh.hq_status = 'HQ_FIN_PENDING'
                    tanbakh.status = 'PAID'
                    if hasattr(tanbakh, 'current_stage'):
                        tanbakh.current_stage = 'FIN'  # پایان جریان
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tanbakh.status = 'REJECTED'
            tanbakh.last_stopped_post = user_post.post if user_post else None
            tanbakh.save()

        elif form.instance.factor:
            factor = form.instance.factor
            factor.status = 'APPROVED' if form.instance.action else 'REJECTED'
            factor.save()

        elif form.instance.factor_item:
            item = form.instance.factor_item
            # اگر FactorItem فیلد status داشته باشد
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.action else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial['tanbakh'] = self.request.GET.get('tanbakh')
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

@method_decorator(has_permission('Approval_update'), name='dispatch')
class ApprovalUpdateView(PermissionRequiredMixin, UpdateView):
    model = ApprovalLog
    form_class = ApprovalForm
    template_name = 'tanbakh/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_update'

    def form_valid(self, form):
        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

@method_decorator(has_permission('Approval_delete'), name='dispatch')
class ApprovalDeleteView(PermissionRequiredMixin, DeleteView):
    model = ApprovalLog
    template_name = 'tanbakh/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'tanbakh.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)