from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class VehicleStatus(models.TextChoices):
    IN_PREPARATION = "in_preparation", "In Vorbereitung"
    AVAILABLE = "available", "Verfügbar"
    RESERVED = "reserved", "Reserviert"
    SOLD = "sold", "Verkauft"


class Vehicle(models.Model):
    internal_number = models.CharField(max_length=50, unique=True, verbose_name="Interne Fahrzeugnummer")
    brand = models.CharField(max_length=100, verbose_name="Marke")
    model = models.CharField(max_length=120, verbose_name="Modell")
    variant = models.CharField(max_length=150, blank=True, verbose_name="Variante / Modellbezeichnung")
    vehicle_type = models.CharField(max_length=80, verbose_name="Fahrzeugtyp")
    first_registration = models.DateField(verbose_name="Erstzulassung")
    year = models.PositiveIntegerField(verbose_name="Baujahr")
    mileage = models.PositiveIntegerField(verbose_name="Kilometerstand")
    fuel_type = models.CharField(max_length=60, verbose_name="Kraftstoffart")
    transmission = models.CharField(max_length=50, verbose_name="Getriebe")
    power_kw = models.PositiveIntegerField(verbose_name="Leistung kW")
    power_ps = models.PositiveIntegerField(verbose_name="Leistung PS")
    engine_capacity = models.PositiveIntegerField(verbose_name="Hubraum")
    doors = models.PositiveIntegerField(verbose_name="Anzahl Türen")
    seats = models.PositiveIntegerField(verbose_name="Anzahl Sitzplätze")
    exterior_color = models.CharField(max_length=80, verbose_name="Außenfarbe")
    interior_equipment = models.CharField(max_length=200, blank=True, verbose_name="Innenausstattung")
    vin = models.CharField(max_length=50, blank=True, verbose_name="FIN / Fahrgestellnummer")
    previous_owners = models.PositiveIntegerField(default=0, verbose_name="Anzahl Vorbesitzer")
    hu_valid_until = models.DateField(blank=True, null=True, verbose_name="HU gültig bis")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Einkaufspreis")
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Verkaufspreis")
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    equipment = models.TextField(blank=True, verbose_name="Ausstattung")
    status = models.CharField(
        max_length=30,
        choices=VehicleStatus.choices,
        default=VehicleStatus.IN_PREPARATION,
        verbose_name="Status",
    )
    is_published = models.BooleanField(default=False, verbose_name="Veröffentlicht")
    public_visible = models.BooleanField(default=False, verbose_name="Öffentlich sichtbar")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Datum der Aufnahme")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Datum der letzten Änderung")

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Fahrzeug"
        verbose_name_plural = "Fahrzeuge"

    def __str__(self) -> str:
        return f"{self.brand} {self.model} ({self.internal_number})"

    @property
    def is_publicly_listed(self) -> bool:
        return self.is_published and self.public_visible and self.status == VehicleStatus.AVAILABLE


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="vehicles/%Y/%m/%d/", verbose_name="Bild")
    alt_text = models.CharField(max_length=200, blank=True, verbose_name="Alt-Text")
    is_main = models.BooleanField(default=False, verbose_name="Hauptbild")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "Fahrzeugbild"
        verbose_name_plural = "Fahrzeugbilder"

    def __str__(self) -> str:
        return f"{self.vehicle} - Bild {self.sort_order}"


class CustomerInquiry(models.Model):
    inquiry_type = models.CharField(
        max_length=30,
        choices=[("vehicle_request", "Fahrzeug anfragen"), ("test_drive", "Probefahrt anfragen")],
        default="vehicle_request",
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, blank=True, null=True, related_name="inquiries")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kundenanfrage"
        verbose_name_plural = "Kundenanfragen"

    def __str__(self) -> str:
        return f"{self.name} - {self.inquiry_type}"


class VehicleAIText(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="ai_texts")
    text_type = models.CharField(
        max_length=40,
        choices=[
            ("short_description", "Kurze Fahrzeugbeschreibung"),
            ("long_description", "Ausführliche Fahrzeugbeschreibung"),
            ("seo_text", "SEO-Text"),
            ("social_text", "Social-Media-Text"),
            ("translation_de", "Übersetzung Deutsch"),
            ("translation_en", "Übersetzung Englisch"),
            ("translation_es", "Übersetzung Spanisch"),
        ],
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "KI-Text"
        verbose_name_plural = "KI-Texte"

    def __str__(self) -> str:
        return f"{self.vehicle} - {self.text_type}"
