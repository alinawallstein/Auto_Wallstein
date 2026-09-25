from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("anmelden/", views.admin_login, name="login"),
    path("abmelden/", views.admin_logout, name="logout"),
    path("fahrzeuge/neu/", views.vehicle_create, name="vehicle_create"),
    path("fahrzeuge/<int:pk>/bearbeiten/", views.vehicle_update, name="vehicle_update"),
    path("fahrzeuge/<int:pk>/bilder/", views.vehicle_images, name="vehicle_images"),
    path("fahrzeuge/<int:pk>/loeschen/", views.vehicle_delete, name="vehicle_delete"),
]
