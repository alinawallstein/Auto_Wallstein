"""Explicit draft import. Provider access is GET-only; local edits are preserved."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from urllib.error import URLError, HTTPError

from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from vehicles.models import Vehicle, VehicleImage, VehicleStatus
from vehicles.webmobil24 import APIError, NoRedirect, positive_id
from .models import ImportedListing, ImportedImage


FUEL = {'GASOLINE': 'Benzin', 'DIESEL': 'Diesel', 'HYBRID': 'Hybrid', 'ELECTRIC': 'Elektro', 'GAS': 'Gas', 'HYDROGEN': 'Wasserstoff'}
GEAR = {'AUTOMATIC': 'Automatik', 'MANUAL': 'Schaltgetriebe', 'SEMI_AUTOMATIC': 'Halbautomatik'}
BODY = {1000: 'Kompaktwagen', 1001: 'Sportwagen', 1002: 'Kombi', 1003: 'Cabriolet', 1004: 'Van / Minivan', 1005: 'SUV / Geländewagen', 1006: 'Nutzfahrzeug', 1036: 'Limousine', 1225: 'Kleinwagen'}
TYPE = {'P': 'Pkw', 'M': 'Motorrad', 'B': 'Bus', 'L': 'Lkw', 'T': 'Anhänger', 'W': 'Wohnmobil'}
UPHOLSTERY = {'ALCANTARA': 'Alcantara', 'CLOTH': 'Stoff', 'FULL_LEATHER': 'Leder', 'PART_LEATHER': 'Teilleder', 'FAKE_LEATHER': 'Kunstleder', 'VELOUR': 'Velours', 'OTHER': 'Sonstige'}


def plain_text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise APIError('Unerwartetes Textformat im Fahrzeugdatensatz.')
    value = re.sub(r'\\([\\`*_{}\[\]()#+.!\-])', r'\1', value)
    return value.replace('**', '').strip()


def number(data, key):
    value = data.get(key)
    if type(value) is not int or value < 0:
        raise APIError(f'Pflichtangabe fehlt oder ist ungültig: {key}.')
    return value


def mapping(data, equipment):
    try:
        registration = date.fromisoformat(data['firstRegistrationDate'])
        prices = [p for p in data['prices'] if p.get('type') == 'PUBLIC' and p.get('currency') == 'EUR']
        if data.get('priceOnRequest') or len(prices) != 1:
            raise ValueError
        price = Decimal(str(prices[0]['price']))
        if not price.is_finite() or price <= 0:
            raise ValueError
        price = price.quantize(Decimal('.01'))
        inspection = date.fromisoformat(data['nextInspectionDate']) if data.get('nextInspectionDate') else None
    except (KeyError, TypeError, ValueError, InvalidOperation):
        raise APIError('Erstzulassung, HU-Datum oder öffentlicher EUR-Preis fehlt/ist ungültig.') from None
    if data.get('status') != 'ACTIVE':
        raise APIError('Fahrzeug ist nicht aktiv; keine automatische Statusübernahme.')
    kw = number(data, 'power')
    names = []
    for identifier in data.get('equipment', []):
        item = equipment.get(str(identifier))
        if not item or not isinstance(item.get('name'), str):
            raise APIError('Ausstattungsreferenz fehlt.')
        names.append(plain_text(item['name']))
    for key in ('standardEquipment', 'specialEquipment'):
        for item in data.get(key, []):
            if item.get('active'):
                names.append(plain_text(item.get('text')))
    result = {
        'brand': plain_text(data.get('make')), 'model': plain_text(data.get('model') or data.get('modelName')),
        'variant': plain_text(data.get('modelVersion')),
        'vehicle_type': BODY.get(data.get('bodyTypeId'), TYPE.get(data.get('vehicleType'), '')),
        'first_registration': registration.isoformat(), 'year': number(data, 'productionYear') if data.get('productionYear') is not None else None,
        'mileage': number(data, 'mileage'), 'fuel_type': FUEL.get(data.get('fuelCategory'), ''),
        'transmission': GEAR.get(data.get('transmission'), ''), 'power_kw': kw,
        'power_ps': int((Decimal(kw) * Decimal('1.3596216173')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
        'engine_capacity': number(data, 'cylinderCapacity'), 'doors': number(data, 'doorCount'),
        'seats': number(data, 'seatCount'), 'exterior_color': plain_text(data.get('bodyColorName') or data.get('bodyColor')),
        'interior_equipment': UPHOLSTERY.get(data.get('upholsteryType'), ''),
        'vin': plain_text(data.get('vin')), 'previous_owners': number(data, 'previousOwnersCount'),
        'hu_valid_until': inspection.isoformat() if inspection else None, 'sale_price': str(price),
        'description': plain_text(data.get('description')), 'equipment': '\n'.join(dict.fromkeys(names)),
    }
    if any(not result[key] for key in ('brand', 'model', 'vehicle_type', 'fuel_type', 'transmission')):
        raise APIError('Marke/Modell oder ein Referenzwert fehlt.')
    return result


def download_image(url, timeout):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == 'https' and parsed.hostname == 'cdn.webmobil24.com'
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and parsed.path.startswith('/images/'))
        if not valid:
            raise APIError('Bildhost oder Bildpfad ist nicht freigegeben.')
        # Deliberately no API Authorization header on CDN requests; redirects blocked.
        request = Request(url, headers={'Accept': 'image/*'}, method='GET')
        with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            if response.status != 200 or response.headers.get_content_type() not in ('image/jpeg', 'image/png', 'image/webp'):
                raise APIError('Bildantwort ist ungültig.')
            raw = response.read(10 * 1024 * 1024 + 1)
        if len(raw) > 10 * 1024 * 1024:
            raise APIError('Bild überschreitet 10 MB.')
        with Image.open(BytesIO(raw)) as image:
            if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 40_000_000:
                raise APIError('Bildformat oder Bildabmessungen sind ungültig.')
            image.load()
            rendered = ImageOps.exif_transpose(image).convert('RGB')
            rendered.thumbnail((1600, 1200))
            output = BytesIO()
            rendered.save(output, 'WEBP', quality=88)
        return output.getvalue()
    except APIError:
        raise
    except (HTTPError, URLError, OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
        raise APIError('Bilddownload oder Bildprüfung fehlgeschlagen.') from None


def import_listing(client, data, mapped, images, downloader=download_image):
    identity = dict(environment=client.config.environment, dealer_id=client.config.dealer_id, listing_id=positive_id(data.get('listingId')))
    # Full image downloads occur before DB changes. Failure leaves this vehicle unchanged.
    source = ImportedListing.objects.filter(**identity).first()
    known = {i.remote_id: i for i in source.imported_images.select_related('image')} if source else {}
    prepared = []
    seen = set()
    if len(images) > 100:
        raise APIError('Mehr als 100 Bilder pro Fahrzeug; Import abgebrochen.')
    for item in images:
        identifier = positive_id(item.get('id'))
        if identifier in seen:
            raise APIError('Doppelte Bild-ID.')
        seen.add(identifier)
        version = item['url'] + '|' + str(item.get('lastModification', ''))
        if len(version) > 1000:
            raise APIError('Bildmetadaten sind zu lang.')
        old = known.get(identifier)
        if old and old.source_version == version and old.image.image.storage.exists(old.image.image.name):
            continue
        prepared.append((identifier, version, downloader(item['url'], client.config.timeout)))
    written = []
    try:
        with transaction.atomic():
            source = ImportedListing.objects.select_for_update().filter(**identity).first()
            created = source is None
            conflicts = []
            if created:
                vehicle = Vehicle(internal_number=f'WM24-{identity["environment"]}-{identity["dealer_id"]}-{identity["listing_id"]}',
                                  purchase_price=None, status=VehicleStatus.IN_PREPARATION,
                                  is_published=False, public_visible=False, **mapped)
            else:
                vehicle = Vehicle.objects.select_for_update().get(pk=source.vehicle_id)
                for key, value in mapped.items():
                    current = getattr(vehicle, key)
                    current = current.isoformat() if isinstance(current, date) else str(current) if isinstance(current, Decimal) else current
                    if current == source.last_mapping.get(key):
                        setattr(vehicle, key, value)
                    elif current != value:
                        conflicts.append(key)
            try:
                vehicle.full_clean()
            except ValidationError:
                raise APIError('Fahrzeugdaten passen nicht zum lokalen Formular; keine Übernahme.') from None
            vehicle.save()
            if created:
                source = ImportedListing.objects.create(vehicle=vehicle, **identity)
            source.source_data = data
            source.last_mapping = mapped
            source.save()
            for identifier, version, content in prepared:
                linked = ImportedImage.objects.filter(listing=source, remote_id=identifier).select_related('image').first()
                image = linked.image if linked else VehicleImage(vehicle=vehicle,
                    sort_order=(vehicle.images.order_by('-sort_order').values_list('sort_order', flat=True).first() or 0) + 1,
                    is_main=not vehicle.images.filter(is_main=True).exists(),
                    alt_text=f'{vehicle.brand} {vehicle.model} – Bild {identifier}'[:200])
                image.image.save(f'wm24-{identity["listing_id"]}-{identifier}.webp', ContentFile(content), save=False)
                written.append((image.image.storage, image.image.name))
                image.save()
                if linked:
                    linked.source_version = version
                    linked.save(update_fields=['source_version'])
                else:
                    ImportedImage.objects.create(listing=source, image=image, remote_id=identifier, source_version=version)
            return created, len(prepared), conflicts
    except Exception:
        for storage, name in written:
            storage.delete(name)
        raise
