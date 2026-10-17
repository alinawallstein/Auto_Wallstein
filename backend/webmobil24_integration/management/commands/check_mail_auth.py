"""Authenticate only. This command never calls sendMail."""
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured

from vehicles.graph_mail import EmailBackend


class Command(BaseCommand):
    help = 'Check Microsoft OAuth authentication without sending any email.'

    def handle(self, *args, **options):
        try:
            EmailBackend().authenticate()
        except (OSError, ValueError, ImproperlyConfigured):
            raise CommandError('OAuth check failed. Check server configuration and Microsoft app credentials; no mail sent.') from None
        self.stdout.write(self.style.SUCCESS(
            'OAuth authentication succeeded; no mail sent. Mailbox send permission and delivery remain unverified.'))
