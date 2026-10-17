import io
import json
from email.message import Message
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from vehicles.webmobil24 import APIError, Client, Config


class ClientTests(SimpleTestCase):
    def setUp(self):
        self.opener = Mock()
        self.client = Client(Config("private-test-token", dealer_id=42), self.opener)

    def response(self, data, headers=None, raw=None, content_type="application/json"):
        response = Mock()
        response.status = 200
        response.headers = Message()
        response.headers["Content-Type"] = content_type
        for key, value in (headers or {}).items():
            response.headers[key] = value
        response.read.return_value = raw if raw is not None else json.dumps(data).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        self.opener.open.return_value = response
        return response

    def test_documented_request_and_pagination(self):
        self.response([{"listingId": 7, "dealerId": 42}], {"X-Total-Count": "5", "X-Result-Count": "1"})
        page = self.client.listings(offset=2, limit=1)
        self.assertEqual(page.total, 5)
        req = self.opener.open.call_args.args[0]
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.full_url, "https://testapi.webmobil24.com/rest/dealers/42/listings?offset=2&limit=1&language=DE&onlyActiveAds=true")
        self.assertEqual(req.get_header("Authorization"), "Bearer private-test-token")
        self.assertEqual(self.opener.open.call_args.kwargs["timeout"], 15)

    def test_details_and_images(self):
        self.response({"listingId": 7, "dealerId": 42})
        self.client.detail(7)
        self.response([{"id": 1, "url": "https://cdn.webmobil24.com/images/7/1.jpg"}])
        self.assertEqual(len(self.client.images(7)), 1)

    def test_invalid_responses(self):
        cases = [{}, [None], [{"listingId": 7, "dealerId": 99}],
                 [{"listingId": True, "dealerId": 42}],
                 [{"listingId": 7, "dealerId": 42}] * 2]
        for data in cases:
            with self.subTest(data=data):
                self.response(data)
                with self.assertRaises(APIError):
                    self.client.listings(limit=1)

    def test_bad_json_content_type_and_size(self):
        for raw, content in [(b"bad", "application/json"), (b"[]", "text/html"),
                             (b"x" * (Client.MAX_BYTES + 1), "application/json")]:
            self.response(None, raw=raw, content_type=content)
            with self.assertRaises(APIError):
                self.client.dealers()

    def test_bad_headers(self):
        for headers in [{"X-Total-Count": "bad"}, {"X-Result-Count": "2"}, {"X-Total-Count": "0"}]:
            self.response([{"dealerId": 42}], headers)
            with self.assertRaises(APIError):
                self.client.dealers()

    def test_http_errors_are_safe_and_not_retried(self):
        for code in (301, 400, 401, 403, 404, 429, 500):
            self.opener.reset_mock()
            self.opener.open.side_effect = HTTPError("secret-url", code, "private-test-token", {}, io.BytesIO(b"secret"))
            with self.assertRaises(APIError) as error:
                self.client.dealers()
            self.assertNotIn("private-test-token", str(error.exception))
            self.assertNotIn("secret", str(error.exception))
            self.opener.open.assert_called_once()

    def test_network_errors(self):
        for error in (TimeoutError("private-test-token"), URLError("private-test-token")):
            self.opener.open.side_effect = error
            with self.assertRaises(APIError) as caught:
                self.client.dealers()
            self.assertNotIn("private-test-token", str(caught.exception))

    def test_config_validation_and_redaction(self):
        self.assertNotIn("private-test-token", repr(self.client.config))
        for kwargs in ({"token": ""}, {"token": "x\ny"}, {"token": "x", "environment": "other"},
                       {"token": "x", "timeout": float("nan")}, {"token": "x", "dealer_id": "../7"}):
            with self.assertRaises(APIError):
                Config(**kwargs)
        self.assertEqual(Client(Config("x", "production")).base_url, "https://api.webmobil24.com/rest")

    def test_missing_dealer_and_invalid_ids(self):
        with self.assertRaises(APIError):
            Client(Config("x")).listings()
        for identifier in ("../7", False, 0, -1):
            with self.assertRaises(APIError):
                self.client.detail(identifier)

    def test_invalid_details_and_images(self):
        self.response({"listingId": 8, "dealerId": 42})
        with self.assertRaises(APIError):
            self.client.detail(7)
        for url in ("http://cdn.example/1", "https://user:secret@cdn.example/1", "not-url", "https://["):
            self.response([{"id": 1, "url": url}])
            with self.assertRaises(APIError):
                self.client.images(7)

    def test_redirect_handler_blocks_forwarding(self):
        from vehicles.webmobil24 import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example"))


class CommandTests(SimpleTestCase):
    @patch.dict("os.environ", {"WEBMOBIL24_TOKEN": "test-token", "WEBMOBIL24_DEALER_ID": "42", "WEBMOBIL24_ENV": "test"})
    @patch("webmobil24_integration.management.commands.test_webmobil24.Client")
    def test_connection_flow_without_database(self, cls):
        from vehicles.webmobil24 import Page
        client = cls.return_value
        client.config.environment = "test"
        client.listings.side_effect = [Page([{"listingId": 7}], 2), Page([{"listingId": 8}], 2)]
        client.images.return_value = [{"id": 1, "url": "https://cdn.example/1"}]
        out = io.StringIO()
        call_command("test_webmobil24", page_size=1, max_pages=2, stdout=out)
        client.detail.assert_called_once_with(7)
        client.images.assert_called_once_with(7)
        self.assertIn("2 Datensätze", out.getvalue())
        self.assertNotIn("test-token", out.getvalue())

    @patch("webmobil24_integration.management.commands.test_webmobil24.Client")
    def test_discovery_prints_only_id_company(self, cls):
        from vehicles.webmobil24 import Page
        client = cls.return_value
        client.config.token = "secret-token"
        client.dealers.return_value = Page([{"dealerId": 42, "company": "Auto Wallstein", "exportTargetCredentials": {"password": "secret"}}], 1)
        with patch("webmobil24_integration.management.commands.test_webmobil24.Config.from_env"):
            out = io.StringIO()
            call_command("test_webmobil24", list_dealers=True, stdout=out)
        self.assertIn("Händler-ID: 42", out.getvalue())
        self.assertNotIn("secret", out.getvalue())
        client.detail.assert_not_called()

    @patch("webmobil24_integration.management.commands.test_webmobil24.Client")
    def test_empty_and_duplicate_pages(self, cls):
        from vehicles.webmobil24 import Page
        client = cls.return_value
        with patch("webmobil24_integration.management.commands.test_webmobil24.Config.from_env"):
            client.listings.return_value = Page([], 0)
            call_command("test_webmobil24", stdout=io.StringIO())
            client.detail.assert_not_called()
            client.listings.side_effect = [Page([{"listingId": 7}], 3)] * 2
            with self.assertRaises(CommandError):
                call_command("test_webmobil24", page_size=1, max_pages=2, stdout=io.StringIO())

    def test_invalid_bounds(self):
        with self.assertRaises(CommandError):
            call_command("test_webmobil24", max_pages=11)
