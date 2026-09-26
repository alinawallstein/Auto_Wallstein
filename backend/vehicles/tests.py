from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from PIL import Image
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.models import model_to_dict
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import CustomerInquiry, Vehicle, VehicleImage, VehicleStatus


class VehicleTestCase(TestCase):
    def setUp(self):
        media_directory = TemporaryDirectory(prefix="wallstein-tests-")
        self.addCleanup(media_directory.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=media_directory.name))
        self.vehicle = Vehicle.objects.create(
            internal_number="V-001",
            brand="BMW",
            model="3er",
            variant="320d",
            vehicle_type="Limousine",
            first_registration=date(2022, 1, 1),
            year=2022,
            mileage=20000,
            fuel_type="Diesel",
            transmission="Automatik",
            power_kw=140,
            power_ps=190,
            engine_capacity=1995,
            doors=4,
            seats=5,
            exterior_color="Schwarz",
            interior_equipment="Leder",
            vin="WBA1234567",
            purchase_price=Decimal("21000.00"),
            sale_price=Decimal("25990.00"),
            status=VehicleStatus.AVAILABLE,
            is_published=True,
            public_visible=True,
        )

    def another_vehicle(self, **changes):
        data = model_to_dict(self.vehicle, exclude=["id"])
        data.update(internal_number="V-OTHER")
        data.update(changes)
        return Vehicle.objects.create(**data)

    def login_admin(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "admin123")
        self.client.force_login(user)

    def image_upload(self, name="car.png"):
        buffer = BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class InquiryFlowTests(VehicleTestCase):
    def test_vehicle_inquiry_can_be_submitted(self):
        response = self.client.post(
            reverse("kontakt"),
            {
                "inquiry_type": "vehicle_request",
                "vehicle": self.vehicle.pk,
                "name": "Max Mustermann",
                "email": "max@example.com",
                "phone": "0123456789",
                "message": "Ich interessiere mich für dieses Fahrzeug.",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vielen Dank")
        inquiry = CustomerInquiry.objects.get(email="max@example.com")
        self.assertEqual(inquiry.vehicle, self.vehicle)
        self.assertEqual(inquiry.inquiry_type, "vehicle_request")

    @override_settings(DEBUG=True)
    def test_image_upload_and_media_access_work_for_admin(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "admin123")
        self.client.force_login(user)

        image_buffer = BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(image_buffer, format="PNG")
        image = SimpleUploadedFile("car.png", image_buffer.getvalue(), content_type="image/png")

        response = self.client.post(
            reverse("vehicle_images", args=[self.vehicle.pk]),
            {"images": [image]},
            follow=True,
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(VehicleImage.objects.filter(vehicle=self.vehicle).count(), 1)

        uploaded = VehicleImage.objects.filter(vehicle=self.vehicle).first()
        self.assertTrue(uploaded.image.name.startswith("vehicles/"))
        self.assertTrue(uploaded.image.url.startswith("/media/"))
        self.assertTrue(uploaded.image.storage.exists(uploaded.image.name))

    def test_homepage_contains_branding_and_fahrzeuge_call_to_action(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Auto Wallstein")
        self.assertContains(response, "FINDEN SIE IHREN NÄCHSTEN MERCEDES")
        self.assertContains(response, "Fahrzeuge ansehen")

    def test_fahrzeuge_url_alias_is_available(self):
        response = self.client.get("/fahrzeuge/")

        self.assertEqual(response.status_code, 200)

    def test_public_pages_share_consistent_nav_and_footer_links(self):
        response = self.client.get("/ueberuns/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/finanzierung/")
        self.assertContains(response, "/oeffnungszeiten/")
        self.assertContains(response, "/kontakt/")

    def test_public_pages_are_available(self):
        for url in [
            "/",
            "/fahrzeuge/",
            "/ueberuns/",
            "/finanzierung/",
            "/oeffnungszeiten/",
            "/service/",
            "/kontakt/",
            "/impressum/",
            "/datenschutz/",
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, msg=f"Expected 200 for {url}")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_renders_for_admin(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "admin123")
        self.client.force_login(user)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/dashboard.html")
        self.assertContains(response, "BMW 3er")
        self.assertContains(response, reverse("vehicle_update", args=[self.vehicle.pk]))

    def test_vehicle_create_form_renders_for_admin(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "admin123")
        self.client.force_login(user)

        response = self.client.get(reverse("vehicle_create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/vehicle_form.html")
        self.assertContains(response, "Neues Fahrzeug")
        self.assertContains(response, 'name="internal_number"')
        self.assertFalse(response.context["form"].is_bound)

    def test_vehicle_edit_form_renders_existing_vehicle_for_admin(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "admin123")
        self.client.force_login(user)

        response = self.client.get(reverse("vehicle_update", args=[self.vehicle.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/vehicle_form.html")
        self.assertContains(response, "Fahrzeug bearbeiten")
        self.assertContains(response, 'value="V-001"')
        self.assertEqual(response.context["form"].instance, self.vehicle)

    def test_only_public_visible_vehicles_are_shown(self):
        hidden_vehicle = Vehicle.objects.create(
            internal_number="V-002",
            brand="Audi",
            model="A4",
            variant="2.0 TDI",
            vehicle_type="Limousine",
            first_registration=date(2021, 6, 1),
            year=2021,
            mileage=48000,
            fuel_type="Diesel",
            transmission="Automatik",
            power_kw=120,
            power_ps=163,
            engine_capacity=1968,
            doors=4,
            seats=5,
            exterior_color="Weiß",
            interior_equipment="Nappaleder",
            vin="AUDI123456",
            purchase_price=Decimal("18000.00"),
            sale_price=Decimal("21990.00"),
            status=VehicleStatus.AVAILABLE,
            is_published=True,
            public_visible=False,
        )

        response = self.client.get(reverse("public_vehicles"))

        self.assertContains(response, self.vehicle.brand)
        self.assertNotContains(response, hidden_vehicle.brand)
        self.assertNotContains(response, hidden_vehicle.model)


class PublicInventoryTests(VehicleTestCase):
    def test_visibility_matrix_across_list_home_detail_and_inquiry_choices(self):
        for published in (False, True):
            for visible in (False, True):
                for status in VehicleStatus.values:
                    with self.subTest(published=published, visible=visible, status=status):
                        self.vehicle.is_published = published
                        self.vehicle.public_visible = visible
                        self.vehicle.status = status
                        self.vehicle.save()
                        expected = published and visible and status == VehicleStatus.AVAILABLE
                        for name, key in [("home", "featured_vehicles"), ("public_vehicles", "vehicles")]:
                            response = self.client.get(reverse(name))
                            self.assertEqual(self.vehicle in response.context[key], expected)
                        contact = self.client.get(reverse("kontakt"))
                        self.assertEqual(
                            contact.context["form"].fields["vehicle"].queryset.filter(pk=self.vehicle.pk).exists(),
                            expected,
                        )
                        detail = self.client.get(reverse("vehicle_detail", args=[self.vehicle.pk]))
                        if expected:
                            self.assertContains(detail, "BMW 3er")
                        else:
                            self.assertEqual(detail.status_code, 404)

    def test_public_detail_offers_both_inquiry_types_without_internal_price(self):
        response = self.client.get(reverse("vehicle_detail", args=[self.vehicle.pk]))
        self.assertContains(response, f"?inquiry_type=vehicle_request&vehicle={self.vehicle.pk}")
        self.assertContains(response, f"?inquiry_type=test_drive&vehicle={self.vehicle.pk}")
        self.assertNotContains(response, "Einkaufspreis")
        self.assertNotContains(response, self.vehicle.vin)

    def test_filters_and_boundary_values(self):
        other = self.another_vehicle(brand="Audi", model="A4", sale_price=35000, year=2020,
                                     mileage=60000, fuel_type="Benzin", transmission="Schaltgetriebe")
        cases = [
            ({"brand": "bmw"}, [self.vehicle]), ({"model": "3er"}, [self.vehicle]),
            ({"price_min": "25990"}, [self.vehicle, other]),
            ({"price_max": "25990"}, [self.vehicle]),
            ({"year_min": "2022"}, [self.vehicle]), ({"year_max": "2020"}, [other]),
            ({"mileage_max": "20000"}, [self.vehicle]),
            ({"fuel_type": "Diesel"}, [self.vehicle]),
            ({"transmission": "Automatik"}, [self.vehicle]),
            ({"brand": "BMW", "price_max": "20000"}, []),
            ({"brand": "BMW", "fuel_type": "Diesel", "sort": "price_desc"}, [self.vehicle]),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                response = self.client.get(reverse("public_vehicles"), params)
                self.assertCountEqual(response.context["vehicles"], expected)
                for key, value in params.items():
                    self.assertEqual(response.context["active_filters"][key], value)

    def test_sorting(self):
        other = self.another_vehicle(sale_price=15000, mileage=60000)
        Vehicle.objects.filter(pk=self.vehicle.pk).update(created_at=timezone.now() - timedelta(days=2))
        for sort, expected in [
            ("newest", [other, self.vehicle]), ("price_asc", [other, self.vehicle]),
            ("price_desc", [self.vehicle, other]), ("mileage", [self.vehicle, other]),
        ]:
            with self.subTest(sort=sort):
                response = self.client.get(reverse("public_vehicles"), {"sort": sort})
                self.assertEqual(list(response.context["vehicles"]), expected)

    def test_current_legacy_urls_remain_available_with_query_parameters(self):
        # Old links must reach canonical pages with their query parameters intact.
        for url in ["/vehicles/?brand=BMW", "/contact/?inquiry_type=test_drive", "/about/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, follow=True).status_code, 200)
        response = self.client.get("/vehicles/", {"brand": "Audi"}, follow=True)
        self.assertEqual(list(response.context["vehicles"]), [])


class InquiryRegressionTests(VehicleTestCase):
    def payload(self, **changes):
        data = {"inquiry_type": "test_drive", "vehicle": self.vehicle.pk,
                "name": "Erika Muster", "email": "erika@example.com", "message": "Bitte um Probefahrt."}
        data.update(changes)
        return data

    def test_test_drive_prefill_and_submission(self):
        response = self.client.get(reverse("kontakt"), {"vehicle": self.vehicle.pk, "inquiry_type": "test_drive"})
        self.assertEqual(str(response.context["form"]["vehicle"].value()), str(self.vehicle.pk))
        self.assertEqual(response.context["form"]["inquiry_type"].value(), "test_drive")
        response = self.client.post(reverse("kontakt"), self.payload())
        self.assertContains(response, "Vielen Dank")
        inquiry = CustomerInquiry.objects.get()
        self.assertEqual(inquiry.inquiry_type, "test_drive")
        self.assertEqual(inquiry.vehicle, self.vehicle)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@autowallstein.test",
        INQUIRY_NOTIFICATION_EMAIL="info@autowallstein.test",
    )
    def test_inquiry_sends_notification_and_auto_reply(self):
        response = self.client.post(reverse("kontakt"), self.payload())
        self.assertContains(response, "Vielen Dank")
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].subject, "Neue Kundenanfrage: Probefahrt anfragen")
        self.assertIn("erika@example.com", mail.outbox[1].to)
        self.assertIn("wir haben ihre e-mail erhalten", mail.outbox[1].body.lower())

    def test_general_contact_without_vehicle(self):
        response = self.client.post(reverse("kontakt"), self.payload(vehicle="", inquiry_type="vehicle_request"))
        self.assertContains(response, "Vielen Dank")
        self.assertIsNone(CustomerInquiry.objects.get().vehicle)

    def test_invalid_inquiries_are_not_saved(self):
        for field, value in [("email", "invalid"), ("name", ""), ("message", ""),
                             ("inquiry_type", "invalid"), ("vehicle", 999999)]:
            with self.subTest(field=field):
                response = self.client.post(reverse("kontakt"), self.payload(**{field: value}))
                self.assertIn(field, response.context["form"].errors)
                self.assertFalse(CustomerInquiry.objects.exists())

    def test_hidden_vehicle_cannot_be_requested_by_posting_its_id(self):
        self.vehicle.public_visible = False
        self.vehicle.save()
        response = self.client.post(reverse("kontakt"), self.payload())
        self.assertIn("vehicle", response.context["form"].errors)
        self.assertFalse(CustomerInquiry.objects.exists())


class ManagementRegressionTests(VehicleTestCase):
    def test_anonymous_get_and_post_require_login_without_mutation(self):
        for name, args in [("dashboard", []), ("vehicle_create", []),
                           ("vehicle_update", [self.vehicle.pk]), ("vehicle_delete", [self.vehicle.pk]),
                           ("vehicle_images", [self.vehicle.pk])]:
            for method in (self.client.get, self.client.post):
                with self.subTest(route=name, method=method.__name__):
                    url = reverse(name, args=args)
                    response = method(url)
                    self.assertRedirects(response, f"{reverse('login')}?next={url}", fetch_redirect_response=False)
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertFalse(VehicleImage.objects.exists())

    def test_admin_can_create_edit_and_delete_vehicle(self):
        self.login_admin()
        data = model_to_dict(self.vehicle, exclude=["id"])
        data["hu_valid_until"] = ""
        data["internal_number"] = "V-NEW"
        response = self.client.post(reverse("vehicle_create"), data)
        created = Vehicle.objects.get(internal_number="V-NEW")
        self.assertRedirects(response, reverse("vehicle_update", args=[created.pk]))
        data["sale_price"] = "29990.00"
        response = self.client.post(reverse("vehicle_update", args=[created.pk]), data)
        self.assertRedirects(response, reverse("vehicle_update", args=[created.pk]))
        created.refresh_from_db()
        self.assertEqual(created.sale_price, Decimal("29990.00"))
        url = reverse("vehicle_delete", args=[created.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Vehicle.objects.filter(pk=created.pk).exists())
        self.assertRedirects(self.client.post(url), reverse("dashboard"))
        self.assertFalse(Vehicle.objects.filter(pk=created.pk).exists())
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_invalid_vehicle_edit_does_not_change_saved_price(self):
        self.login_admin()
        data = model_to_dict(self.vehicle, exclude=["id"])
        data.update(hu_valid_until="", sale_price="-1")
        response = self.client.post(reverse("vehicle_update", args=[self.vehicle.pk]), data)
        self.assertIn("sale_price", response.context["form"].errors)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.sale_price, Decimal("25990.00"))


class ImageRegressionTests(VehicleTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()
        self.url = reverse("vehicle_images", args=[self.vehicle.pk])

    def test_empty_upload_is_invalid_and_creates_no_images(self):
        response = self.client.post(self.url, {"images": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("images", response.context["upload_form"].errors)
        self.assertFalse(self.vehicle.images.exists())

    def test_multiple_uploads_preserve_files_and_one_main_image(self):
        response = self.client.post(self.url, {"images": [self.image_upload("one.png"), self.image_upload("two.png")]})
        self.assertRedirects(response, self.url)
        self.assertEqual(self.vehicle.images.count(), 2)
        self.assertEqual(self.vehicle.images.filter(is_main=True).count(), 1)
        for image in self.vehicle.images.all():
            self.assertTrue(image.image.storage.exists(image.image.name))

    def test_main_image_reorder_and_delete(self):
        first = VehicleImage.objects.create(vehicle=self.vehicle, image=self.image_upload("one.png"), sort_order=1, is_main=True)
        second = VehicleImage.objects.create(vehicle=self.vehicle, image=self.image_upload("two.png"), sort_order=2)
        self.client.post(self.url, {"action": "set_main", "image_id": second.pk})
        self.assertEqual(list(self.vehicle.images.filter(is_main=True)), [second])
        self.client.post(self.url, {"action": "move_up", "image_id": second.pk})
        self.assertEqual(list(self.vehicle.images.all()), [second, first])
        self.client.post(self.url, {"action": "move_down", "image_id": second.pk})
        self.assertEqual(list(self.vehicle.images.all()), [first, second])
        self.client.post(self.url, {"action": "delete", "image_id": second.pk})
        self.assertEqual(list(self.vehicle.images.all()), [first])
        first.refresh_from_db()
        self.assertTrue(first.is_main)
        self.assertEqual(first.sort_order, 1)

    def test_image_actions_cannot_modify_another_vehicle(self):
        other = self.another_vehicle()
        image = VehicleImage.objects.create(vehicle=other, image=self.image_upload(), is_main=True, sort_order=1)
        for action in ("delete", "set_main", "move_up", "move_down"):
            with self.subTest(action=action):
                self.client.post(self.url, {"action": action, "image_id": image.pk})
                image.refresh_from_db()
                self.assertEqual(image.vehicle_id, other.pk)
                self.assertTrue(image.is_main)
                self.assertEqual(image.sort_order, 1)


class AccessAndValidationTests(VehicleTestCase):
    def test_authenticated_user_without_permissions_cannot_manage(self):
        user = get_user_model().objects.create_user('reader', is_staff=True)
        self.client.force_login(user)
        for name, args in [('dashboard', []), ('vehicle_create', []),
                           ('vehicle_update', [self.vehicle.pk]), ('vehicle_delete', [self.vehicle.pk]),
                           ('vehicle_images', [self.vehicle.pk])]:
            for method in (self.client.get, self.client.post):
                with self.subTest(name=name, method=method.__name__):
                    self.assertEqual(method(reverse(name, args=args)).status_code, 403)
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_view_permission_does_not_grant_mutation_permissions(self):
        from django.contrib.auth.models import Permission
        user = get_user_model().objects.create_user('reader')
        user.user_permissions.add(Permission.objects.get(content_type__app_label='vehicles', codename='view_vehicle'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        for name, args in [('vehicle_create', []), ('vehicle_update', [self.vehicle.pk]),
                           ('vehicle_delete', [self.vehicle.pk]), ('vehicle_images', [self.vehicle.pk])]:
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name, args=args)).status_code, 403)

    def test_missing_objects_return_404(self):
        self.assertEqual(self.client.get(reverse('vehicle_detail', args=[999999])).status_code, 404)
        self.login_admin()
        for name in ('vehicle_update', 'vehicle_delete', 'vehicle_images'):
            for method in (self.client.get, self.client.post):
                with self.subTest(name=name, method=method.__name__):
                    self.assertEqual(method(reverse(name, args=[999999])).status_code, 404)

    def test_invalid_filters_show_errors_without_results(self):
        for field in ('price_min', 'price_max', 'year_min', 'year_max', 'mileage_max'):
            for value in ('abc', '-1', 'NaN', 'Infinity', '99999999999999999999999999'):
                with self.subTest(field=field, value=value):
                    response = self.client.get(reverse('public_vehicles'), {field: value})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(field, response.context['filter_form'].errors)
                    self.assertContains(response, 'Bitte korrigieren Sie die Filterangaben.')
                    self.assertEqual(list(response.context['vehicles']), [])

    def test_reversed_ranges_and_unknown_sort_are_invalid(self):
        for params in ({'price_min': '30000', 'price_max': '10000'},
                       {'year_min': '2025', 'year_max': '2020'}, {'sort': 'invalid'}):
            with self.subTest(params=params):
                response = self.client.get(reverse('public_vehicles'), params)
                self.assertTrue(response.context['filter_form'].errors)
                self.assertEqual(list(response.context['vehicles']), [])

    def test_zero_max_price_is_not_ignored(self):
        response = self.client.get(reverse('public_vehicles'), {'price_max': '0'})
        self.assertEqual(list(response.context['vehicles']), [])

    def test_filter_options_remain_available_after_empty_search(self):
        self.another_vehicle(brand='Audi')
        response = self.client.get(reverse('public_vehicles'), {'price_max': '0'})
        self.assertCountEqual(response.context['brands'], ['Audi', 'BMW'])

    def test_individual_vehicle_permissions_allow_only_their_action(self):
        from django.contrib.auth.models import Permission
        for permission, allowed_route in [('add_vehicle', 'vehicle_create'),
                                          ('change_vehicle', 'vehicle_update'),
                                          ('delete_vehicle', 'vehicle_delete')]:
            user = get_user_model().objects.create_user(permission)
            user.user_permissions.set(Permission.objects.filter(
                content_type__app_label='vehicles', codename__in=['view_vehicle', permission]))
            self.client.force_login(user)
            for route in ('vehicle_create', 'vehicle_update', 'vehicle_delete'):
                with self.subTest(permission=permission, route=route):
                    args = [] if route == 'vehicle_create' else [self.vehicle.pk]
                    self.assertEqual(self.client.get(reverse(route, args=args)).status_code,
                                     200 if route == allowed_route else 403)
            data = model_to_dict(self.vehicle, exclude=['id'])
            data.update(hu_valid_until='', sale_price='28000.00')
            if allowed_route == 'vehicle_create':
                data['internal_number'] = 'NEW'
                response = self.client.post(reverse(allowed_route), data)
                self.assertRedirects(response, reverse('dashboard'))
                self.assertTrue(Vehicle.objects.filter(internal_number='NEW').exists())
            elif allowed_route == 'vehicle_update':
                response = self.client.post(reverse(allowed_route, args=[self.vehicle.pk]), data)
                self.assertRedirects(response, reverse('vehicle_update', args=[self.vehicle.pk]))
                self.vehicle.refresh_from_db()
                self.assertEqual(self.vehicle.sale_price, Decimal('28000.00'))
            else:
                response = self.client.post(reverse(allowed_route, args=[self.vehicle.pk]))
                self.assertRedirects(response, reverse('dashboard'))
                self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_vehicle_editor_needs_separate_image_permissions(self):
        from django.contrib.auth.models import Permission
        user = get_user_model().objects.create_user('editor')
        user.user_permissions.set(Permission.objects.filter(
            content_type__app_label='vehicles', codename__in=['view_vehicle', 'change_vehicle']))
        self.client.force_login(user)
        image = VehicleImage.objects.create(vehicle=self.vehicle, image=self.image_upload(), sort_order=1)
        url = reverse('vehicle_images', args=[self.vehicle.pk])
        self.assertEqual(self.client.post(url, {'images': [self.image_upload()]}).status_code, 403)
        for action in ('set_main', 'move_up', 'move_down', 'delete'):
            with self.subTest(action=action):
                self.assertEqual(self.client.post(url, {'action': action, 'image_id': image.pk}).status_code, 403)
        image.refresh_from_db()
        self.assertFalse(image.is_main)
        self.assertEqual(self.vehicle.images.count(), 1)
        for permission, payload in [
            ('add_vehicleimage', {'images': [self.image_upload('extra.png')]}),
            ('change_vehicleimage', {'action': 'set_main', 'image_id': image.pk}),
            ('delete_vehicleimage', {'action': 'delete', 'image_id': image.pk}),
        ]:
            user.user_permissions.add(Permission.objects.get(content_type__app_label='vehicles', codename=permission))
            self.assertRedirects(self.client.post(url, payload), url)
        self.assertFalse(VehicleImage.objects.filter(pk=image.pk).exists())
        self.assertEqual(self.vehicle.images.count(), 1)


class PublicShellTests(VehicleTestCase):
    def test_all_public_pages_share_one_document_and_accessible_navigation(self):
        urls = ['/', '/fahrzeuge/', f'/fahrzeuge/{self.vehicle.pk}/', '/ueberuns/',
                '/finanzierung/', '/service/', '/kontakt/', '/oeffnungszeiten/',
                '/impressum/', '/datenschutz/']
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'public/base.html')
                self.assertTemplateUsed(response, 'partials/header.html')
                self.assertTemplateUsed(response, 'partials/footer.html')
                html = response.content.decode()
                self.assertEqual(html.count('<html '), 1)
                self.assertEqual(html.count('<main '), 1)
                self.assertEqual(html.count('<h1'), 1)
                self.assertNotIn('css/site.css', html)
                self.assertNotIn('bootstrap', html)
                self.assertNotIn('style=', html)
                for stylesheet in ('tokens', 'base', 'components', 'layout'):
                    self.assertEqual(html.count(f'css/{stylesheet}.css'), 1)
                self.assertEqual(html.count('js/nav.js'), 1)
                self.assertContains(response, 'href="#main-content"')
                self.assertContains(response, 'aria-controls="site-menu"')
                nav = html.split('<nav class="site-nav"')[1].split('</nav>')[0]
                for route in ('public_vehicles', 'finanzierung', 'service', 'ueberuns', 'kontakt'):
                    self.assertIn(f'href="{reverse(route)}"', nav)
                for route in ('impressum', 'datenschutz'):
                    self.assertNotIn(f'href="{reverse(route)}"', nav)
                    self.assertContains(response, f'href="{reverse(route)}"')
                self.assertNotIn('Historie', nav)


class PublicComponentTests(VehicleTestCase):
    def test_home_and_inventory_use_shared_vehicle_card(self):
        for route in ('home', 'public_vehicles'):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertTemplateUsed(response, 'partials/vehicle_card.html')
                self.assertContains(response, '320d')
                self.assertContains(response, '140 kW / 190 PS')
                self.assertContains(response, reverse('vehicle_detail', args=[self.vehicle.pk]))

    def test_contact_errors_for_vehicle_and_inquiry_type_are_visible(self):
        response = self.client.post(reverse('kontakt'), {
            'inquiry_type': 'invalid', 'vehicle': 999999,
            'name': 'Max', 'email': 'max@example.com', 'message': 'Anfrage',
        })
        for field in ('vehicle', 'inquiry_type'):
            for error in response.context['form'].errors[field]:
                self.assertContains(response, error)
        self.assertFalse(CustomerInquiry.objects.exists())

    def test_public_stylesheet_files_exist(self):
        from django.contrib.staticfiles import finders
        for path in ('tokens.css', 'base.css', 'layout.css', 'components.css',
                     'pages/home.css', 'pages/vehicles.css', 'pages/contact.css'):
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find('css/' + path))


class CanonicalRouteTests(VehicleTestCase):
    def test_management_names_resolve_under_verwaltung(self):
        for name, args, expected in [
            ('dashboard', [], '/verwaltung/'), ('login', [], '/verwaltung/anmelden/'),
            ('logout', [], '/verwaltung/abmelden/'),
            ('vehicle_create', [], '/verwaltung/fahrzeuge/neu/'),
            ('vehicle_update', [self.vehicle.pk], f'/verwaltung/fahrzeuge/{self.vehicle.pk}/bearbeiten/'),
            ('vehicle_images', [self.vehicle.pk], f'/verwaltung/fahrzeuge/{self.vehicle.pk}/bilder/'),
            ('vehicle_delete', [self.vehicle.pk], f'/verwaltung/fahrzeuge/{self.vehicle.pk}/loeschen/'),
        ]:
            with self.subTest(name=name):
                self.assertEqual(reverse(name, args=args), expected)

    def test_old_get_urls_redirect_with_query_string(self):
        query = '?brand=Mercedes-Benz&model=A%2B200&sort=price_asc'
        for old, name, args in [
            ('/vehicles/', 'public_vehicles', []), ('/contact/', 'kontakt', []),
            ('/about/', 'ueberuns', []), ('/login/', 'login', []),
            ('/logout/', 'logout', []), ('/dashboard/', 'dashboard', []),
            ('/fahrzeuge/neu/', 'vehicle_create', []),
            (f'/fahrzeuge/{self.vehicle.pk}/bearbeiten/', 'vehicle_update', [self.vehicle.pk]),
            (f'/fahrzeuge/{self.vehicle.pk}/bilder/', 'vehicle_images', [self.vehicle.pk]),
            (f'/fahrzeuge/{self.vehicle.pk}/loeschen/', 'vehicle_delete', [self.vehicle.pk]),
        ]:
            with self.subTest(old=old):
                self.assertRedirects(self.client.get(old + query), reverse(name, args=args) + query,
                                     status_code=301, fetch_redirect_response=False)

    def test_old_contact_post_preserves_body_and_saves_once(self):
        data = {'name': 'Max', 'email': 'max@example.com', 'message': 'Probefahrt bitte',
                'inquiry_type': 'test_drive', 'vehicle': self.vehicle.pk}
        url = f'/contact/?vehicle={self.vehicle.pk}&inquiry_type=test_drive'
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 307)
        self.assertFalse(CustomerInquiry.objects.exists())
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Vielen Dank')
        inquiry = CustomerInquiry.objects.get()
        self.assertEqual(inquiry.inquiry_type, 'test_drive')
        self.assertEqual(inquiry.vehicle, self.vehicle)

    def test_old_management_post_preserves_permission_checks(self):
        user = get_user_model().objects.create_user('no_permissions')
        self.client.force_login(user)
        response = self.client.post(f'/fahrzeuge/{self.vehicle.pk}/loeschen/', follow=True)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
        self.login_admin()
        response = self.client.post(f'/fahrzeuge/{self.vehicle.pk}/loeschen/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[-1], (reverse('dashboard'), 302))
        self.assertFalse(Vehicle.objects.filter(pk=self.vehicle.pk).exists())

    def test_old_login_post_reaches_new_dashboard(self):
        get_user_model().objects.create_superuser('admin', 'admin@example.com', 'admin123')
        response = self.client.post('/login/', {'username': 'admin', 'password': 'admin123'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [(reverse('login'), 307), (reverse('dashboard'), 302)])
        self.assertTemplateUsed(response, 'admin/dashboard.html')

    def test_old_image_upload_preserves_file(self):
        self.login_admin()
        from django.test.client import encode_multipart
        # Reuse the encoded request body across 307, rather than an exhausted file stream.
        body = encode_multipart('wallstein-upload', {'images': [self.image_upload()]})
        response = self.client.post(f'/fahrzeuge/{self.vehicle.pk}/bilder/', body,
                                    content_type="multipart/form-data; boundary=wallstein-upload", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0], (reverse('vehicle_images', args=[self.vehicle.pk]), 307))
        image = self.vehicle.images.get()
        self.assertTrue(image.image.storage.exists(image.image.name))

    def test_old_management_url_still_requires_login(self):
        response = self.client.get(f'/fahrzeuge/{self.vehicle.pk}/bearbeiten/', follow=True)
        target = reverse('vehicle_update', args=[self.vehicle.pk])
        self.assertEqual(response.redirect_chain, [
            (target, 301), (reverse('login') + '?next=' + target, 302),
        ])
        self.assertTemplateUsed(response, 'management/login.html')


class PublicGalleryTests(VehicleTestCase):
    def setUp(self):
        super().setUp()
        self.first = VehicleImage.objects.create(vehicle=self.vehicle, image=self.image_upload('first.png'), sort_order=1)
        self.cover = VehicleImage.objects.create(vehicle=self.vehicle, image=self.image_upload('cover.png'), sort_order=2,
                                                is_main=True, alt_text='Ansicht von vorne')

    def test_selected_main_image_leads_all_public_views(self):
        for route in ('home', 'public_vehicles'):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, self.cover.image.url)
                self.assertNotContains(response, self.first.image.url)
                self.assertContains(response, 'alt="Ansicht von vorne"')
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertEqual(list(response.context['gallery']), [self.cover, self.first])
        self.assertContains(response, 'alt="Ansicht von vorne"')
        self.assertContains(response, f'href="{self.first.image.url}"')
        self.assertContains(response, 'js/gallery.js')

    def test_missing_main_image_falls_back_to_sort_order(self):
        self.cover.is_main = False
        self.cover.save()
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertEqual(list(response.context['gallery']), [self.first, self.cover])

    def test_empty_gallery_has_no_controls(self):
        self.vehicle.images.all().delete()
        response = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertContains(response, 'Kein Bild vorhanden.')
        self.assertNotContains(response, 'data-gallery-main')

    def test_prefetched_images_do_not_query_per_vehicle(self):
        from .selectors import public_vehicles_with_images
        self.another_vehicle()
        with self.assertNumQueries(2):
            vehicles = list(public_vehicles_with_images())
        with self.assertNumQueries(0):
            for vehicle in vehicles:
                list(vehicle.public_images)


class ManagementInventoryTests(VehicleTestCase):
    def test_inventory_requires_login_and_view_permission(self):
        url = reverse('management_vehicles')
        self.assertEqual(self.client.get(url).status_code, 302)
        user = get_user_model().objects.create_user('reader')
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        from django.contrib.auth.models import Permission
        user.user_permissions.add(Permission.objects.get(content_type__app_label='vehicles', codename='view_vehicle'))
        response = self.client.get(url)
        self.assertContains(response, 'BMW 3er')
        self.assertNotContains(response, reverse('vehicle_update', args=[self.vehicle.pk]))
        self.assertNotContains(response, reverse('vehicle_delete', args=[self.vehicle.pk]))

    def test_search_status_and_visibility(self):
        self.login_admin()
        self.another_vehicle(brand='Audi', status=VehicleStatus.RESERVED)
        for params, brands in [({'q': 'V-001'}, ['BMW']), ({'q': '320d', 'status': 'reserved'}, ['Audi']),
                               ({'visibility': 'hidden'}, ['Audi']), ({'visibility': 'public'}, ['BMW'])]:
            with self.subTest(params=params):
                response = self.client.get(reverse('management_vehicles'), params)
                self.assertEqual([v.brand for v in response.context['page_obj']], brands)

    def test_all_vehicles_are_reachable_through_pagination(self):
        self.login_admin()
        for index in range(22):
            self.another_vehicle(internal_number=f'STOCK-{index}')
        url = reverse('management_vehicles')
        response = self.client.get(url, {'q': 'STOCK', 'visibility': 'public'})
        self.assertEqual(response.context['page_obj'].paginator.count, 22)
        self.assertEqual(len(response.context['page_obj']), 20)
        self.assertContains(response, 'q=STOCK&amp;visibility=public&amp;page=2')
        second = self.client.get(url, {'q': 'STOCK', 'visibility': 'public', 'page': 2})
        self.assertEqual(len(second.context['page_obj']), 2)
        self.assertFalse(set(v.pk for v in response.context['page_obj']) & set(v.pk for v in second.context['page_obj']))

    def test_management_pages_share_shell(self):
        self.login_admin()
        for name, args in [('dashboard', []), ('management_vehicles', []), ('vehicle_create', []),
                           ('vehicle_update', [self.vehicle.pk]), ('vehicle_images', [self.vehicle.pk]),
                           ('vehicle_delete', [self.vehicle.pk])]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'management/base.html')
                self.assertContains(response, reverse('management_vehicles'))
                self.assertEqual(response.content.decode().count('<main '), 1)


class VehicleWorkspaceTests(VehicleTestCase):
    def setUp(self):
        super().setUp()
        self.login_admin()

    def payload(self, **changes):
        data = model_to_dict(self.vehicle, exclude=['id', 'is_published', 'public_visible'])
        data.update(hu_valid_until='')
        data.update(changes)
        return data

    def test_save_stays_on_data_and_preserves_publication_flags(self):
        self.vehicle.public_visible = False
        self.vehicle.save()
        url = reverse('vehicle_update', args=[self.vehicle.pk])
        response = self.client.post(url, self.payload(sale_price='30000.00'), follow=True)
        self.assertRedirects(response, url)
        self.assertContains(response, 'Fahrzeug wurde erfolgreich bearbeitet.')
        self.assertContains(response, 'Bilder hinzufügen')
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.is_published)
        self.assertFalse(self.vehicle.public_visible)
        self.assertEqual(self.vehicle.sale_price, Decimal('30000.00'))

    def test_create_starts_unpublished_and_opens_workspace(self):
        response = self.client.post(reverse('vehicle_create'), self.payload(internal_number='NEW'), follow=True)
        created = Vehicle.objects.get(internal_number='NEW')
        self.assertRedirects(response, reverse('vehicle_update', args=[created.pk]))
        self.assertContains(response, 'Fahrzeug wurde erfolgreich angelegt.')
        self.assertContains(response, reverse('vehicle_images', args=[created.pk]))
        self.assertFalse(created.is_published)
        self.assertFalse(created.public_visible)

    def test_all_sections_keep_vehicle_context_and_active_navigation(self):
        for name in ('vehicle_update', 'vehicle_images', 'vehicle_publication'):
            with self.subTest(name=name):
                url = reverse(name, args=[self.vehicle.pk])
                response = self.client.get(url)
                self.assertContains(response, f'href="{url}" aria-current="page"')
                self.assertContains(response, 'V-001')
                self.assertContains(response, 'Zurück zum Bestand')
                self.assertContains(response, 'data-unsaved-form')
                self.assertContains(response, 'unsaved-changes.js')

    def test_publication_checkbox_controls_flags_but_keeps_sales_status(self):
        url = reverse('vehicle_publication', args=[self.vehicle.pk])
        for status in VehicleStatus.values:
            self.vehicle.status = status
            self.vehicle.save()
            self.assertRedirects(self.client.post(url, {'website_enabled': 'on'}), url)
            self.vehicle.refresh_from_db()
            self.assertTrue(self.vehicle.is_published)
            self.assertTrue(self.vehicle.public_visible)
            self.assertEqual(self.vehicle.status, status)
            self.assertEqual(self.vehicle.is_publicly_listed, status == VehicleStatus.AVAILABLE)
        self.assertRedirects(self.client.post(url, {}), url)
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.is_published)
        self.assertFalse(self.vehicle.public_visible)

    def test_publication_requires_permissions_and_existing_vehicle(self):
        self.assertEqual(self.client.get(reverse('vehicle_publication', args=[999999])).status_code, 404)
        user = get_user_model().objects.create_user('no_access')
        self.client.force_login(user)
        url = reverse('vehicle_publication', args=[self.vehicle.pk])
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.is_publicly_listed)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_invalid_save_keeps_values_and_displays_errors(self):
        url = reverse('vehicle_update', args=[self.vehicle.pk])
        response = self.client.post(url, self.payload(sale_price='-1', variant='Neue Variante'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Neue Variante')
        self.assertContains(response, 'data-unsaved-errors')
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.variant, '320d')
        response = self.client.post(url, {})
        self.assertTrue(response.context['form'].errors)

    def test_grouped_form_covers_every_editable_field_once(self):
        from .forms import VehicleForm
        form = VehicleForm(instance=self.vehicle)
        names = [field.name for title, fields in form.field_groups() for field in fields]
        self.assertCountEqual(names, list(form.fields))
        response = self.client.get(reverse('vehicle_update', args=[self.vehicle.pk]))
        self.assertContains(response, 'value="2022-01-01"')
        self.assertNotContains(response, 'name="is_published"')
        self.assertNotContains(response, 'name="public_visible"')
