from django import forms
from tankhah.models import FactorItem
class FactorItemForm(forms.ModelForm):
  status = forms.CharField(required=False, widget=forms.HiddenInput())
  comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'توضیحات آیتم'}))

  class Meta:
      model = FactorItem
      fields = ['description', 'amount', 'status', 'comment']
      widgets = {
          'description': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-modern'}),
          'amount': forms.NumberInput(attrs={'readonly': 'readonly', 'class': 'form-control-modern'}),
      }
