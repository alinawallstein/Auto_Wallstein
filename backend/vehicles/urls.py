from django.urls import path

from . import views

urlpatterns = [
    path("", views.public_home, name="home"),
    path("login/", views.admin_login, name="login"),
    path("logout/", views.admin_logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("fahrzeuge/", views.public_vehicles, name="public_vehicles"),
    path("fahrzeuge/neu/", views.vehicle_create, name="vehicle_create"),
    path("fahrzeuge/<int:pk>/", views.vehicle_detail, name="vehicle_detail"),
    path("fahrzeuge/<int:pk>/bearbeiten/", views.vehicle_update, name="vehicle_update"),
    path("fahrzeuge/<int:pk>/bilder/", views.vehicle_images, name="vehicle_images"),
    path("fahrzeuge/<int:pk>/loeschen/", views.vehicle_delete, name="vehicle_delete"),
    path("vehicles/", views.public_vehicles, name="public_vehicles_legacy"),
    path("ueberuns/", views.ueberuns_page, name="ueberuns"),
    path("finanzierung/", views.financing_page, name="finanzierung"),
    path("oeffnungszeiten/", views.openings_page, name="oeffnungszeiten"),
    path("service/", views.service_page, name="service"),
    path("kontakt/", views.contact_page, name="kontakt"),
    path("impressum/", views.impressum_page, name="impressum"),
    path("datenschutz/", views.datenschutz_page, name="datenschutz"),
    path("contact/", views.contact_page, name="contact"),
    path("about/", views.about_page, name="about"),
]
