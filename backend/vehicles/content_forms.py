from django import forms
from .content_schema import TEXT_FIELDS, IMAGE_FIELDS
from .catalog_forms import validate_photo
from .content import homepage_content


class HomepageForm(forms.Form):
    revision = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, page, **kwargs):
        self.page = page
        initial = {'revision': page.revision}
        initial.update({key: page.draft.get(key, default) for key, label, default, group in TEXT_FIELDS})
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        for key, label, default, group in TEXT_FIELDS:
            field = forms.EmailField if key == 'email' else forms.CharField
            widget = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}) if len(default) > 100 else forms.TextInput(attrs={'class': 'form-control'})
            self.fields[key] = field(label=label, max_length=4000 if len(default) > 100 else 250, widget=widget)
        self.fields['phone'] = forms.RegexField(r'^\+?[0-9 ()/\-]{5,40}$', label='Telefonnummer', widget=forms.TextInput(attrs={'class': 'form-control'}))
        image_previews = homepage_content(page.draft)
        for key, label, fallback, group in IMAGE_FIELDS:
            self.fields[key] = forms.ImageField(label=label + ' ersetzen', required=False, validators=[validate_photo])
            self.fields[key].current_image_url = image_previews[key]
            self.fields[key + '_reset'] = forms.BooleanField(label='Originalbild wiederherstellen' if fallback else 'Bild entfernen', required=False)

    def groups(self):
        groups = {}
        for key, label, default, group in TEXT_FIELDS:
            groups.setdefault(group, []).append(self[key])
        for key, label, fallback, group in IMAGE_FIELDS:
            groups.setdefault(group, []).extend([self[key], self[key + '_reset']])
        return groups.items()
