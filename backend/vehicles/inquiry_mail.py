"""Mail transport and durable reply records; the original inquiry remains untouched."""
import base64
import logging
from pathlib import Path
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.mail import BadHeaderError, EmailMessage, EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone

from .models import CustomerInquiry, InquiryReply, InquiryStatus
from .expose_pdf import build_vehicle_expose

logger = logging.getLogger(__name__)
MAIL_ERRORS = (SMTPException, OSError, BadHeaderError, ValueError, ImproperlyConfigured)
TEST_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
}


def mail_is_test_mode():
    return settings.EMAIL_BACKEND in TEST_BACKENDS


def send_inquiry_reply(*, inquiry, author, body, request_id):
    subject = 'Re: ' + inquiry.display_subject.replace('\r', ' ').replace('\n', ' ')
    reply, created = InquiryReply.objects.get_or_create(request_id=request_id, defaults={
        'inquiry': inquiry, 'author': author, 'body': body,
        'recipient': inquiry.email, 'subject': subject,
    })
    if reply.inquiry_id != inquiry.pk or reply.author_id != author.pk:
        raise PermissionDenied
    if not created:
        return reply, False
    try:
        sent = EmailMessage(subject=reply.subject, body=reply.body,
                            from_email=settings.DEFAULT_FROM_EMAIL, to=[reply.recipient]).send(fail_silently=False)
        if sent != 1:
            raise OSError('Mail backend did not accept the message')
    except MAIL_ERRORS:
        # Do not expose SMTP credentials, customer content or backend exceptions in the UI/logs.
        logger.warning('Reply transport failed for reply %s', reply.pk)
        reply.status = InquiryReply.Status.FAILED
    else:
        reply.status = InquiryReply.Status.TEST if mail_is_test_mode() else InquiryReply.Status.SENT
        if reply.status == InquiryReply.Status.SENT:
            reply.sent_at = timezone.now()
            CustomerInquiry.objects.filter(pk=inquiry.pk).update(status=InquiryStatus.ANSWERED, updated_at=timezone.now())
    reply.save(update_fields=['status', 'sent_at'])
    return reply, True


def _vehicle_context(inquiry, request=None):
    vehicle = inquiry.vehicle
    name = f'{vehicle.brand} {vehicle.model}' if vehicle else 'Fahrzeug'
    context = {
        'inquiry': inquiry, 'vehicle': vehicle, 'vehicle_name': name,
        'logo_url': static('images/logo.png'),
        'vehicle_url': request.build_absolute_uri(f'/fahrzeuge/{vehicle.pk}/') if request and vehicle and vehicle.is_publicly_listed else '',
        'image_url': '', 'price': '', 'registration': '', 'mileage': '', 'power': '', 'fuel': '', 'transmission': '',
        'contact_name': 'Auto Wallstein', 'contact_address': 'Rudolf-Braas-Straße 27a · 63150 Heusenstamm',
        'contact_phone': '+496104406770', 'contact_phone_display': '+49 6104 406770', 'contact_email': 'verkauf@auto-wallstein.de',
    }
    if vehicle:
        image = vehicle.images.first()
        context.update({'image_url': request.build_absolute_uri(image.image.url) if request and image else '', 'price': f'{vehicle.sale_price:,.2f} €'.replace(',', 'X').replace('.', ',').replace('X', '.'), 'registration': vehicle.first_registration.strftime('%m/%Y') if vehicle.first_registration else '', 'mileage': f'{vehicle.mileage:,}'.replace(',', '.'), 'power': f'{vehicle.power_kw} kW / {vehicle.power_ps} PS', 'fuel': vehicle.fuel_type, 'transmission': vehicle.transmission})
    return context


def send_customer_inquiry_mails(inquiry, request=None):
    recipients = [address.strip() for address in str(settings.INQUIRY_NOTIFICATION_EMAIL).split(',') if address.strip()]
    vehicle = str(inquiry.vehicle) if inquiry.vehicle else 'Kein Fahrzeug ausgewählt'
    body = (f'Neue Kundenanfrage\n\nTyp: {inquiry.get_inquiry_type_display()}\nName: {inquiry.name}\n'
            f'E-Mail: {inquiry.email}\nTelefon: {inquiry.phone or "-"}\nFahrzeug: {vehicle}\n\nNachricht:\n{inquiry.message}\n')
    messages = []
    if recipients:
        messages.append((f'Neue Kundenanfrage: {inquiry.get_inquiry_type_display()}', body, recipients))
    if inquiry.email:
        context = _vehicle_context(inquiry, request)
        confirmation = EmailMultiAlternatives('Ihre Anfrage bei Auto Wallstein', render_to_string('email/inquiry_confirmation.txt', context), settings.DEFAULT_FROM_EMAIL, [inquiry.email])
        confirmation.attach_alternative(render_to_string('email/inquiry_confirmation.html', context), 'text/html')
        logo_path = Path(settings.BASE_DIR) / 'static' / 'images' / 'logo.png'
        try:
            context['logo_url'] = 'data:image/png;base64,' + base64.b64encode(logo_path.read_bytes()).decode('ascii')
            confirmation.alternatives = []
            confirmation.attach_alternative(render_to_string('email/inquiry_confirmation.html', context), 'text/html')
        except OSError:
            logger.warning('Inquiry logo embedding failed for inquiry %s', inquiry.pk)
        if inquiry.vehicle:
            try:
                pdf = build_vehicle_expose(inquiry.vehicle)
                filename = f'Auto-Wallstein_Expose_{inquiry.vehicle.brand}_{inquiry.vehicle.model}.pdf'.replace(' ', '_')
                confirmation.attach(filename, pdf, 'application/pdf')
            except Exception:
                logger.warning('Vehicle expose generation failed for inquiry %s', inquiry.pk)
        try:
            sent = confirmation.send(fail_silently=False)
            if sent != 1:
                raise OSError('Mail backend did not accept the confirmation')
        except MAIL_ERRORS:
            logger.warning('Inquiry confirmation failed for inquiry %s; original remains stored', inquiry.pk)
    for subject, text, addresses in messages:
        try:
            send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, addresses, fail_silently=False)
        except MAIL_ERRORS:
            logger.warning('Inquiry notification failed for inquiry %s; original remains stored', inquiry.pk)
