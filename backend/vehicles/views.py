from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerInquiryForm, VehicleFilterForm, VehicleForm, VehicleImageActionForm, VehicleImageUploadForm, VehiclePublicationForm
from .models import CustomerInquiry, Vehicle, VehicleImage, VehicleStatus, Homepage
from .selectors import public_news_items, public_vehicles_with_images


from .content import website_content
from .slider import homepage_slides
from .inquiry_mail import send_customer_inquiry_mails
from .management import can_manage
from django.views.decorators.http import require_POST


def public_home(request):
    content = website_content(request)['site_content']
    featured_vehicles = public_vehicles_with_images()[:6]
    latest_news = public_news_items()[:3]
    return render(request, "public/home.html", {"hero_slides": homepage_slides(content), "featured_vehicles": featured_vehicles, "latest_news": latest_news})


def public_vehicles(request):
    base_queryset = public_vehicles_with_images()
    filter_form = VehicleFilterForm(request.GET)
    queryset = base_queryset
    if filter_form.is_valid():
        filters = filter_form.cleaned_data
        lookups = {
            "brand": "brand__icontains", "model": "model__icontains",
            "price_min": "sale_price__gte", "price_max": "sale_price__lte",
            "year_min": "year__gte", "year_max": "year__lte",
            "mileage_max": "mileage__lte", "fuel_type": "fuel_type__icontains",
            "transmission": "transmission__icontains",
        }
        for field, lookup in lookups.items():
            value = filters.get(field)
            if value is not None and value != "":
                queryset = queryset.filter(**{lookup: value})
        ordering = {
            "price_asc": "sale_price", "price_desc": "-sale_price",
            "mileage": "mileage", "newest": "-created_at",
        }
        queryset = queryset.order_by(ordering[filters.get("sort") or "newest"], "pk")
    else:
        queryset = queryset.none()

    context = {
        "vehicles": queryset,
        "filter_form": filter_form,
        "brands": base_queryset.values_list("brand", flat=True).distinct().order_by("brand"),
        "fuel_types": base_queryset.values_list("fuel_type", flat=True).distinct().order_by("fuel_type"),
        "transmissions": base_queryset.values_list("transmission", flat=True).distinct().order_by("transmission"),
        "active_filters": {name: request.GET.get(name, "") for name in filter_form.fields},
    }
    return render(request, "public/vehicles.html", context)


def vehicle_detail(request, pk):
    vehicle = get_object_or_404(public_vehicles_with_images(), pk=pk)
    gallery = vehicle.public_images
    return render(request, "public/vehicle_detail.html", {"vehicle": vehicle, "gallery": gallery})


def about_page(request):
    return render(request, "public/about.html")


def financing_page(request):
    page = Homepage.objects.filter(pk=1).first()
    rate = page.financing_annual_rate if page else None
    return render(request, "public/finanzierung.html", {'financing_rate': rate})


def openings_page(request):
    return render(request, "public/oeffnungszeiten.html")


def service_page(request):
    return render(request, "public/service.html")


def impressum_page(request):
    return render(request, "public/impressum.html")


def datenschutz_page(request):
    return render(request, "public/datenschutz.html")


def contact_page(request):
    inquiry_type = request.GET.get("inquiry_type", "vehicle_request")
    vehicle_id = request.GET.get("vehicle")
    initial = {"inquiry_type": inquiry_type}
    if vehicle_id:
        initial["vehicle"] = vehicle_id

    form = CustomerInquiryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.subject = inquiry.display_subject
        inquiry.save()
        send_customer_inquiry_mails(inquiry, request=request)
        vehicle = inquiry.vehicle
        return render(
            request,
            "public/contact.html",
            {
                "form": CustomerInquiryForm(initial={"inquiry_type": inquiry_type, "vehicle": vehicle.pk if vehicle else None}),
                "success": True,
                "submitted_vehicle": vehicle,
            },
        )

    return render(request, "public/contact.html", {"form": form})


def management_destination(user):
    if can_manage(user):
        return 'dashboard'
    raise PermissionDenied


def admin_login(request):
    if request.user.is_authenticated:
        return redirect(management_destination(request.user))

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        from django.contrib.auth import login

        login(request, form.get_user())
        return redirect(management_destination(request.user))

    return render(request, "management/login.html", {"form": form})


@login_required(login_url="login")
@require_POST
def admin_logout(request):
    logout(request)
    messages.success(request, "Sie wurden erfolgreich abgemeldet.")
    return redirect("login")


@login_required(login_url="login")
@permission_required(('vehicles.view_vehicle', 'vehicles.add_vehicle'), raise_exception=True)
def vehicle_create(request):
    form = VehicleForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        messages.success(request, "Fahrzeug wurde erfolgreich angelegt.")
        if request.user.has_perm("vehicles.change_vehicle"):
            return redirect("vehicle_update", pk=vehicle.pk)
        return redirect("dashboard")
    return render(request, "admin/vehicle_form.html", {"form": form, "title": "Neues Fahrzeug"})


