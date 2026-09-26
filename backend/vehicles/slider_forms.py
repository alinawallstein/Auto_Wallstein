from django import forms

from .catalog_forms import validate_photo
from .models import HeroSlide, Homepage


class HeroSlideForm(forms.ModelForm):
    image = forms.ImageField(label='Bild', validators=[validate_photo],
                             help_text='JPEG, PNG oder WebP, höchstens 10 MB. Querformat empfohlen.')

    class Meta:
        model = HeroSlide
        fields = ['title', 'subtitle', 'image', 'image_alt', 'button_text', 'button_url', 'sort_order', 'is_active']
        widgets = {'subtitle': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'


class SliderSettingsForm(forms.ModelForm):
    class Meta:
        model = Homepage
        fields = ['slider_interval']
        widgets = {'slider_interval': forms.NumberInput(attrs={'class': 'form-control'})}
