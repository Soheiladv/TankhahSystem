from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, DetailView
from core.PermissionBase import PermissionBaseView, get_lowest_access_level
from core.models import WorkflowStage
from tankhah.forms import FactorForm, FactorItemFormSet, TankhahDocumentForm, FactorDocumentForm
from tankhah.models import Factor, Tankhah, FactorDocument, TankhahDocument
import logging
from django.db.models import Q
from persiantools.jdatetime import JalaliDate  # ایمپورت درست
from tankhah.utils import restrict_to_user_organization

logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _

class FactorCreateView(PermissionBaseView, CreateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    context_object_name = 'factor'
    permission_denied_message = 'متاسفانه دسترسی مجاز ندارید'
    permission_codenames = ['tankhah.a_factor_add']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = Tankhah.objects.get(id=self.kwargs.get('tankhah_id', None)) if 'tankhah_id' in self.kwargs else None
        if self.request.POST:
            form = self.form_class(self.request.POST, user=self.request.user, tankhah=tankhah)
            context['form'] = form
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['form'] = self.form_class(user=self.request.user, tankhah=tankhah)
            context['item_formset'] = FactorItemFormSet(prefix='form')
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()
        context['title'] = 'ایجاد فاکتور جدید'
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all() if tankhah else []
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if 'tankhah_id' in self.kwargs:
            kwargs['tankhah'] = Tankhah.objects.get(id=self.kwargs['tankhah_id'])
        return kwargs

    def form_valid(self, form):
        tankhah = form.cleaned_data['tankhah']
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order  # پایین‌ترین order به‌عنوان اولیه
        if tankhah.current_stage.order != initial_stage_order:
            messages.error(self.request, 'فقط در مرحله اولیه می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        if tankhah.status not in ['DRAFT', 'PENDING']:
            messages.error(self.request, 'فقط برای تنخواه‌های پیش‌نویس یا در انتظار می‌توانید فاکتور ثبت کنید.')
            return self.form_invalid(form)

        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, prefix='form')
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
        tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                self.object.status = 'PENDING'  # وضعیت اولیه فاکتور
                self.object.save()

                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)

                tankhah_files = self.request.FILES.getlist('documents')
                for file in tankhah_files:
                    TankhahDocument.objects.create(tankhah=tankhah, document=file)

            messages.success(self.request, 'فاکتور با موفقیت ثبت شد و آماده بررسی است.')
            return super().form_valid(form)
        else:
            logger.info(f"Errors: {item_formset.errors}, {document_form.errors}, {tankhah_document_form.errors}")
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return super().handle_no_permission()

class FactorUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_update']
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object.tankhah
        if self.request.POST:
            context['form'] = self.form_class(self.request.POST, user=self.request.user, instance=self.object)
            context['item_formset'] = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form')
            context['document_form'] = FactorDocumentForm(self.request.POST, self.request.FILES)
            context['tankhah_document_form'] = TankhahDocumentForm(self.request.POST, self.request.FILES)
        else:
            context['form'] = self.form_class(user=self.request.user, instance=self.object)
            context['item_formset'] = FactorItemFormSet(instance=self.object, prefix='form')
            context['document_form'] = FactorDocumentForm()
            context['tankhah_document_form'] = TankhahDocumentForm()

        context['tankhah_count'] = 1  # اگر فقط یک تنخواه مرتبط است، یا منطق دیگری اعمال کنید
        context['documents_count'] = self.object.documents.count() + tankhah.documents.count()  # جمع اسناد فاکتور و تنخواه
        context['title'] = _('ویرایش فاکتور') + f" - {self.object.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()
        context['total_amount'] = sum(item.amount * item.quantity for item in self.object.items.all())
        return context

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if getattr(obj, 'locked', False):
            raise PermissionDenied("این فاکتور قفل شده و قابل ویرایش نیست.")
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order  # پایین‌ترین order به‌عنوان اولیه
        user_post = request.user.userpost_set.first().post if request.user.userpost_set.exists() else None
        lowest_level = get_lowest_access_level()  # فرضاً پایین‌ترین سطح دسترسی

        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل ویرایش نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
        if obj.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
            raise PermissionDenied(_('فاکتور تأییدشده یا پرداخت‌شده قابل ویرایش نیست.'))
        if getattr(obj, 'is_finalized', False) and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('شما اجازه ویرایش این فاکتور نهایی‌شده را ندارید.'))

        if not request.user.is_superuser:
            if obj.tankhah.current_stage.order != initial_stage_order:
                logger.info(f"مرحله فعلی: {obj.tankhah.current_stage.order}, مرحله اولیه: {initial_stage_order}")
                raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
            if obj.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
                raise PermissionDenied(_('فاکتور تأییدشده یا پرداخت‌شده قابل ویرایش نیست.'))
            if getattr(obj, 'is_finalized', False) and not request.user.has_perm('tankhah.Factor_full_edit'):
                raise PermissionDenied(_('شما اجازه ویرایش این فاکتور نهایی‌شده را ندارید.'))
            if user_post and user_post.level != lowest_level and not request.user.has_perm('tankhah.Factor_full_edit'):
                raise PermissionDenied(_('فقط کاربران سطح پایین یا دارای مجوز کامل می‌توانند ویرایش کنند.'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.object:
            tankhah = self.object.tankhah
            restrict_to_user_organization(self.request.user, tankhah.organization)
            kwargs['tankhah'] = tankhah
        return kwargs

    def form_valid(self, form):
        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form')
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
        tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)

        if item_formset.is_valid() and document_form.is_valid() and tankhah_document_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                logger.info(f"Saved {self.object.items.count()} items for factor {self.object.number}")

                # لاگ داده‌های POST برای دیباگ
                logger.info(f"POST data: {self.request.POST}")

                # پردازش حذف اسناد فاکتور
                for key in self.request.POST.keys():
                    if key.startswith('delete_factor_doc_'):
                        doc_id = self.request.POST.get(key)  # مقدار value چک‌باکس
                        if doc_id:  # اگر مقدار وجود دارد
                            try:
                                doc_id_int = int(doc_id)
                                FactorDocument.objects.get(pk=doc_id_int, factor=self.object).delete()
                                logger.info(f"Deleted factor document with ID {doc_id_int}")
                            except (ValueError, FactorDocument.DoesNotExist):
                                logger.warning(f"Invalid or non-existent factor document ID: {doc_id}")
                                continue

                # # پردازش حذف اسناد تنخواه
                # for key in self.request.POST.keys():
                #     if key.startswith('delete_tankhah_doc_'):
                #         doc_id = self.request.POST.get(key)
                #         if doc_id:
                #             try:
                #                 doc_id_int = int(doc_id)
                #                 TankhahDocument.objects.get(pk=doc_id_int, tankhah=self.object.tankhah).delete()
                #                 logger.info(f"Deleted tankhah document with ID {doc_id_int}")
                #             except (ValueError, TankhahDocument.DoesNotExist):
                #                 logger.warning(f"Invalid or non-existent tankhah document ID: {doc_id}")
                #                 continue

                # اضافه کردن اسناد جدید فاکتور
                factor_files = self.request.FILES.getlist('files')
                for file in factor_files:
                    FactorDocument.objects.create(factor=self.object, file=file)
                    logger.info(f"Added new factor document: {file.name}")

                # # اضافه کردن اسناد جدید تنخواه
                # tankhah_files = self.request.FILES.getlist('documents')
                # for file in tankhah_files:
                #     TankhahDocument.objects.create(tankhah=self.object.tankhah, document=file)
                #     logger.info(f"Added new tankhah document: {file.name}")

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)
        else:
            logger.info(
                f"Formset errors: {item_formset.errors}, Document errors: {document_form.errors}, Tankhah doc errors: {tankhah_document_form.errors}")
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))


class FactorDeleteView(PermissionBaseView, DeleteView):
    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_delete']
    check_organization = True

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        initial_stage_order = WorkflowStage.objects.order_by('-order').first().order
        if obj.status != 'PENDING' and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('فاکتور تأییدشده یا ردشده قابل حذف نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را حذف کنید.'))
        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل حذف نیست.'))
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        messages.success(self.request, _('فاکتور با موفقیت حذف شد.'))
        return redirect(self.success_url)

