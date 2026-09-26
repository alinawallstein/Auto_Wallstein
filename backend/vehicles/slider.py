"""Build the homepage slider context with one ordered database query."""
from django.core.exceptions import ValidationError
from django.templatetags.static import static
from django.urls import reverse

from .models import HeroSlide
from .slider_validation import validate_slide_link


def homepage_slides(content):
    slides = []
    for slide in HeroSlide.objects.filter(is_active=True):
        link = slide.button_url
        try:
            validate_slide_link(link)
        except ValidationError:
            link = ''
        slides.append({
            'title': slide.title,
            'subtitle': slide.subtitle,
            'image_url': slide.image.url if slide.image else '',
            'image_alt': slide.image_alt,
            'button_text': slide.button_text if link else '',
            'button_url': link,
        })
    return slides or [{
        'title': content['hero_title'],
        'subtitle': content['hero_text'],
        'image_url': static('images/titelbild.jpeg'),
        'image_alt': '',
        'button_text': content['hero_button'],
        'button_url': reverse('public_vehicles'),
    }]
