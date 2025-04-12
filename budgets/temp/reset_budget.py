# reset_budget.py
from django.db import transaction
from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation

def reset_all_budget_data():
    try:
        with transaction.atomic():
            # پاک کردن همه تخصیص‌های پروژه
            project_count = ProjectBudgetAllocation.objects.count()
            ProjectBudgetAllocation.objects.all().delete()
            print(f"Deleted {project_count} ProjectBudgetAllocation records.")

            # پاک کردن همه تخصیص‌های شعبه
            allocation_count = BudgetAllocation.objects.count()
            BudgetAllocation.objects.all().delete()
            print(f"Deleted {allocation_count} BudgetAllocation records.")

            # پاک کردن همه دوره‌های بودجه
            period_count = BudgetPeriod.objects.count()
            BudgetPeriod.objects.all().delete()
            print(f"Deleted {period_count} BudgetPeriod records.")

            print("All budget data has been reset successfully!")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    reset_all_budget_data()



"""
from budgets.reset_budget import reset_all_budget_data
reset_all_budget_data()
"""