class FactorListView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factor_list.html'
    context_object_name = 'factors'
    paginate_by = 10
    extra_context = {'title': _('لیست فاکتورها')}
    permission_codenames = [
    'tankhah.a_factor_view'
    #     'Tankhah.Tankhah_view', 'Tankhah.Tankhah_update', 'Tankhah.Tankhah_add',
    #     'Tankhah.Tankhah_approve', 'Tankhah.Tankhah_part_approve', 'Tankhah.FactorItem_approve',
    #     'Tankhah.edit_full_Tankhah', 'Tankhah.Tankhah_hq_view', 'Tankhah.Tankhah_hq_approve',
    #     'Tankhah.Tankhah_HQ_OPS_PENDING', 'Tankhah.Tankhah_HQ_OPS_APPROVED', 'Tankhah.FactorItem_approve'
    ]

    def get_queryset(self):
        user = self.request.user
        user_posts = user.userpost_set.all()
        if not user_posts.exists():
            return Factor.objects.none()

        user_orgs = [up.post.organization for up in user.userpost_set.all()]
        is_hq_user = any(up.post.organization.org_type == 'HQ' for up in user.userpost_set.all())

        if is_hq_user:
            queryset = Factor.objects.all()
        else:
            queryset = Factor.objects.filter(tankhah__organization__in=user_orgs)

        query = self.request.GET.get('q', '').strip()
        date_query = self.request.GET.get('date', '').strip()
        status_query = self.request.GET.get('status', '').strip()

        if query or date_query or status_query:
            filter_conditions = Q()
            if query:
                filter_conditions |= (
                    Q(number__icontains=query) |
                    Q(Tankhah__number__icontains=query) |
                    Q(amount__icontains=query) |
                    Q(description__icontains=query)
                )
            if date_query:
                try:
                    if len(date_query) == 4:  # فقط سال
                        year = int(date_query)
                        gregorian_year = year - 621
                        filter_conditions &= Q(date__year=gregorian_year)
                    else:  # تاریخ کامل
                        year, month, day = map(int, date_query.split('-'))
                        gregorian_date = JalaliDate(year, month, day).to_gregorian()
                        filter_conditions &= Q(date=gregorian_date)
                except (ValueError, Exception):
                    filter_conditions &= Q(date__isnull=True)
            if status_query:
                filter_conditions &= Q(status=status_query)
            queryset = queryset.filter(filter_conditions).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['date_query'] = self.request.GET.get('date', '')
        context['status_query'] = self.request.GET.get('status', '')
        context['is_hq'] = any(up.post.organization.org_type == 'HQ' for up in self.request.user.userpost_set.all())
        # نمایش رکورد های قفل شده
        for factor in context['factors']:
            tankhah = factor.tankhah
            current_stage_order = tankhah.current_stage.order
            user = self.request.user
            user_posts = user.userpost_set.all()
            user_can_approve = any(
                p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists()
                for p in user_posts
            ) and tankhah.status in ['DRAFT', 'PENDING']
            factor.can_approve = user_can_approve
            # قفل شدن: اگه مرحله تأییدکننده پایین‌تر (order کمتر) از مرحله فعلی باشه
            factor.is_locked = factor.locked_by_stage is not None and factor.locked_by_stage.order < current_stage_order
        return context

class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_detail.html'  # تمپلیت نمایشی جدید
    context_object_name = 'factor'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    permission_codename = 'tankhah.a_factor_view'
    check_organization = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.get_object()
        tankhah = factor.tankhah

        context['title'] = _('جزئیات فاکتور') + f" - {factor.number}"
        context['tankhah'] = tankhah
        context['tankhah_documents'] = tankhah.documents.all()

        # محاسبه جمع کل و جمع هر آیتم
        items_with_total = [
            {'item': item, 'total': item.amount * item.quantity}
            for item in factor.items.all()
        ]
        context['items_with_total'] = items_with_total
        context['total_amount'] = sum(item['total'] for item in items_with_total)
        context['difference'] = factor.amount - context['total_amount'] if factor.amount else 0

        return context

    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect('factor_list')