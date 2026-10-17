from django import forms
from django.core.exceptions import ValidationError

from .catalog_forms import validate_photo
from .models import HeroSlide, Homepage


class HeroSlideForm(forms.ModelForm):
    image = forms.ImageField(label='Bild', validators=[validate_photo],
                             help_text='JPEG, PNG oder WebP, höchstens 10 MB. Querformat empfohlen.')

    class Meta:
        model = HeroSlide
        fields = ['title', 'subtitle', 'image', 'crop_x', 'crop_y', 'crop_width', 'crop_height', 'image_scale', 'image_offset_x', 'image_offset_y', 'mobile_crop_x', 'mobile_crop_y', 'mobile_crop_width', 'mobile_crop_height', 'mobile_image_scale', 'mobile_image_offset_x', 'mobile_image_offset_y', 'image_alt', 'button_text', 'button_url', 'sort_order', 'is_active']
        widgets = {'subtitle': forms.Textarea(attrs={'rows': 3})}

    crop_x = forms.DecimalField(min_value=0, max_value=100, max_digits=6, decimal_places=3, initial=0, widget=forms.HiddenInput())
    crop_y = forms.DecimalField(min_value=0, max_value=100, max_digits=6, decimal_places=3, initial=0, widget=forms.HiddenInput())
    crop_width = forms.DecimalField(min_value=0.1, max_value=100, max_digits=6, decimal_places=3, initial=100, widget=forms.HiddenInput())
    crop_height = forms.DecimalField(min_value=0.1, max_value=100, max_digits=6, decimal_places=3, initial=100, widget=forms.HiddenInput())
    image_scale = forms.DecimalField(min_value=0.6, max_value=1.3, max_digits=4, decimal_places=2, initial=1, widget=forms.HiddenInput())
    image_offset_x = forms.DecimalField(min_value=-50, max_value=50, max_digits=5, decimal_places=2, initial=0, widget=forms.HiddenInput())
    image_offset_y = forms.DecimalField(min_value=-50, max_value=50, max_digits=5, decimal_places=2, initial=0, widget=forms.HiddenInput())
    mobile_crop_x = forms.DecimalField(min_value=0, max_value=100, max_digits=6, decimal_places=3, initial=0, widget=forms.HiddenInput())
    mobile_crop_y = forms.DecimalField(min_value=0, max_value=100, max_digits=6, decimal_places=3, initial=0, widget=forms.HiddenInput())
    mobile_crop_width = forms.DecimalField(min_value=0.1, max_value=100, max_digits=6, decimal_places=3, initial=100, widget=forms.HiddenInput())
    mobile_crop_height = forms.DecimalField(min_value=0.1, max_value=100, max_digits=6, decimal_places=3, initial=100, widget=forms.HiddenInput())
    mobile_image_scale = forms.DecimalField(min_value=0.6, max_value=1.3, max_digits=4, decimal_places=2, initial=1, widget=forms.HiddenInput())
    mobile_image_offset_x = forms.DecimalField(min_value=-50, max_value=50, max_digits=5, decimal_places=2, initial=0, widget=forms.HiddenInput())
    mobile_image_offset_y = forms.DecimalField(min_value=-50, max_value=50, max_digits=5, decimal_places=2, initial=0, widget=forms.HiddenInput())

    def clean(self):
        cleaned = super().clean()
        x, y = cleaned.get('crop_x'), cleaned.get('crop_y')
        width, height = cleaned.get('crop_width'), cleaned.get('crop_height')
        if None not in (x, y, width, height) and (x + width > 100 or y + height > 100):
            raise ValidationError('Der Ausschnitt muss innerhalb des Originalbildes liegen.')
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
        for name in ('crop_x', 'crop_y', 'crop_width', 'crop_height', 'image_scale', 'image_offset_x', 'image_offset_y', 'mobile_crop_x', 'mobile_crop_y', 'mobile_crop_width', 'mobile_crop_height', 'mobile_image_scale', 'mobile_image_offset_x', 'mobile_image_offset_y'):
            if name in self.fields:
                self.fields[name].widget = forms.HiddenInput()

class SliderSettingsForm(forms.ModelForm):
    class Meta:
        model = Homepage
        fields = ['slider_interval', 'slider_height', 'slider_mobile_height']
        widgets = {name: forms.NumberInput(attrs={'class': 'form-control'})
                   for name in ['slider_interval', 'slider_height', 'slider_mobile_height']}
