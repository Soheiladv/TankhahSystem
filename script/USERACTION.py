from django.contrib.auth import get_user_model
from accounts.models import AuditLog, ActiveUser

User = get_user_model()

try:
    user = User.objects.get(username='rheyran')
except User.DoesNotExist:
    print("کاربر rheyran یافت نشد.")

# دسترسی‌ها
permissions = user.get_all_permissions()
print("دسترسی‌های کاربر rheyran:")
for perm in permissions:
    print(perm)

# نقش‌ها
groups = user.groups.all()
roles = set()
for group in groups:
    for role in group.roles.all():
        roles.add(role.name)
print("نقش‌های کاربر rheyran:", roles)

# سازمان‌ها
organizations = user.get_authorized_organizations()
print("سازمان‌های مجاز برای rheyran:")
for org in organizations:
    print(org.name)

# دفتر مرکزی
print(f"آیا کاربر rheyran در دفتر مرکزی است؟: {user.is_hq}")

# لاگ‌ها
logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:5]
print("آخرین لاگ‌های فعالیت کاربر rheyran:")
for log in logs:
    print(f"{log.action} - {log.model_name} - {log.timestamp}")

# سشن‌های فعال
active_sessions = ActiveUser.objects.filter(user=user, is_active=True)
print("سشن‌های فعال کاربر rheyran:")
for session in active_sessions:
    print(f"{session.session_key} - {session.login_time}")