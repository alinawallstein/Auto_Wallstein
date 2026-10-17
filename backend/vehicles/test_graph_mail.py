import base64
from email import policy
from email.parser import BytesParser
from unittest.mock import patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from .graph_mail import EmailBackend


@override_settings(MS_GRAPH_TENANT_ID='11111111-1111-1111-1111-111111111111',
                   MS_GRAPH_CLIENT_ID='22222222-2222-2222-2222-222222222222',
                   MS_GRAPH_CLIENT_SECRET='test-only-secret',
                   MS_GRAPH_MAILBOX='verkauf@auto-wallstein.de')
class GraphMailTests(SimpleTestCase):
    @patch('vehicles.graph_mail.urlopen')
    def test_oauth_and_mime_preserve_customer_mail(self, urlopen):
        token = urlopen.return_value.__enter__.return_value
        token.status = 200
        token.read.return_value = b'{"access_token":"test-only-token"}'
        backend = EmailBackend()
        self.assertEqual(backend.authenticate(), 'test-only-token')
        request = urlopen.call_args.args[0]
        self.assertIn(b'grant_type=client_credentials', request.data)
        self.assertIn('login.microsoftonline.com', request.full_url)
        message = EmailMultiAlternatives('Anfrage ä', 'Text',
            'verkauf@auto-wallstein.de', ['customer@example.com'])
        message.attach_alternative('<p>Danke</p>', 'text/html')
        message.attach('Expose.pdf', b'%PDF-test', 'application/pdf')
        with patch.object(backend, 'authenticate', return_value='test-only-token'):
            token.status = 202
            token.read.return_value = b''
            self.assertEqual(backend.send_messages([message]), 1)
        request = urlopen.call_args.args[0]
        parsed = BytesParser(policy=policy.default).parsebytes(base64.b64decode(request.data))
        self.assertEqual(parsed['To'], 'customer@example.com')
        self.assertEqual(parsed['Subject'], 'Anfrage ä')
        self.assertEqual(list(parsed.iter_attachments())[0].get_payload(decode=True), b'%PDF-test')

    @patch.object(EmailBackend, 'authenticate', return_value='test-only-token')
    @patch('vehicles.graph_mail.urlopen')
    def test_rejection_is_failure_and_never_retried(self, urlopen, authenticate):
        response = urlopen.return_value.__enter__.return_value
        response.status = 403
        message = EmailMultiAlternatives('Test', 'Text', 'verkauf@auto-wallstein.de', ['customer@example.com'])
        with self.assertRaises(OSError):
            EmailBackend().send_messages([message])
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(EmailBackend(fail_silently=True).send_messages([message]), 0)
