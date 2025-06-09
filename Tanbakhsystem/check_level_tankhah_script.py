# # توی ترمینال بزن: python manage.py shell
# # بعد این کدها رو خط به خط اجرا کن یا توی یه فایل بذار و با execfile اجرا کن
#
# from tankhah.models import Tankhah, Factor, ApprovalLog, WorkflowStage
# from django.utils import timezone
#
# # شماره تنخواه رو وارد کن (مثلاً 12)
# tankhah_id = 12
# tankhah = Tankhah.objects.get(id=tankhah_id)
#
# # اطلاعات اولیه
# print(f"تنخواه: {tankhah.number}")
# print(f"وضعیت تنخواه: {tankhah.status}")
# print(f"مرحله فعلی: {tankhah.current_stage.name if tankhah.current_stage else 'تنظیم نشده'}")
#
# # بررسی فاکتورها
# print("\nفاکتورها:")
# for factor in tankhah.factors.all():
#     print(f" - شماره فاکتور: {factor.number}, وضعیت: {factor.status}, مبلغ: {factor.amount}")
#
# # بررسی مراحل و لاگ‌ها
# stages = WorkflowStage.objects.order_by('order')
# print("\nمراحل و لاگ‌ها:")
# for stage in stages:
#     approvals = ApprovalLog.objects.filter(tankhah=tankhah, stage=stage)
#     print(f"مرحله {stage.order}: {stage.name}")
#     if approvals.exists():
#         for approval in approvals:
#             print(f"  - کاربر: {approval.user.get_full_name()}, اقدام: {approval.action}, زمان: {approval.timestamp}")
#     else:
#         print("  - لاگی ثبت نشده")
#
# # بررسی چرا مرحله عوض نمی‌شه
# current_stage = tankhah.current_stage
# if current_stage:
#     approvals_in_current = ApprovalLog.objects.filter(tankhah=tankhah, stage=current_stage, action='APPROVE')
#     if approvals_in_current.exists():
#         next_stage = stages.filter(order__gt=current_stage.order).first()
#         if next_stage:
#             print(f"\nمرحله فعلی تأیید شده، باید به {next_stage.name} بره ولی نرفته!")
#         else:
#             print("\nمرحله فعلی تأیید شده و مرحله بعدی وجود نداره، باید وضعیت تنخواه به APPROVED تغییر کنه!")
#     else:
#         print(f"\nمرحله فعلی ({current_stage.name}) هنوز تأیید نشده.")
# else:
#     print("\nمرحله فعلی تنظیم نشده، باید اولین مرحله رو ست کنی!")
#
# # تست دستی تغییر مرحله
# if approvals_in_current.exists() and next_stage:
#     tankhah.current_stage = next_stage
#     tankhah.save()
#     print(f"مرحله به {next_stage.name} تغییر کرد.")
# elif approvals_in_current.exists() and not next_stage and all(f.status == 'APPROVED' for f in tankhah.factors.all()):
#     tankhah.status = 'APPROVED'
#     tankhah.save()
#     print("وضعیت تنخواه به APPROVED تغییر کرد.")