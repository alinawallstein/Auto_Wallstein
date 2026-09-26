from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .admin import HeroSlideAdminForm
from .content import homepage_content
from .models import HeroSlide, Homepage, HomepageImage
from .slider import homepage_slides
from .slider_validation import validate_slide_link
from .tests import VehicleTestCase


class HeroSlideTests(VehicleTestCase):
    def slide(self, **changes):
        values = dict(title='Mercedes-Benz entdecken', image=self.image_upload(), is_active=True)
        values.update(changes)
        return HeroSlide.objects.create(**values)

    def test_empty_slider_has_fallback_and_no_controls(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['hero_slides']), 1)
        self.assertContains(response, '/static/images/titelbild.jpeg')
        self.assertNotContains(response, 'data-hero-controls')

    def test_active_order_and_one_database_query(self):
        third = self.slide(title='Dritter', sort_order=20)
        first = self.slide(title='Erster', sort_order=10)
        second = self.slide(title='Zweiter', sort_order=10)
        self.slide(title='Nicht öffentlich', is_active=False)
        content = homepage_content({})
        with self.assertNumQueries(1):
            slides = homepage_slides(content)
        self.assertEqual([s['title'] for s in slides], [first.title, second.title, third.title])
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'data-hero-controls')
        self.assertContains(response, 'data-hero-dot', count=3)
        self.assertNotContains(response, 'Nicht öffentlich')

    def test_single_slide_optional_copy_and_button(self):
        slide = self.slide(title='', subtitle='', image_alt='Silberne Limousine')
        response = self.client.get(reverse('home'))
        self.assertContains(response, slide.image.url)
        self.assertContains(response, 'alt="Silberne Limousine"')
        self.assertNotContains(response, 'data-hero-controls')
        self.assertNotContains(response, 'hero-slider__button')
        self.assertContains(response, 'fetchpriority="high"')

    def test_content_is_escaped_and_unsafe_stored_links_are_not_rendered(self):
        self.slide(title='<script>alert(1)</script>', subtitle='<b>Text</b>',
                   button_text='Klicken', button_url='javascript:alert(1)')
        response = self.client.get(reverse('home'))
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(response, '&lt;b&gt;Text&lt;/b&gt;')
        self.assertNotContains(response, 'javascript:')
        self.assertNotContains(response, 'hero-slider__button')

    def test_link_validation(self):
        for value in ('/fahrzeuge/', '/kontakt/?inquiry_type=test_drive', 'https://example.com/cars', ''):
            validate_slide_link(value)
        for value in ('javascript:alert(1)', 'data:text/html,hi', '//evil.com', '/\\evil.com',
                      '/\nevil.com', 'https://user:password@example.com', 'ftp://example.com'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_slide_link(value)
        with self.assertRaises(ValidationError):
            self.slide(button_text='Ohne Link').clean()

    def test_missing_image_file_does_not_break_rendering(self):
        self.slide(image='homepage/missing.jpg')
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        HeroSlide.objects.update(image='')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mercedes-Benz entdecken')

    def test_admin_upload_edit_activate_and_delete(self):
        self.login_admin()
        self.assertContains(self.client.get(reverse('admin:index')), 'Startseiten-Slides')
        self.assertContains(self.client.get(reverse('admin:vehicles_heroslide_add')), 'multipart/form-data')
        data = {'title': 'Neues Angebot', 'subtitle': 'Jetzt entdecken', 'image': self.image_upload(),
                'image_alt': 'Schwarze Limousine', 'button_text': 'Angebote', 'button_url': '/fahrzeuge/',
                'sort_order': 10, 'is_active': 'on', '_save': 'Speichern'}
        response = self.client.post(reverse('admin:vehicles_heroslide_add'), data)
        self.assertEqual(response.status_code, 302)
        slide = HeroSlide.objects.get()
        self.assertTrue(slide.image.storage.exists(slide.image.name))
        self.assertContains(self.client.get(reverse('home')), 'Neues Angebot')
        listing = self.client.get(reverse('admin:vehicles_heroslide_changelist'))
        self.assertContains(listing, 'hero-admin-preview')
        self.assertContains(listing, 'name="form-0-sort_order"')
        # Saving without a new file must preserve the existing upload.
        data.pop('image')
        data.pop('is_active')
        data['sort_order'] = 30
        response = self.client.post(reverse('admin:vehicles_heroslide_change', args=[slide.pk]), data)
        self.assertEqual(response.status_code, 302)
        slide.refresh_from_db()
        self.assertFalse(slide.is_active)
        self.assertEqual(slide.sort_order, 30)
        self.assertTrue(slide.image)
        self.assertNotContains(self.client.get(reverse('home')), 'Neues Angebot')
        response = self.client.post(reverse('admin:vehicles_heroslide_delete', args=[slide.pk]), {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HeroSlide.objects.exists())

    def test_admin_template_isolation_and_permissions(self):
        response = self.client.get(reverse('admin:login'))
        self.assertContains(response, 'name="next"')
        self.assertNotContains(response, 'management-header')
        user = get_user_model().objects.create_user('slide-editor', is_staff=True)
        self.client.force_login(user)
        url = reverse('admin:vehicles_heroslide_changelist')
        self.assertEqual(self.client.get(url).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename='view_heroslide'))
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:vehicles_heroslide_add')).status_code, 403)

    def test_invalid_uploads_are_rejected(self):
        for upload in (SimpleUploadedFile('fake.png', b'not an image'),):
            form = HeroSlideAdminForm(data={'sort_order': 0}, files={'image': upload})
            self.assertFalse(form.is_valid())
            self.assertIn('image', form.errors)
        upload = self.image_upload()
        upload.size = 11 * 1024 * 1024
        form = HeroSlideAdminForm(data={'sort_order': 0}, files={'image': upload})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_homepage_content_is_not_queried_twice(self):
        Homepage.objects.create()
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse('home'))
        reads = [q['sql'] for q in queries if 'FROM "vehicles_homepage"' in q['sql']]
        self.assertEqual(len(reads), 1)

    def test_old_editor_has_no_competing_slider_uploads(self):
        self.login_admin()
        response = self.client.get(reverse('homepage_edit'))
        self.assertContains(response, reverse('admin:vehicles_heroslide_changelist'))
        self.assertNotIn('hero_image', response.context['form'].fields)

    def test_data_import_preserves_files_and_draft_visibility(self):
        published = HomepageImage.objects.create(image=self.image_upload('published.png'))
        draft = HomepageImage.objects.create(image=self.image_upload('draft.png'))
        page = Homepage.objects.create(published={'hero_image_2': published.pk, 'hero_title': 'Öffentlich'},
                                       draft={'hero_image_2': published.pk, 'hero_image_3': draft.pk})
        migration = import_module('vehicles.migrations.0004_import_homepage_slides')
        migration.import_slides(apps, SimpleNamespace(connection=connection))
        self.assertEqual(HeroSlide.objects.count(), 2)
        self.assertTrue(HeroSlide.objects.get(image=published.image.name).is_active)
        self.assertFalse(HeroSlide.objects.get(image=draft.image.name).is_active)
        page.refresh_from_db()
        self.assertEqual(page.draft['hero_image_3'], draft.pk)
        self.assertTrue(draft.image.storage.exists(draft.image.name))
