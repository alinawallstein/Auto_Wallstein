"""Microsoft Graph transport. Tokens stay in memory; failures contain no secrets."""
import base64
import json
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def _request(self, request, expected):
        try:
            with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                if response.status != expected:
                    raise OSError('Microsoft mail service returned an unexpected status')
                return response.read()
        except HTTPError as exc:
            raise OSError(f'Microsoft mail service rejected request (HTTP {exc.code})') from None
        except (URLError, TimeoutError):
            raise OSError('Microsoft mail service unavailable') from None

    def authenticate(self):
        tenant = settings.MS_GRAPH_TENANT_ID
        client = settings.MS_GRAPH_CLIENT_ID
        secret = settings.MS_GRAPH_CLIENT_SECRET
        try:
            UUID(tenant)
            UUID(client)
        except (ValueError, TypeError, AttributeError):
            raise ImproperlyConfigured('Microsoft tenant and client UUIDs are required') from None
        if not secret:
            raise ImproperlyConfigured('Microsoft application credential is missing')
        request = Request(
            f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
            data=urlencode({'client_id': client, 'client_secret': secret,
                            'scope': 'https://graph.microsoft.com/.default',
                            'grant_type': 'client_credentials'}).encode(),
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
        try:
            token = json.loads(self._request(request, 200))['access_token']
            if not isinstance(token, str) or not token:
                raise ValueError
            return token
        except (KeyError, ValueError, TypeError):
            raise OSError('Microsoft authentication returned an invalid response') from None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        count = 0
        try:
            token = self.authenticate()
            mailbox = settings.MS_GRAPH_MAILBOX
            if not mailbox or '@' not in mailbox:
                raise ImproperlyConfigured('Microsoft sending mailbox is required')
            for message in email_messages:
                if not message.recipients():
                    continue
                if parseaddr(message.from_email)[1].lower() != mailbox.lower():
                    raise ImproperlyConfigured('Message sender must match the Microsoft mailbox')
                # Django MIME preserves HTML alternatives, reply-to, and PDF attachments.
                mime = message.message().as_bytes(linesep='\r\n')
                request = Request(
                    f'https://graph.microsoft.com/v1.0/users/{quote(mailbox, safe="")}/sendMail',
                    data=base64.b64encode(mime),
                    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'text/plain'},
                )
                self._request(request, 202)
                count += 1
        except (OSError, ValueError, ImproperlyConfigured):
            if not self.fail_silently:
                raise
        return count
