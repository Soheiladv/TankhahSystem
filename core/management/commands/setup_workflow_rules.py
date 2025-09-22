"""
دستور Django برای راه‌اندازی قوانین گردش کار پیش‌فرض
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Organization, Status, Action, EntityType, Transition, Post, PostAction
from core.workflow_management import   WorkflowRuleManager
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'راه‌اندازی قوانین گردش کار پیش‌فرض'

    def add_arguments(self, parser):
        parser.add_argument(
            '--organization-id',
            type=int,
            help='شناسه سازمان برای ایجاد قوانین',
        )
        parser.add_argument(
            '--entity-type',
            type=str,
            choices=['FACTOR', 'TANKHAH', 'PAYMENTORDER', 'BUDGET_ALLOCATION'],
            help='نوع موجودیت برای ایجاد قوانین',
        )
        parser.add_argument(
            '--create-template',
            action='store_true',
            help='ایجاد تمپلیت از قوانین موجود',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('شروع راه‌اندازی قوانین گردش کار...')
        )

        try:
            # ایجاد وضعیت‌های پیش‌فرض
            self.create_default_statuses()
            
            # ایجاد اقدامات پیش‌فرض
            self.create_default_actions()
            
            # ایجاد انواع موجودیت
            self.create_entity_types()
            
            # اگر سازمان مشخص شده، قوانین را برای آن ایجاد کن
            if options['organization_id']:
                organization = Organization.objects.get(id=options['organization_id'])
                entity_type = options['entity_type']
                
                if entity_type:
                    self.create_workflow_rules_for_organization(organization, entity_type)
                else:
                    # ایجاد قوانین برای همه انواع موجودیت
                    for entity_code, entity_name in [
                        ('FACTOR', 'فاکتور'),
                        ('TANKHAH', 'تنخواه'),
                        ('PAYMENTORDER', 'دستور پرداخت'),
                        ('BUDGET_ALLOCATION', 'تخصیص بودجه')
                    ]:
                        self.create_workflow_rules_for_organization(organization, entity_code)
            
            # ایجاد تمپلیت اگر درخواست شده
            if options['create_template'] and options['organization_id'] and options['entity_type']:
                organization = Organization.objects.get(id=options['organization_id'])
                template = WorkflowRuleManager.create_rule_template_from_existing(
                    organization=organization,
                    entity_type=options['entity_type'],
                    name=f"تمپلیت پیش‌فرض {options['entity_type']}",
                    description="تمپلیت پیش‌فرض ایجاد شده توسط دستور مدیریت",
                    user=User.objects.filter(is_superuser=True).first()
                )
                self.stdout.write(
                    self.style.SUCCESS(f'تمپلیت {template.name} ایجاد شد.')
                )

            self.stdout.write(
                self.style.SUCCESS('راه‌اندازی قوانین گردش کار با موفقیت انجام شد.')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطا در راه‌اندازی: {str(e)}')
            )
            logger.error(f"خطا در راه‌اندازی قوانین گردش کار: {str(e)}")

    def create_default_statuses(self):
        """ایجاد وضعیت‌های پیش‌فرض"""
        statuses = [
            {
                'name': 'پیش‌نویس',
                'code': 'DRAFT',
                'is_initial': True,
                'is_final_approve': False,
                'is_final_reject': False,
                'description': 'وضعیت اولیه برای اسناد جدید'
            },
            {
                'name': 'در انتظار تأیید',
                'code': 'PENDING_APPROVAL',
                'is_initial': False,
                'is_final_approve': False,
                'is_final_reject': False,
                'description': 'در انتظار بررسی و تأیید'
            },
            {
                'name': 'تأیید شده',
                'code': 'APPROVED',
                'is_initial': False,
                'is_final_approve': True,
                'is_final_reject': False,
                'description': 'تأیید نهایی شده'
            },
            {
                'name': 'رد شده',
                'code': 'REJECTED',
                'is_initial': False,
                'is_final_approve': False,
                'is_final_reject': True,
                'description': 'رد شده توسط تأییدکننده'
            },
            {
                'name': 'پرداخت شده',
                'code': 'PAID',
                'is_initial': False,
                'is_final_approve': True,
                'is_final_reject': False,
                'description': 'پرداخت انجام شده'
            }
        ]

        for status_data in statuses:
            status, created = Status.objects.get_or_create(
                code=status_data['code'],
                defaults=status_data
            )
            if created:
                self.stdout.write(f'وضعیت {status.name} ایجاد شد.')
            else:
                self.stdout.write(f'وضعیت {status.name} قبلاً وجود داشت.')

    def create_default_actions(self):
        """ایجاد اقدامات پیش‌فرض"""
        actions = [
            {
                'name': 'ارسال برای تأیید',
                'code': 'SUBMIT',
                'description': 'ارسال سند برای بررسی و تأیید'
            },
            {
                'name': 'تأیید',
                'code': 'APPROVE',
                'description': 'تأیید سند'
            },
            {
                'name': 'رد',
                'code': 'REJECT',
                'description': 'رد سند'
            },
            {
                'name': 'بازگشت به مرحله قبل',
                'code': 'RETURN',
                'description': 'بازگشت سند به مرحله قبل'
            },
            {
                'name': 'امضای دستور پرداخت',
                'code': 'SIGN_PAYMENT',
                'description': 'امضای دستور پرداخت'
            }
        ]

        for action_data in actions:
            action, created = Action.objects.get_or_create(
                code=action_data['code'],
                defaults=action_data
            )
            if created:
                self.stdout.write(f'اقدام {action.name} ایجاد شد.')
            else:
                self.stdout.write(f'اقدام {action.name} قبلاً وجود داشت.')

    def create_entity_types(self):
        """ایجاد انواع موجودیت"""
        entity_types = [
            ('FACTOR', 'فاکتور'),
            ('TANKHAH', 'تنخواه'),
            ('PAYMENTORDER', 'دستور پرداخت'),
            ('BUDGET_ALLOCATION', 'تخصیص بودجه'),
        ]

        for code, name in entity_types:
            entity_type, created = EntityType.objects.get_or_create(
                code=code,
                defaults={'name': name}
            )
            if created:
                self.stdout.write(f'نوع موجودیت {entity_type.name} ایجاد شد.')
            else:
                self.stdout.write(f'نوع موجودیت {entity_type.name} قبلاً وجود داشت.')

    def create_workflow_rules_for_organization(self, organization, entity_type):
        """ایجاد قوانین گردش کار برای یک سازمان"""
        try:
            entity_type_obj = EntityType.objects.get(code=entity_type)
            
            # ایجاد گذارهای پیش‌فرض
            transitions = [
                {
                    'name': f'ارسال {entity_type} برای تأیید',
                    'from_status_code': 'DRAFT',
                    'action_code': 'SUBMIT',
                    'to_status_code': 'PENDING_APPROVAL'
                },
                {
                    'name': f'تأیید {entity_type}',
                    'from_status_code': 'PENDING_APPROVAL',
                    'action_code': 'APPROVE',
                    'to_status_code': 'APPROVED'
                },
                {
                    'name': f'رد {entity_type}',
                    'from_status_code': 'PENDING_APPROVAL',
                    'action_code': 'REJECT',
                    'to_status_code': 'REJECTED'
                },
                {
                    'name': f'بازگشت {entity_type} به پیش‌نویس',
                    'from_status_code': 'PENDING_APPROVAL',
                    'action_code': 'RETURN',
                    'to_status_code': 'DRAFT'
                }
            ]

            for transition_data in transitions:
                from_status = Status.objects.get(code=transition_data['from_status_code'])
                to_status = Status.objects.get(code=transition_data['to_status_code'])
                action = Action.objects.get(code=transition_data['action_code'])

                transition, created = Transition.objects.get_or_create(
                    entity_type=entity_type_obj,
                    from_status=from_status,
                    action=action,
                    organization=organization,
                    defaults={
                        'name': transition_data['name'],
                        'to_status': to_status,
                        'created_by': User.objects.filter(is_superuser=True).first()
                    }
                )

                if created:
                    self.stdout.write(f'گذار {transition.name} ایجاد شد.')
                else:
                    self.stdout.write(f'گذار {transition.name} قبلاً وجود داشت.')

            # ایجاد قوانین پست‌ها (PostAction) برای پست‌های موجود
            posts = Post.objects.filter(organization=organization, is_active=True)
            statuses = Status.objects.filter(is_active=True)
            
            for post in posts:
                for status in statuses:
                    # تعیین نوع اقدام بر اساس وضعیت
                    if status.code == 'DRAFT':
                        action_type = 'SUBMIT'
                        allowed_actions = ['SUBMIT']
                    elif status.code == 'PENDING_APPROVAL':
                        action_type = 'APPROVE'
                        allowed_actions = ['APPROVE', 'REJECT', 'RETURN']
                    elif status.code == 'APPROVED':
                        action_type = 'SIGN_PAYMENT'
                        allowed_actions = ['SIGN_PAYMENT']
                    else:
                        continue

                    post_action, created = PostAction.objects.get_or_create(
                        post=post,
                        stage=status,
                        action_type=action_type,
                        entity_type=entity_type,
                        defaults={
                            'is_active': True,
                            'min_level': post.level,
                            'triggers_payment_order': status.code == 'APPROVED',
                            'allowed_actions': allowed_actions
                        }
                    )

                    if created:
                        self.stdout.write(f'قانون پست {post.name} برای وضعیت {status.name} ایجاد شد.')

            self.stdout.write(
                self.style.SUCCESS(f'قوانین گردش کار برای {entity_type} در سازمان {organization.name} ایجاد شد.')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'خطا در ایجاد قوانین برای {entity_type}: {str(e)}')
            )
            logger.error(f"خطا در ایجاد قوانین گردش کار: {str(e)}")
