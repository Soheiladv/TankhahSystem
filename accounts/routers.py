# ===== FILE: accounts/routers.py (نسخه نهایی و صحیح) =====

class LogRouter:
    """
    A router to control all database operations on models that should be
    in the tankhah_logs_db.
    """
    route_models = {
        'accounts.auditlog',
        # حذف version_tracker models از logs database
        # 'version_tracker.appversion',
        # 'version_tracker.filehash', 
        # 'version_tracker.codechangelog',
        # 'version_tracker.finalversion',
    }
    route_db = 'tankhah_logs_db'  # <<<< نام صحیح دیتابیس اینجا تعریف شود

    def _is_log_model(self, model):
        """Helper function to check if a model is targeted for the logs_db."""
        return f'{model._meta.app_label}.{model._meta.model_name.lower()}' in self.route_models

    def db_for_read(self, model, **hints):
        if self._is_log_model(model):
            return self.route_db
        return None

    def db_for_write(self, model, **hints):
        if self._is_log_model(model):
            return self.route_db
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if self._is_log_model(obj1._meta.model) or self._is_log_model(obj2._meta.model):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        is_log_model = model_name and f'{app_label}.{model_name.lower()}' in self.route_models

        if is_log_model:
            # اگر مدل لاگ بود، فقط اجازه مایگریت در دیتابیس لاگ را بده
            return db == self.route_db
        elif db == self.route_db:
            # اگر دیتابیس، دیتابیس لاگ بود ولی مدل، مدل لاگ نبود، اجازه نده
            return False

        # در غیر این صورت (مدل‌های معمولی در دیتابیس‌های دیگر)، اجازه بده
        return None