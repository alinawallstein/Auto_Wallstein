from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .inquiry_forms import InquiryFilterForm, InquiryReplyForm, InquiryStatusForm
from .inquiry_mail import mail_is_test_mode, send_inquiry_reply
from .models import CustomerInquiry, InquiryReply, InquiryStatus


def inquiry_queryset():
    return CustomerInquiry.objects.select_related('vehicle')


@never_cache
@login_required
@permission_required('vehicles.view_customerinquiry', raise_exception=True)
def inquiries(request):
    form = InquiryFilterForm(request.GET)
    items = inquiry_queryset()
    if form.is_valid():
        query = form.cleaned_data['q']
        if query:
            items = items.filter(Q(name__icontains=query) | Q(email__icontains=query) |
                Q(subject__icontains=query) | Q(vehicle__brand__icontains=query) | Q(vehicle__model__icontains=query))
        if form.cleaned_data['status']:
            items = items.filter(status=form.cleaned_data['status'])
        items = items.order_by('created_at', 'pk') if form.cleaned_data['order'] == 'oldest' else items.order_by('-created_at', '-pk')
    else:
        items = items.none()
    latest_reply = InquiryReply.objects.filter(inquiry_id=OuterRef('pk')).order_by('-created_at', '-pk')
    items = items.annotate(latest_reply_status=Subquery(latest_reply.values('status')[:1]))
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'management/inquiry_list.html', {
        'form': form, 'page_obj': Paginator(items, 20).get_page(request.GET.get('page')), 'page_query': query.urlencode(),
    })


def render_detail(request, inquiry, *, reply_form=None, status_form=None):
    return render(request, 'management/inquiry_detail.html', {
        'inquiry': inquiry, 'replies': inquiry.replies.select_related('author'),
        'reply_form': reply_form if reply_form is not None else InquiryReplyForm(),
        'status_form': status_form if status_form is not None else InquiryStatusForm(initial={'status': inquiry.status}),
        'mail_test_mode': mail_is_test_mode(),
    })


@never_cache
@login_required
@permission_required('vehicles.view_customerinquiry', raise_exception=True)
def inquiry_detail(request, pk):
    inquiry = get_object_or_404(inquiry_queryset(), pk=pk)
    if request.user.has_perm('vehicles.change_customerinquiry') and inquiry.status == InquiryStatus.NEW:
        updated = CustomerInquiry.objects.filter(pk=pk, status=InquiryStatus.NEW).update(status=InquiryStatus.READ, updated_at=timezone.now())
        if updated:
            inquiry.status = InquiryStatus.READ
    return render_detail(request, inquiry)


@never_cache
@login_required
@permission_required(('vehicles.view_customerinquiry', 'vehicles.change_customerinquiry'), raise_exception=True)
@require_POST
def inquiry_status(request, pk):
    inquiry = get_object_or_404(inquiry_queryset(), pk=pk)
    form = InquiryStatusForm(request.POST)
    if form.is_valid():
        CustomerInquiry.objects.filter(pk=pk).update(status=form.cleaned_data['status'], updated_at=timezone.now())
        messages.success(request, 'Status gespeichert.')
        if form.cleaned_data['status'] == InquiryStatus.NEW:
            return redirect('management_inquiries')
        return redirect('inquiry_detail', pk=pk)
    return render_detail(request, inquiry, status_form=form)


@never_cache
@login_required
@permission_required(('vehicles.view_customerinquiry', 'vehicles.change_customerinquiry', 'vehicles.add_inquiryreply'), raise_exception=True)
@require_POST
def inquiry_reply(request, pk):
    inquiry = get_object_or_404(inquiry_queryset(), pk=pk)
    form = InquiryReplyForm(request.POST)
    if not form.is_valid():
        return render_detail(request, inquiry, reply_form=form)
    reply, created = send_inquiry_reply(inquiry=inquiry, author=request.user, **form.cleaned_data)
    if not created:
        messages.info(request, 'Diese Antwort wurde bereits verarbeitet. Es wurde keine weitere E-Mail versendet. Bitte prüfen Sie den Verlauf.')
    elif reply.status == InquiryReply.Status.SENT:
        messages.success(request, 'Antwort an den Mailserver übergeben. Die Anfrage ist als beantwortet markiert.')
    elif reply.status == InquiryReply.Status.TEST:
        messages.warning(request, 'Testbetrieb: Die Antwort wurde protokolliert, aber nicht per E-Mail zugestellt. Die Anfrage bleibt offen.')
    else:
        messages.error(request, 'Die Antwort konnte nicht versendet werden. Ihr Text bleibt im Verlauf erhalten. Bitte prüfen Sie die Mail-Konfiguration, bevor Sie erneut antworten.')
    return redirect('inquiry_detail', pk=pk)
