from __future__ import annotations

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone
from django.utils.text import slugify
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

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
    year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Baujahr")
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
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Einkaufspreis")
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
    class Type(models.TextChoices):
        NEWS = 'news', 'News'
        VEHICLE = 'vehicle', 'Neues Fahrzeug'
        OFFER = 'offer', 'Angebot / Aktion'
        COMPANY = 'company', 'Unternehmen'
        EVENT = 'event', 'Event'
        NOTICE = 'notice', 'Hinweis'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Entwurf'
        PUBLISHED = 'published', 'Veröffentlicht'
        ARCHIVED = 'archived', 'Archiviert'

    type = models.CharField('News-Typ', max_length=12, choices=Type.choices, default=Type.NEWS)
    title = models.CharField('Überschrift', max_length=180)
    excerpt = models.CharField('Kurztext', max_length=350)
    body = models.TextField('Inhalt', blank=True)
    slug = models.SlugField('URL-Adresse', max_length=200, unique=True, blank=True)
    image = models.ImageField('Titelbild', upload_to='news/%Y/%m/', blank=True)
    image_alt = models.CharField('Bildbeschreibung', max_length=200, blank=True)
    status = models.CharField('Status', max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    end_date = models.DateField('Gültig bis', null=True, blank=True)
    event_date = models.DateField('Veranstaltungsdatum', null=True, blank=True)
    event_time = models.TimeField('Uhrzeit', null=True, blank=True)
    event_location = models.CharField('Veranstaltungsort', max_length=200, blank=True)
    vehicle = models.ForeignKey('Vehicle', verbose_name='Verknüpftes Fahrzeug', null=True, blank=True,
                                on_delete=models.SET_NULL, related_name='news_articles')
    is_featured = models.BooleanField('Hervorgehoben', default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-published_at', '-pk']
        verbose_name = 'Neuigkeit'
        verbose_name_plural = 'Neuigkeiten'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or 'neuigkeit'
            slug = base_slug
            suffix = 2
            while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)


class HeroSlide(models.Model):
    CROP_ASPECT = 50 / 17
    MOBILE_CROP_ASPECT = 1.22
    title = models.CharField('Titel', max_length=180, blank=True)
    subtitle = models.TextField('Untertitel', max_length=500, blank=True)
    image = models.ImageField('Bild', upload_to='homepage/slides/%Y/%m/',
                              help_text='JPEG, PNG oder WebP, höchstens 10 MB. Querformat empfohlen; Desktop- und Smartphoneausschnitt im Editor einstellbar.')
    crop_x = models.DecimalField('Crop links (%)', max_digits=6, decimal_places=3, default=0,
                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    crop_y = models.DecimalField('Crop oben (%)', max_digits=6, decimal_places=3, default=0,
                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    crop_width = models.DecimalField('Crop-Breite (%)', max_digits=6, decimal_places=3, default=100,
                                     validators=[MinValueValidator(0.1), MaxValueValidator(100)])
    crop_height = models.DecimalField('Crop-Höhe (%)', max_digits=6, decimal_places=3, default=100,
                                      validators=[MinValueValidator(0.1), MaxValueValidator(100)])
    crop_rendered = models.ImageField('Slider-Crop', upload_to='homepage/slides/crops/%Y/%m/', blank=True)
    image_scale = models.DecimalField('Bildgröße (%)', max_digits=4, decimal_places=2, default=1,
                                      validators=[MinValueValidator(0.6), MaxValueValidator(1.3)])
    image_offset_x = models.DecimalField('Bildposition horizontal (%)', max_digits=5, decimal_places=2, default=0,
                                         validators=[MinValueValidator(-50), MaxValueValidator(50)])
    image_offset_y = models.DecimalField('Bildposition vertikal (%)', max_digits=5, decimal_places=2, default=0,
                                         validators=[MinValueValidator(-50), MaxValueValidator(50)])
    mobile_crop_x = models.DecimalField('Smartphone-Crop links (%)', max_digits=6, decimal_places=3, default=0,
                                        validators=[MinValueValidator(0), MaxValueValidator(100)])
    mobile_crop_y = models.DecimalField('Smartphone-Crop oben (%)', max_digits=6, decimal_places=3, default=0,
                                        validators=[MinValueValidator(0), MaxValueValidator(100)])
    mobile_crop_width = models.DecimalField('Smartphone-Crop-Breite (%)', max_digits=6, decimal_places=3, default=100,
                                            validators=[MinValueValidator(0.1), MaxValueValidator(100)])
    mobile_crop_height = models.DecimalField('Smartphone-Crop-Höhe (%)', max_digits=6, decimal_places=3, default=100,
                                             validators=[MinValueValidator(0.1), MaxValueValidator(100)])
    mobile_crop_rendered = models.ImageField('Smartphone-Slider-Crop', upload_to='homepage/slides/crops/%Y/%m/', blank=True)
    mobile_image_scale = models.DecimalField('Smartphone-Bildgröße (%)', max_digits=4, decimal_places=2, default=1,
                                             validators=[MinValueValidator(0.6), MaxValueValidator(1.3)])
    mobile_image_offset_x = models.DecimalField('Smartphone-Bildposition horizontal (%)', max_digits=5, decimal_places=2, default=0,
                                                validators=[MinValueValidator(-50), MaxValueValidator(50)])
    mobile_image_offset_y = models.DecimalField('Smartphone-Bildposition vertikal (%)', max_digits=5, decimal_places=2, default=0,
                                                validators=[MinValueValidator(-50), MaxValueValidator(50)])
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

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        image_available = bool(self.image and (not self.image._committed or self.image.storage.exists(self.image.name)))
        crop_sets = (
            ('crop', 'crop_rendered', self.CROP_ASPECT, 'slider', 'image_scale', 'image_offset_x', 'image_offset_y'),
            ('mobile_crop', 'mobile_crop_rendered', self.MOBILE_CROP_ASPECT, 'mobile', 'mobile_image_scale', 'mobile_image_offset_x', 'mobile_image_offset_y'),
        )
        crop_value_fields = tuple(f'{prefix}_{suffix}' for prefix, *_ in crop_sets for suffix in ('x', 'y', 'width', 'height'))
        scale_value_fields = tuple(name for _, _, _, _, scale, offset_x, offset_y in crop_sets for name in (scale, offset_x, offset_y))
        value_fields = crop_value_fields + scale_value_fields
        previous = type(self).objects.filter(pk=self.pk).values('image', *value_fields,
            *(field_name for _, field_name, *_ in crop_sets)).first() if self.pk else None
        old_crop_names = {field_name: getattr(self, field_name).name for _, field_name, *_ in crop_sets}
        changed_fields = not previous or str(previous['image']) != str(self.image) or any(
            str(previous[name]) != str(getattr(self, name)) for name in value_fields
        ) or not self.crop_rendered or not self.mobile_crop_rendered
        if previous and image_available:
            changed_fields = changed_fields or any(
                not getattr(self, field_name) or not getattr(self, field_name).storage.exists(getattr(self, field_name).name)
                for _, field_name, *_ in crop_sets
            )
        if image_available and changed_fields:
            self.image.seek(0)
            original = ImageOps.exif_transpose(Image.open(self.image)).convert('RGB')
            width, height = original.size
            base = self.image.name.rsplit('.', 1)[0].split('/')[-1]
            from django.core.files.base import ContentFile
            for prefix, field_name, aspect, suffix, scale_name, offset_x_name, offset_y_name in crop_sets:
                x_name, y_name, w_name, h_name = (f'{prefix}_{part}' for part in ('x', 'y', 'width', 'height'))
                crop_x, crop_y, crop_w, crop_h = (getattr(self, name) for name in (x_name, y_name, w_name, h_name))
                saved_ratio = float(crop_w / crop_h) * width / height
                if (crop_w == 100 and crop_h == 100) or abs(saved_ratio - aspect) > 0.02:
                    if width / height > aspect:
                        crop_w, crop_h = height * aspect / width * 100, 100
                        crop_x, crop_y = (100 - crop_w) / 2, 0
                    else:
                        crop_w, crop_h = 100, width / aspect / height * 100
                        crop_x, crop_y = 0, (100 - crop_h) / 2
                    for name, value in ((x_name, crop_x), (y_name, crop_y), (w_name, crop_w), (h_name, crop_h)):
                        setattr(self, name, value)
                left, top = round(width * float(crop_x) / 100), round(height * float(crop_y) / 100)
                crop_width, crop_height = min(width - left, round(width * float(crop_w) / 100)), min(height - top, round(height * float(crop_h) / 100))
                rendered = original.crop((left, top, left + crop_width, top + crop_height))
                target_width = min(2400, max(1200, rendered.width))
                target_height = round(target_width / aspect)
                rendered = ImageOps.fit(rendered, (target_width, target_height), method=Image.Resampling.LANCZOS)
                scale = float(getattr(self, scale_name))
                foreground_width = max(1, round(target_width * scale))
                foreground_height = max(1, round(target_height * scale))
                offset_x = round(target_width * float(getattr(self, offset_x_name)) / 100)
                offset_y = round(target_height * float(getattr(self, offset_y_name)) / 100)
                position_x = (target_width - foreground_width) // 2 + offset_x
                position_y = (target_height - foreground_height) // 2 + offset_y
                needs_background = (
                    position_x > 0 or position_y > 0 or
                    position_x + foreground_width < target_width or
                    position_y + foreground_height < target_height
                )
                if needs_background:
                    background = ImageEnhance.Brightness(rendered.filter(
                        ImageFilter.GaussianBlur(max(16, target_width * 0.025))
                    )).enhance(0.62)
                else:
                    background = Image.new('RGB', (target_width, target_height), 'black')
                foreground = rendered.resize((foreground_width, foreground_height), Image.Resampling.LANCZOS)
                background.paste(foreground, (position_x, position_y))
                output = BytesIO()
                background.save(output, format='WEBP', quality=90, method=6)
                output.seek(0)
                getattr(self, field_name).save(f'{base}-{suffix}.webp', ContentFile(output.read()), save=False)
        super().save(*args, **kwargs)
        for _, field_name, *_ in crop_sets:
            old_name = old_crop_names[field_name]
            current = getattr(self, field_name)
            if old_name and current.name != old_name:
                current.storage.delete(old_name)

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if bool(self.button_text) != bool(self.button_url):
            raise ValidationError('Für einen Button bitte Text und Link ausfüllen oder beide Felder leer lassen.')
        for prefix in ('crop', 'mobile_crop'):
            if getattr(self, f'{prefix}_x') + getattr(self, f'{prefix}_width') > 100 or getattr(self, f'{prefix}_y') + getattr(self, f'{prefix}_height') > 100:
                raise ValidationError('Der Ausschnitt muss innerhalb des Originalbildes liegen.')
        for field_name in ('image_scale', 'mobile_image_scale'):
            if not 0.6 <= getattr(self, field_name) <= 1.3:
                raise ValidationError({field_name: 'Die Bildgröße muss zwischen 60 und 130 Prozent liegen.'})
        for field_name in ('image_offset_x', 'image_offset_y', 'mobile_image_offset_x', 'mobile_image_offset_y'):
            if not -50 <= getattr(self, field_name) <= 50:
                raise ValidationError({field_name: 'Die Bildposition muss zwischen -50 und +50 Prozent liegen.'})


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
