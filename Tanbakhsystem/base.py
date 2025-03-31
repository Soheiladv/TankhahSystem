# forms/base.py
import logging
from django import forms
from django.utils.translation import gettext_lazy as _
import jdatetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class JalaliDateForm(forms.ModelForm):
    """
    فرم پایه برای مدیریت تاریخ‌های شمسی
    - نمایش تاریخ به‌صورت شمسی در فرانت‌اند
    - تبدیل به میلادی برای ذخیره در دیتابیس
    """

    def set_jalali_initial(self, field_name, instance_field):
        """تنظیم مقدار اولیه تاریخ شمسی برای یک فیلد"""
        if self.instance and getattr(self.instance, instance_field):
            jalali_date = jdatetime.date.fromgregorian(date=getattr(self.instance, instance_field))
            self.initial[field_name] = jalali_date.strftime('%Y/%m/%d')
            logger.info(f"Set initial {field_name} to: {self.initial[field_name]}")
        else:
            self.initial[field_name] = ''

    def clean_jalali_date(self, field_name):
        """تبدیل تاریخ شمسی به میلادی برای یک فیلد"""
        date_str = self.cleaned_data.get(field_name)
        logger.info(f"Raw {field_name}: {date_str}")
        if date_str:
            try:
                j_date = jdatetime.datetime.strptime(date_str, '%Y/%m/%d').date()
                g_date = j_date.togregorian()
                logger.info(f"Converted {field_name} to: {g_date}")
                return g_date
            except ValueError as e:
                logger.error(f"Error parsing {field_name}: {e}")
                raise forms.ValidationError(_("تاریخ را به فرمت درست وارد کنید (مثل 1404/01/17)"))
        return None