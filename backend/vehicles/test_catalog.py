from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from .tests import VehicleTestCase
from .models import Accessory, AccessoryImage, Homepage, HomepageImage, NewsArticle
from .content_schema import TEXT_FIELDS


class CatalogTests(VehicleTestCase):
    def setUp(self):
        super().setUp()
        self.item = Accessory.objects.create(title='Winterreifen', category='tires', description='Vier Reifen', price=200)

    def payload(self, **changes):
        data = {'title': 'Sommerreifen', 'category': 'tires', 'condition': 'used', 'price': '250.00',
                'description': 'Vier Reifen', 'status': 'available',
                'images-TOTAL_FORMS': '1', 'images-INITIAL_FORMS': '0',
                'images-0-image': self.image_upload(), 'images-0-sort_order': '0'}
        data.update(changes)
        return data

    def test_public_visibility_and_detail(self):
        for published in (False, True):
            for status in ('available', 'reserved', 'sold'):
                self.item.is_published = published
                self.item.status = status
                self.item.save()
                expected = published and status == 'available'
                self.assertEqual(self.client.get(reverse('accessory_detail', args=[self.item.pk])).status_code, 200 if expected else 404)
                self.assertEqual(self.item in self.client.get(reverse('public_accessories')).context['page_obj'], expected)

    def test_create_edit_with_images_and_delete(self):
        self.login_admin()
        response = self.client.post(reverse('accessory_create'), self.payload())
        created = Accessory.objects.get(title='Sommerreifen')
        self.assertRedirects(response, reverse('accessory_edit', args=[created.pk]))
        image = created.images.get()
        self.assertTrue(image.image.storage.exists(image.image.name))
        data = self.payload(title='Sommerreifen neu', **{'images-INITIAL_FORMS': '1', 'images-0-id': image.pk, 'images-0-DELETE': 'on'})
        data.pop('images-0-image')
        self.assertRedirects(self.client.post(reverse('accessory_edit', args=[created.pk]), data), reverse('accessory_edit', args=[created.pk]))
        self.assertFalse(created.images.exists())
        url = reverse('accessory_delete', args=[created.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Accessory.objects.filter(pk=created.pk).exists())
        self.assertRedirects(self.client.post(url), reverse('management_accessories'))
        self.assertFalse(Accessory.objects.filter(pk=created.pk).exists())

    def test_invalid_image_and_price_do_not_create_offer(self):
        self.login_admin()
        data = self.payload(price='-1', **{'images-0-image': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')})
        response = self.client.post(reverse('accessory_create'), data)
        self.assertIn('price', response.context['form'].errors)
        self.assertTrue(response.context['images'].errors)
        self.assertEqual(Accessory.objects.count(), 1)
        self.assertFalse(AccessoryImage.objects.exists())

    def test_permissions_cover_mutations(self):
        user = get_user_model().objects.create_user('reader')
        user.user_permissions.add(Permission.objects.get(codename='view_accessory'))
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('management_accessories')).status_code, 200)
        for name, args in [('accessory_create', []), ('accessory_edit', [self.item.pk]), ('accessory_delete', [self.item.pk])]:
            self.assertEqual(self.client.post(reverse(name, args=args), self.payload()).status_code, 403)
        self.assertEqual(Accessory.objects.count(), 1)

    def test_foreign_image_cannot_be_deleted(self):
        self.login_admin()
        other = Accessory.objects.create(title='Anderes Angebot', category='other', price=10, description='Andere')
        image = AccessoryImage.objects.create(accessory=other, image=self.image_upload())
        data = self.payload(**{'images-INITIAL_FORMS': '1', 'images-0-id': image.pk, 'images-0-DELETE': 'on'})
        self.client.post(reverse('accessory_edit', args=[self.item.pk]), data)
        self.assertTrue(AccessoryImage.objects.filter(pk=image.pk, accessory=other).exists())


class HomepageEditingTests(VehicleTestCase):
    def payload(self, **changes):
        data = {key: default for key, label, default, group in TEXT_FIELDS}
        data.update(revision=0, action='save')
        data.update(changes)
        return data

    def test_draft_preview_publish_and_escaping(self):
        self.login_admin()
        url = reverse('homepage_edit')
        title = '<script>alert(1)</script>'
        self.assertRedirects(self.client.post(url, self.payload(hero_title=title)), url)
        self.assertNotContains(self.client.get(reverse('home')), '&lt;script&gt;')
        preview = self.client.get(reverse('homepage_preview'))
        self.assertContains(preview, '&lt;script&gt;')
        self.assertNotContains(preview, title)
        self.assertIn('no-store', preview['Cache-Control'])
        self.assertEqual(preview['X-Robots-Tag'], 'noindex, nofollow')
        self.assertRedirects(self.client.post(url, self.payload(hero_title=title, revision=1, action='publish')), url)
        self.assertContains(self.client.get(reverse('home')), '&lt;script&gt;')
        self.assertIsNotNone(Homepage.objects.get().published_at)

    def test_stale_revision_does_not_overwrite(self):
        self.login_admin()
        url = reverse('homepage_edit')
        self.client.post(url, self.payload(hero_title='Erste Fassung'))
        response = self.client.post(url, self.payload(hero_title='Veraltete Fassung'))
        self.assertTrue(response.context['form'].non_field_errors())
        self.assertEqual(Homepage.objects.get().draft['hero_title'], 'Erste Fassung')

    def test_images_remain_draft_until_publication_and_can_reset(self):
        self.login_admin()
        url = reverse('homepage_edit')
        self.client.post(url, self.payload(vehicles_image=self.image_upload()))
        image = HomepageImage.objects.get()
        self.assertNotContains(self.client.get(reverse('home')), image.image.url)
        self.assertContains(self.client.get(reverse('homepage_preview')), image.image.url)
        self.client.post(url, self.payload(revision=1, action='publish'))
        self.assertNotContains(self.client.get(url), 'Unveröffentlichte Änderungen')
        self.assertContains(self.client.get(reverse('home')), image.image.url)
        self.client.post(url, self.payload(revision=2, action='publish', vehicles_image_reset='on'))
        self.assertNotContains(self.client.get(reverse('home')), image.image.url)

    def test_invalid_content_is_not_saved(self):
        self.login_admin()
        response = self.client.post(reverse('homepage_edit'), self.payload(email='invalid', vehicles_image=SimpleUploadedFile('bad.png', b'bad')))
        self.assertIn('email', response.context['form'].errors)
        self.assertIn('vehicles_image', response.context['form'].errors)
        self.assertFalse(Homepage.objects.exists())

    def test_editor_permissions_and_preview_access(self):
        for route in ('homepage_edit', 'homepage_preview'):
            self.assertEqual(self.client.get(reverse(route)).status_code, 302)
        user = get_user_model().objects.create_user('editor')
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse('homepage_edit'), self.payload()).status_code, 403)
        self.assertEqual(self.client.get(reverse('homepage_preview')).status_code, 403)
        user.user_permissions.add(Permission.objects.get(codename='change_homepage'))
        self.assertEqual(self.client.get(reverse('homepage_edit')).status_code, 200)