@login_required(login_url="login")
@permission_required(('vehicles.view_vehicle', 'vehicles.change_vehicle'), raise_exception=True)
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehicleForm(request.POST if request.method == "POST" else None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fahrzeug wurde erfolgreich bearbeitet.")
        return redirect("vehicle_update", pk=vehicle.pk)
    return render(request, "admin/vehicle_form.html", {"form": form, "vehicle": vehicle, "title": "Fahrzeug bearbeiten", "active_section": "data", "has_images": vehicle.images.exists()})


@login_required(login_url="login")
@permission_required(('vehicles.view_vehicle', 'vehicles.delete_vehicle'), raise_exception=True)
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Fahrzeug wurde gelöscht.")
        return redirect("dashboard")
    return render(request, "admin/vehicle_confirm_delete.html", {"vehicle": vehicle})


@login_required(login_url="login")
@permission_required(('vehicles.view_vehicle', 'vehicles.change_vehicle'), raise_exception=True)
def vehicle_images(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    upload_form = VehicleImageUploadForm(request.POST or None, request.FILES or None)
    action_form = VehicleImageActionForm(request.POST or None)

    if request.method == "POST":
        if request.FILES.getlist("images") and not request.user.has_perm("vehicles.add_vehicleimage"):
            raise PermissionDenied
        if upload_form.is_valid():
            files = request.FILES.getlist("images")
            for index, uploaded_file in enumerate(files, start=1):
                sort_order = (vehicle.images.count() + index)
                VehicleImage.objects.create(
                    vehicle=vehicle,
                    image=uploaded_file,
                    sort_order=sort_order,
                    is_main=not vehicle.images.exists(),
                )
            messages.success(request, "Bilder wurden erfolgreich hochgeladen.")
            return redirect("vehicle_images", pk=vehicle.pk)

        if action_form.is_valid():
            permission = "vehicles.delete_vehicleimage" if action_form.cleaned_data["action"] == "delete" else "vehicles.change_vehicleimage"
            if not request.user.has_perm(permission):
                raise PermissionDenied
            image_id = action_form.cleaned_data["image_id"]
            action = action_form.cleaned_data["action"]
            image = vehicle.images.filter(pk=image_id).first()
            if not image:
                messages.error(request, "Bild wurde nicht gefunden.")
                return redirect("vehicle_images", pk=vehicle.pk)

            if action == "set_main":
                vehicle.images.update(is_main=False)
                image.is_main = True
                image.save()
                messages.success(request, "Hauptbild wurde aktualisiert.")
            elif action == "delete":
                image.delete()
                remaining = vehicle.images.order_by("sort_order", "created_at")
                for idx, item in enumerate(remaining, start=1):
                    item.sort_order = idx
                    item.save(update_fields=["sort_order"])
                if not vehicle.images.filter(is_main=True).exists() and vehicle.images.exists():
                    first_image = vehicle.images.order_by("sort_order", "created_at").first()
                    first_image.is_main = True
                    first_image.save(update_fields=["is_main"])
                messages.success(request, "Bild wurde gelöscht.")
            elif action == "move_up":
                previous = vehicle.images.filter(sort_order__lt=image.sort_order).order_by("-sort_order").first()
                if previous:
                    image.sort_order, previous.sort_order = previous.sort_order, image.sort_order
                    image.save(update_fields=["sort_order"])
                    previous.save(update_fields=["sort_order"])
                messages.success(request, "Bildreihenfolge wurde angepasst.")
            elif action == "move_down":
                next_image = vehicle.images.filter(sort_order__gt=image.sort_order).order_by("sort_order").first()
                if next_image:
                    image.sort_order, next_image.sort_order = next_image.sort_order, image.sort_order
                    image.save(update_fields=["sort_order"])
                    next_image.save(update_fields=["sort_order"])
                messages.success(request, "Bildreihenfolge wurde angepasst.")

            return redirect("vehicle_images", pk=vehicle.pk)

    images = vehicle.images.order_by("sort_order", "created_at")
    return render(
        request,
        "admin/vehicle_images.html",
        {"vehicle": vehicle, "images": images, "upload_form": upload_form, "action_form": action_form, "active_section": "images"},
    )


@login_required(login_url="login")
@permission_required("vehicles.view_vehicle", raise_exception=True)
def management_vehicles(request):
    queryset = Vehicle.objects.annotate(image_count=Count("images"))
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    visibility = request.GET.get("visibility", "")
    if query:
        queryset = queryset.filter(Q(brand__icontains=query) | Q(model__icontains=query)
                                   | Q(variant__icontains=query) | Q(internal_number__icontains=query))
    if status in VehicleStatus.values:
        queryset = queryset.filter(status=status)
    else:
        status = ""
    public = Q(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)
    if visibility == "public":
        queryset = queryset.filter(public)
    elif visibility == "hidden":
        queryset = queryset.exclude(public)
    else:
        visibility = ""
    page = Paginator(queryset.order_by("-updated_at", "-pk"), 20).get_page(request.GET.get("page"))
    parameters = request.GET.copy()
    parameters.pop("page", None)
    return render(request, "admin/vehicle_list.html", {
        "page_obj": page, "query": query, "selected_status": status,
        "visibility": visibility, "statuses": VehicleStatus.choices,
        "page_query": parameters.urlencode(),
    })


@login_required(login_url="login")
@permission_required(("vehicles.view_vehicle", "vehicles.change_vehicle"), raise_exception=True)
def vehicle_publication(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    form = VehiclePublicationForm(
        request.POST if request.method == "POST" else None,
        initial={"website_enabled": vehicle.is_published and vehicle.public_visible},
    )
    if request.method == "POST" and form.is_valid():
        enabled = form.cleaned_data["website_enabled"]
        vehicle.is_published = enabled
        vehicle.public_visible = enabled
        vehicle.save(update_fields=["is_published", "public_visible", "updated_at"])
        messages.success(request, "Veröffentlichungseinstellungen gespeichert.")
        return redirect("vehicle_publication", pk=vehicle.pk)
    return render(request, "admin/vehicle_publication.html", {
        "vehicle": vehicle, "form": form, "active_section": "publication",
    })
