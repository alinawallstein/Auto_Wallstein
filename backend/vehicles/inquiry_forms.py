import uuid

from django import forms

from .models import CustomerInquiry, InquiryStatus


class InquiryFilterForm(forms.Form):
    q = forms.CharField(label='Name, E-Mail, Betreff oder Fahrzeug', required=False, max_length=200,
                        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'search'}))
    status = forms.ChoiceField(label='Status', required=False,
        choices=[('', 'Alle')] + list(InquiryStatus.choices), widget=forms.Select(attrs={'class': 'form-select'}))
    inquiry_type = forms.ChoiceField(label='Anfragetyp', required=False,
        choices=[('', 'Alle Anfragetypen')] + list(CustomerInquiry._meta.get_field('inquiry_type').choices),
        widget=forms.Select(attrs={'class': 'form-select'}))
    order = forms.ChoiceField(label='Sortierung', required=False,
        choices=[('newest', 'Neueste zuerst'), ('oldest', 'Älteste zuerst')],
        widget=forms.Select(attrs={'class': 'form-select'}))


class InquiryStatusForm(forms.Form):
    status = forms.ChoiceField(label='Status', choices=InquiryStatus.choices,
                               widget=forms.Select(attrs={'class': 'form-select'}))


class InquiryReplyForm(forms.Form):
    request_id = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput())
    body = forms.CharField(label='Ihre Antwort', max_length=10000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 8}))