class NewsTests(VehicleTestCase):
    def test_draft_publication_and_public_rendering(self):
        self.login_admin()
        data = {'title': 'Neu bei uns', 'excerpt': 'Kurztext', 'body': '<script>unsafe</script>', 'image': self.image_upload()}
        response = self.client.post(reverse('news_create'), data)
        article = NewsArticle.objects.get()
        self.assertRedirects(response, reverse('news_edit', args=[article.pk]))
        self.assertEqual(self.client.get(reverse('news_detail', args=[article.pk])).status_code, 404)
        data.pop('image')
        data['is_published'] = 'on'
        self.client.post(reverse('news_edit', args=[article.pk]), data)
        article.refresh_from_db()
        self.assertIsNotNone(article.published_at)
        response = self.client.get(reverse('news_detail', args=[article.pk]))
        self.assertContains(response, '&lt;script&gt;')
        self.assertContains(self.client.get(reverse('home')), 'Neu bei uns')
        self.assertRedirects(self.client.post(reverse('news_delete', args=[article.pk])), reverse('management_news'))
        self.assertFalse(NewsArticle.objects.exists())

    def test_noneditor_cannot_create_news(self):
        self.client.force_login(get_user_model().objects.create_user('reader'))
        self.assertEqual(self.client.post(reverse('news_create'), {}).status_code, 403)


