from django.db.models import Prefetch

from .models import Vehicle, VehicleImage, VehicleStatus


def public_vehicles():
    return Vehicle.objects.filter(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)


def public_vehicles_with_images():
    return public_vehicles().prefetch_related(Prefetch(
        "images", queryset=VehicleImage.objects.order_by("-is_main", "sort_order", "created_at", "pk"),
        to_attr="public_images",
    ))
