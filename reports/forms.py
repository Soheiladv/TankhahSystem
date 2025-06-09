from django import forms
from reports.models import FinancialReport

class FinancialReportForm(forms.ModelForm):
     class Meta:
         model = FinancialReport
         fields = ['payment_number'] # فقط شماره پرداخت قابل ویرایش باشه
         labels = {
         'payment_number': 'شماره پرداخت',
         }
         widgets = {
         'payment_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره پرداخت را وارد کنید'}),
         }

     def __init__(self, *args, **kwargs):
         super().__init__(*args, **kwargs)
         # فیلدهای فقط خواندنی رو ت وی فرم نشون بده
         for field in ['total_amount', 'approved_amount', 'rejected_amount', 'total_factors', 'approved_factors', 'rejected_factors']:
             self.fields[field] = forms.DecimalField(
             initial=getattr(self.instance, field),
             disabled=True,
             widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
             )

