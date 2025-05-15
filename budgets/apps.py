from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budgets'
    verbose_name = 'سیستم بودجه بندی'

    def ready(self):
        import budgets.signals