class ContentAccessTests(VehicleTestCase):
    def test_draft_previews_are_private_and_not_cached(self):
        accessory = Accessory.objects.create(title='Entwurf', category='other', price=10, description='Entwurf')
        article = NewsArticle.objects.create(title='Entwurf', excerpt='Entwurf', body='Entwurf')
        for name, pk in [('accessory_preview', accessory.pk), ('news_preview', article.pk)]:
            self.assertEqual(self.client.get(reverse(name, args=[pk])).status_code, 302)
        self.login_admin()
        for name, pk in [('accessory_preview', accessory.pk), ('news_preview', article.pk)]:
            response = self.client.get(reverse(name, args=[pk]))
            self.assertEqual(response.status_code, 200)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')

    def test_content_only_editor_can_login_to_content_area(self):
        user = get_user_model().objects.create_user('content_editor', password='test-editor-password')
        user.user_permissions.add(Permission.objects.get(codename='change_homepage'))
        response = self.client.post(reverse('login'), {'username': 'content_editor', 'password': 'test-editor-password'}, follow=True)
        self.assertRedirects(response, reverse('dashboard'))
        self.assertContains(response, 'Website-Inhalte')
        self.assertNotContains(response, 'href="' + reverse('management_vehicles') + '"')

    def test_all_editable_homepage_fields_are_used(self):
        from pathlib import Path
        from django.conf import settings
        from .content_schema import IMAGE_FIELDS
        template = (Path(settings.BASE_DIR) / 'templates/public/home.html').read_text()
        template += (Path(settings.BASE_DIR) / 'vehicles/slider.py').read_text()
        for key, *_ in TEXT_FIELDS:
            self.assertTrue('site_content.' + key in template or "content['" + key + "']" in template, key)
        from .content import homepage_content
        content = homepage_content({})
        for key, *_ in IMAGE_FIELDS:
            self.assertIn(key, content)
        self.assertIn("partials/hero_slider.html", template)

    def test_oversized_image_is_rejected(self):
        from .catalog_forms import validate_photo
        from django.core.exceptions import ValidationError
        image = self.image_upload()
        image.size = 11 * 1024 * 1024
        with self.assertRaises(ValidationError):
            validate_photo(image)

    def test_new_templates_compile(self):
        from django.template.loader import get_template
        for name in ('admin/catalog_list.html', 'admin/catalog_form.html', 'admin/catalog_delete.html',
                     'admin/homepage_form.html', 'public/accessories.html', 'public/accessory_detail.html',
                     'public/news.html', 'public/news_detail.html'):
            get_template(name)

    def test_offer_without_images_can_be_saved_as_draft(self):
        self.login_admin()
        data = {'title': 'Ohne Bilder', 'category': 'parts', 'condition': 'used', 'price': '10',
                'description': 'Noch in Vorbereitung', 'status': 'available',
                'images-TOTAL_FORMS': '3', 'images-INITIAL_FORMS': '0'}
        for index in range(3):
            data[f'images-{index}-sort_order'] = '0'
        response = self.client.post(reverse('accessory_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Accessory.objects.get(title='Ohne Bilder').is_published)
