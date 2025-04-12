from django.utils import timezone
from budgets.models import BudgetPeriod, BudgetAllocation, ProjectBudgetAllocation
from core.models import Organization, Project, SubProject
from accounts.models import CustomUser

user = CustomUser.objects.get(id=1)  # کاربرت رو انتخاب کن
org = Organization.objects.get(id=1)  # سازمان کلان
project = Project.objects.get(id=1)  # یه پروژه
subproject = SubProject.objects.get(id=1)  # یه زیرپروژه

# 1. دوره بودجه
bp = BudgetPeriod.objects.create(
    name="سال 1404",
    organization=org,
    total_amount=1000000000,
    start_date=timezone.now().date(),
    end_date=timezone.now().date(),
    is_active=True,
    created_by=user
)

# 2. تخصیص به شعبه
ba = BudgetAllocation.objects.create(
    budget_period=bp,
    organization=org,
    allocated_amount=500000000,
    allocation_date=timezone.now().date(),
    created_by=user
)

# 3. تخصیص به پروژه
pba = ProjectBudgetAllocation.objects.create(
    budget_allocation=ba,
    project=project,
    subproject=subproject,
    allocated_amount=200000000,
    allocation_date=timezone.now().date(),
    created_by=user,
    description="تخصیص اولیه پروژه"
)