from django.utils.translation import gettext_lazy as _
#
# فایل: tankhah/constants.py (نسخه نهایی و تمیز شده)
#
from django.utils.translation import gettext_lazy as _

# --- وضعیت‌های ممکن برای فاکتور و ردیف‌های آن ---
FACTOR_STATUSES = (
    ('DRAFT', _('پیش‌نویس')),
    ('PENDING_APPROVAL', _('در انتظار تأیید')),
    ('APPROVED_INTERMEDIATE', _('تأیید میانی')),
    ('APPROVED_FINAL', _('تأیید نهایی')),
    ('REJECT', _('رد شده')),
    ('PAID', _('پرداخت شده')),
    ('PARTIAL', _('تأیید جزئی')),
)

# --- اقدامات ممکن توسط کاربران در سیستم ---
# این لیست شامل هم اقدامات گردش کار و هم اقدامات عمومی است
ACTION_TYPES = (
    # اقدامات گردش کار
    ('APPROVE', _('تأیید')),
    ('REJECT', _('رد')),
    ('SUBMIT', _('ارسال برای تایید')),
    ('FINAL_APPROVE', _('تایید نهایی')),

    # اقدامات عمومی (بدون نیاز به مرحله)
    ('VIEW', _('مشاهده')),
    ('EDIT', _('ویرایش')),
    ('CREATE', _('ایجاد')),
    ('DELETE', _('حذف')),
    ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
)

# --- لیستی برای تفکیک اقدامات عمومی از اقدامات گردش کار ---
# این لیست باید شامل کدهایی از ACTION_TYPES باشد که به مرحله (stage) نیازی ندارند.

# --- انواع موجودیت‌ها در سیستم ---
ENTITY_TYPES = (
    ('FACTOR', _('فاکتور')),
    ('FACTORITEM', _('ردیف فاکتور')),
    ('TANKHAH', _('تنخواه')),
    ('BUDGET', _('بودجه')),
    ('PAYMENTORDER', _('دستور پرداخت')),
    ('REPORTS', _('گزارشات')),
    ('GENERAL', _('عمومی')),
)

# این لیست کدهای رشته‌ای است
ACTIONS_WITHOUT_STAGE = ('VIEW', 'EDIT', 'CREATE', 'DELETE', 'SIGN_PAYMENT')


ACTION_TYPES_ = (
    ('DRAFT', _('پیش‌نویس')),
    ('APPROVE', _('تأیید')),
    ('REJECT', _('رد شده')),  # از 'REJECTE' به 'REJECT' اصلاح شد تا استاندارد باشد
    ('SUBMIT', _('ارسال برای تایید')),
    ('PENDING_APPROVAL', _('در انتظار تأیید')),
    ('APPROVED_INTERMEDIATE', _('تأیید میانی')),
    ('FINAL_APPROVE', _('تایید نهایی')),
    ('VIEW', _('مشاهده')),
    ('EDIT', _('ویرایش')),
    ('CREATE', _('ایجاد')),
    ('DELETE', _('حذف')),
    ('SIGN_PAYMENT', _('امضای دستور پرداخت')),

    ('APPROVED_FINAL', _('تأیید نهایی')),
    ('PAID', _('پرداخت شده')),
    ('PARTIAL', _('تأیید جزئی')),
)

#
# ACTIONS_WITHOUT_STAGE = ( ['VIEW', 'EDIT', 'CREATE', 'DELETE', 'SIGN_PAYMENT'] )
#
# ENTITY_TYPES = (
#     ('FACTOR', 'فاکتور'),
#     ('TANKHAH', 'تنخواه'),
#     ('BUDGET', 'بودجه'),
#     ('PAYMENTORDER', 'دستور پرداخت'),
#     ('REPORTS', 'گزارشات'),
#     ('GENERAL', 'عمومی')
# )


# ACTION_TYPES = (
#     ('DRAFT', _('پیش‌نویس')),
#     ('PENDING', _('در حال بررسی')),
#     ('APPROVE', _('تأیید شده')),
#     ('REJECT', _('رد شده')),
#     ('STAGE_CHANGE', _('تغییر مرحله')),
#     ('DELETE', _('حذف')),
#     ('CREATE', _('ایجاد')),
#     ('EDIT', _('ویرایش')),
#     ('VIEW', _('مشاهده')),
#     ('PAID', _('پرداخت شده')),
#     ('PARTIAL', _('تأیید جزئی')),
#     ('PENDING_APPROVAL', _('در انتظار تأیید')),
#     ('APPROVED_INTERMEDIATE', _('تأیید میانی')),
#     ('APPROVED_FINAL', _('تأیید نهایی')),
#     ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
#     ('SENT_TO_HQ', _('ارسال‌شده به HQ')),
#     ('HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
#     ('HQ_OPS_APPROVED', _('تأییدشده - بهره‌برداری')),
#     ('HQ_FIN_PENDING', _('در حال بررسی - مالی')),
#     ('TEMP_APPROVED', _('تأیید موقت')),
# )
