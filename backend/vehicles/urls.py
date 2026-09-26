from django.urls import include, path

from . import views, catalog_views
from .redirects import canonical_redirect

urlpatterns = [
    path("zubehoer/", catalog_views.public_accessories, name="public_accessories"),
    path("zubehoer/<int:pk>/", catalog_views.accessory_detail, name="accessory_detail"),
    path("aktuelles/", catalog_views.public_news, name="public_news"),
    path("aktuelles/<slug:slug>/", catalog_views.news_detail, name="news_detail"),
    path("", views.public_home, name="home"),
    path("fahrzeuge/", views.public_vehicles, name="public_vehicles"),
    path("fahrzeuge/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("ueberuns/", views.about_page, name="ueberuns"),
    path("finanzierung/", views.financing_page, name="finanzierung"),
    path("oeffnungszeiten/", views.openings_page, name="oeffnungszeiten"),
    path("service/", views.service_page, name="service"),
    path("kontakt/", views.contact_page, name="kontakt"),
    path("impressum/", views.impressum_page, name="impressum"),
    path("datenschutz/", views.datenschutz_page, name="datenschutz"),
    path("verwaltung/", include("vehicles.urls_management")),
    # Retain old route names for external callers; internal links use canonical names.
    path("vehicles/", canonical_redirect, {"route_name": "public_vehicles"}, name="public_vehicles_legacy"),
    path("contact/", canonical_redirect, {"route_name": "kontakt"}, name="contact"),
    path("about/", canonical_redirect, {"route_name": "ueberuns"}, name="about"),
    path("login/", canonical_redirect, {"route_name": "login"}),
    path("logout/", canonical_redirect, {"route_name": "logout"}),
    path("dashboard/", canonical_redirect, {"route_name": "dashboard"}),
    path("fahrzeuge/neu/", canonical_redirect, {"route_name": "vehicle_create"}),
    path("fahrzeuge/<int:pk>/bearbeiten/", canonical_redirect, {"route_name": "vehicle_update"}),
    path("fahrzeuge/<int:pk>/bilder/", canonical_redirect, {"route_name": "vehicle_images"}),
    path("fahrzeuge/<int:pk>/loeschen/", canonical_redirect, {"route_name": "vehicle_delete"}),
]
