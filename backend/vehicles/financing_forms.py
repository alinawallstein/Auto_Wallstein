from django import forms


class FinancingInquiryForm(forms.Form):
    first_name = forms.CharField(max_length=80, label='Vorname')
    last_name = forms.CharField(max_length=80, label='Nachname')
    email = forms.EmailField(label='E-Mail')
    phone = forms.CharField(max_length=50, label='Telefon')
    downpayment = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, label='Anzahlung (€)')
    term_months = forms.IntegerField(min_value=12, max_value=120, label='Laufzeit (Monate)')
    message = forms.CharField(required=False, max_length=5000, label='Nachricht', widget=forms.Textarea(attrs={'rows': 4}))


class FinancingSettingsForm(forms.ModelForm):
    class Meta:
        from .models import Homepage
        model = Homepage
        fields = ['financing_annual_rate']
        widgets = {'financing_annual_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '50'})}
