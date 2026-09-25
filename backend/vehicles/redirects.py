from django.http import HttpResponseRedirect
from django.urls import reverse


def canonical_redirect(request, route_name, **kwargs):
    """Keep old URLs usable, preserving submitted bodies on non-GET requests."""
    target = reverse(route_name, kwargs=kwargs)
    query = request.META.get("QUERY_STRING", "")
    if query:
        target += "?" + query
    status = 301 if request.method in {"GET", "HEAD"} else 307
    return HttpResponseRedirect(target, status=status)
