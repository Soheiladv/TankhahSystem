from django.db import migrations
from decimal import Decimal


def seed_system_settings(apps, schema_editor):
    SystemSettings = apps.get_model('core', 'SystemSettings')
    # ایجاد/به‌روزرسانی ایمن singleton با مقادیر معتبر
    SystemSettings.objects.update_or_create(
        pk=1,
        defaults={
            'budget_locked_percentage_default': Decimal('0'),
            'budget_warning_threshold_default': Decimal('10'),
            'budget_warning_action_default': 'NOTIFY',
            'allocation_locked_percentage_default': Decimal('0'),
            'tankhah_used_statuses': [],
            'tankhah_accessible_organizations': [],
            'tankhah_payment_ceiling_default': Decimal('0'),
            'tankhah_payment_ceiling_enabled_default': False,
            'enforce_strict_approval_order': True,
            'allow_bypass_org_chart': False,
            'allow_action_without_org_chart': False,
        }
    )


def unseed_system_settings(apps, schema_editor):
    # عدم حذف برای ایمنی؛ اگر لازم است می‌توان اینجا خالی گذاشت
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_systemsettings_allow_action_without_org_chart_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_system_settings, unseed_system_settings),
    ]


