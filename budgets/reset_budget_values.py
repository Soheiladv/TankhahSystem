# reset_budget_values.py
from django.db import transaction
from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation

def reset_budget_values():
    try:
        with transaction.atomic():
            # صفر کردن تخصیص‌های پروژه
            project_allocations = ProjectBudgetAllocation.objects.all()
            for allocation in project_allocations:
                allocation.allocated_amount = 0
                allocation.remaining_amount = 0
                allocation.save(update_fields=['allocated_amount', 'remaining_amount'])
            print(f"Reset {project_allocations.count()} ProjectBudgetAllocation records.")

            # صفر کردن تخصیص‌های شعبه
            budget_allocations = BudgetAllocation.objects.all()
            for allocation in budget_allocations:
                allocation.allocated_amount = 0
                allocation.remaining_amount = 0  # اگه این فیلد رو داری
                allocation.save(update_fields=['allocated_amount', 'remaining_amount'])
            print(f"Reset {budget_allocations.count()} BudgetAllocation records.")

            # صفر کردن دوره‌های بودجه
            budget_periods = BudgetPeriod.objects.all()
            for period in budget_periods:
                period.total_amount = 0
                # اگه remaining_amount داری، این خط رو اضافه کن:
                # period.remaining_amount = 0
                period.save(update_fields=['total_amount'])
            print(f"Reset {budget_periods.count()} BudgetPeriod records.")

            print("All budget values have been reset to zero!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    reset_budget_values()