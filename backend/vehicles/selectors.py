from django.db.models import Prefetch, Q
from django.utils import timezone

from .models import NewsArticle, Vehicle, VehicleImage, VehicleStatus


def public_vehicles():
    return Vehicle.objects.filter(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)


def public_vehicles_with_images():
    return public_vehicles().prefetch_related(Prefetch(
        "images", queryset=VehicleImage.objects.order_by("-is_main", "sort_order", "created_at", "pk"),
        to_attr="public_images",
    ))


def public_news_items():
    now = timezone.now()
    return NewsArticle.objects.filter(
        status=NewsArticle.Status.PUBLISHED,
        published_at__lte=now,
    ).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.localdate()))
