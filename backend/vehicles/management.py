from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from datetime import timedelta

from django.db.models import Count, Q, Prefetch
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import CustomerInquiry, HeroSlide, InquiryStatus, NewsArticle, Vehicle, VehicleImage, VehicleStatus

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
        context['recent_vehicles'] = Vehicle.objects.prefetch_related(Prefetch(
            'images', queryset=VehicleImage.objects.order_by('-is_main', 'sort_order', 'created_at'),
            to_attr='dashboard_images',
        )).order_by('-created_at', '-pk')[:5]
        vehicle_status_counts = dict(Vehicle.objects.values_list('status').annotate(count=Count('pk')))
        context['vehicle_statuses'] = [
            {'label': label, 'count': vehicle_status_counts.get(value, 0)}
            for value, label in VehicleStatus.choices
        ]
        fuel_stats = list(
            Vehicle.objects.values('fuel_type').annotate(count=Count('pk')).order_by('-count', 'fuel_type')
        )
        if len(fuel_stats) > 5:
            fuel_stats = fuel_stats[:4] + [{
                'fuel_type': 'Weitere', 'count': sum(item['count'] for item in fuel_stats[4:]),
            }]
        context['fuel_stats'] = fuel_stats
    if request.user.has_perm('vehicles.view_customerinquiry'):
        context['inquiry_stats'] = CustomerInquiry.objects.aggregate(
            total=Count('pk'), new=Count('pk', filter=Q(status=InquiryStatus.NEW)),
            answered=Count('pk', filter=Q(status=InquiryStatus.ANSWERED)),
            open=Count('pk', filter=Q(status__in=[InquiryStatus.NEW, InquiryStatus.READ, InquiryStatus.IN_PROGRESS])),
            financing_new=Count('pk', filter=Q(inquiry_type='financing_request', status=InquiryStatus.NEW)),
        )
        context['recent_inquiries'] = CustomerInquiry.objects.select_related('vehicle').order_by('-created_at', '-pk')[:5]
        context['recent_financing'] = CustomerInquiry.objects.filter(
            inquiry_type='financing_request'
        ).select_related('vehicle').order_by('-created_at', '-pk')[:4]
        today = timezone.localdate()
        start_date = today - timedelta(days=29)
        inquiry_counts = dict(
            CustomerInquiry.objects.filter(created_at__date__gte=start_date, created_at__date__lte=today)
            .annotate(day=TruncDate('created_at', tzinfo=timezone.get_current_timezone()))
            .values_list('day').annotate(count=Count('pk'))
        )
        max_daily_count = max(inquiry_counts.values(), default=0)
        context['inquiry_activity'] = [
            {'date': start_date + timedelta(days=offset),
             'count': inquiry_counts.get(start_date + timedelta(days=offset), 0),
             'percent': round(inquiry_counts.get(start_date + timedelta(days=offset), 0) * 100 / max_daily_count) if max_daily_count else 0}
            for offset in range(30)
        ]
        status_counts = dict(CustomerInquiry.objects.values_list('status').annotate(count=Count('pk')))
        context['inquiry_statuses'] = [
            {'value': value, 'label': label, 'count': status_counts.get(value, 0)}
            for value, label in InquiryStatus.choices
        ]
    if request.user.has_perm('vehicles.view_newsarticle'):
        today = timezone.now()
        context['news_stats'] = NewsArticle.objects.aggregate(
            total=Count('pk'),
            published=Count('pk', filter=Q(status=NewsArticle.Status.PUBLISHED, published_at__lte=today)),
            drafts=Count('pk', filter=Q(status=NewsArticle.Status.DRAFT)),
            scheduled=Count('pk', filter=Q(status=NewsArticle.Status.PUBLISHED, published_at__gt=today)),
        )
        context['recent_news'] = NewsArticle.objects.order_by('-updated_at', '-pk')[:4]
    if request.user.has_perm('vehicles.view_heroslide'):
        context['slide_stats'] = HeroSlide.objects.aggregate(total=Count('pk'), active=Count('pk', filter=Q(is_active=True)))
    return render(request, 'admin/dashboard.html', context)
