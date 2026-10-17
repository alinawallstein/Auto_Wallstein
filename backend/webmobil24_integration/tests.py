import io
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, Mock
from decimal import Decimal
from PIL import Image
from django.test import TestCase, SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from vehicles.webmobil24 import Page
from vehicles.models import Vehicle, VehicleImage, VehicleStatus
from vehicles.webmobil24 import APIError
from .models import ImportedListing, ImportedImage
from .importer import mapping, import_listing, download_image


def listing():
    return dict(listingId=7, dealerId=42, status='ACTIVE', make='Mercedes-Benz', model='GLC',
                firstRegistrationDate='2022-07-22', productionYear=2022, mileage=24404,
                power=190, cylinderCapacity=1999, doorCount=5, seatCount=5, previousOwnersCount=1,
                fuelCategory='GASOLINE', transmission='AUTOMATIC', vehicleType='P', bodyTypeId=1005,
                bodyColorName='Blau', prices=[dict(type='PUBLIC', currency='EUR', price='45980.00')],
                description='**AMG** mit Memory\\-Paket', equipment=[101])


EQUIPMENT = {'101': {'name': 'Automatik'}}
IMAGES = [dict(id=1, url='https://cdn.webmobil24.com/images/7/1.jpg', lastModification='v1')]


class ImportTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.client = SimpleNamespace(config=SimpleNamespace(environment='test', dealer_id=42, timeout=15))

    def run_import(self, data=None, images=None, downloader=None):
        data = data or listing()
        return import_listing(self.client, data, mapping(data, EQUIPMENT), IMAGES if images is None else images,
                              downloader=downloader or Mock(return_value=b'local-image'))

    def test_drafts_and_idempotence(self):
        self.run_import()
        vehicle = Vehicle.objects.get()
        self.assertFalse(vehicle.is_publicly_listed)
        self.assertEqual(vehicle.status, VehicleStatus.IN_PREPARATION)
        self.assertIsNone(vehicle.purchase_price)
        self.assertEqual(vehicle.sale_price, Decimal('45980.00'))
        self.assertEqual(vehicle.power_ps, 258)
        self.assertEqual(vehicle.description, 'AMG mit Memory-Paket')
        self.assertEqual(vehicle.equipment, 'Automatik')
        downloader = Mock()
        self.run_import(downloader=downloader)
        downloader.assert_not_called()
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(ImportedListing.objects.count(), 1)
        self.assertEqual(VehicleImage.objects.count(), 1)

    def test_manual_edits_publication_and_local_images_preserved(self):
        self.run_import()
        vehicle = Vehicle.objects.get()
        vehicle.description = 'Manueller Text'
        vehicle.status = VehicleStatus.RESERVED
        vehicle.is_published = vehicle.public_visible = True
        vehicle.purchase_price = Decimal('35000')
        vehicle.save()
        original = VehicleImage.objects.get()
        original.sort_order = 77
        original.save()
        data = listing()
        data['prices'][0]['price'] = '44000'
        data['description'] = 'Neuer API-Text'
        _, _, conflicts = self.run_import(data)
        vehicle.refresh_from_db()
        original.refresh_from_db()
        self.assertEqual(vehicle.sale_price, Decimal('44000'))
        self.assertEqual(vehicle.description, 'Manueller Text')
        self.assertIn('description', conflicts)
        self.assertTrue(vehicle.is_published)
        self.assertEqual(vehicle.status, VehicleStatus.RESERVED)
        self.assertEqual(vehicle.purchase_price, Decimal('35000'))
        self.assertEqual(original.sort_order, 77)

    def test_failed_download_does_not_create_partial_vehicle(self):
        with self.assertRaises(APIError):
            self.run_import(downloader=Mock(side_effect=APIError('Download fehlgeschlagen')))
        self.assertFalse(Vehicle.objects.exists())
        self.assertFalse(ImportedListing.objects.exists())

    def test_missing_local_image_is_repaired(self):
        self.run_import()
        image = VehicleImage.objects.get()
        image.image.storage.delete(image.image.name)
        downloader = Mock(return_value=b'repaired')
        self.run_import(downloader=downloader)
        downloader.assert_called_once()
        self.assertEqual(ImportedImage.objects.count(), 1)

    def test_unsafe_mapping_fails(self):
        for key, value in [('prices', []), ('prices', [dict(type='PUBLIC', currency='EUR', price='NaN')]),
                           ('status', 'SOLD'), ('equipment', [999]), ('mileage', -1)]:
            data = listing()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(APIError):
                mapping(data, EQUIPMENT)

    def test_distinct_environment_does_not_merge(self):
        self.run_import(images=[])
        self.client.config.environment = 'production'
        self.run_import(images=[])
        self.assertEqual(Vehicle.objects.count(), 2)

    def test_missing_production_year_is_not_inferred_from_registration(self):
        data = listing()
        data.pop('productionYear')
        self.run_import(data, images=[])
        self.assertIsNone(Vehicle.objects.get().year)


