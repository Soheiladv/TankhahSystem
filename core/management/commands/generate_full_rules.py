"""
ایجاد کامل قوانین گردش کار برای شعبه و دفتر مرکزی، شامل:
- وضعیت‌ها و اقدامات پایه (در صورت نبود)
- گذارهای شعبه: DRAFT -> SUBMIT -> PENDING_APPROVAL
- گذارهای شعبه: PENDING_APPROVAL -> SUBMIT (ارسال به مرکز) -> APPROVED_INTERMEDIATE
- گذارهای شعبه: PENDING_APPROVAL -> REJECT -> REJECTED
- گذارهای دفتر مرکزی: APPROVED_INTERMEDIATE -> APPROVE (تأییدهای میانی، ماندن در همان وضعیت)
- گذارهای دفتر مرکزی: APPROVED_INTERMEDIATE -> FINAL_APPROVE (تأیید نهایی) -> APPROVED
- گذارهای دفتر مرکزی: APPROVED_INTERMEDIATE -> REJECT -> REJECTED

همچنین، تخصیص allowed_posts برای هر گذار بر اساس پست‌های سازمان و پرچم‌های can_final_approve_*.

پوشش موجودیت‌ها: FACTOR, BUDGET, PAYMENTORDER
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.models import (
    Organization,
    Status,
    Action,
    EntityType,
    Transition,
    Post,
)
from core.services.workflow import wf

User = get_user_model()


REQUIRED_STATUSES = [
    dict(code='DRAFT', name=_('پیش‌نویس'), is_initial=True),
    dict(code='PENDING_APPROVAL', name=_('در انتظار تأیید')),
    dict(code='APPROVED_INTERMEDIATE', name=_('تأیید میانی')),
    dict(code='APPROVED', name=_('تأیید شده'), is_final_approve=True),
    dict(code='REJECTED', name=_('رد شده'), is_final_reject=True),
]

REQUIRED_ACTIONS = [
    dict(code='SUBMIT', name=_('ارسال')),
    dict(code='APPROVE', name=_('تأیید')),
    dict(code='FINAL_APPROVE', name=_('تأیید نهایی')),
    dict(code='REJECT', name=_('رد')),
]

ENTITY_CODES = ['FACTOR', 'BUDGET', 'PAYMENTORDER']


class Command(BaseCommand):
    help = 'ایجاد کامل قوانین گردش کار برای شعبه و دفتر مرکزی (FACTOR, BUDGET, PAYMENTORDER)'

    def add_arguments(self, parser):
        parser.add_argument('--branch-code', required=True, help='کد سازمان شعبه (مثلاً SARAIN)')
        parser.add_argument('--hq-code', required=True, help='کد سازمان دفتر مرکزی')
        parser.add_argument('--dry-run', action='store_true', help='فقط گزارش بده، تغییری ایجاد نکن')

    def handle(self, *args, **options):
        branch_code = options['branch_code']
        hq_code = options['hq_code']
        dry_run = options['dry_run']

        try:
            branch = Organization.objects.get(code=branch_code)
            hq = Organization.objects.get(code=hq_code)
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR('سازمان‌های ورودی یافت نشدند.'))
            return

        creator = User.objects.filter(is_superuser=True).first()
        if not creator:
            self.stderr.write(self.style.ERROR('هیچ کاربر سوپریوزری برای ثبت ایجادکننده یافت نشد.'))
            return

        with transaction.atomic():
            # Ensure statuses, actions, and entity types via service (DB-driven)
            status_objs = wf.ensure_statuses(REQUIRED_STATUSES, creator)
            action_objs = wf.ensure_actions(REQUIRED_ACTIONS, creator)
            entity_types = wf.ensure_entity_types(ENTITY_CODES)

            def ensure_transition(org, et_code, from_code, action_code, to_code):
                name = f"{org.code} {et_code}: {from_code} --{action_code}--> {to_code}"
                tr, created = Transition.objects.get_or_create(
                    organization=org,
                    entity_type=entity_types[et_code],
                    from_status=status_objs[from_code],
                    action=action_objs[action_code],
                    defaults={
                        'name': name,
                        'to_status': status_objs[to_code],
                        'created_by': creator,
                        'is_active': True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"ایجاد گذار: {name}"))
                else:
                    self.stdout.write(f"گذار موجود بود: {name}")
                return tr

            # Create transitions for each entity
            for et in ENTITY_CODES:
                # Branch transitions
                t1 = ensure_transition(branch, et, 'DRAFT', 'SUBMIT', 'PENDING_APPROVAL')
                t2 = ensure_transition(branch, et, 'PENDING_APPROVAL', 'SUBMIT', 'APPROVED_INTERMEDIATE')
                t3 = ensure_transition(branch, et, 'PENDING_APPROVAL', 'REJECT', 'REJECTED')

                # Assign allowed posts for branch transitions: all active posts in branch
                if not dry_run:
                    branch_posts = list(Post.objects.filter(organization=branch, is_active=True).values_list('id', flat=True))
                    t1.allowed_posts.set(branch_posts)
                    t2.allowed_posts.set(branch_posts)
                    t3.allowed_posts.set(branch_posts)

                # HQ transitions
                # Intermediate approvals: APPROVE stays in APPROVED_INTERMEDIATE for non-final approvers
                tr_intermediate_approve = ensure_transition(hq, et, 'APPROVED_INTERMEDIATE', 'APPROVE', 'APPROVED_INTERMEDIATE')
                # Final approvers move to APPROVED (final)
                tr_final_approve = ensure_transition(hq, et, 'APPROVED_INTERMEDIATE', 'FINAL_APPROVE', 'APPROVED')
                tr_reject = ensure_transition(hq, et, 'APPROVED_INTERMEDIATE', 'REJECT', 'REJECTED')

                if not dry_run:
                    hq_posts = Post.objects.filter(organization=hq, is_active=True)
                    if et == 'FACTOR':
                        non_final = hq_posts.filter(can_final_approve_factor=False).values_list('id', flat=True)
                        finals = hq_posts.filter(can_final_approve_factor=True).values_list('id', flat=True)
                    elif et == 'BUDGET':
                        non_final = hq_posts.filter(can_final_approve_budget=False).values_list('id', flat=True)
                        finals = hq_posts.filter(can_final_approve_budget=True).values_list('id', flat=True)
                    else:  # PAYMENTORDER (reuse factor final flag for PO if specific flag not present)
                        non_final = hq_posts.filter(can_final_approve_factor=False).values_list('id', flat=True)
                        finals = hq_posts.filter(can_final_approve_factor=True).values_list('id', flat=True)

                    tr_intermediate_approve.allowed_posts.set(list(non_final))
                    tr_final_approve.allowed_posts.set(list(finals))
                    tr_reject.allowed_posts.set(list(hq_posts.values_list('id', flat=True)))

        self.stdout.write(self.style.SUCCESS('قوانین گردش کار شعبه و دفتر مرکزی با موفقیت اعمال شد.'))


