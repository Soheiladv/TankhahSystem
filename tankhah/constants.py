from django.utils.translation import gettext_lazy as _
ACTION_TYPES = (
    ('APPROVE', _('تأیید')),
    ('REJECT', _('رد')),
    ('SUBMIT', _('ارسال برای تایید')),
    ('FINAL_APPROVE', _('تایید نهایی')),
    ('VIEW', _('مشاهده')),
    ('EDIT', _('ویرایش')),
    ('CREATE', _('ایجاد')),
    ('DELETE', _('حذف')),
    ('SIGN_PAYMENT', _('امضای دستور پرداخت')),
)

# این لیست کدهای رشته‌ای است
ACTIONS_WITHOUT_STAGE = ('VIEW', 'EDIT', 'CREATE', 'DELETE', 'SIGN_PAYMENT')

ENTITY_TYPES = (
    ('FACTOR', _('فاکتور')),
    ('FACTORITEM', _('ردیف فاکتور')),
    ('TANKHAH', _('تنخواه')),
    ('BUDGET', _('بودجه')),
    ('PAYMENTORDER', _('دستور پرداخت')),
    ('REPORTS', _('گزارشات')),
    ('GENERAL', _('عمومی')),
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
