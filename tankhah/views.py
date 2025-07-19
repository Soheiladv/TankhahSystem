import logging
from django.utils import timezone
import jdatetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, View, TemplateView, ListView
from notifications.signals import notify
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from accounts.models import CustomUser
from core.models import UserPost, WorkflowStage, SubProject, Project
from .Factor.forms_Factor import FactorForm
from .fun_can_edit_approval import can_edit_approval
from tankhah.models import ApprovalLog, Tankhah, StageApprover, Factor, FactorItem, FactorDocument, TankhahDocument, \
    FactorHistory, create_budget_transaction
from .utils import restrict_to_user_organization
from persiantools.jdatetime import JalaliDate
from django.db.models import Q
from core.views import PermissionBaseView
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.contrib import messages
from django.forms import inlineformset_factory
# from tankhah.forms import FactorForm, FactorItemForm, FactorDocumentForm, TankhahDocumentForm
from budgets.budget_calculations import get_tankhah_remaining_budget, get_factor_remaining_budget
from core.PermissionBase import PermissionBaseView, get_lowest_access_level

from tankhah.forms import (
    FactorDocumentForm, TankhahDocumentForm, get_factor_item_formset, FactorApprovalForm
)
logger = logging.getLogger(__name__)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from .models import ItemCategory
from .forms import ItemCategoryForm
###########################################
# ثبت و ویرایش تنخواه
def get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        user_orgs = set(up.post.organization for up in request.user.userpost_set.all())
        logger.info(f'project_id: {project_id}, user_orgs: {user_orgs}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بر اساس project_id برگردون، بدون فیلتر سازمان
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)
def old___get_subprojects(request):
    logger.info('ورود به تابع get_subprojects')
    project_id = request.GET.get('project_id')
    if not project_id:
        logger.warning('project_id دریافت نشد')
        return JsonResponse({'subprojects': []}, status=400)

    try:
        project_id = int(project_id)
        logger.info(f'project_id: {project_id}')

        project = Project.objects.get(id=project_id)
        logger.info(f'پروژه {project_id}: {project.name}')

        # همه ساب‌پروژه‌ها رو بدون فیلتر سازمان برگردون
        subprojects = SubProject.objects.filter(project_id=project_id).values('id', 'name')
        logger.info(f'subprojects found: {list(subprojects)}')
        return JsonResponse({'subprojects': list(subprojects)})
    except Project.DoesNotExist:
        logger.error(f'پروژه با id {project_id} یافت نشد')
        return JsonResponse({'subprojects': []}, status=404)
    except ValueError:
        logger.error(f'project_id نامعتبر: {project_id}')
        return JsonResponse({'subprojects': []}, status=400)
    except Exception as e:
        logger.error(f'خطا در get_subprojects: {str(e)}')
        return JsonResponse({'subprojects': []}, status=500)

    #* ** * * ** * ** **

#--------------------------------------------
"""بررسی سطح فاکتور"""
def mark_approval_seen(request, tankhah):
    user_post = UserPost.objects.filter(user=request.user, end_date__isnull=True).first()
    if user_post:
        from tankhah.models import ApprovalLog
        ApprovalLog.objects.filter(
            tankhah=tankhah,
            post__level__lte=user_post.post.level,
            seen_by_higher=False
        ).update(seen_by_higher=True, seen_at=timezone.now())
        logger.info(f"Approval logs for Tankhah {tankhah.id} marked as seen by {request.user.username}")
#------------------------------------------------

