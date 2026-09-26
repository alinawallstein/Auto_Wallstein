from __future__ import annotations

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone

from .slider_validation import validate_slide_link


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


class InquiryStatus(models.TextChoices):
    NEW = 'new', 'Neu'
    READ = 'read', 'Gelesen'
    IN_PROGRESS = 'in_progress', 'In Bearbeitung'
    ANSWERED = 'answered', 'Beantwortet'
    DONE = 'done', 'Erledigt'


class CustomerInquiry(models.Model):
    status = models.CharField('Status', max_length=20, choices=InquiryStatus.choices, default=InquiryStatus.NEW, db_index=True)
    subject = models.CharField('Betreff', max_length=300, blank=True, editable=False)
    inquiry_type = models.CharField(
        max_length=30,
        choices=[("vehicle_request", "Fahrzeug anfragen"), ("test_drive", "Probefahrt anfragen"), ("financing_request", "Finanzierung anfragen")],
        default="vehicle_request",
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, blank=True, null=True, related_name="inquiries")
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField()
    financing_vehicle_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    financing_downpayment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    financing_term_months = models.PositiveSmallIntegerField(null=True, blank=True, editable=False)
    financing_annual_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, editable=False)
    financing_monthly_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    financing_final_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Kundenanfrage"
        verbose_name_plural = "Kundenanfragen"

    def __str__(self) -> str:
        return f"{self.name} - {self.inquiry_type}"

    @property
    def display_subject(self):
        if self.subject:
            return self.subject
        vehicle = f'{self.vehicle.brand} {self.vehicle.model}' if self.vehicle else ''
        return f'{self.get_inquiry_type_display()}{": " + vehicle if vehicle else ""}'[:300]


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


class Accessory(models.Model):
    class Category(models.TextChoices):
        TIRES = 'tires', 'Reifen'
        WHEELS = 'wheels', 'Felgen & Kompletträder'
        PARTS = 'parts', 'Autoteile'
        OTHER = 'other', 'Zubehör'

    title = models.CharField('Bezeichnung', max_length=160)
    category = models.CharField('Kategorie', max_length=20, choices=Category.choices)
    condition = models.CharField('Zustand', max_length=10, choices=[('new', 'Neu'), ('used', 'Gebraucht')], default='used')
    description = models.TextField('Beschreibung')
    compatibility = models.CharField('Passend für / Maße', max_length=250, blank=True)
    price = models.DecimalField('Preis in Euro', max_digits=10, decimal_places=2)
    status = models.CharField('Verkaufsstatus', max_length=20, choices=[('available', 'Verfügbar'), ('reserved', 'Reserviert'), ('sold', 'Verkauft')], default='available')
    is_published = models.BooleanField('Auf der Website veröffentlichen', default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-pk']
        verbose_name = 'Zubehörangebot'
        verbose_name_plural = 'Zubehörangebote'
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name='accessory_price_nonnegative')]

    def __str__(self):
        return self.title

    @property
    def is_public(self):
        return self.is_published and self.status == 'available'


class AccessoryImage(models.Model):
    accessory = models.ForeignKey(Accessory, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField('Bild', upload_to='accessories/%Y/%m/')
    alt_text = models.CharField('Bildbeschreibung', max_length=200, blank=True)
    sort_order = models.PositiveIntegerField('Reihenfolge (kleinste Zahl = Hauptbild)', default=0)

    class Meta:
        ordering = ['sort_order', 'pk']


class Homepage(models.Model):
    financing_annual_rate = models.DecimalField('Effektiver Jahreszins in Prozent', max_digits=5, decimal_places=2, default='6.99', validators=[MinValueValidator(0), MaxValueValidator(50)], help_text='Zentrale Einstellung für fahrzeugbezogene Finanzierungsrechner.')
    slider_interval = models.PositiveSmallIntegerField('Wechselgeschwindigkeit in Sekunden', default=4,
        validators=[MinValueValidator(2), MaxValueValidator(15)],
        help_text='Zwischen 2 und 15 Sekunden. Änderungen gelten sofort für den Slider.')
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    draft = models.JSONField(default=dict)
    published = models.JSONField(default=dict)
    revision = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Startseite'
        verbose_name_plural = 'Startseite'
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='homepage_singleton'),
                       models.CheckConstraint(condition=models.Q(slider_interval__gte=2, slider_interval__lte=15), name='homepage_slider_interval_range')]
        permissions = [('change_slider_settings', 'Kann Slider-Einstellungen ändern')]


