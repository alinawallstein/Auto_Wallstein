"""Validation shared by the slider model and its public presentation."""
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def validate_slide_link(value):
    if not value:
        return
    if any(character.isspace() or ord(character) < 32 for character in value) or '\\' in value:
        raise ValidationError('Bitte einen gültigen Link ohne Leerzeichen eingeben.')
    if value.startswith('/') and not value.startswith('//'):
        return
    URLValidator(schemes=['https', 'http'])(value)
    parsed = urlsplit(value)
    if parsed.username or parsed.password:
        raise ValidationError('Links dürfen keine Zugangsdaten enthalten.')
