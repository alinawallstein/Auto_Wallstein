from decimal import Decimal

from django.core import mail
from django.test import override_settings
from django.urls import reverse

from .financing import calculate_financing
from .models import CustomerInquiry
from .tests import VehicleTestCase


class FinancingFlowTests(VehicleTestCase):
    def test_effective_rate_formula_uses_decimal_and_snapshot_values(self):
        result = calculate_financing(Decimal('25000'), Decimal('5000'), 60, Decimal('6.99'))
        self.assertEqual(result['price'], Decimal('25000.00'))
        self.assertEqual(result['annual_rate'], Decimal('6.99'))
        self.assertGreater(result['monthly_rate'], Decimal('0'))

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_financing_inquiry_recalculates_server_side_and_saves_snapshot(self):
        response = self.client.post(reverse('financing_inquiry', args=[self.vehicle.pk]), {
            'first_name': 'Erika', 'last_name': 'Muster', 'email': 'erika@example.com', 'phone': '06104 123',
            'downpayment': '5000', 'term_months': '60', 'message': 'Bitte melden Sie sich.'})
        self.assertEqual(response.status_code, 200)
        inquiry = CustomerInquiry.objects.get(inquiry_type='financing_request')
        self.assertEqual(inquiry.financing_vehicle_price, self.vehicle.sale_price)
        self.assertEqual(inquiry.financing_annual_rate, Decimal('6.99'))
        self.assertIsNotNone(inquiry.financing_monthly_rate)
        self.assertEqual(len(mail.outbox), 2)
