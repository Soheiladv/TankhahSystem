import datetime

from django import forms
from jdatetime import datetime as jdatetime

class JalaliDateField(forms.DateField):
    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.date):
            return value
        try:
            jalali_date = jdatetime.strptime(value, '%Y/%m/%d')
            return jalali_date.togregorian().date()
        except ValueError:
            raise forms.ValidationError("فرمت تاریخ نامعتبر است.")

    def prepare_value(self, value):
        if isinstance(value, datetime.date):
            jalali_date = jdatetime.fromgregorian(date=value)
            return jalali_date.strftime('%Y/%m/%d')
        return value