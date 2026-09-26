from django import forms
from django.forms import inlineformset_factory
from .models import Accessory, AccessoryImage, NewsArticle


def validate_photo(upload):
    if upload.size > 10 * 1024 * 1024:
        raise forms.ValidationError('Bitte ein Bild mit höchstens 10 MB auswählen.')
    if getattr(upload, 'image', None) and upload.image.format not in {'JPEG', 'PNG', 'WEBP'}:
        raise forms.ValidationError('Bitte ein JPEG-, PNG- oder WebP-Bild verwenden.')


class AccessoryForm(forms.ModelForm):
    class Meta:
        model = Accessory
        fields = ['title', 'category', 'condition', 'price', 'compatibility', 'description', 'status', 'is_published']
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
        self.fields['price'].min_value = 0

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Der Preis darf nicht negativ sein.')
        return price


class AccessoryImageForm(forms.ModelForm):
    image = forms.ImageField(label='Bild', required=False, validators=[validate_photo])

    class Meta:
        model = AccessoryImage
        fields = ['image', 'alt_text', 'sort_order']

    def clean(self):
        data = super().clean()
        if not data.get('DELETE') and not data.get('image'):
            self.add_error('image', 'Bitte ein Bild auswählen.')
        return data


AccessoryImages = inlineformset_factory(Accessory, AccessoryImage, form=AccessoryImageForm,
                                       extra=3, max_num=12, validate_max=True, can_delete=True)


class NewsArticleForm(forms.ModelForm):
    image = forms.ImageField(label='Titelbild', required=False, validators=[validate_photo])

    class Meta:
        model = NewsArticle
        fields = ['title', 'excerpt', 'body', 'image', 'image_alt', 'is_published']
        widgets = {'body': forms.Textarea(attrs={'rows': 12})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
