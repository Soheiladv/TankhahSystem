# RCMS/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
import logging

logger = logging.getLogger(__name__)

class UserAccessMixin(LoginRequiredMixin):
    def has_permission(self, permission_codename):
        """چک می‌کند که آیا کاربر مجوز خاصی دارد یا خیر."""
        if self.request.user.is_superuser:
            return True
        for group in self.request.user.groups.all():
            for role in group.roles.all():
                if role.permissions.filter(codename=permission_codename).exists():
                    return True
        return False

    def get_queryset(self):
        """متد پیش‌فرض برای فیلتر کردن کوئری‌ست در ویوها."""
        queryset = super().get_queryset() if hasattr(super(), 'get_queryset') else self.model.objects.all()
        return self.filter_queryset(queryset)