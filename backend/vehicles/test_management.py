import uuid
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core import mail
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from .models import CustomerInquiry, HeroSlide, Homepage, InquiryReply, InquiryStatus, NewsArticle
from .tests import VehicleTestCase


class InquiryManagementTests(VehicleTestCase):
    def setUp(self):
        super().setUp()
        self.inquiry = CustomerInquiry.objects.create(name='Erika Muster', email='erika@example.com',
            phone='06104 123', vehicle=self.vehicle, message='Ist das Fahrzeug noch verfügbar?', subject='Anfrage zu BMW 3er')

    def reply_data(self):
        return {'body': 'Vielen Dank für Ihre Anfrage.', 'request_id': str(uuid.uuid4())}

    def test_routes_reject_anonymous_and_unprivileged_users(self):
        routes = [('management_inquiries', []), ('inquiry_detail', [self.inquiry.pk]),
                  ('inquiry_status', [self.inquiry.pk]), ('inquiry_reply', [self.inquiry.pk]),
                  ('management_slides', []), ('slide_create', []), ('slider_settings', []), ('dashboard', [])]
        for route, args in routes:
            self.assertEqual(self.client.get(reverse(route, args=args)).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user('visitor'))
        for route, args in routes:
            self.assertEqual(self.client.get(reverse(route, args=args)).status_code, 403)

    def test_inbox_filter_search_sort_and_pagination(self):
        self.login_admin()
        CustomerInquiry.objects.bulk_create([
            CustomerInquiry(name=f'Kunde {n}', email='kunde@example.com', message='Frage', status=InquiryStatus.DONE)
            for n in range(24)])
        response = self.client.get(reverse('management_inquiries'))
        self.assertEqual(len(response.context['page_obj']), 20)
        self.assertContains(response, 'inquiry-new', count=0)  # The oldest inquiry is on page two.
        response = self.client.get(reverse('management_inquiries'), {'status': 'new', 'q': 'Erika'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertContains(response, 'inquiry-new')
        self.assertEqual(self.client.get(reverse('management_inquiries'), {'status': 'unknown'}).context['page_obj'].paginator.count, 0)
        response = self.client.get(reverse('management_inquiries'), {'order': 'oldest'})
        self.assertEqual(response.context['page_obj'][0].pk, self.inquiry.pk)

    def test_original_read_only_status_and_read_transition(self):
        self.login_admin()
        url = reverse('inquiry_detail', args=[self.inquiry.pk])
        response = self.client.get(url)
        self.assertContains(response, self.inquiry.message)
        self.assertNotContains(response, 'name="message"')
        self.assertIn('no-store', response['Cache-Control'])
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, InquiryStatus.READ)
        self.client.post(reverse('inquiry_status', args=[self.inquiry.pk]), {
            'status': InquiryStatus.IN_PROGRESS, 'message': 'Manipuliert', 'email': 'attacker@example.com'})
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, InquiryStatus.IN_PROGRESS)
        self.assertEqual(self.inquiry.message, 'Ist das Fahrzeug noch verfügbar?')
        self.assertEqual(self.inquiry.email, 'erika@example.com')
        self.client.post(reverse('inquiry_status', args=[self.inquiry.pk]), {'status': InquiryStatus.NEW}, follow=True)
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, InquiryStatus.NEW)

    def test_read_only_employee_cannot_change_status_or_reply(self):
        user = get_user_model().objects.create_user('reader')
        user.user_permissions.add(Permission.objects.get(codename='view_customerinquiry'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        response = self.client.get(reverse('inquiry_detail', args=[self.inquiry.pk]))
        self.assertNotContains(response, 'id="reply"')
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, InquiryStatus.NEW)
        for route in ('inquiry_status', 'inquiry_reply'):
            self.assertEqual(self.client.post(reverse(route, args=[self.inquiry.pk]), self.reply_data()).status_code, 403)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
    @patch('vehicles.inquiry_mail.EmailMessage.send', return_value=1)
    def test_successful_reply_uses_original_recipient_and_prevents_duplicate_sends(self, send):
        self.login_admin()
        data = self.reply_data() | {'email': 'attacker@example.com', 'subject': 'Manipuliert', 'message': 'Verändert'}
        url = reverse('inquiry_reply', args=[self.inquiry.pk])
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('inquiry_detail', args=[self.inquiry.pk]))
        reply = InquiryReply.objects.get()
        self.assertEqual(reply.recipient, self.inquiry.email)
        self.assertEqual(reply.subject, 'Re: Anfrage zu BMW 3er')
        self.assertEqual(reply.status, InquiryReply.Status.SENT)
        self.assertIsNotNone(reply.sent_at)
        self.assertEqual(reply.author.username, 'admin')
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.status, InquiryStatus.ANSWERED)
        self.assertEqual(self.inquiry.message, 'Ist das Fahrzeug noch verfügbar?')
        self.client.post(url, data)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(InquiryReply.objects.count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_mail_body_and_test_backend_are_honestly_recorded(self):
        self.login_admin()
        data = self.reply_data()
        self.client.post(reverse('inquiry_reply', args=[self.inquiry.pk]), data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].body, data['body'])
        self.assertEqual(mail.outbox[0].to, ['erika@example.com'])
        self.assertEqual(mail.outbox[0].subject, 'Re: Anfrage zu BMW 3er')
        reply = InquiryReply.objects.get()
        self.assertEqual(reply.status, InquiryReply.Status.TEST)
        self.assertIsNone(reply.sent_at)
        self.inquiry.refresh_from_db()
        self.assertNotEqual(self.inquiry.status, InquiryStatus.ANSWERED)

    @patch('vehicles.inquiry_mail.EmailMessage.send', side_effect=SMTPException('secret transport details'))
    def test_mail_failure_keeps_reply_and_does_not_mark_answered(self, send):
        self.login_admin()
        response = self.client.post(reverse('inquiry_reply', args=[self.inquiry.pk]), self.reply_data(), follow=True)
        self.assertContains(response, 'konnte nicht versendet werden')
        self.assertNotContains(response, 'secret transport details')
        self.assertEqual(InquiryReply.objects.get().status, InquiryReply.Status.FAILED)
        self.inquiry.refresh_from_db()
        self.assertNotEqual(self.inquiry.status, InquiryStatus.ANSWERED)

    @patch('vehicles.inquiry_mail.EmailMessage.send', return_value=0)
    def test_zero_sent_messages_is_a_failure(self, send):
        self.login_admin()
        self.client.post(reverse('inquiry_reply', args=[self.inquiry.pk]), self.reply_data())
        self.assertEqual(InquiryReply.objects.get().status, InquiryReply.Status.FAILED)

    def test_mutations_require_post_and_csrf(self):
        self.login_admin()
        for route in ('inquiry_reply', 'inquiry_status'):
            url = reverse(route, args=[self.inquiry.pk])
            self.assertEqual(self.client.get(url).status_code, 405)
            strict = Client(enforce_csrf_checks=True)
            strict.force_login(get_user_model().objects.get(username='admin'))
            self.assertEqual(strict.post(url, self.reply_data()).status_code, 403)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)

    def test_empty_reply_invalid_status_and_native_admin_cannot_overwrite_original(self):
        self.login_admin()
        response = self.client.post(reverse('inquiry_reply', args=[self.inquiry.pk]), {'body': '', 'request_id': str(uuid.uuid4())})
        self.assertIn('body', response.context['reply_form'].errors)
        self.assertFalse(InquiryReply.objects.exists())
        response = self.client.post(reverse('inquiry_status', args=[self.inquiry.pk]), {'status': 'fake'})
        self.assertIn('status', response.context['status_form'].errors)
        self.client.post(reverse('admin:vehicles_customerinquiry_change', args=[self.inquiry.pk]), {
            'status': InquiryStatus.DONE, 'name': 'Changed', 'message': 'Changed', '_save': 'Save'})
        self.inquiry.refresh_from_db()
        self.assertEqual(self.inquiry.name, 'Erika Muster')
        self.assertEqual(self.inquiry.message, 'Ist das Fahrzeug noch verfügbar?')
        self.assertEqual(self.inquiry.status, InquiryStatus.DONE)

    @patch('vehicles.inquiry_mail.send_mail', side_effect=SMTPException())
    def test_notification_failure_does_not_break_public_contact(self, send):
        response = self.client.post(reverse('kontakt'), {
            'inquiry_type': 'vehicle_request', 'name': 'Neuer Kunde', 'email': 'new@example.com', 'message': 'Hallo'})
        self.assertContains(response, 'Vielen Dank')
        self.assertTrue(CustomerInquiry.objects.filter(name='Neuer Kunde').exists())

    def test_dashboard_counts_and_permissions(self):
        self.login_admin()
        finance = CustomerInquiry.objects.create(
            inquiry_type='financing_request', name='Finanzkunde', email='finance@example.com',
            vehicle=self.vehicle, message='Bitte Finanzierung anbieten.',
            financing_monthly_rate='350.00',
        )
        NewsArticle.objects.create(title='Aktuelle Meldung', excerpt='Kurzer Teaser', status='published',
                                   published_at=timezone.now())
        NewsArticle.objects.create(title='Interner Entwurf', excerpt='Noch nicht veröffentlicht')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['inquiry_stats']['new'], 2)
        self.assertEqual(response.context['inquiry_stats']['financing_new'], 1)
        self.assertEqual(response.context['stats']['public'], 1)
        self.assertEqual(len(response.context['inquiry_activity']), 30)
        self.assertEqual(response.context['news_stats']['published'], 1)
        self.assertEqual(response.context['news_stats']['drafts'], 1)
        self.assertEqual(response.context['recent_financing'][0], finance)
        self.assertContains(response, 'Zuletzt hinzugefügt')
        self.assertContains(response, 'Fahrzeugbestand')
        user = get_user_model().objects.create_user('inbox-only')
        user.user_permissions.add(Permission.objects.get(codename='view_customerinquiry'))
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))
        self.assertNotIn('stats', response.context)
        self.assertNotContains(response, 'Fahrzeugübersicht')

    def test_inquiry_type_filter_supports_financing_dashboard_link(self):
        self.login_admin()
        finance = CustomerInquiry.objects.create(inquiry_type='financing_request', name='Finanzkunde',
            email='finance@example.com', message='Finanzierung')
        response = self.client.get(reverse('management_inquiries'), {'inquiry_type': 'financing_request'})
        self.assertContains(response, 'Finanzkunde')
        self.assertNotContains(response, self.inquiry.name)

    def test_dashboard_empty_states_and_zero_chart_data(self):
        self.login_admin()
        self.vehicle.delete()
        CustomerInquiry.objects.all().delete()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['stats']['total'], 0)
        self.assertEqual(response.context['inquiry_stats']['total'], 0)
        self.assertEqual(sum(day['count'] for day in response.context['inquiry_activity']), 0)
        self.assertEqual(response.context['news_stats']['published'], 0)
        self.assertContains(response, 'Noch keine Kundenanfragen vorhanden.')
        self.assertContains(response, 'Keine Fahrzeuge gefunden.')
        self.assertContains(response, 'Noch keine News vorhanden.')

    def test_dashboard_query_count_does_not_grow_with_recent_vehicles(self):
        self.login_admin()
        self.client.get(reverse('dashboard'))
        with CaptureQueriesContext(connection) as one_vehicle_queries:
            self.client.get(reverse('dashboard'))
        for index in range(4):
            self.another_vehicle(internal_number=f'DASH-{index}')
        with CaptureQueriesContext(connection) as five_vehicle_queries:
            self.client.get(reverse('dashboard'))
        self.assertEqual(len(one_vehicle_queries), len(five_vehicle_queries))


