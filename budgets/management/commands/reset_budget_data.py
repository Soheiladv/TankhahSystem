import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.cache import cache
from tankhah.models import Factor, Tankhah
from budgets.models import BudgetAllocation, BudgetTransaction, ProjectBudgetAllocation
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# Run Reset
# python manage.py reset_budget_data --models all
"""
برای ریست تمام مدل‌ها:
python manage.py reset_budget_data --models all
برای ریست مدل‌های خاص (مثل فقط Factor و Tankhah):
python manage.py reset_budget_data --models factor tankhah
برای ریست بدون پاک کردن کش:
python manage.py reset_budget_data --models all --no-cache

تست ۱: مطمئن شو که تمام رکوردهای مدل‌های انتخاب‌شده حذف شدن:

SELECT COUNT(*) FROM tankhah_factor;
SELECT COUNT(*) FROM tankhah_tankhah;
SELECT COUNT(*) FROM budgets_budgettransaction;
SELECT COUNT(*) FROM budgets_projectbudgetallocation;
SELECT COUNT(*) FROM budgets_budgetallocation;
"""
class Command(BaseCommand):
    help = 'Reset data for budget-related models (Factor, Tankhah, BudgetAllocation, BudgetTransaction, ProjectBudgetAllocation)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            choices=['factor', 'tankhah', 'budget_allocation', 'budget_transaction', 'project_budget_allocation',
                     'all'],
            default=['all'],
            help='Specify which models to reset. Use "all" to reset all models.'
        )
        parser.add_argument(
            '--no-cache',
            action='store_true',
            help='Skip clearing cache after resetting data.'
        )

    def handle(self, *args, **options):
        models_to_reset = options['models']
        clear_cache = not options['no_cache']
        if 'all' in models_to_reset:
            models_to_reset = ['factor', 'tankhah', 'budget_transaction', 'project_budget_allocation',
                               'budget_allocation']

        self.stdout.write(self.style.WARNING('Starting data reset...'))
        logger.info(f"Starting data reset for models: {models_to_reset}")

        try:
            with transaction.atomic():
                # حذف رکوردها به ترتیب درست برای جلوگیری از نقض قیدها
                if 'factor' in models_to_reset:
                    self.reset_factors()
                if 'budget_transaction' in models_to_reset:
                    self.reset_budget_transactions()
                if 'tankhah' in models_to_reset:
                    self.reset_tankhahs()
                if 'project_budget_allocation' in models_to_reset:
                    self.reset_project_budget_allocations()
                if 'budget_allocation' in models_to_reset:
                    self.reset_budget_allocations()

                # پاک کردن کش (اگه فعال باشه)
                if clear_cache:
                    self.clear_related_caches()

            self.stdout.write(self.style.SUCCESS('Data reset completed successfully.'))
            logger.info('Data reset completed successfully.')

        except Exception as e:
            logger.error(f"Error during data reset: {str(e)}", exc_info=True)
            self.stdout.write(self.style.ERROR(f'Error during data reset: {str(e)}'))
            raise

    def reset_factors(self):
        count = Factor.objects.count()
        Factor.objects.all().delete()
        logger.info(f"Deleted {count} Factor records.")
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} Factor records.'))

    def reset_budget_transactions(self):
        count = BudgetTransaction.objects.count()
        BudgetTransaction.objects.all().delete()
        logger.info(f"Deleted {count} BudgetTransaction records.")
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} BudgetTransaction records.'))

    def reset_tankhahs(self):
        count = Tankhah.objects.count()
        # ریست remaining_budget به مقدار اولیه (budget)
        Tankhah.objects.update(remaining_budget=F('budget'), is_active=True)
        Tankhah.objects.all().delete()
        logger.info(f"Deleted {count} Tankhah records and reset remaining_budget.")
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} Tankhah records and reset remaining_budget.'))

    def reset_project_budget_allocations(self):
        count = ProjectBudgetAllocation.objects.count()
        ProjectBudgetAllocation.objects.all().delete()
        logger.info(f"Deleted {count} ProjectBudgetAllocation records.")
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} ProjectBudgetAllocation records.'))

    def reset_budget_allocations(self):
        count = BudgetAllocation.objects.count()
        # ریست returned_amount و is_locked
        BudgetAllocation.objects.update(returned_amount=0, is_locked=False, is_active=True)
        BudgetAllocation.objects.all().delete()
        logger.info(f"Deleted {count} BudgetAllocation records and reset returned_amount/is_locked.")
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} BudgetAllocation records and reset returned_amount/is_locked.'))

    def clear_related_caches(self):
        cache_keys = set()
        # اضافه کردن کلیدهای کش مرتبط
        for budget_period_id in BudgetAllocation.objects.values_list('budget_period_id', flat=True).distinct():
            cache_keys.add(f"budget_transfers_{budget_period_id}_no_filters")
            cache_keys.add(f"returned_budgets_{budget_period_id}_all_no_filters")
            cache_keys.add(f"tankhah_report_{budget_period_id}_no_filters")
            cache_keys.add(f"invoice_report_{budget_period_id}_no_filters")

        for org_id in BudgetAllocation.objects.values_list('organization_id', flat=True).distinct():
            cache_keys.add(f"organization_remaining_budget_{org_id}")

        for project_id in ProjectBudgetAllocation.objects.values_list('project_id', flat=True).distinct():
            if project_id:
                cache_keys.add(f"project_remaining_budget_{project_id}")

        for subproject_id in ProjectBudgetAllocation.objects.values_list('subproject_id', flat=True).distinct():
            if subproject_id:
                cache_keys.add(f"subproject_remaining_budget_{subproject_id}")

        for allocation_id in BudgetAllocation.objects.values_list('id', flat=True):
            cache_keys.add(f"allocation_remaining_{allocation_id}")

        for tankhah_id in Tankhah.objects.values_list('id', flat=True):
            cache_keys.add(f"tankhah_remaining_{tankhah_id}")

        for key in cache_keys:
            cache.delete(key)

        logger.info(f"Cleared cache keys: {cache_keys}")
        self.stdout.write(self.style.SUCCESS(f'Cleared {len(cache_keys)} cache keys.'))