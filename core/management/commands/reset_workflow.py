from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as trans

from core.models import (
    Organization,
    EntityType,
    Status,
    Action,
    Transition,
    Post,
)
from django.contrib.auth import get_user_model


User = get_user_model()


class Command(BaseCommand):
    help = 'حذف کامل قوانین گردش کار و بازنویسی قوانین استاندارد برای دفتر مرکزی و شعب (EntityType/Status/Action/Transition)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='تایید حذف کامل قوانین')
        parser.add_argument('--dry-run', action='store_true', help='فقط گزارش، بدون اعمال تغییر')

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']

        if not force and not dry_run:
            raise CommandError("برای اجرا باید --force بدهید یا از --dry-run استفاده کنید.")

        # قوانین پایه جهت بازنویسی
        REQUIRED_STATUSES = [
            dict(code='DRAFT', name=trans('پیش‌نویس'), is_initial=True),
            dict(code='PENDING_APPROVAL', name=trans('در انتظار تأیید')),
            dict(code='APPROVED_INTERMEDIATE', name=trans('تأیید میانی')),
            dict(code='APPROVED', name=trans('تأیید شده')),
            dict(code='REJECTED', name=trans('رد شده')),
        ]
        REQUIRED_ACTIONS = [
            dict(code='SUBMIT', name=trans('ارسال')),
            dict(code='APPROVE', name=trans('تأیید')),
            dict(code='FINAL_APPROVE', name=trans('تأیید نهایی')),
            dict(code='REJECT', name=trans('رد')),
        ]
        ENTITY_CODES = ['FACTOR', 'BUDGET', 'PAYMENTORDER']

        creator = User.objects.filter(is_superuser=True).first()
        if not creator:
            raise CommandError('هیچ کاربر سوپریوزری برای ثبت ایجادکننده یافت نشد.')

        with transaction.atomic():
            # حذف مرتب بر اساس وابستگی‌ها
            self.stdout.write(self.style.WARNING('حذف همه Transition ها...'))
            if not dry_run:
                Transition.objects.all().delete()
            # به‌جای حذف Status/Action/EntityType (به علت ارجاعات محافظت‌شده)، فقط از نو می‌سازیم/به‌روزرسانی می‌کنیم
            self.stdout.write(self.style.NOTICE('Status/Action/EntityType حذف نمی‌شوند (برای جلوگیری از ProtectedError).'))

            if dry_run:
                self.stdout.write(self.style.NOTICE('dry-run: فقط گزارش حذف Transitions انجام شد.'))
                return

            # بازنویسی مقادیر پایه
            self.stdout.write(self.style.MIGRATE_HEADING('ایجاد EntityType ها'))
            entity_types = {}
            for code in ENTITY_CODES:
                et, created_flag = EntityType.objects.get_or_create(code=code, defaults=dict(name=code))
                entity_types[code] = et

            self.stdout.write(self.style.MIGRATE_HEADING('ایجاد Status ها'))
            status_objs = {}
            for sd in REQUIRED_STATUSES:
                obj, created_flag = Status.objects.get_or_create(
                    code=sd['code'],
                    defaults=dict(
                        name=sd['name'],
                        is_initial=sd.get('is_initial', False),
                        is_active=True,
                        created_by=creator,
                    ),
                )
                status_objs[obj.code] = obj

            self.stdout.write(self.style.MIGRATE_HEADING('ایجاد Action ها'))
            action_objs = {}
            for ad in REQUIRED_ACTIONS:
                obj, created_flag = Action.objects.get_or_create(
                    code=ad['code'],
                    defaults=dict(name=ad['name'], is_active=True, created_by=creator),
                )
                action_objs[obj.code] = obj

            # توابع کمکی برای ایجاد Transition
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
                return tr

            # بازنویسی قوانین بر اساس دفتر مرکزی و شعب
            self.stdout.write(self.style.MIGRATE_HEADING('ایجاد قوانین شعب و دفتر مرکزی'))
            for org in Organization.objects.filter(is_active=True):
                # برای هر EntityType
                for et in ENTITY_CODES:
                    if org.is_core:
                        # مرکز: APPROVED_INTERMEDIATE -> APPROVE (self)
                        tr_intermediate = ensure_transition(org, et, 'APPROVED_INTERMEDIATE', 'APPROVE', 'APPROVED_INTERMEDIATE')
                        tr_final = ensure_transition(org, et, 'APPROVED_INTERMEDIATE', 'FINAL_APPROVE', 'APPROVED')
                        tr_reject = ensure_transition(org, et, 'APPROVED_INTERMEDIATE', 'REJECT', 'REJECTED')
                        # تخصیص پست‌ها: نهایی/غیرنهایی بر اساس پرچم‌های پست
                        hq_posts = Post.objects.filter(organization=org, is_active=True)
                        if et == 'FACTOR':
                            non_final = hq_posts.filter(can_final_approve_factor=False).values_list('id', flat=True)
                            finals = hq_posts.filter(can_final_approve_factor=True).values_list('id', flat=True)
                        elif et == 'BUDGET':
                            non_final = hq_posts.filter(can_final_approve_budget=False).values_list('id', flat=True)
                            finals = hq_posts.filter(can_final_approve_budget=True).values_list('id', flat=True)
                        else:  # PAYMENTORDER: استفاده از پرچم فاکتور به عنوان پیش‌فرض
                            non_final = hq_posts.filter(can_final_approve_factor=False).values_list('id', flat=True)
                            finals = hq_posts.filter(can_final_approve_factor=True).values_list('id', flat=True)
                        tr_intermediate.allowed_posts.set(list(non_final))
                        tr_final.allowed_posts.set(list(finals))
                        tr_reject.allowed_posts.set(list(hq_posts.values_list('id', flat=True)))
                    else:
                        # شعبه: DRAFT -> SUBMIT -> PENDING_APPROVAL
                        t1 = ensure_transition(org, et, 'DRAFT', 'SUBMIT', 'PENDING_APPROVAL')
                        t2 = ensure_transition(org, et, 'PENDING_APPROVAL', 'SUBMIT', 'APPROVED_INTERMEDIATE')
                        t3 = ensure_transition(org, et, 'PENDING_APPROVAL', 'REJECT', 'REJECTED')
                        # تخصیص پست‌های شعبه: همه پست‌های فعال شعبه
                        branch_posts = list(Post.objects.filter(organization=org, is_active=True).values_list('id', flat=True))
                        t1.allowed_posts.set(branch_posts)
                        t2.allowed_posts.set(branch_posts)
                        t3.allowed_posts.set(branch_posts)

        self.stdout.write(self.style.SUCCESS('ریست کامل قوانین و بازنویسی قوانین استاندارد با موفقیت انجام شد.'))


