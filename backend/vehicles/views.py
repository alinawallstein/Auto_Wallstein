from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render

from .forms import CustomerInquiryForm, VehicleForm, VehicleImageActionForm, VehicleImageUploadForm
from .models import CustomerInquiry, Vehicle, VehicleImage, VehicleStatus


def public_home(request):
    featured_vehicles = Vehicle.objects.filter(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)[:6]
    return render(request, "public/home.html", {"featured_vehicles": featured_vehicles})


def public_vehicles(request):
    queryset = Vehicle.objects.filter(is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE)

    brand = request.GET.get("brand")
    model = request.GET.get("model")
    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")
    year_min = request.GET.get("year_min")
    year_max = request.GET.get("year_max")
    mileage_max = request.GET.get("mileage_max")
    fuel_type = request.GET.get("fuel_type")
    transmission = request.GET.get("transmission")
    sort = request.GET.get("sort", "newest")

    if brand:
        queryset = queryset.filter(brand__icontains=brand)
    if model:
        queryset = queryset.filter(model__icontains=model)
    if price_min:
        queryset = queryset.filter(sale_price__gte=price_min)
    if price_max:
        queryset = queryset.filter(sale_price__lte=price_max)
    if year_min:
        queryset = queryset.filter(year__gte=year_min)
    if year_max:
        queryset = queryset.filter(year__lte=year_max)
    if mileage_max:
        queryset = queryset.filter(mileage__lte=mileage_max)
    if fuel_type:
        queryset = queryset.filter(fuel_type__icontains=fuel_type)
    if transmission:
        queryset = queryset.filter(transmission__icontains=transmission)

    if sort == "price_asc":
        queryset = queryset.order_by("sale_price")
    elif sort == "price_desc":
        queryset = queryset.order_by("-sale_price")
    elif sort == "mileage":
        queryset = queryset.order_by("mileage")
    else:
        queryset = queryset.order_by("-created_at")

    context = {
        "vehicles": queryset,
        "brands": queryset.values_list("brand", flat=True).distinct().order_by("brand"),
        "models": queryset.values_list("model", flat=True).distinct().order_by("model"),
        "fuel_types": queryset.values_list("fuel_type", flat=True).distinct().order_by("fuel_type"),
        "transmissions": queryset.values_list("transmission", flat=True).distinct().order_by("transmission"),
        "active_filters": {
            "brand": brand,
            "model": model,
            "price_min": price_min,
            "price_max": price_max,
            "year_min": year_min,
            "year_max": year_max,
            "mileage_max": mileage_max,
            "fuel_type": fuel_type,
            "transmission": transmission,
            "sort": sort,
        },
    }
    return render(request, "public/vehicles.html", context)


def vehicle_detail(request, pk):
    vehicle = Vehicle.objects.filter(pk=pk, is_published=True, public_visible=True, status=VehicleStatus.AVAILABLE).first()
    if not vehicle:
        return redirect("public_vehicles")
    gallery = vehicle.images.order_by("sort_order", "created_at")
    return render(request, "public/vehicle_detail.html", {"vehicle": vehicle, "gallery": gallery})


def about_page(request):
    return render(request, "public/about.html")


def ueberuns_page(request):
    return render(request, "public/about.html")


def financing_page(request):
    return render(request, "public/finanzierung.html")


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
        inquiry = form.save()
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


def admin_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        from django.contrib.auth import login

        login(request, form.get_user())
        return redirect("dashboard")

    return render(request, "admin/login.html", {"form": form})


@login_required(login_url="login")
def admin_logout(request):
    logout(request)
    messages.success(request, "Sie wurden erfolgreich abgemeldet.")
    return redirect("login")


@login_required(login_url="login")
def dashboard(request):
    vehicles = Vehicle.objects.all()
    stats = {
        "total": vehicles.count(),
        "available": vehicles.filter(status=VehicleStatus.AVAILABLE).count(),
        "in_preparation": vehicles.filter(status=VehicleStatus.IN_PREPARATION).count(),
        "reserved": vehicles.filter(status=VehicleStatus.RESERVED).count(),
        "sold": vehicles.filter(status=VehicleStatus.SOLD).count(),
    }
    recent = vehicles.order_by("-updated_at")[:5]
    return render(request, "admin/dashboard.html", {"stats": stats, "recent_vehicles": recent})


@login_required(login_url="login")
def vehicle_create(request):
    form = VehicleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        vehicle = form.save()
        messages.success(request, "Fahrzeug wurde erfolgreich angelegt.")
        return redirect("vehicle_images", pk=vehicle.pk)
    return render(request, "admin/vehicle_form.html", {"form": form, "title": "Neues Fahrzeug"})


@login_required(login_url="login")
def vehicle_update(request, pk):
    vehicle = Vehicle.objects.get(pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Fahrzeug wurde erfolgreich bearbeitet.")
        return redirect("vehicle_images", pk=vehicle.pk)
    return render(request, "admin/vehicle_form.html", {"form": form, "title": "Fahrzeug bearbeiten"})


@login_required(login_url="login")
def vehicle_delete(request, pk):
    vehicle = Vehicle.objects.get(pk=pk)
    if request.method == "POST":
        vehicle.delete()
        messages.success(request, "Fahrzeug wurde gelöscht.")
        return redirect("dashboard")
    return render(request, "admin/vehicle_confirm_delete.html", {"vehicle": vehicle})


@login_required(login_url="login")
def vehicle_images(request, pk):
    vehicle = Vehicle.objects.get(pk=pk)
    upload_form = VehicleImageUploadForm(request.POST or None, request.FILES or None)
    action_form = VehicleImageActionForm(request.POST or None)

    if request.method == "POST":
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
        {"vehicle": vehicle, "images": images, "upload_form": upload_form, "action_form": action_form},
    )
