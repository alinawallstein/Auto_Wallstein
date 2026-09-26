from decimal import Decimal

from django.urls import reverse

from .financing import calculate_financing
from .models import Homepage
from .tests import VehicleTestCase


class FinancingFlowTests(VehicleTestCase):
    def test_effective_rate_formula_uses_decimal_and_snapshot_values(self):
        result = calculate_financing(Decimal('25000'), Decimal('5000'), 60, Decimal('6.99'))
        self.assertEqual(result['price'], Decimal('25000.00'))
        self.assertEqual(result['annual_rate'], Decimal('6.99'))
        self.assertGreater(result['monthly_rate'], Decimal('0'))

    def test_financing_page_uses_backend_rate_as_display_and_calculation_value(self):
        page = Homepage.objects.create(financing_annual_rate=Decimal('5.99'))
        response = self.client.get(reverse('finanzierung'))
        self.assertContains(response, '5,99 %')
        self.assertContains(response, 'data-value="5.99"')
        self.assertNotContains(response, 'type="number" value="5.99"')
        self.assertEqual(response.context['financing_rate'], page.financing_annual_rate)

    def test_financing_page_has_fallback_when_no_backend_setting_exists(self):
        Homepage.objects.all().delete()
        response = self.client.get(reverse('finanzierung'))
        self.assertContains(response, 'wird vom Verkäufer festgelegt')
        self.assertContains(response, 'data-value=""')

    def test_vehicle_card_links_to_detail_and_detail_view_renders_requested_vehicle(self):
        response = self.client.get(reverse('public_vehicles'))
        self.assertContains(response, reverse('vehicle_detail', args=[self.vehicle.pk]))
        card = response.content.decode().split('<article class="vehicle-card">', 1)[1].split('</article>', 1)[0]
        self.assertNotIn(reverse('finanzierung'), card)
        self.assertIn(reverse('vehicle_detail', args=[self.vehicle.pk]), card)

        detail = self.client.get(reverse('vehicle_detail', args=[self.vehicle.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.context['vehicle'], self.vehicle)
        self.assertContains(detail, f'{self.vehicle.brand} {self.vehicle.model}')