class ImageTests(SimpleTestCase):
    def test_invalid_hosts_blocked_before_network(self):
        for url in ['http://cdn.webmobil24.com/images/7/1.jpg', 'https://127.0.0.1/images/x',
                    'https://cdn.webmobil24.com.evil.example/images/x', 'https://cdn.webmobil24.com:8443/images/x',
                    'https://secret@cdn.webmobil24.com/images/x']:
            with self.subTest(url=url), patch('webmobil24_integration.importer.build_opener') as opener:
                with self.assertRaises(APIError):
                    download_image(url, 15)
                opener.assert_not_called()

    def test_download_reencodes_without_authorization(self):
        raw = io.BytesIO()
        Image.new('RGB', (20, 10)).save(raw, 'JPEG')
        response = Mock()
        response.status = 200
        response.headers.get_content_type.return_value = 'image/jpeg'
        response.read.return_value = raw.getvalue()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch('webmobil24_integration.importer.build_opener') as factory:
            factory.return_value.open.return_value = response
            result = download_image(IMAGES[0]['url'], 15)
            request = factory.return_value.open.call_args.args[0]
            self.assertIsNone(request.get_header('Authorization'))
        self.assertEqual(Image.open(io.BytesIO(result)).format, 'WEBP')


class CommandAndPreviewTests(TestCase):
    def api(self):
        client = Mock()
        client.config = SimpleNamespace(environment='test', dealer_id=42, timeout=15)
        client._get.return_value = EQUIPMENT, {}
        client.listings.return_value = Page([{'listingId': 7}], 1)
        client.detail.return_value = listing()
        client.images.return_value = IMAGES
        return client

    @patch('webmobil24_integration.management.commands.import_webmobil24.Client')
    @patch('webmobil24_integration.management.commands.import_webmobil24.Config.from_env')
    def test_dry_run_never_saves(self, config, factory):
        factory.return_value = self.api()
        call_command('import_webmobil24', stdout=io.StringIO())
        self.assertFalse(Vehicle.objects.exists())
        self.assertFalse(ImportedImage.objects.exists())

    @patch('webmobil24_integration.management.commands.import_webmobil24.Client')
    @patch('webmobil24_integration.management.commands.import_webmobil24.Config.from_env')
    def test_incomplete_inventory_stops_before_writes(self, config, factory):
        client = self.api()
        client.listings.return_value = Page([{'listingId': 7}], 2)
        factory.return_value = client
        with self.assertRaises(CommandError):
            call_command('import_webmobil24', apply=True, stdout=io.StringIO())
        self.assertFalse(Vehicle.objects.exists())
        client.detail.assert_not_called()

    @patch('webmobil24_integration.management.commands.import_webmobil24.Client')
    @patch('webmobil24_integration.management.commands.import_webmobil24.Config.from_env')
    def test_overlong_data_rejected_in_preview(self, config, factory):
        client = self.api()
        client.detail.return_value['modelVersion'] = 'x' * 151
        factory.return_value = client
        with self.assertRaises(CommandError):
            call_command('import_webmobil24', stdout=io.StringIO())
        self.assertFalse(Vehicle.objects.exists())

    @patch('webmobil24_integration.management.commands.import_webmobil24.Client')
    @patch('webmobil24_integration.management.commands.import_webmobil24.Config.from_env')
    def test_existing_import_passes_command_validation(self, config, factory):
        client = self.api()
        factory.return_value = client
        client.images.return_value = []
        call_command('import_webmobil24', apply=True, stdout=io.StringIO())
        out = io.StringIO()
        call_command('import_webmobil24', apply=True, stdout=out)
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertIn('0 neue Entwürfe', out.getvalue())

    def test_preview_private_and_draft_not_public(self):
        data = mapping(listing(), EQUIPMENT)
        vehicle = Vehicle.objects.create(internal_number='preview', purchase_price=None, **data)
        url = f'/verwaltung/fahrzeuge/{vehicle.pk}/vorschau/'
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user(username='reader', password='test')
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        user.is_superuser = True
        user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotContains(response, 'Probefahrt anfragen')
        self.assertEqual(self.client.get(f'/fahrzeuge/{vehicle.pk}/').status_code, 404)
