# tankhah/constants.py
from django.utils.translation import gettext_lazy as _

ACTION_TYPES = (
    ('DRAFT', 'پیش‌نویس'),
    ('PENDING', _('در حال بررسی')),
    ('APPROVE',  _('تأیید شده')),
    ('REJECT',  _('رد شده')),
    ('STAGE_CHANGE', 'تغییر مرحله'),
    ('DELETE', 'حذف'),
    ('CREATE', 'ایجاد'),
    ('EDIT', 'ویرایش'),
    ('VIEW', 'مشاهده'),
    ('PAID', 'پرداخت شده'),
    ('PARTIAL', 'تأیید جزئی'),
    ('PENDING_APPROVAL', _('در انتظار تأیید')),
    ('APPROVED_INTERMEDIATE', _('تأیید میانی')),
    ('APPROVED_FINAL', _('تأیید نهایی')),
    ('SIGN_PAYMENT', 'امضای دستور پرداخت'),
    ('SENT_TO_HQ', _('ارسال‌شده به HQ')),
    ('HQ_OPS_PENDING', _('در حال بررسی - بهره‌برداری')),
    ('HQ_OPS_APPROVED', _('تأییدشده - بهره‌برداری')),
    ('HQ_FIN_PENDING', _('در حال بررسی - مالی')),
)


ENTITY_TYPES = (
    ('FACTOR', 'فاکتور'),
    ('TANKHAH', 'تنخواه'),
    ('BUDGET', 'بودجه'),
    ('PAYMENTORDER', 'دستور پرداخت'),
    ('REPORTS', 'گزارشات'),
    ('GENERAL', 'عمومی')
)