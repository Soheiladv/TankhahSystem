from django.db import transaction
from django.contrib import messages
from django.urls.base import reverse_lazy
from accounts.models import CustomUser
from core.PermissionBase import PermissionBaseView
from notificationApp.utils import send_notification
from tankhah.Factor.Approved.from_Approved import FactorApprovalForm
from django.views.generic import ListView, UpdateView
from django.db.models import Q
from tankhah.models import Factor
from core.models import UserPost, Transition


class FactorApproveView(PermissionBaseView, UpdateView):
    model = Factor
    form_class = FactorApprovalForm
    template_name = 'tankhah/factor_approval.html'
    success_url = reverse_lazy('factor_list')
    permission_codenames = ['tankhah.factor_view', 'tankhah.factor_update']

    def form_valid(self, form):
        factor = self.object
        tankhah = factor.tankhah
        user_posts = self.request.user.userpost_set.all()

        if not any(p.post.stageapprover_set.filter(stage=tankhah.current_stage).exists() for p in user_posts):
            messages.error(self.request, 'شما مجاز به تأیید در این مرحله نیستید.')
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            all_items_approved = all(item.status == 'APPROVED' for item in self.object.items.all())

            if all_items_approved:
                factor.status = 'APPROVED'
                factor.approved_by.add(self.request.user)
                factor.locked_by_stage = tankhah.current_stage
                factor.save()

                # ---- اعلان به کاربران مرتبط با فاکتور ----
                related_users = factor.related_users.all()  # فرض: M2M یا متد مشابه
                if related_users.exists():
                    send_notification(
                        sender=self.request.user,
                        users=related_users,
                        verb='FACTOR_APPROVED',
                        description=f"فاکتور {factor.number} تأیید شد.",
                        target=factor,
                        entity_type='FACTOR',
                        priority='HIGH'
                    )

                # ---- بررسی آماده بودن برای صدور دستور پرداخت ----
                all_factors_approved = all(f.status == 'APPROVED' for f in tankhah.factors.all())
                if all_factors_approved:
                    # مرحله بعدی یا شروع دستور پرداخت
                    next_stage = Transition.objects.filter(order__lt=tankhah.current_stage.order).order_by('-order').first()
                    if next_stage:
                        tankhah.current_stage = next_stage
                        tankhah.status = 'PENDING'
                        tankhah.save()

                        # کاربران پست‌های مرحله بعدی
                        approvers = CustomUser.objects.filter(userpost__post__stageapprover__stage=next_stage)
                        if approvers.exists():
                            send_notification(
                                sender=self.request.user,
                                users=approvers,
                                verb='TANKHAH_READY',
                                description=f"تنخواه {tankhah.number} آماده صدور دستور پرداخت است.",
                                target=tankhah,
                                entity_type='TANKHAH',
                                priority='HIGH'
                            )
                        messages.info(self.request, f"تنخواه به مرحله {next_stage.name} منتقل شد.")
                    else:
                        tankhah.status = 'COMPLETED'
                        tankhah.save()
                        messages.success(self.request, 'تنخواه تکمیل شد.')
                else:
                    messages.success(self.request, 'فاکتور تأیید شد اما فاکتورهای دیگر در انتظارند.')
            else:
                messages.warning(self.request, 'برخی ردیف‌ها هنوز تأیید نشده‌اند.')

        return super().form_valid(form)




class ApprovedFactorsForPaymentView(PermissionBaseView, ListView):
    model = Factor
    template_name = 'tankhah/factors/approved_for_payment.html'
    context_object_name = 'factors'
    paginate_by = 10
    permission_codename = 'tankhah.factor_view'

    def get_queryset(self):
        user = self.request.user
        queryset = Factor.objects.filter(
            status='APPROVED',  # فقط فاکتورهای تاییدشده
            tankhah__factors__status='APPROVED'  # مرتبط با تنخواه‌هایی که آماده هستند
        ).select_related('tankhah', 'tankhah__organization', 'tankhah__project')

        # فیلتر سازمانی برای کاربران غیرسوپر
        if not user.is_superuser:
            user_orgs = UserPost.objects.filter(user=user, is_active=True).values_list('post__organization', flat=True)
            queryset = queryset.filter(tankhah__organization__in=user_orgs)

        # جستجو بر اساس شماره یا توضیحات
        query = self.request.GET.get('query', '')
        if query:
            queryset = queryset.filter(
                Q(number__icontains=query) |
                Q(description__icontains=query)
            )
        return queryset.distinct().order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query', '')
        return context

