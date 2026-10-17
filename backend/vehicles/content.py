from django.templatetags.static import static
from .content_schema import TEXT_FIELDS, IMAGE_FIELDS
from .models import Homepage, HomepageImage


def homepage_content(values=None):
    slider_fields = ('slider_interval', 'slider_height', 'slider_mobile_height')
    slider_settings = {name: Homepage._meta.get_field(name).default for name in slider_fields}
    page = Homepage.objects.filter(pk=1).first()
    if page:
        slider_settings.update({name: getattr(page, name) for name in slider_fields})
    if values is None:
        values = page.published if page else {}
    result = {key: values.get(key, default) for key, label, default, group in TEXT_FIELDS}
    image_ids = [values[key] for key, *_ in IMAGE_FIELDS if isinstance(values.get(key), int)]
    images = HomepageImage.objects.in_bulk(image_ids)
    for key, label, fallback, group in IMAGE_FIELDS:
        asset = images.get(values.get(key))
        result[key] = asset.image.url if asset else (static(fallback) if fallback else '')
    result.update(slider_settings)
    return result


def website_content(request):
    if not hasattr(request, '_homepage_content'):
        request._homepage_content = homepage_content()
    return {'site_content': request._homepage_content}
