from django import forms


class FinancingSettingsForm(forms.ModelForm):
    class Meta:
        from .models import Homepage
        model = Homepage
        fields = ['financing_annual_rate']
        widgets = {'financing_annual_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '50'})}