class oldd__FactorUpdateView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorForm
    template_name = 'tankhah/factor_form.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_update']
    check_organization = True
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.locked:
            raise PermissionDenied(_("این فاکتور قفل شده و قابل ویرایش نیست."))
        return obj

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        initial_stage_order = WorkflowStage.objects.order_by('order').first().order
        user_post = request.user.userpost_set.first().post if request.user.userpost_set.exists() else None
        lowest_level = get_lowest_access_level()

        if obj.locked_by_stage and obj.locked_by_stage.order < obj.tankhah.current_stage.order:
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل ویرایش نیست.'))
        if obj.tankhah.current_stage.order != initial_stage_order:
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را ویرایش کنید.'))
        if obj.tankhah.status in ['APPROVED', 'SENT_TO_HQ', 'HQ_OPS_APPROVED', 'PAID']:
            raise PermissionDenied(_('فاکتور تأییدشده یا پرداخت‌شده قابل ویرایش نیست.'))
        if obj.is_finalized and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('شما اجازه ویرایش این فاکتور نهایی‌شده را ندارید.'))
        if not request.user.is_superuser and user_post and user_post.level != lowest_level and not request.user.has_perm('tankhah.Factor_full_edit'):
            raise PermissionDenied(_('فقط کاربران سطح پایین یا دارای مجوز کامل می‌توانند ویرایش کنند.'))

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.object:
            restrict_to_user_organization(self.request.user, self.object.tankhah.organization)
            kwargs['tankhah'] = self.object.tankhah
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tankhah = self.object.tankhah

        # تعریف FactorItemFormSet در داخل متد
        # FactorItemFormSet = inlineformset_factory(
        #     Factor, FactorItem, form=FactorItemForm,
        #     fields=['description', 'amount', 'quantity'],
        #     extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
        # )
        FactorItemFormSet = get_factor_item_formset()

        if self.request.method == 'POST':
            context.update({
                'form': self.form_class(self.request.POST, self.request.FILES, user=self.request.user, instance=self.object),
                'item_formset': FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form'),
                'document_form': FactorDocumentForm(self.request.POST, self.request.FILES),
                'tankhah_document_form': TankhahDocumentForm(self.request.POST, self.request.FILES)
            })
        else:
            context.update({
                'form': self.form_class(user=self.request.user, instance=self.object),
                'item_formset': FactorItemFormSet(instance=self.object, prefix='form'),
                'document_form': FactorDocumentForm(),
                'tankhah_document_form': TankhahDocumentForm()
            })

        context.update({
            'tankhah': tankhah,
            'tankhah_count': 1,
            'documents_count': self.object.documents.count() + tankhah.documents.count(),
            'title': _(f"ویرایش فاکتور {self.object.number}"),
            'tankhah_remaining_budget': get_tankhah_remaining_budget(tankhah),
            'factor_remaining_budget': get_factor_remaining_budget(self.object),
            'tankhah_documents': tankhah.documents.all(),
            'total_amount': sum(item.amount * item.quantity for item in self.object.items.all()),
        })

        return context

    def form_valid(self, form):
        # # تعریف FactorItemFormSet در داخل متد
        # FactorItemFormSet = inlineformset_factory(
        #     Factor, FactorItem, form=FactorItemForm,
        #     fields=['description', 'amount', 'quantity'],
        #     extra=1, can_delete=True, min_num=1, validate_min=True, max_num=100
        # )
        FactorItemFormSet = get_factor_item_formset()

        item_formset = FactorItemFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='form')
        document_form = FactorDocumentForm(self.request.POST, self.request.FILES)
        tankhah_document_form = TankhahDocumentForm(self.request.POST, self.request.FILES)

        if all([item_formset.is_valid(), document_form.is_valid(), tankhah_document_form.is_valid()]):
            with transaction.atomic():
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()

                self._handle_deleted_documents()
                self._handle_new_documents()

            messages.success(self.request, _('فاکتور با موفقیت به‌روزرسانی شد.'))
            return super().form_valid(form)

        logger.info(f"Form errors: item_formset={item_formset.errors}, document_form={document_form.errors}, tankhah_document_form={tankhah_document_form.errors}")
        return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

    def _handle_deleted_documents(self):
        """حذف اسناد تیک‌خورده از فرم"""
        for key in self.request.POST:
            if key.startswith('delete_factor_doc_'):
                try:
                    doc_id = int(self.request.POST[key])
                    FactorDocument.objects.get(pk=doc_id, factor=self.object).delete()
                    logger.info(f"Deleted factor document ID: {doc_id}")
                except (ValueError, FactorDocument.DoesNotExist):
                    logger.warning(f"Invalid factor document ID: {self.request.POST[key]}")

    def _handle_new_documents(self):
        """اضافه کردن اسناد جدید"""
        for file in self.request.FILES.getlist('files'):
            FactorDocument.objects.create(factor=self.object, file=file)
            logger.info(f"Added new factor document: {file.name}")

