from django.db import models
from django.db.models import Sum
# from budgets.models import BudgetAllocation, ProjectBudgetAllocation
# from core.models import Project, SubProject

def get_organization_budget(organization):
    from budgets.models import BudgetAllocation
    """بودجه کل تخصیص‌یافته به سازمان"""
    return BudgetAllocation.objects.filter(organization=organization).aggregate(total=Sum('allocated_amount'))['total'] or 0

def get_project_total_budget(project):
    from budgets.models import  ProjectBudgetAllocation
    """بودجه کل تخصیص‌یافته به پروژه از ProjectBudgetAllocation"""
    return ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=True).aggregate(total=Sum('allocated_amount'))['total'] or 0

def get_project_used_budget(project):
    from budgets.models import   ProjectBudgetAllocation
    """بودجه مصرف‌شده پروژه (زیرپروژه‌ها + تنخواه‌ها)"""
    # بودجه تخصیص‌یافته به زیرپروژه‌ها
    subproject_budget = ProjectBudgetAllocation.objects.filter(project=project, subproject__isnull=False).aggregate(total=Sum('allocated_amount'))['total'] or 0
    # بودجه مصرف‌شده توسط تنخواه‌های مستقیم پروژه
    tankhah_budget = project.tankhah_set.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
    return subproject_budget + tankhah_budget

def get_project_remaining_budget(project):
    """بودجه باقی‌مانده پروژه"""
    return get_project_total_budget(project) - get_project_used_budget(project)

def get_subproject_used_budget(subproject):
    """بودجه مصرف‌شده زیرپروژه (تنخواه‌ها)"""
    return subproject.tankhah_set.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0

def get_subproject_total_budget(subproject):
    """بودجه کل تخصیص‌یافته به زیرپروژه"""
    from budgets.models import   ProjectBudgetAllocation
    return ProjectBudgetAllocation.objects.filter(subproject=subproject).aggregate(total=Sum('allocated_amount'))['total'] or 0

def get_subproject_remaining_budget(subproject):
    """بودجه باقی‌مانده زیرپروژه"""
    return get_subproject_total_budget(subproject) - get_subproject_used_budget(subproject)

def can_delete_budget(entity):
    from core.models import Project,SubProject
    """چک می‌کنه که آیا بودجه پروژه یا زیرپروژه قابل حذف هست یا نه"""
    if isinstance(entity, Project):
        return not entity.tankhah_set.exists() and not entity.subprojects.exists()
    elif isinstance(entity, SubProject):
        return not entity.tankhah_set.exists()
    return False

"""محاسبه باقی‌مانده بودجه به‌صورت دینامیک"""
def get_remaining_amount(self):
    """محاسبه باقی‌مانده بودجه به‌صورت دینامیک"""
    allocated_total = self.allocations.aggregate(total=models.Sum('allocated_amount'))['total'] or 0
    return self.total_amount - allocated_total
