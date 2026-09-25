from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import CustomerInquiry, Vehicle, VehicleStatus


class InquiryFlowTests(TestCase):
    def setUp(self):
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

    def test_vehicle_inquiry_can_be_submitted(self):
        response = self.client.post(
            reverse("contact"),
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

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

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