#----------------------------------------------------------
class FactorDeleteView(PermissionBaseView, DeleteView):
    model = Factor
    template_name = 'tankhah/factor_confirm_delete.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.factor_delete']
    check_organization = True

    def dispatch(self, request, *args, **kwargs):
        """
        بررسی دسترسی‌ها و شرایط حذف فاکتور.
        """
        obj = self.get_object()
        tankhah = obj.tankhah
        user = request.user
        user_post = user.userpost_set.filter(is_active=True, end_date__isnull=True).first()

        # بررسی پست فعال کاربر
        if not user_post:
            logger.error(f"[FactorDeleteView] کاربر {user.username} هیچ پست فعالی ندارد")
            messages.error(request, _("شما پست فعالی ندارید."))
            return redirect('factor_item_approve', pk=obj.pk)

        # بررسی قفل بودن تنخواه یا فاکتور
        if tankhah.is_locked or tankhah.is_archived or obj.is_locked:
            logger.warning(
                f"[FactorDeleteView] تنخواه {tankhah.number} یا فاکتور {obj.number} قفل/آرشیو شده است"
            )
            messages.error(request, _('این فاکتور یا تنخواه قفل/آرشیو شده و قابل حذف نیست.'))
            return redirect('factor_item_approve', pk=obj.pk)

        # بررسی وضعیت فاکتور
        if obj.status != 'PENDING' and not request.user.has_perm('tankhah.Factor_full_edit'):
            logger.warning(
                f"[FactorDeleteView] فاکتور {obj.number} در وضعیت {obj.status} قابل حذف نیست"
            )
            raise PermissionDenied(_('فاکتور تأییدشده یا ردشده قابل حذف نیست.'))

        # بررسی مرحله ابتدایی
        initial_stage = WorkflowStage.objects.order_by('order').first()  # مرحله با order=1
        if not initial_stage or tankhah.current_stage.order != initial_stage.order:
            logger.warning(
                f"[FactorDeleteView] فاکتور {obj.number} فقط در مرحله ابتدایی قابل حذف است"
            )
            raise PermissionDenied(_('فقط در مرحله اولیه می‌توانید فاکتور را حذف کنید.'))

        # بررسی قفل توسط مرحله بالاتر
        if obj.locked_by_stage and obj.locked_by_stage.order < tankhah.current_stage.order:
            logger.warning(
                f"[FactorDeleteView] فاکتور {obj.number} توسط مرحله {obj.locked_by_stage} قفل شده است"
            )
            raise PermissionDenied(_('این فاکتور توسط مرحله بالاتر قفل شده و قابل حذف نیست.'))

        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        حذف فاکتور، آزادسازی بودجه، ثبت لاگ و تاریخچه، و ارسال اعلان.
        """
        self.object = self.get_object()
        tankhah = self.object.tankhah
        user = request.user
        user_post = user.userpost_set.filter(is_active=True).first()

        try:
            with transaction.atomic():
                # ثبت تراکنش بازگشت بودجه
                create_budget_transaction(
                    allocation=tankhah.project_budget_allocation,
                    transaction_type='RETURN',
                    amount=self.object.amount,
                    related_obj=self.object,
                    created_by=user,
                    description=f"بازگشت بودجه به دلیل حذف فاکتور {self.object.number} در مرحله ابتدایی",
                    transaction_id=f"TX-FAC-DEL-{self.object.number}"
                )
                tankhah.remaining_budget += self.object.amount
                tankhah.save(update_fields=['remaining_budget'])

                # ثبت لاگ
                ApprovalLog.objects.create(
                    tankhah=tankhah,
                    factor=self.object,
                    user=user,
                    action='REJECT',
                    stage=tankhah.current_stage,
                    comment=f"حذف فاکتور {self.object.number} در مرحله ابتدایی",
                    post=user_post.post if user_post else None
                )

                # ثبت تاریخچه
                FactorHistory.objects.create(
                    factor=self.object,
                    change_type=FactorHistory.ChangeType.DELETION,
                    changed_by=user,
                    old_data={'status': self.object.status, 'amount': str(self.object.amount)},
                    new_data={},
                    description=f"فاکتور {self.object.number} حذف شد"
                )

                # ارسال اعلان
                self.send_notifications(
                    entity=self.object,
                    action='DELETED',
                    priority='HIGH',
                    description=f"فاکتور {self.object.number} حذف شد (توسط {user.username}).",
                    recipients=[self.object.created_by_post] if self.object.created_by_post else []
                )

                # حذف فاکتور
                self.object.delete()
                logger.info(f"[FactorDeleteView] فاکتور {self.object.pk} حذف شد و بودجه آزاد شد")
                messages.success(request, _('فاکتور با موفقیت حذف شد و بودجه آزاد شد.'))
                return redirect(self.success_url)
        except Exception as e:
            logger.error(f"[FactorDeleteView] خطا در حذف فاکتور {self.object.pk}: {e}", exc_info=True)
            messages.error(request, _("خطا در حذف فاکتور."))
            return redirect('factor_item_approve', pk=self.object.pk)

#----------------------------------------------------------
class FactorDetailView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_detail.html'  # تمپلیت نمایشی جدید
    context_object_name = 'factor'
    permission_denied_message = _('متاسفانه دسترسی مجاز ندارید')
    permission_codename = 'tankhah.factor_view'
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
#------------------------------------------------
"""  ویو برای تأیید فاکتور"""
class FactorApproveView(UpdateView):
    model =  Factor
    form_class =  FactorApprovalForm   # فرض بر وجود این فرم
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.factor_view', 'tankhah.factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        tankhah = factor.tankhah
        user_posts = self.request.user.userpost_set.all()

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_items_approved:
                factor.status = 'APPROVED'
                factor.approved_by.add(self.request.user)
                factor.locked_by_stage = tankhah.current_stage  # قفل برای مراحل بالاتر
                factor.save()

                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است', target=tankhah)
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tankhah.status = 'COMPLETED'
                        tankhah.save()
                        messages.success(self.request, _('تنخواه تکمیل شد.'))
                else:
                    messages.success(self.request, _('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

        return super().form_valid(form)
class FactorApproveView1(PermissionBaseView,UpdateView):
    model =  Factor
    form_class = 'tankhah.forms.FactorApprovalForm'  # فرض می‌کنیم این فرم وجود دارد
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.a_factor_view', 'tankhah.a_factor_update']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('تأیید فاکتور') + f" - {self.object.number}"
        context['items'] = self.object.items.all()
        return context

    def form_valid(self, form):
        factor = self.object
        tankhah = factor.tankhah
        user_posts = self.request.user.userpost_set.all()

        # # چک دسترسی به سازمان
        # try:
        #     restrict_to_user_organization(self.request.user, [Tankhah.organization])
        # except PermissionDenied as e:
        #     messages.error(self.request, str(e))
        #     return self.form_invalid(form)

        # چک اینکه کاربر تأییدکننده این مرحله است
        if not any(p.post.stageapprover_set.filter(stage='tankhah.Tankhah'.current_stage).exists() for p in user_posts):
            messages.error(self.request, _('شما مجاز به تأیید در این مرحله نیستید.'))
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())
            if all_items_approved:
                factor.status = 'APPROVED'
                factor.approved_by.add(self.request.user)
                factor.locked_by_stage = tankhah.current_stage  # قفل برای مراحل بالاتر
                factor.save()

                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    next_stage = WorkflowStage.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            notify.send(self.request.user, recipient=approvers, verb='تنخواه برای تأیید آماده است', target=tankhah)
                            messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tankhah.status = 'COMPLETED'
                        tankhah.save()
                        messages.success(self.request, _('تنخواه تکمیل شد.'))
                else:
                    messages.success(self.request, _('فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.'))
            else:
                messages.warning(self.request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))

        return super().form_valid(form)

    def handle_no_permission(self):
        messages.error(self.request, _('شما مجوز لازم برای تأیید این فاکتور را ندارید.'))
        return redirect('factor_list')
"""تأیید آیتم‌های فاکتور"""
class old__FactorItemApproveView(PermissionBaseView, DetailView):
    model = Factor
    template_name = 'tankhah/factor_item_approve.html'
    permission_codenames = ['tankhah.FactorItem_approve']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factor = self.object
        user = self.request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        if user_level > factor.tankhah.current_stage.order:
            mark_approval_seen(self.request, factor.tankhah)

        from tankhah.forms import  FactorItemApprovalForm
        from django.forms import formset_factory
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status.upper()} for item in factor.items.all()]
        context['formset'] = FactorItemApprovalFormSet(self.request.POST or None, initial=initial_data, prefix='items')
        context['item_form_pairs'] = zip(factor.items.all(), context['formset'])

        context['approval_logs'] = ApprovalLog.objects.filter(tankhah=factor.tankhah).order_by('-timestamp')
        context['title'] = _('تأیید ردیف‌های فاکتور') + f" - {factor.number}"
        context['tankhah'] = factor.tankhah
        context['can_edit'] = can_edit_approval(user, factor.tankhah, factor.tankhah.current_stage)
        context['can_change_stage'] = context['can_edit'] and factor.tankhah.current_stage.order < user_level
        context['workflow_stages'] = WorkflowStage.objects.filter(order__lte=max_change_level).order_by('order')
        context['show_payment_number'] = factor.tankhah.status == 'APPROVED' and not factor.tankhah.payment_number
        context['can_final_approve'] = context['can_edit'] and all(
            f.status == 'APPROVED' for f in factor.tankhah.factors.all())
        context['higher_approval_changed'] = ApprovalLog.objects.filter(
            tankhah=factor.tankhah,
            post__level__gt=user_level,
            action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
        ).exists()
        # بررسی اینکه آیا تأیید نهایی قبلاً انجام شده یا نه
        context['is_final_approved'] = ApprovalLog.objects.filter(
            tankhah=factor.tankhah,
            action='STAGE_CHANGE',
            comment__contains='تأیید نهایی'
        ).exists()

        logger.info(f"Factor Item IDs: {[item.id for item in factor.items.all()]}")
        logger.info(f"Current Tankhah ID: {factor.tankhah.id}")
        logger.info(f"Approval Logs Count: {context['approval_logs'].count()}")
        logger.info(f"Factor Item Statuses: {[item.status for item in factor.items.all()]}")
        for form in context['formset']:
            logger.info(f"Form Action Value: {form['action'].value()}")

        return context

    def post(self, request, *args, **kwargs):
        factor = self.get_object()
        tankhah = factor.tankhah
        user = request.user
        user_post = UserPost.objects.filter(user=user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0
        max_change_level = user_post.post.max_change_level if user_post else 0

        logger.info(f"POST Request for Factor {factor.pk}:")
        logger.info(f"User: {user.username}, Level: {user_level}, Max Change Level: {max_change_level}")
        logger.info(f"POST Data: {request.POST}")

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        can_edit = can_edit_approval(user, tankhah, tankhah.current_stage)
        if not can_edit:
            messages.error(request, _('تأیید توسط سطح بالاتر انجام شده یا خارج از دسترسی شماست.'))
            return redirect('factor_item_approve', pk=factor.pk)

        # تغییر مرحله دستی
        if 'change_stage' in request.POST:
            new_stage_order = int(request.POST.get('new_stage_order'))
            if factor.tankhah.current_stage.order >= user_level:
                messages.error(request, _('شما نمی‌توانید مراحل بالاتر یا برابر با سطح خود را تغییر دهید.'))
                return redirect('factor_item_approve', pk=factor.pk)
            if new_stage_order > max_change_level:
                messages.error(request,
                               _(f"سطح انتخاب‌شده ({new_stage_order}) از حداکثر سطح مجاز شما ({max_change_level}) بیشتر است."))
                return redirect('factor_item_approve', pk=factor.pk)
            new_stage = WorkflowStage.objects.filter(order=new_stage_order).first()
            if new_stage:
                tankhah.current_stage = new_stage
                tankhah.status = 'PENDING'
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
            return redirect('factor_item_approve', pk=factor.pk)

        # رد کل فاکتور
        if request.POST.get('reject_factor'):
            with transaction.atomic():
                factor.status = 'REJECTED'
                factor.save()
                for item in factor.items.all():
                    item.status = 'REJECTED'
                    item.save()
                    ApprovalLog.objects.create(
                        tankhah=tankhah,
                        factor_item=item,
                        user=user,
                        action='REJECT',
                        stage=tankhah.current_stage,
                        comment='فاکتور به‌صورت کامل رد شد',
                        post=user_post.post if user_post else None
                    )
                messages.error(request, _('فاکتور به‌صورت کامل رد شد.'))
                logger.info(f"Factor {factor.pk} fully rejected by {user.username}")
            return redirect('dashboard_flows')

        # تأیید نهایی
        if request.POST.get('final_approve'):
            with transaction.atomic():
                if all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                    current_stage_order = tankhah.current_stage.order
                    next_stage = WorkflowStage.objects.filter(order__gt=current_stage_order).order_by('order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            user=user,
                            action='STAGE_CHANGE',
                            stage=next_stage,
                            comment=f"تأیید نهایی و انتقال به مرحله {next_stage.name} توسط {user.get_full_name()}",
                            post=user_post.post if user_post else None
                        )
                        messages.success(request,
                                         _(f"تأیید نهایی انجام شد و تنخواه به مرحله {next_stage.name} منتقل شد."))
                        return redirect('factor_list')
                    elif tankhah.current_stage.is_final_stage:
                        payment_number = request.POST.get('payment_number')
                        if payment_number:
                            tankhah.payment_number = payment_number
                            tankhah.status = 'PAID'
                            tankhah.save()
                            messages.success(request, _('تنخواه پرداخت شد.'))
                            return redirect('factor_list')
                        else:
                            messages.warning(request, _('شماره پرداخت وارد نشده است.'))
                    else:
                        messages.error(request, _('مرحله بعدی وجود ندارد.'))
                else:
                    messages.warning(request, _('همه فاکتورها باید تأیید شده باشند تا تأیید نهایی انجام شود.'))
                return redirect('factor_item_approve', pk=factor.pk)

        # تأیید/رد ردیف‌ها
        from tankhah.forms import  FactorItemApprovalForm
        from django.forms.formsets import formset_factory
        FactorItemApprovalFormSet = formset_factory(FactorItemApprovalForm, extra=0)
        initial_data = [{'item_id': item.id, 'action': item.status.upper()} for item in factor.items.all()]
        formset = FactorItemApprovalFormSet(request.POST, initial=initial_data, prefix='items')

        if formset.is_valid():
            with transaction.atomic():
                all_approved = True
                any_rejected = False
                bulk_approve = request.POST.get('bulk_approve') == 'on'
                bulk_reject = request.POST.get('bulk_reject') == 'on'
                has_changes = False

                for form, item in zip(formset, factor.items.all()):
                    action = 'APPROVE' if bulk_approve else ('REJECT' if bulk_reject else form.cleaned_data['action'])
                    if action != item.status:
                        has_changes = True
                        ApprovalLog.objects.create(
                            tankhah=tankhah,
                            factor_item=item,
                            user=user,
                            action=action,
                            stage=tankhah.current_stage,
                            comment=form.cleaned_data.get('comment', ''),
                            post=user_post.post if user_post else None
                        )
                        item.status = action
                        item.save()
                        logger.info(f"Item {item.id} updated to {action} by {user.username}")
                    if action == 'REJECT':
                        all_approved = False
                        any_rejected = True
                    elif action != 'APPROVE':
                        all_approved = False

                higher_approval_changed = ApprovalLog.objects.filter(
                    tankhah=tankhah,
                    post__level__gt=user_level,
                    action__in=['APPROVE', 'REJECT', 'STAGE_CHANGE']
                ).exists()

                if any_rejected:
                    factor.status = 'PENDING'
                    messages.warning(request, _('برخی ردیف‌ها رد شدند.'))
                    # انتقال به رده پایین‌تر اگر ردیفی رد شده باشد
                    current_stage_order = tankhah.current_stage.order
                    if current_stage_order > 1:  # مطمئن می‌شیم به زیر مرحله 1 نره
                        previous_stage = WorkflowStage.objects.filter(order=current_stage_order - 1).first()
                        if previous_stage:
                            tankhah.current_stage = previous_stage
                            tankhah.status = 'PENDING'
                            tankhah.save()
                            ApprovalLog.objects.create(
                                tankhah=tankhah,
                                user=user,
                                action='STAGE_CHANGE',
                                stage=previous_stage,
                                comment=f"انتقال به مرحله پایین‌تر ({previous_stage.name}) به دلیل رد ردیف",
                                post=user_post.post if user_post else None
                            )
                            messages.info(request,
                                          _(f"تنخواه به مرحله {previous_stage.name} منتقل شد به دلیل رد ردیف."))
                elif all_approved and factor.items.exists():
                    factor.status = 'APPROVED'
                    if higher_approval_changed:
                        messages.info(request,
                                      _('سطح بالاتری قبلاً تغییراتی اعمال کرده است و شما نمی‌توانید ادامه دهید.'))
                    elif not has_changes:
                        messages.info(request,
                                      _('هیچ تغییری در وضعیت ردیف‌ها رخ نداده است. برای انتقال به مرحله بعد، تأیید نهایی را بزنید.'))
                    else:
                        messages.success(request, _('فاکتور تأیید شد. برای انتقال به مرحله بعد، تأیید نهایی را بزنید.'))
                else:
                    factor.status = 'PENDING'
                    messages.warning(request, _('برخی ردیف‌ها هنوز تأیید نشده‌اند.'))
                factor.save()

                messages.success(request, _('تغییرات با موفقیت ثبت شدند.'))
            return redirect('factor_item_approve', pk=factor.pk)
        else:
            messages.error(request, _('فرم نامعتبر است.'))
            logger.error(f"Formset errors: {formset.errors}")
            self.object = factor
            return self.render_to_response(self.get_context_data(formset=formset))
class FactorItemRejectView(PermissionBaseView, View):
    permission_codenames = ['tankhah.FactorItem_approve']
    template_name = 'tankhah/factor_item_reject_confirm.html'

    def get(self, request, pk):
        item = get_object_or_404('tankhah.FactorItem', pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # نمایش فرم تأیید
        return render(request, self.template_name, {
            'item': item,
            'factor': factor,
            'tankhah': tankhah,
        })

    def post(self, request, pk):
        item = get_object_or_404('tankhah.FactorItem', pk=pk)
        factor = item.factor
        tankhah = factor.tankhah
        user_posts = request.user.userpost_set.all()

        # چک دسترسی
        try:
            restrict_to_user_organization(request.user, [tankhah.organization])
        except PermissionDenied as e:
            messages.error(request, str(e))
            return redirect('dashboard_flows')

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(request, _('شما اجازه رد این ردیف را ندارید.'))
            return redirect('dashboard_flows')

        # تصمیم کاربر
        keep_in_tankhah = request.POST.get('keep_in_tankhah') == 'yes'

        with transaction.atomic():
            # رد کردن ردیف فاکتور
            item.status = 'REJECTED'
            item.save()
            logger.info(f"ردیف فاکتور {item.id} رد شد توسط {request.user.username}")

            # ثبت در لاگ
            ApprovalLog.objects.create(
                tankhah=tankhah,
                factor_item=item,
                user=request.user,
                action='REJECT',
                stage=tankhah.current_stage,
                comment='رد شده توسط کاربر'
            )

            if keep_in_tankhah:
                # فاکتور توی تنخواه می‌مونه و به تأیید برمی‌گرده
                factor.status = 'PENDING'
                factor.save()
                messages.info(request, _('ردیف فاکتور رد شد و فاکتور برای تأیید دوباره در تنخواه باقی ماند.'))
            else:
                # فاکتور رد می‌شه، تنخواه دست‌نخورده می‌مونه
                factor.status = 'REJECTED'
                factor.save()
                logger.info(f"فاکتور {factor.number} رد شد توسط {request.user.username}")
                messages.error(request, _('فاکتور رد شد و از جریان تأیید خارج شد.'))

        return redirect('dashboard_flows')# ---######## Approval Views ---
class ApprovalListView1(PermissionBaseView, ListView):
    model =  ApprovalLog
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        # تأییدات کاربر فعلی با اطلاعات مرتبط
        return ApprovalLog.objects.filter(user=self.request.user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')
class ApprovalListView(PermissionBaseView, ListView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_list.html'
    context_object_name = 'approvals'
    paginate_by = 10
    extra_context = {'title': _('تاریخچه تأییدات')}

    def get_queryset(self):
        user = self.request.user
        # اگه کاربر HQ هست، همه تأییدات رو نشون بده
        if hasattr(user, 'is_hq') and user.is_hq:
            return ApprovalLog.objects.select_related(
                'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
            ).order_by('-timestamp')
        # در غیر این صورت، فقط تأییدات کاربر فعلی
        return ApprovalLog.objects.filter(user=user).select_related(
            'tankhah', 'factor_item', 'factor_item__factor', 'stage', 'post'
        ).order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # چک کردن امکان تغییر
        for approval in context['approvals']:
            approval.can_edit = (
                (hasattr(user, 'is_hq') and user.is_hq) or  # HQ همیشه می‌تونه تغییر بده
                (approval.user == user and  # کاربر خودش باشه
                 not ApprovalLog.objects.filter(
                     tankhah=approval.tankhah,
                     stage__order__gt=approval.stage.order,
                     action='APPROVE'
                 ).exists())  # هنوز بالادستی تأیید نکرده
            )
        return context
class ApprovalLogListView(PermissionBaseView, ListView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_log_list.html'
    context_object_name = 'logs'
    paginate_by = 10

    def get_queryset(self):
        # چک کن که tankhah_number توی kwargs باشه
        tankhah_number = self.kwargs.get('tankhah_number')
        if not tankhah_number:
            raise ValueError("پارامتر 'tankhah_number' در URL تعریف نشده است.")
        return ApprovalLog.objects.filter(tankhah__number=tankhah_number).order_by('-timestamp')
class ApprovalDetailView(PermissionBaseView, DetailView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_detail.html'
    context_object_name = 'approval'
    extra_context = {'title': _('جزئیات تأیید')}
    # نسخه جدید بنویس
class ApprovalCreateView(PermissionRequiredMixin, CreateView):
    model = 'tankhah.ApprovalLog'
    form_class = 'tankhah.forms.ApprovalForm'
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_add'

    def form_valid(self, form):
        form.instance.user = self.request.user
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()  # فقط پست فعال
        user_level = user_post.post.level if user_post else 0

        # ثبت لاگ و به‌روزرسانی وضعیت
        if form.instance.tankhah:  # دقت کن که Tankhah باید tankhah باشه (کوچیک)
            tankhah = form.instance.tankhah
            current_status = tankhah.status
            branch = form.instance.action

            if hasattr(tankhah, 'current_stage') and branch != tankhah.current_stage.name:  # مقایسه با نام مرحله
                messages.error(self.request, _('شما نمی‌توانید در این مرحله تأیید کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'
                    tankhah.hq_status = 'SENT_TO_HQ'
                    tankhah.current_stage = WorkflowStage.objects.get(name='OPS')
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tankhah.hq_status = 'HQ_OPS_APPROVED'
                    tankhah.current_stage = WorkflowStage.objects.get(name='FIN')
                elif branch == 'FIN' and tankhah.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tankhah.hq_status = 'HQ_FIN_PENDING'
                    tankhah.status = 'PAID'
                else:
                    messages.error(self.request, _('شما اجازه تأیید در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)
            else:
                tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
            tankhah.save()

            # ثبت لاگ برای تنخواه
            form.instance.stage = tankhah.current_stage
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor:
            factor = form.instance.factor
            tankhah = factor.tankhah  # گرفتن تنخواه مرتبط
            factor.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
            factor.save()

            # ثبت لاگ برای فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        elif form.instance.factor_item:
            item = form.instance.factor_item
            tankhah = item.factor.tankhah  # گرفتن تنخواه از ردیف فاکتور
            if hasattr(item, 'status'):
                item.status = 'APPROVED' if form.instance.action == 'APPROVE' else 'REJECTED'
                item.save()
            else:
                messages.warning(self.request, _('ردیف فاکتور فاقد وضعیت است و تأیید اعمال نشد.'))

            # ثبت لاگ برای ردیف فاکتور
            form.instance.tankhah = tankhah
            form.instance.stage = tankhah.current_stage if tankhah else None
            form.instance.post = user_post.post if user_post else None

        messages.success(self.request, _('تأیید با موفقیت ثبت شد.'))
        return super().form_valid(form)

    def can_approve_user(self, user, tankhah):
        current_stage = tankhah.current_stage
        approver_posts =   StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        user_posts = user.userpost_set.filter(end_date__isnull=True).values_list('post', flat=True)
        return bool(set(user_posts) & set(approver_posts))

    def get_initial(self):
        initial = super().get_initial()
        initial['tankhah'] = self.request.GET.get('tankhah')  # کوچیک شده
        initial['factor'] = self.request.GET.get('factor')
        initial['factor_item'] = self.request.GET.get('factor_item')
        return initial

    def dispatch(self, request, *args, **kwargs):
        # اصلاح برای گرفتن tankhah
        from tankhah.models import  Tankhah,FactorItem
        if 'tankhah' in request.GET:
            tankhah = Tankhah.objects.get(pk=request.GET['tankhah'])
        elif 'factor' in request.GET:
            tankhah = Factor.objects.get(pk=request.GET['factor']).tankhah
        elif 'factor_item' in request.GET:
            tankhah = FactorItem.objects.get(pk=request.GET['factor_item']).factor.tankhah
        else:
            raise PermissionDenied(_('تنخواه مشخص نشده است.'))

        if not self.can_approve_user(request.user, tankhah):
            raise PermissionDenied(_('شما مجاز به تأیید در این مرحله نیستید.'))
        return super().dispatch(request, *args, **kwargs)
class ApprovalUpdateView(PermissionBaseView, UpdateView):
    model = 'tankhah.ApprovalLog'
    form_class = 'tankhah.forms.ApprovalForm'
    template_name = 'tankhah/approval_form.html'
    success_url = reverse_lazy('approval_list')
    permission_codenames = ['tankhah.Approval_update']

    def get_queryset(self):
        return ApprovalLog.objects.filter(user=self.request.user)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        tankhah = self.object.tankhah
        current_stage = tankhah.current_stage
        user_posts = UserPost.objects.filter(user=request.user, end_date__isnull=True).values_list('post', flat=True)
        approver_posts =  StageApprover.objects.filter(stage=current_stage).values_list('post', flat=True)
        can_edit = bool(set(user_posts) & set(approver_posts))

        if not can_edit:
            raise PermissionDenied(_('شما نمی‌توانید این تأیید را ویرایش کنید، چون مرحله تغییر کرده یا دسترسی ندارید.'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        approval = form.instance
        tankhah = approval.tankhah
        user_post = UserPost.objects.filter(user=self.request.user, end_date__isnull=True).first()
        user_level = user_post.post.level if user_post else 0

        # به‌روزرسانی وضعیت و انتقال مرحله
        if tankhah:
            current_status = tankhah.status
            branch = form.instance.action

            if tankhah.current_stage != approval.stage:
                messages.error(self.request, _('مرحله تغییر کرده و نمی‌توانید این تأیید را ویرایش کنید.'))
                return self.form_invalid(form)

            if form.instance.action == 'APPROVE':
                if branch == 'COMPLEX' and current_status == 'PENDING' and user_level <= 2:
                    tankhah.status = 'APPROVED'
                    tankhah.hq_status = 'SENT_TO_HQ'
                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'OPS' and current_status == 'APPROVED' and user_level > 2:
                    tankhah.hq_status = 'HQ_OPS_APPROVED'
                    next_stage = WorkflowStage.objects.filter(order__gt=tankhah.current_stage.order).order_by(
                        'order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                elif branch == 'FIN' and tankhah.hq_status == 'HQ_OPS_APPROVED' and user_level > 3:
                    tankhah.hq_status = 'HQ_FIN_PENDING'
                    tankhah.status = 'PAID'
                    next_stage = None  # مرحله آخر
                else:
                    messages.error(self.request, _('شما اجازه ویرایش در این مرحله را ندارید یا وضعیت نادرست است.'))
                    return self.form_invalid(form)

                # انتقال به مرحله بعدی و اعلان
                if next_stage:
                    tankhah.save()
                    approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage,
                                                          userpost__end_date__isnull=True)
                    if approvers.exists():
                        notify.send(self.request.user, recipient=approvers, verb='تنخواه در انتظار تأیید',
                                    target=tankhah)
                    messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                else:
                    tankhah.is_locked = True
                    tankhah.is_archived = True
                    tankhah.save()
                    messages.success(self.request, _('تنخواه تکمیل و آرشیو شد.'))

            elif form.instance.action == 'REJECT':
                tankhah.status = 'REJECTED'
                tankhah.last_stopped_post = user_post.post if user_post else None
                tankhah.save()
                messages.warning(self.request, _('تنخواه رد شد.'))

        messages.success(self.request, _('تأیید با موفقیت به‌روزرسانی شد.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('خطا در ویرایش تأیید. لطفاً ورودی‌ها را بررسی کنید.'))
        return super().form_invalid(form)
class ApprovalDeleteView(PermissionBaseView, DeleteView):
    model = 'tankhah.ApprovalLog'
    template_name = 'tankhah/approval_confirm_delete.html'
    success_url = reverse_lazy('approval_list')
    permission_required = 'Tankhah.Approval_delete'

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _('تأیید با موفقیت حذف شد.'))
        return super().delete(request, *args, **kwargs)
#---------------------
@permission_required('tankhah.ItemCategory_view')
def itemcategory_list(request):
    categories = ItemCategory.objects.all()
    return render(request, 'tankhah/itemcategory/list.html', {'categories': categories})

@permission_required('tankhah.ItemCategory_add')
def itemcategory_create(request):
    form = ItemCategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/form.html', {'form': form})

@permission_required('tankhah.ItemCategory_update')
def itemcategory_update(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    form = ItemCategoryForm(request.POST or None, instance=category)
    if form.is_valid():
        form.save()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/form.html', {'form': form})

@permission_required('tankhah.ItemCategory_delete')
def itemcategory_delete(request, pk):
    category = get_object_or_404(ItemCategory, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('itemcategory_list')
    return render(request, 'tankhah/itemcategory/confirm_delete.html', {'category': category})
# --- لیست دسته‌بندی‌ها ---
class ItemCategoryListView(PermissionRequiredMixin, ListView):
    model = ItemCategory
    template_name = 'tankhah/itemcategory/list.html'
    context_object_name = 'categories' # نامی که در template استفاده می‌شود
    permission_required = 'tankhah.view_itemcategory' # مجوز مورد نیاز برای نمایش لیست

    # اگر نیاز به فیلتر یا مرتب سازی خاصی دارید:
    # def get_queryset(self):
    #     return ItemCategory.objects.filter(some_field=True)
# --- ایجاد دسته‌بندی جدید ---
class ItemCategoryCreateView(PermissionRequiredMixin, CreateView):
    model = ItemCategory
    form_class = ItemCategoryForm # استفاده از فرم سفارشی
    template_name = 'tankhah/itemcategory/form.html'
    success_url = reverse_lazy('itemcategory_list') # به کجا بعد از موفقیت ریدایرکت شود
    permission_required = 'tankhah.add_itemcategory' # مجوز مورد نیاز برای ایجاد
# --- به‌روزرسانی دسته‌بندی ---
class ItemCategoryUpdateView(PermissionRequiredMixin, UpdateView):
    model = ItemCategory
    form_class = ItemCategoryForm
    template_name = 'tankhah/itemcategory/form.html'
    context_object_name = 'category' # نامی که در template برای آبجکت استفاده می‌شود (به جای object)
    success_url = reverse_lazy('itemcategory_list')
    permission_required = 'tankhah.change_itemcategory' # مجوز مورد نیاز برای ویرایش
# --- حذف دسته‌بندی ---
class ItemCategoryDeleteView(PermissionRequiredMixin, DeleteView):
    model = ItemCategory
    template_name = 'tankhah/itemcategory/confirm_delete.html'
    context_object_name = 'category' # نامی که در template برای آبجکت استفاده می‌شود
    success_url = reverse_lazy('itemcategory_list')
    permission_required = 'tankhah.delete_itemcategory' # مجوز مورد نیاز برای حذف

    # برای نمایش نام دسته‌بندی در صفحه حذف (اگرچه context_object_name هم این کار را می‌کند)
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context['category_name'] = self.object.name # اگر بخواهید نام خاصی را پاس دهید
    #     return context
# -- وضعیت تنخواه
@login_required
def upload_tankhah_documents(request, tankhah_id):
    from tankhah.models import   Tankhah
    tankhah = Tankhah.objects.get(id=tankhah_id)
    if request.method == 'POST':
        from tankhah.forms import TankhahDocumentForm
        form = TankhahDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('documents')
            for file in files:
               TankhahDocument.objects.create(Tankhah='tankhah.Tankhah', document=file)
            messages.success(request, 'اسناد با موفقیت آپلود شدند.')
            return redirect('Tankhah_detail', pk='tankhah.Tankhah'.id)
        else:
            messages.error(request, 'خطایی در آپلود اسناد رخ داد.')
    else:
        from tankhah.forms import  TankhahDocumentForm
        form = TankhahDocumentForm()

    return render(request, 'tankhah/upload_documents.html', {
        'form': form,
        'Tankhah': 'tankhah.Tankhah',
        'existing_documents':  Tankhah.documents.all()
    })
class FactorStatusUpdateView(PermissionBaseView, View):
    permission_required = 'tankhah.FactorItem_approve'
    def post(self, request, pk, *args, **kwargs):
        factor = Factor.objects.get(pk=pk)
        tankhah = factor.tankhah
        action = request.POST.get('action')

        if tankhah.is_locked or tankhah.is_archived:
            messages.error(request, _('این تنخواه قفل یا آرشیو شده و قابل تغییر نیست.'))
            return redirect('tankhah_tracking', pk=tankhah.pk)

        user_post = request.user.userpost_set.filter(end_date__isnull=True).first()
        if action == 'REJECT' and factor.status == 'APPROVED':
            factor.status = 'REJECTED'
            tankhah.status = 'REJECTED'
            tankhah.last_stopped_post = user_post.post if user_post else None
        elif action == 'APPROVE' and factor.status == 'REJECTED':
            factor.status = 'APPROVED'
            tankhah.status = 'PENDING' if any(f.status != 'APPROVED' for f in tankhah.factors.all()) else 'APPROVED'

        factor.save()
        tankhah.save()

        # ثبت لاگ
        ApprovalLog.objects.create(
            tankhah=tankhah,
            factor=factor,
            user=request.user,
            action=action,
            stage=tankhah.current_stage,
            post=user_post.post if user_post else None
        )

        # آپدیت مرحله
        workflow_stages = WorkflowStage.objects.order_by('order')
        current_stage = tankhah.current_stage
        if not current_stage:
            tankhah.current_stage = workflow_stages.first()
            tankhah.save()

        # چک کردن تأیید همه فاکتورها توی مرحله فعلی
        approvals_in_current = ApprovalLog.objects.filter(
            tankhah=tankhah, stage=current_stage, action='APPROVE'
        ).count()
        factors_count = tankhah.factors.count()
        if approvals_in_current >= factors_count and action == 'APPROVE':
            # next_stage = workflow_stages.filter(order__gt=current_stage.order).first()
            next_stage = workflow_stages.filter(order__lt=current_stage.order).order_by('-order').first()

            if next_stage:
                tankhah.current_stage = next_stage
                tankhah.status = 'PENDING'
                tankhah.save()
                messages.info(request, _(f"تنخواه به مرحله {next_stage.name} منتقل شد."))
            elif all(f.status == 'APPROVED' for f in tankhah.factors.all()):
                tankhah.status = 'APPROVED'
                tankhah.save()
                messages.info(request, _('تنخواه کاملاً تأیید شد.'))

        messages.success(request, _('وضعیت فاکتور با موفقیت تغییر کرد.'))
        return redirect('tankhah_tracking', pk=tankhah.pk)

@require_POST
def mark_notification_as_read(request, notif_id):
    from notifications.models import Notification
    notif = Notification.get(id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'status': 'success'})

@login_required
def get_unread_notifications(request):
    # دریافت اعلان‌های خوانده نشده کاربر
    from notifications.views import Notification
    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:10]  # 10 اعلان آخر خوانده نشده

    # سریالایز کردن داده‌ها
    serialized_notifications = []
    for notification in unread_notifications:
        serialized_notifications.append({
            'id': notification.id,
            'message': notification.message,
            'tankhah_id': notification.tankhah.id if notification.tankhah else None,
            'tankhah_number': notification.tankhah.number if notification.tankhah else None,
            'created_at': notification.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_read': notification.is_read
        })

    # ساخت پاسخ JSON
    response_data = {
        'status': 'success',
        'count': unread_notifications.count(),
        'notifications': serialized_notifications,
        'unread_count': request.user.notifications.filter(is_read=False).count()
    }

    return JsonResponse(response_data)
