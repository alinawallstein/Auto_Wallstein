from django.urls import path

from . import views, catalog_views, content_views

urlpatterns = [
    path("zubehoer/<int:pk>/vorschau/", catalog_views.accessory_preview, name="accessory_preview"),
    path("neuigkeiten/<int:pk>/vorschau/", catalog_views.news_preview, name="news_preview"),
    path("zubehoer/", catalog_views.accessories, name="management_accessories"),
    path("zubehoer/neu/", catalog_views.accessory_edit, name="accessory_create"),
    path("zubehoer/<int:pk>/", catalog_views.accessory_edit, name="accessory_edit"),
    path("zubehoer/<int:pk>/loeschen/", catalog_views.accessory_delete, name="accessory_delete"),
    path("neuigkeiten/", catalog_views.news, name="management_news"),
    path("neuigkeiten/neu/", catalog_views.news_edit, name="news_create"),
    path("neuigkeiten/<int:pk>/", catalog_views.news_edit, name="news_edit"),
    path("neuigkeiten/<int:pk>/loeschen/", catalog_views.news_delete, name="news_delete"),
    path("website/", content_views.homepage_edit, name="homepage_edit"),
    path("website/vorschau/", content_views.homepage_preview, name="homepage_preview"),
    path("", views.dashboard, name="dashboard"),
    path("anmelden/", views.admin_login, name="login"),
    path("abmelden/", views.admin_logout, name="logout"),
    path("fahrzeuge/", views.management_vehicles, name="management_vehicles"),
    path("fahrzeuge/neu/", views.vehicle_create, name="vehicle_create"),
    path("fahrzeuge/<int:pk>/bearbeiten/", views.vehicle_update, name="vehicle_update"),
    path("fahrzeuge/<int:pk>/veroeffentlichung/", views.vehicle_publication, name="vehicle_publication"),
    path("fahrzeuge/<int:pk>/bilder/", views.vehicle_images, name="vehicle_images"),
    path("fahrzeuge/<int:pk>/loeschen/", views.vehicle_delete, name="vehicle_delete"),
]
