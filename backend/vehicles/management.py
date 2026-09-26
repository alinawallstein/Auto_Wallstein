from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from .models import CustomerInquiry, HeroSlide, InquiryStatus, Vehicle, VehicleStatus

MANAGEMENT_PERMISSIONS = (
    'vehicles.view_vehicle', 'vehicles.view_customerinquiry', 'vehicles.view_accessory',
    'vehicles.view_newsarticle', 'vehicles.change_homepage', 'vehicles.view_heroslide',
    'vehicles.change_slider_settings',
)


def can_manage(user):
    return any(user.has_perm(permission) for permission in MANAGEMENT_PERMISSIONS)


@never_cache
@login_required
def dashboard(request):
    if not can_manage(request.user):
        raise PermissionDenied
    context = {}
    if request.user.has_perm('vehicles.view_vehicle'):
        context['stats'] = Vehicle.objects.aggregate(
            total=Count('pk'),
            available=Count('pk', filter=Q(status=VehicleStatus.AVAILABLE)),
            public=Count('pk', filter=Q(status=VehicleStatus.AVAILABLE, is_published=True, public_visible=True)),
        )
        context['recent_vehicles'] = Vehicle.objects.order_by('-updated_at', '-pk')[:5]
    if request.user.has_perm('vehicles.view_customerinquiry'):
        context['inquiry_stats'] = CustomerInquiry.objects.aggregate(
            total=Count('pk'), new=Count('pk', filter=Q(status=InquiryStatus.NEW)),
            answered=Count('pk', filter=Q(status=InquiryStatus.ANSWERED)),
            open=Count('pk', filter=Q(status__in=[InquiryStatus.NEW, InquiryStatus.READ, InquiryStatus.IN_PROGRESS])),
        )
        context['recent_inquiries'] = CustomerInquiry.objects.select_related('vehicle').order_by('-created_at', '-pk')[:5]
    if request.user.has_perm('vehicles.view_heroslide'):
        context['slide_stats'] = HeroSlide.objects.aggregate(total=Count('pk'), active=Count('pk', filter=Q(is_active=True)))
    return render(request, 'admin/dashboard.html', context)
