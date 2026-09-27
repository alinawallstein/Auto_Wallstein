from importlib import import_module
from io import BytesIO
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from .slider_forms import HeroSlideForm
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
        self.assertContains(response, slide.crop_rendered.url)
        self.assertContains(response, 'alt="Silberne Limousine"')
        self.assertNotContains(response, 'data-hero-controls')
        self.assertNotContains(response, 'hero-slider__button')
        self.assertContains(response, 'fetchpriority="high"')

    def test_saved_crops_are_passed_to_desktop_and_mobile_slider_sources(self):
        slide = self.slide(crop_x=25, crop_y=15, crop_width=50, crop_height=17,
                           mobile_crop_x=25, mobile_crop_y=15, mobile_crop_width=30, mobile_crop_height=24.59)
        context_slides = homepage_slides(homepage_content({}))
        self.assertEqual(context_slides[0]['image_url'], slide.crop_rendered.url)
        response = self.client.get(reverse('home'))
        self.assertContains(response, slide.crop_rendered.url)
        self.assertContains(response, slide.mobile_crop_rendered.url)

    def test_slide_form_has_crop_values(self):
        form = HeroSlideForm()
        self.assertEqual(form.fields['crop_x'].initial, 0)
        self.assertEqual(form.fields['crop_y'].initial, 0)
        self.assertTrue(form.fields['crop_x'].widget.is_hidden)
        self.assertTrue(form.fields['crop_y'].widget.is_hidden)
        self.assertTrue(form.fields['crop_width'].widget.is_hidden)
        self.assertTrue(form.fields['crop_height'].widget.is_hidden)
        self.assertTrue(form.fields['mobile_crop_x'].widget.is_hidden)
        self.assertTrue(form.fields['image_scale'].widget.is_hidden)
        self.assertTrue(form.fields['image_offset_x'].widget.is_hidden)

    def test_crop_values_are_validated(self):
        for values in ({'crop_x': 101}, {'crop_y': 101}, {'crop_width': 0}, {'crop_height': 0}, {'crop_x': 90, 'crop_width': 20}):
            data = {'crop_x': 0, 'crop_y': 0, 'crop_width': 100, 'crop_height': 35, **values}
            form = HeroSlideForm(data=data, files={'image': self.image_upload()})
            self.assertFalse(form.is_valid(), values)

    def test_scale_and_position_values_are_validated_separately_from_crop(self):
        base = {'crop_x': 10, 'crop_y': 20, 'crop_width': 50, 'crop_height': 17,
                'image_scale': 0.8, 'image_offset_x': 3, 'image_offset_y': -4,
                'mobile_crop_x': 0, 'mobile_crop_y': 0, 'mobile_crop_width': 50, 'mobile_crop_height': 40,
                'mobile_image_scale': 1, 'mobile_image_offset_x': 0, 'mobile_image_offset_y': 0}
        form = HeroSlideForm(data={**base, 'sort_order': 0}, files={'image': self.image_upload()})
        self.assertTrue(form.is_valid(), form.errors)
        for key, value in (('image_scale', 1.31), ('mobile_image_scale', 0.59), ('image_offset_x', 50.01), ('mobile_image_offset_y', -50.01)):
            values = {**base, key: value}
            self.assertFalse(HeroSlideForm(data={**values, 'sort_order': 0}, files={'image': self.image_upload()}).is_valid(), key)

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
        slide = HeroSlide.objects.create(title='Fehlendes Bild', image='homepage/missing.jpg', is_active=True)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        HeroSlide.objects.update(image='')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '/media/homepage/missing.jpg')

    def test_crop_derivative_matches_slider_ratio_and_original_is_preserved(self):
        source = Image.new('RGB', (200, 100))
        for x in range(200):
            for y in range(100):
                source.putpixel((x, y), (220, 0, 0) if x < 100 else (0, 0, 220))
        buffer = BytesIO()
        source.save(buffer, 'PNG')
        upload = SimpleUploadedFile('two-halves.png', buffer.getvalue(), content_type='image/png')
        slide = self.slide(image=upload, crop_x=0, crop_y=33, crop_width=50, crop_height=34,
                           mobile_crop_x=0, mobile_crop_y=0, mobile_crop_width=50, mobile_crop_height=81.97)
        original_name = slide.image.name
        original_bytes = slide.image.read()
        with Image.open(slide.crop_rendered.path) as rendered:
            self.assertAlmostEqual(rendered.width / rendered.height, HeroSlide.CROP_ASPECT, places=2)
            pixel = rendered.getpixel((rendered.width // 2, rendered.height // 2))
            self.assertGreater(pixel[0], 170)
            self.assertLess(pixel[2], 70)
        with Image.open(slide.mobile_crop_rendered.path) as rendered:
            self.assertAlmostEqual(rendered.width / rendered.height, HeroSlide.MOBILE_CROP_ASPECT, places=2)
        previous_render = slide.crop_rendered.name
        slide.crop_x = 50
        slide.save()
        slide.refresh_from_db()
        self.assertEqual(slide.crop_x, 50)
        self.assertEqual(slide.mobile_crop_x, 0)
        with Image.open(slide.crop_rendered.path) as rendered:
            pixel = rendered.getpixel((rendered.width // 2, rendered.height // 2))
            self.assertGreater(pixel[2], 170)
            self.assertLess(pixel[0], 70)
        self.assertNotEqual(slide.crop_rendered.name, previous_render)
        self.assertTrue(slide.image.storage.exists(original_name))
        with slide.image.open('rb') as original:
            self.assertEqual(original.read(), original_bytes)

    def test_picture_zoom_keeps_crop_frame_values_and_uses_background_for_empty_edges(self):
        slide = self.slide(crop_x=25, crop_y=10, crop_width=50, crop_height=17)
        crop_data = (slide.crop_x, slide.crop_y, slide.crop_width, slide.crop_height)
        previous_render = slide.crop_rendered.name
        slide.image_scale = 0.7
        slide.image_offset_x = 10
        slide.save()
        slide.refresh_from_db()
        self.assertEqual((slide.crop_x, slide.crop_y, slide.crop_width, slide.crop_height), crop_data)
        self.assertEqual((float(slide.image_scale), float(slide.image_offset_x)), (0.7, 10))
        self.assertNotEqual(slide.crop_rendered.name, previous_render)
        with Image.open(slide.crop_rendered.path) as rendered:
            self.assertAlmostEqual(rendered.width / rendered.height, HeroSlide.CROP_ASPECT, places=2)
            self.assertEqual(rendered.mode, 'RGB')

    def test_crop_initialization_handles_landscape_portrait_and_panorama(self):
        for name, size in (('landscape-16x9.png', (1600, 900)), ('portrait.png', (900, 1600)), ('panorama.png', (2800, 1000))):
            with self.subTest(image=size):
                buffer = BytesIO()
                Image.new('RGB', size, color='navy').save(buffer, 'PNG')
                slide = self.slide(image=SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png'))
                with Image.open(slide.crop_rendered.path) as desktop, Image.open(slide.mobile_crop_rendered.path) as mobile:
                    self.assertAlmostEqual(desktop.width / desktop.height, HeroSlide.CROP_ASPECT, places=2)
                    self.assertAlmostEqual(mobile.width / mobile.height, HeroSlide.MOBILE_CROP_ASPECT, places=2)
                self.assertGreaterEqual(slide.crop_x, 0)
                self.assertLessEqual(slide.crop_x + slide.crop_width, 100)
                self.assertGreaterEqual(slide.mobile_crop_y, 0)
                self.assertLessEqual(slide.mobile_crop_y + slide.mobile_crop_height, 100)

    def test_admin_upload_edit_activate_and_delete(self):
        self.login_admin()
        self.assertContains(self.client.get(reverse('admin:index')), 'Startseiten-Slides')
        self.assertContains(self.client.get(reverse('admin:vehicles_heroslide_add')), 'multipart/form-data')
        data = {'title': 'Neues Angebot', 'subtitle': 'Jetzt entdecken', 'image': self.image_upload(),
                'crop_x': 0, 'crop_y': 0, 'crop_width': 100, 'crop_height': 35,
                'mobile_crop_x': 0, 'mobile_crop_y': 0, 'mobile_crop_width': 100, 'mobile_crop_height': 35,
                'image_scale': 1, 'image_offset_x': 0, 'image_offset_y': 0,
                'mobile_image_scale': 1, 'mobile_image_offset_x': 0, 'mobile_image_offset_y': 0,
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
            form = HeroSlideForm(data={'sort_order': 0}, files={'image': upload})
            self.assertFalse(form.is_valid())
            self.assertIn('image', form.errors)
        upload = self.image_upload()
        upload.size = 11 * 1024 * 1024
        form = HeroSlideForm(data={'sort_order': 0}, files={'image': upload})
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
        self.assertContains(response, reverse('management_slides'))
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
