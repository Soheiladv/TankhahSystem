from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Organization, EntityType, Status, Action, Transition, Post
from tankhah.models import Factor, Tankhah


class Command(BaseCommand):
    help = "ایجاد یک فاکتور تست و عبور دادن آن از روند تا تایید نهایی."

    def add_arguments(self, parser):
        parser.add_argument('--org', default='SARAIN', help='کد سازمان/شعبه شروع (پیش‌فرض: SARAIN)')
        parser.add_argument('--number', default='FAC-TEST-SARAIN-001', help='شماره فاکتور تست')
        parser.add_argument('--amount', default='100000', help='مبلغ فاکتور')

    def handle(self, *args, **options):
        org_code = options['org']
        number = options['number']
        amount = options['amount']

        try:
            org = Organization.objects.get(code=org_code)
        except Organization.DoesNotExist:
            raise CommandError(f"سازمان {org_code} یافت نشد.")

        try:
            et = EntityType.objects.get(code='FACTOR')
        except EntityType.DoesNotExist:
            raise CommandError("EntityType=FACTOR موجود نیست. ابتدا reset_workflow را اجرا کنید.")

        def print_rules(o):
            qs = Transition.objects.filter(organization=o, entity_type=et, is_active=True).select_related('from_status','to_status','action')
            self.stdout.write(self.style.MIGRATE_HEADING(f"قوانین فعال برای {o.code}:"))
            for t in qs:
                posts = list(t.allowed_posts.values_list('name', flat=True))
                self.stdout.write(f" - {t.from_status.code} --{t.action.code}--> {t.to_status.code} | posts={posts}")

        # نمایش قوانین برای شعبه و دفتر مرکزی
        print_rules(org)
        hq = Organization.objects.filter(is_core=True).first()
        if hq:
            print_rules(hq)

        draft = Status.objects.get(code='DRAFT')

        try:
            with transaction.atomic():
                # Factor در این پروژه به احتمال زیاد به Tankhah وصل است، نه Organization مستقیم
                tankhah = Tankhah.objects.filter(organization__code=org.code).order_by('-id').first()
                if not tankhah:
                    raise CommandError(f"هیچ تنخواهی برای سازمان {org.code} یافت نشد. ابتدا یک تنخواه بسازید.")

                defaults = {
                    'tankhah': tankhah,
                    'status': draft,
                    'amount': amount,
                }
                # تلاش برای پرکردن فیلدهای متداول در صورت وجود
                try:
                    from accounts.models import CustomUser  # type: ignore
                    su = CustomUser.objects.filter(is_superuser=True).first()
                    if su and 'created_by' in [f.name for f in Factor._meta.fields]:
                        defaults['created_by'] = su
                except Exception:
                    pass

                factor, created = Factor.objects.get_or_create(
                    number=number,
                    defaults=defaults,
                )
                if not created:
                    # ریست وضعیت برای تکرار سناریو
                    factor.status = draft
                    factor.tankhah = tankhah
                    factor.save(update_fields=['status','tankhah'])
                self.stdout.write(self.style.SUCCESS(f"FACTOR created/reset: id={factor.id} number={factor.number} status={factor.status.code} org={org.code}"))
        except Exception as e:
            # اگر ایجاد به‌دلیل فیلدهای اجباری ممکن نشد، از فاکتور موجود استفاده می‌کنیم
            self.stdout.write(self.style.WARNING(f"ایجاد فاکتور جدید ممکن نشد: {e}. تلاش برای استفاده از فاکتور موجود."))
            factor = Factor.objects.filter(tankhah__organization__code=org.code).order_by('-id').first()
            if not factor:
                raise CommandError("هیچ فاکتور موجودی یافت نشد تا روند روی آن تست شود.")
            # اگر وضعیتش DRAFT نیست، سعی می‌کنیم از نزدیک‌ترین روند شروع کنیم
            if factor.status.code not in ('DRAFT','PENDING_APPROVAL','APPROVED_INTERMEDIATE'):
                self.stdout.write(self.style.NOTICE(f"وضعیت فعلی فاکتور: {factor.status.code}. تلاش برای ادامه روند از وضعیت موجود."))

        # حرکت در روند از شعبه
        def do_transition(o, act_code):
            tr = Transition.objects.get(
                organization=o,
                entity_type=et,
                from_status=factor.status,
                action=Action.objects.get(code=act_code)
            )
            factor.status = tr.to_status
            factor.save(update_fields=['status'])
            self.stdout.write(self.style.SUCCESS(f"{o.code}: {tr.from_status.code} --{act_code}--> {tr.to_status.code}"))

        # شعبه: تلاش برای SUBMIT تا دو مرحله (DRAFT->PENDING_APPROVAL و سپس ->APPROVED_INTERMEDIATE)
        for _ in range(2):
            try:
                do_transition(org, 'SUBMIT')
            except Transition.DoesNotExist:
                break

        # دفتر مرکزی: میانی و نهایی
        if not hq:
            raise CommandError("دفتر مرکزی یافت نشد (is_core=True).")

        # تاییدهای میانی (self-loop)
        try:
            do_transition(hq, 'APPROVE')
        except Transition.DoesNotExist:
            self.stdout.write("هیچ گذار APPROVE (میانی) تعریف نشده؛ از این مرحله عبور می‌کنیم.")

        # تایید نهایی
        do_transition(hq, 'FINAL_APPROVE')

        self.stdout.write(self.style.MIGRATE_HEADING("وضعیت نهایی فاکتور:"))
        self.stdout.write(self.style.SUCCESS(f"FACTOR #{factor.id} → status={factor.status.code}"))


