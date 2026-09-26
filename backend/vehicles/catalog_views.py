from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.cache import never_cache

from .models import Accessory, NewsArticle
from .catalog_forms import AccessoryForm, AccessoryImages, NewsArticleForm
from .selectors import public_news_items


def public_accessories(request):
    items = Accessory.objects.filter(is_published=True, status='available').prefetch_related('images')
    return render(request, 'public/accessories.html', {'page_obj': Paginator(items, 12).get_page(request.GET.get('page'))})


def accessory_detail(request, pk):
    item = get_object_or_404(Accessory.objects.prefetch_related('images'), pk=pk, is_published=True, status='available')
    return render(request, 'public/accessory_detail.html', {'item': item})


def public_news(request):
    items = public_news_items()
    selected_type = request.GET.get('type', '')
    category_types = {
        'vehicle': [NewsArticle.Type.VEHICLE],
        'offer': [NewsArticle.Type.OFFER],
        'company': [NewsArticle.Type.COMPANY],
        'event': [NewsArticle.Type.EVENT],
        'notice': [NewsArticle.Type.NOTICE],
    }
    if selected_type in category_types:
        items = items.filter(type__in=category_types[selected_type])
    featured = items.filter(is_featured=True).first()
    if not selected_type and featured:
        items = items.exclude(pk=featured.pk)
    page_obj = Paginator(items, 12).get_page(request.GET.get('page'))
    return render(request, 'public/news.html', {
        'page_obj': page_obj, 'featured_article': featured,
        'selected_type': selected_type, 'news_filters': NewsArticle.Type.choices,
    })


def news_detail(request, slug):
    article = get_object_or_404(public_news_items(), slug=slug)
    return render(request, 'public/news_detail.html', {'article': article})


@login_required(login_url='login')
@permission_required('vehicles.view_accessory', raise_exception=True)
def accessories(request):
    items = Accessory.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        items = items.filter(Q(title__icontains=query) | Q(compatibility__icontains=query))
    return render(request, 'admin/catalog_list.html', {'items': items, 'query': query, 'kind': 'accessory', 'title': 'Teile & Zubehör'})


@login_required(login_url='login')
def accessory_edit(request, pk=None):
    permission = 'vehicles.change_accessory' if pk else 'vehicles.add_accessory'
    if not request.user.has_perms(['vehicles.view_accessory', permission]):
        raise PermissionDenied
    item = get_object_or_404(Accessory, pk=pk) if pk else Accessory()
    form = AccessoryForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=item)
    images = AccessoryImages(request.POST if request.method == 'POST' else None, request.FILES or None, instance=item)
    if request.method == 'POST':
        valid = form.is_valid()
        images_valid = images.is_valid()
        if valid and images_valid:
            with transaction.atomic():
                item = form.save()
                images.instance = item
                images.save()
            messages.success(request, 'Angebot und Bilder gespeichert.')
            return redirect('accessory_edit', pk=item.pk) if request.user.has_perm('vehicles.change_accessory') else redirect('management_accessories')
    return render(request, 'admin/catalog_form.html', {'form': form, 'images': images, 'item': item, 'kind': 'accessory', 'title': 'Angebot bearbeiten' if item.pk else 'Neues Angebot'})


@login_required(login_url='login')
@permission_required(('vehicles.view_accessory', 'vehicles.delete_accessory'), raise_exception=True)
def accessory_delete(request, pk):
    item = get_object_or_404(Accessory, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Angebot gelöscht.')
        return redirect('management_accessories')
    return render(request, 'admin/catalog_delete.html', {'item': item, 'kind': 'accessory'})


@login_required(login_url='login')
@permission_required('vehicles.view_newsarticle', raise_exception=True)
def news(request):
    items = NewsArticle.objects.all()
    query = request.GET.get('q', '').strip()
    news_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    published_after = parse_date(request.GET.get('published_after', ''))
    published_before = parse_date(request.GET.get('published_before', ''))
    if query:
        items = items.filter(Q(title__icontains=query) | Q(excerpt__icontains=query))
    if news_type in NewsArticle.Type.values:
        items = items.filter(type=news_type)
    if status in NewsArticle.Status.values:
        items = items.filter(status=status)
    if published_after:
        items = items.filter(published_at__date__gte=published_after)
    if published_before:
        items = items.filter(published_at__date__lte=published_before)
    return render(request, 'admin/catalog_list.html', {
        'items': items.order_by('-updated_at'), 'query': query, 'kind': 'news', 'title': 'Neuigkeiten',
        'news_types': NewsArticle.Type.choices, 'news_statuses': NewsArticle.Status.choices,
        'selected_type': news_type, 'selected_status': status,
        'published_after': request.GET.get('published_after', ''),
        'published_before': request.GET.get('published_before', ''),
    })


@login_required(login_url='login')
def news_edit(request, pk=None):
    permission = 'vehicles.change_newsarticle' if pk else 'vehicles.add_newsarticle'
    if not request.user.has_perms(['vehicles.view_newsarticle', permission]):
        raise PermissionDenied
    item = get_object_or_404(NewsArticle, pk=pk) if pk else NewsArticle()
    form = NewsArticleForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        if article.status == NewsArticle.Status.PUBLISHED and not article.published_at:
            article.published_at = timezone.now()
        if article.status != NewsArticle.Status.PUBLISHED:
            article.is_featured = False
        article.save()
        messages.success(request, 'Beitrag gespeichert.')
        return redirect('news_edit', pk=item.pk) if request.user.has_perm('vehicles.change_newsarticle') else redirect('management_news')
    return render(request, 'admin/catalog_form.html', {'form': form, 'item': item, 'kind': 'news', 'title': 'Beitrag bearbeiten' if item.pk else 'Neuer Beitrag'})


@login_required(login_url='login')
@permission_required(('vehicles.view_newsarticle', 'vehicles.delete_newsarticle'), raise_exception=True)
def news_delete(request, pk):
    item = get_object_or_404(NewsArticle, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Beitrag gelöscht.')
        return redirect('management_news')
    return render(request, 'admin/catalog_delete.html', {'item': item, 'kind': 'news'})


@never_cache
@login_required(login_url='login')
@permission_required(('vehicles.view_newsarticle', 'vehicles.change_newsarticle'), raise_exception=True)
def news_preview(request, pk):
    response = render(request, 'public/news_detail.html', {
            'article': get_object_or_404(NewsArticle, pk=pk), 'content_preview': True,
    })
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
@login_required(login_url='login')
@permission_required(('vehicles.view_accessory', 'vehicles.change_accessory'), raise_exception=True)
def accessory_preview(request, pk):
    response = render(request, 'public/accessory_detail.html', {
        'item': get_object_or_404(Accessory.objects.prefetch_related('images'), pk=pk), 'content_preview': True,
    })
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