class SliderManagementTests(VehicleTestCase):
    def test_upload_edit_delete_and_order(self):
        self.login_admin()
        data = {'title': 'Erster Slide', 'image': self.image_upload(), 'sort_order': 20, 'is_active': 'on'}
        self.assertEqual(self.client.post(reverse('slide_create'), data).status_code, 302)
        slide = HeroSlide.objects.get()
        self.assertContains(self.client.get(reverse('home')), 'Erster Slide')
        self.client.post(reverse('slide_create'), {'title': 'Zweiter Slide', 'image': self.image_upload(), 'sort_order': 10, 'is_active': 'on'})
        slides = self.client.get(reverse('home')).context['hero_slides']
        self.assertEqual([s['title'] for s in slides], ['Zweiter Slide', 'Erster Slide'])
        self.client.post(reverse('slide_edit', args=[slide.pk]), {'title': 'Geändert', 'sort_order': 0})
        slide.refresh_from_db()
        self.assertFalse(slide.is_active)
        self.assertTrue(slide.image)
        self.assertNotContains(self.client.get(reverse('home')), 'Geändert')
        self.assertEqual(self.client.get(reverse('slide_delete', args=[slide.pk])).status_code, 200)
        self.assertTrue(HeroSlide.objects.filter(pk=slide.pk).exists())
        self.client.post(reverse('slide_delete', args=[slide.pk]))
        self.assertFalse(HeroSlide.objects.filter(pk=slide.pk).exists())

    def test_interval_validation_persistence_and_public_context(self):
        self.login_admin()
        page = Homepage.objects.create(draft={'welcome_title': 'Entwurf'}, published={'welcome_title': 'Live'}, revision=7)
        url = reverse('slider_settings')
        for value in (1, 16, 31, 'invalid', '2.5'):
            response = self.client.post(url, {'slider_interval': value})
            self.assertIn('slider_interval', response.context['form'].errors)
            self.assertNotContains(response, 'data-slider-saved-interval')
        response = self.client.post(url, {'slider_interval': 3})
        self.assertRedirects(response, url)
        page.refresh_from_db()
        self.assertEqual(page.slider_interval, 3)
        self.assertEqual(page.draft, {'welcome_title': 'Entwurf'})
        self.assertEqual(page.revision, 7)
        for route in ('home', 'homepage_preview'):
            response = self.client.get(reverse(route))
            self.assertContains(response, 'data-interval="3"')
            self.assertNotContains(response, 'data-hero-toggle')

    def test_settings_have_separate_permission(self):
        user = get_user_model().objects.create_user('slides')
        user.user_permissions.add(Permission.objects.get(codename='view_heroslide'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('management_slides')).status_code, 200)
        self.assertEqual(self.client.get(reverse('slider_settings')).status_code, 403)
        self.assertEqual(self.client.post(reverse('slide_create'), {}).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename='change_slider_settings'))
        self.assertEqual(self.client.post(reverse('slider_settings'), {'slider_interval': 5}).status_code, 302)
        self.assertEqual(Homepage.objects.get().slider_interval, 5)
