from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import Accessory, NewsArticle
from .catalog_forms import AccessoryForm, AccessoryImages, NewsArticleForm


def public_accessories(request):
    items = Accessory.objects.filter(is_published=True, status='available').prefetch_related('images')
    return render(request, 'public/accessories.html', {'page_obj': Paginator(items, 12).get_page(request.GET.get('page'))})


def accessory_detail(request, pk):
    item = get_object_or_404(Accessory.objects.prefetch_related('images'), pk=pk, is_published=True, status='available')
    return render(request, 'public/accessory_detail.html', {'item': item})


def public_news(request):
    items = NewsArticle.objects.filter(is_published=True)
    return render(request, 'public/news.html', {'page_obj': Paginator(items, 12).get_page(request.GET.get('page'))})


def news_detail(request, pk):
    return render(request, 'public/news_detail.html', {'article': get_object_or_404(NewsArticle, pk=pk, is_published=True)})


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
    return render(request, 'admin/catalog_list.html', {'items': NewsArticle.objects.order_by('-updated_at'), 'kind': 'news', 'title': 'Neuigkeiten'})


@login_required(login_url='login')
def news_edit(request, pk=None):
    permission = 'vehicles.change_newsarticle' if pk else 'vehicles.add_newsarticle'
    if not request.user.has_perms(['vehicles.view_newsarticle', permission]):
        raise PermissionDenied
    item = get_object_or_404(NewsArticle, pk=pk) if pk else NewsArticle()
    form = NewsArticleForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        if article.is_published and not article.published_at:
            article.published_at = timezone.now()
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
