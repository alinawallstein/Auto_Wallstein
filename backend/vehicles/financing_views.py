from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from .financing_forms import FinancingSettingsForm
from .models import Homepage


@login_required
@permission_required('vehicles.change_slider_settings', raise_exception=True)
def financing_settings(request):
    page, _ = Homepage.objects.get_or_create(pk=1)
    form = FinancingSettingsForm(request.POST or None, instance=page)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Finanzierungszins gespeichert.')
        return redirect('financing_settings')
    return render(request, 'management/financing_settings.html', {'form': form})
