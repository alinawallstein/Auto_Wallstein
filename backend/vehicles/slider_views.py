from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from .models import HeroSlide, Homepage
from .slider_forms import HeroSlideForm, SliderSettingsForm


@never_cache
@login_required
@permission_required('vehicles.view_heroslide', raise_exception=True)
def slides(request):
    return render(request, 'management/slider_list.html', {
        'page_obj': Paginator(HeroSlide.objects.all(), 20).get_page(request.GET.get('page')),
    })


@never_cache
@login_required
def slide_edit(request, pk=None):
    permission = 'vehicles.change_heroslide' if pk else 'vehicles.add_heroslide'
    if not request.user.has_perms(['vehicles.view_heroslide', permission]):
        raise PermissionDenied
    slide = get_object_or_404(HeroSlide, pk=pk) if pk else HeroSlide()
    form = HeroSlideForm(request.POST if request.method == 'POST' else None,
                         request.FILES or None, instance=slide)
    if request.method == 'POST' and form.is_valid():
        slide = form.save()
        messages.success(request, 'Slide gespeichert. Aktive Slides sind sofort öffentlich sichtbar.')
        return redirect('slide_edit', pk=slide.pk) if request.user.has_perm('vehicles.change_heroslide') else redirect('management_slides')
    return render(request, 'management/slider_form.html', {'form': form, 'slide': slide})


@never_cache
@login_required
@permission_required(('vehicles.view_heroslide', 'vehicles.delete_heroslide'), raise_exception=True)
def slide_delete(request, pk):
    slide = get_object_or_404(HeroSlide, pk=pk)
    if request.method == 'POST':
        slide.delete()
        messages.success(request, 'Slide gelöscht.')
        return redirect('management_slides')
    return render(request, 'management/slider_delete.html', {'slide': slide})


@never_cache
@login_required
@permission_required('vehicles.change_slider_settings', raise_exception=True)
def slider_settings(request):
    page = Homepage.objects.filter(pk=1).first() or Homepage(pk=1)
    form = SliderSettingsForm(request.POST if request.method == 'POST' else None, instance=page)
    if request.method == 'POST' and form.is_valid():
        # Update only settings, never overwrite a concurrently edited content draft.
        Homepage.objects.get_or_create(pk=1)
        Homepage.objects.filter(pk=1).update(slider_interval=form.cleaned_data['slider_interval'])
        messages.success(request, 'Wechselgeschwindigkeit gespeichert.')
        return redirect('slider_settings')
    return render(request, 'management/slider_settings.html', {'form': form})
