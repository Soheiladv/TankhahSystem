from budgets.models import ProjectBudgetAllocation, BudgetAllocation
from tankhah.models import Tankhah


def migrate_tankhah_allocations():
    for tankhah in Tankhah.objects.all():
        if hasattr(tankhah, 'project_budget_allocation') and tankhah.project_budget_allocation:
            tankhah.budget_allocation = tankhah.project_budget_allocation.budget_allocation
            tankhah.save()
            print(f"Migrated Tankhah {tankhah.number} to BudgetAllocation {tankhah.budget_allocation.id}")

if __name__ == "__main__":
    migrate_tankhah_allocations()