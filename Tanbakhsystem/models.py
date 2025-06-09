# dashboards/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class DashboardAccess(models.Model): # مدل ساختگی برای تعریف دسترسی‌ها
    class Meta:
        managed = False # این باعث می‌شود جنگو جدولی برای این مدل در دیتابیس ایجاد نکند
        verbose_name = _("دسترسی داشبورد")
        verbose_name_plural = _("دسترسی‌های داشبورد")
        default_permissions = () # غیرفعال کردن دسترسی‌های پیش‌فرض
        permissions = [
            ("view_dashboard_statistics", _("می‌تواند بخش‌های آماری داشبورد را مشاهده کند")),
            ("view_budget_charts", _("می‌تواند نمودارهای بودجه را مشاهده کند")),
            ("view_tankhah_charts", _("می‌تواند نمودارهای تنخواه را مشاهده کند")),
            ("view_project_status_widget", _("می‌تواند ویجت وضعیت پروژه‌ها را مشاهده کند")),
            ("view_budget_alerts_widget", _("می‌تواند ویجت هشدارهای بودجه را مشاهده کند")),
        ]