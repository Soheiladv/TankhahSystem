from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.views.generic.edit import UpdateView
from django.core.exceptions import ValidationError
from notifications.signals import notify

from accounts.models import CustomUser
from core.PermissionBase import PermissionBaseView
from notificationApp.models import NotificationRule
from tankhah.models import Factor
import logging
logger = logging.getLogger('FactorReRegisterView')


class FactorReRegisterView(PermissionBaseView, UpdateView):
    model = Factor
    fields = ['re_registered_in']
    template_name = 'tankhah/Factors/factor_reregister.html'
    permission_required = 'factor.add_factor'

    def form_valid(self, form):
        factor = form.save(commit=False)
        try:
            if factor.status != 'REJECTED':
                messages.error(self.request, _("فقط فاکتورهای ردشده قابل ثبت مجدد هستند."))
                return self.form_invalid(form)
            if not factor.re_registered_in:
                messages.error(self.request, _("تنخواه جدید باید انتخاب شود."))
                return self.form_invalid(form)
            if factor.re_registered_in.start_date > timezone.now().date() or (
                factor.re_registered_in.end_date and factor.re_registered_in.end_date < timezone.now().date()
            ):
                messages.error(self.request, _("تنخواه جدید در بازه زمانی مجاز نیست."))
                return self.form_invalid(form)

            factor.status = 'PENDING'
            factor.rejected_reason = None
            factor.save()

            self.send_notifications(
                entity=factor,
                action='CREATED',
                priority='MEDIUM',
                description=f"فاکتور {factor.number} در تنخواه جدید {factor.re_registered_in.number} ثبت شد."
            )
            messages.success(self.request, f"فاکتور {factor.number} در تنخواه جدید ثبت شد.")
            return super().form_valid(form)

        except Exception as e:
            logger.error(f"Error in FactorReRegisterView: {e}", exc_info=True)
            messages.error(self.request, "خطایی در ثبت مجدد فاکتور رخ داد.")
            return self.form_invalid(form)

    def send_notifications(self, entity, action, priority, description):
        rules = NotificationRule.objects.filter(
            entity_type=entity.__class__.__name__.upper(),
            action=action,
            is_active=True
        )
        for rule in rules:
            for post in rule.recipients.all():
                users = CustomUser.objects.filter(userpost__post=post, userpost__is_active=True)
                for user in users:
                    notify.send(
                        sender=self.request.user,
                        recipient=user,
                        verb=action.lower(),
                        action_object=entity,
                        description=description,
                        level=rule.priority
                    )
                    if rule.channel == 'EMAIL':
                        from django.core.mail import send_mail
                        send_mail(
                            subject=description,
                            message=description,
                            from_email='system@example.com',
                            recipient_list=[user.email],
                            fail_silently=True
                        )