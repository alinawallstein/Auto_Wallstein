from django.templatetags.static import static
from .content_schema import TEXT_FIELDS, IMAGE_FIELDS
from .models import Homepage, HomepageImage


def homepage_content(values=None):
    interval = Homepage._meta.get_field("slider_interval").default
    if values is None:
        page = Homepage.objects.filter(pk=1).first()
        values = page.published if page else {}
        interval = page.slider_interval if page else interval
    result = {key: values.get(key, default) for key, label, default, group in TEXT_FIELDS}
    image_ids = [values[key] for key, *_ in IMAGE_FIELDS if isinstance(values.get(key), int)]
    images = HomepageImage.objects.in_bulk(image_ids)
    for key, label, fallback, group in IMAGE_FIELDS:
        asset = images.get(values.get(key))
        result[key] = asset.image.url if asset else (static(fallback) if fallback else '')
    result["slider_interval"] = interval
    return result


def website_content(request):
    if not hasattr(request, '_homepage_content'):
        request._homepage_content = homepage_content()
    return {'site_content': request._homepage_content}
