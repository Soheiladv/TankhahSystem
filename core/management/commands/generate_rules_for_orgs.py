from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.models import Organization, EntityType, Status, Action, Transition, Post, PostRuleAssignment
from accounts.models import CustomUser


class Command(BaseCommand):
    help = "ایجاد کامل قوانین، اقدامات و ترنزیشن‌ها برای دو سازمان: دفتر مرکزی و هتل لاله سرعین، برای فاکتور/بودجه/دستور پرداخت"

    def add_arguments(self, parser):
        parser.add_argument('--branch-name', default='هتل لاله سرعین', help='نام سازمان شعبه هدف')
        parser.add_argument('--creator-username', default='admin', help='کاربر ایجادکننده رکوردهای سیستمی')

    def handle(self, *args, **options):
        branch_name = options['branch-name']
        creator_username = options['creator_username']

        try:
            creator = CustomUser.objects.filter(username=creator_username).first() or CustomUser.objects.first()
            if not creator:
                raise CommandError('هیچ کاربری برای ثبت به عنوان ایجادکننده پیدا نشد.')

            hq = Organization.objects.filter(is_core=True, is_active=True).first()
            if not hq:
                raise CommandError('سازمان دفتر مرکزی (is_core=True) یافت نشد.')

            branch = Organization.objects.filter(name=branch_name, is_active=True).first()
            if not branch:
                raise CommandError(f"سازمان شعبه '{branch_name}' یافت نشد.")

            with transaction.atomic():
                self.stdout.write(self.style.MIGRATE_HEADING('1) ایجاد EntityType ها'))
                et_codes = ['FACTOR', 'BUDGET', 'PAYMENTORDER']
                entity_types = {}
                for code in et_codes:
                    entity_types[code], _ = EntityType.objects.get_or_create(
                        code=code,
                        defaults={'name': code, 'created_at': None}
                    )

                self.stdout.write(self.style.MIGRATE_HEADING('2) ایجاد Actions استاندارد'))
                action_codes = {
                    'SUBMIT': _('ارسال برای تایید'),
                    'APPROVE': _('تایید'),
                    'REJECT': _('رد'),
                    'FINAL_APPROVE': _('تایید نهایی'),
                }
                actions = {}
                for code, name in action_codes.items():
                    actions[code], _ = Action.objects.get_or_create(
                        code=code,
                        defaults={'name': name, 'created_by': creator}
                    )

                self.stdout.write(self.style.MIGRATE_HEADING('3) اطمینان از وجود Status ها'))
                status_codes = {
                    'DRAFT': _('پیش‌نویس'),
                    'PENDING_APPROVAL': _('در انتظار تأیید'),
                    'APPROVED_INTERMEDIATE': _('تأیید میانی'),
                    'APPROVED_FINAL': _('تأیید نهایی'),
                    'REJECT': _('رد شده'),
                }
                statuses = {}
                for code, name in status_codes.items():
                    statuses[code], _ = Status.objects.get_or_create(
                        code=code,
                        defaults={'name': name, 'created_by': creator}
                    )

                self.stdout.write(self.style.MIGRATE_HEADING('4) تعریف ترنزیشن‌های شعبه و دفتر مرکزی'))
                # شعبه: DRAFT -> SUBMIT -> PENDING_APPROVAL
                # شعبه: PENDING_APPROVAL -> SUBMIT -> APPROVED_INTERMEDIATE (ارسال به مرکز)
                # مرکز: APPROVED_INTERMEDIATE -> APPROVE -> APPROVED_FINAL
                # مرکز: APPROVED_INTERMEDIATE -> REJECT -> REJECT
                # همچنین امکان REJECT در شعبه از PENDING_APPROVAL -> REJECT

                def ensure_transition(org, et_code, from_code, action_code, to_code):
                    name = f"{org.code} {et_code}: {from_code} --{action_code}--> {to_code}"
                    Transition.objects.update_or_create(
                        organization=org,
                        entity_type=entity_types[et_code],
                        from_status=statuses[from_code],
                        action=actions[action_code],
                        defaults={
                            'name': name,
                            'to_status': statuses[to_code],
                            'created_by': creator,
                            'is_active': True,
                        }
                    )

                for et in et_codes:
                    # Branch transitions
                    ensure_transition(branch, et, 'DRAFT', 'SUBMIT', 'PENDING_APPROVAL')
                    ensure_transition(branch, et, 'PENDING_APPROVAL', 'SUBMIT', 'APPROVED_INTERMEDIATE')
                    ensure_transition(branch, et, 'PENDING_APPROVAL', 'REJECT', 'REJECT')

                    # HQ transitions
                    ensure_transition(hq, et, 'APPROVED_INTERMEDIATE', 'APPROVE', 'APPROVED_FINAL')
                    ensure_transition(hq, et, 'APPROVED_INTERMEDIATE', 'REJECT', 'REJECT')

                self.stdout.write(self.style.MIGRATE_HEADING('5) تخصیص اقدامات به پست‌ها (PostRuleAssignment)'))
                def assign_all_posts(org, et_code, action_code):
                    for post in Post.objects.filter(organization=org, is_active=True):
                        PostRuleAssignment.objects.update_or_create(
                            post=post,
                            action=actions[action_code],
                            organization=org,
                            entity_type=et_code,
                            defaults={'created_by': creator, 'is_active': True}
                        )

                for et in et_codes:
                    # شعبه
                    assign_all_posts(branch, et, 'SUBMIT')
                    assign_all_posts(branch, et, 'REJECT')
                    # مرکز
                    assign_all_posts(hq, et, 'APPROVE')
                    assign_all_posts(hq, et, 'REJECT')
                    assign_all_posts(hq, et, 'FINAL_APPROVE')

            self.stdout.write(self.style.SUCCESS('قوانین، وضعیت‌ها، اقدامات و ترنزیشن‌ها با موفقیت ایجاد/به‌روزرسانی شد.'))

        except Exception as e:
            raise CommandError(str(e))


