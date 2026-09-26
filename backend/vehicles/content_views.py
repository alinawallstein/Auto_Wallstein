from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .content import homepage_content
from .slider import homepage_slides
from .content_forms import HomepageForm
from .content_schema import TEXT_FIELDS, IMAGE_FIELDS
from .models import Homepage, HomepageImage
from .selectors import public_news_items, public_vehicles_with_images


@login_required(login_url='login')
@permission_required('vehicles.change_homepage', raise_exception=True)
def homepage_edit(request):
    page = Homepage.objects.filter(pk=1).first() or Homepage(pk=1)
    form = HomepageForm(request.POST if request.method == 'POST' else None, request.FILES or None, page=page)
    if request.method == 'POST' and form.is_valid():
        action = request.POST.get('action')
        if action not in {'save', 'publish'}:
            form.add_error(None, 'Bitte Entwurf speichern oder veröffentlichen wählen.')
        else:
            with transaction.atomic():
                current, _ = Homepage.objects.get_or_create(pk=1)
                # Compare-and-swap prevents silent overwrites from another editor/tab.
                updated = Homepage.objects.filter(pk=1, revision=form.cleaned_data['revision']).update(revision=form.cleaned_data['revision'] + 1)
                if not updated:
                    form.add_error(None, 'Die Startseite wurde inzwischen geändert. Bitte diese Seite neu laden und Ihre Änderungen erneut prüfen.')
                else:
                    values = {key: form.cleaned_data[key] for key, *_ in TEXT_FIELDS}
                    for key, *_ in IMAGE_FIELDS:
                        upload = form.cleaned_data.get(key)
                        if upload:
                            values[key] = HomepageImage.objects.create(image=upload).pk
                        elif not form.cleaned_data.get(key + '_reset') and key in current.draft:
                            values[key] = current.draft[key]
                    changes = {'draft': values}
                    if action == 'publish':
                        changes.update(published=values, published_at=timezone.now())
                    Homepage.objects.filter(pk=1).update(**changes)
                    messages.success(request, 'Startseite veröffentlicht.' if action == 'publish' else 'Entwurf gespeichert. Die Website ist unverändert.')
                    return redirect('homepage_edit')
    return render(request, 'admin/homepage_form.html', {'form': form, 'page': page, 'draft_content': homepage_content(page.draft)})


@never_cache
@login_required(login_url='login')
@permission_required('vehicles.change_homepage', raise_exception=True)
def homepage_preview(request):
    page = Homepage.objects.filter(pk=1).first() or Homepage(pk=1)
    content = homepage_content(page.draft)
    content["slider_interval"] = page.slider_interval
    response = render(request, 'public/home.html', {
        'hero_slides': homepage_slides(content),
        'site_content': content, 'content_preview': True,
        'featured_vehicles': public_vehicles_with_images()[:6],
        'latest_news': public_news_items()[:3],
    })
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