class HomepageImage(models.Model):
    image = models.ImageField(upload_to='homepage/%Y/%m/')


class NewsArticle(models.Model):
    title = models.CharField('Überschrift', max_length=180)
    excerpt = models.CharField('Kurztext', max_length=350)
    body = models.TextField('Beitrag')
    image = models.ImageField('Titelbild', upload_to='news/%Y/%m/', blank=True)
    image_alt = models.CharField('Bildbeschreibung', max_length=200, blank=True)
    is_published = models.BooleanField('Veröffentlichen', default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-pk']
        verbose_name = 'Neuigkeit'
        verbose_name_plural = 'Neuigkeiten'

    def __str__(self):
        return self.title


class HeroSlide(models.Model):
    title = models.CharField('Titel', max_length=180, blank=True)
    subtitle = models.TextField('Untertitel', max_length=500, blank=True)
    image = models.ImageField('Bild', upload_to='homepage/slides/%Y/%m/',
                              help_text='JPEG, PNG oder WebP, höchstens 10 MB. Querformat empfohlen.')
    image_alt = models.CharField('Bildbeschreibung', max_length=200, blank=True,
                                 help_text='Beschreiben Sie das Motiv. Bei rein dekorativen Bildern leer lassen.')
    button_text = models.CharField('Button-Text', max_length=60, blank=True)
    button_url = models.CharField('Button-Link', max_length=500, blank=True,
                                 validators=[validate_slide_link],
                                 help_text='Interner Pfad wie /fahrzeuge/ oder vollständiger https://-Link.')
    sort_order = models.PositiveIntegerField('Reihenfolge', default=0,
                                            help_text='Kleinere Zahlen erscheinen zuerst.')
    is_active = models.BooleanField('Aktiv', default=False,
                                    help_text='Aktive Slides sind nach dem Speichern sofort öffentlich sichtbar.')
    created_at = models.DateTimeField('Erstellt', auto_now_add=True)
    updated_at = models.DateTimeField('Geändert', auto_now=True)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Startseiten-Slide'
        verbose_name_plural = 'Startseiten-Slides'

    def __str__(self):
        return self.title or f'Slide {self.pk or "(neu)"}'

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if bool(self.button_text) != bool(self.button_url):
            raise ValidationError('Für einen Button bitte Text und Link ausfüllen oder beide Felder leer lassen.')


class InquiryReply(models.Model):
    class Status(models.TextChoices):
        SENDING = 'sending', 'Versand läuft / Ergebnis offen'
        SENT = 'sent', 'An Mailserver übergeben'
        FAILED = 'failed', 'Versand fehlgeschlagen'
        TEST = 'test', 'Nur im Testbetrieb protokolliert'

    inquiry = models.ForeignKey(CustomerInquiry, on_delete=models.CASCADE, related_name='replies')
    body = models.TextField('Antworttext', max_length=10000)
    recipient = models.EmailField('Empfänger', editable=False)
    subject = models.CharField('Betreff', max_length=320, editable=False)
    status = models.CharField('Versandstatus', max_length=16, choices=Status.choices, default=Status.SENDING)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField('Erstellt', auto_now_add=True)
    sent_at = models.DateTimeField('Versanddatum', null=True, blank=True)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Antwort auf Kundenanfrage'
        verbose_name_plural = 'Antwortverlauf'

    def __str__(self):
        return f'Antwort zu Anfrage {self.inquiry_id}'
