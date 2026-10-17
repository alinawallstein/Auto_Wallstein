"""Read-only WebMobil24 OpenAPI 1.3.0 client; no model or storage writes."""
from __future__ import annotations

import json
import math
import os
import socket
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class APIError(Exception):
    """Safe diagnostics: never include request headers, URLs or response bodies."""


def positive_id(value):
    if isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit() or int(value) <= 0:
        raise APIError("Ungültige Händler- oder Fahrzeug-ID.")
    return int(value)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    environment: str = "test"
    dealer_id: int | None = None
    timeout: float = 15

    def __post_init__(self):
        if not isinstance(self.token, str) or not self.token.strip() or any(ord(c) < 33 or ord(c) > 126 for c in self.token):
            raise APIError("WEBMOBIL24_TOKEN fehlt oder ist ungültig; in backend/.env eintragen.")
        if self.environment not in {"test", "production"}:
            raise APIError("WEBMOBIL24_ENV muss test oder production sein.")
        if not math.isfinite(self.timeout) or not 1 <= self.timeout <= 60:
            raise APIError("WEBMOBIL24_TIMEOUT muss zwischen 1 und 60 Sekunden liegen.")
        if self.dealer_id is not None:
            positive_id(self.dealer_id)

    @classmethod
    def from_env(cls, environment=None):
        try:
            timeout = float(os.getenv("WEBMOBIL24_TIMEOUT", "15"))
        except ValueError:
            raise APIError("WEBMOBIL24_TIMEOUT ist ungültig.") from None
        dealer = os.getenv("WEBMOBIL24_DEALER_ID", "").strip()
        return cls(os.getenv("WEBMOBIL24_TOKEN", ""),
                   environment or os.getenv("WEBMOBIL24_ENV", "test"),
                   positive_id(dealer) if dealer else None, timeout)


@dataclass
class Page:
    items: list[dict]
    total: int | None


class Client:
    MAX_BYTES = 8 * 1024 * 1024

    def __init__(self, config, opener=None):
        self.config = config
        self.base_url = {"test": "https://testapi.webmobil24.com/rest",
                         "production": "https://api.webmobil24.com/rest"}[config.environment]
        self.opener = opener or build_opener(NoRedirect())

    def _get(self, path, params=None):
        url = self.base_url + path
        if params:
            url += "?" + urlencode(params)
        request = Request(url, headers={"Authorization": "Bearer " + self.config.token,
                                       "Accept": "application/json"}, method="GET")
        try:
            with self.opener.open(request, timeout=self.config.timeout) as response:
                if response.status != 200:
                    raise APIError("Unerwarteter HTTP-Status.")
                if response.headers.get_content_type() != "application/json":
                    raise APIError("API-Antwort ist kein JSON.")
                raw = response.read(self.MAX_BYTES + 1)
                if len(raw) > self.MAX_BYTES:
                    raise APIError("API-Antwort überschreitet das lokale Größenlimit.")
                headers = response.headers
        except HTTPError as exc:
            code = exc.code
            exc.close()
            messages = {401: "Authentifizierung fehlgeschlagen (HTTP 401).",
                        403: "Zugriff nicht erlaubt (HTTP 403).",
                        404: "Ressource nicht gefunden oder keine Ergebnisse (HTTP 404).",
                        429: "API-Abruflimit erreicht (HTTP 429); später erneut ausführen."}
            raise APIError(messages.get(code, f"API-Fehler (HTTP {code}).")) from None
        except (TimeoutError, socket.timeout):
            raise APIError("Zeitlimit beim API-Abruf überschritten.") from None
        except (URLError, OSError, ValueError):
            raise APIError("API-Verbindung fehlgeschlagen.") from None
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            raise APIError("API-Antwort enthält ungültiges JSON.") from None
        return data, headers

    def _page(self, path, id_key, offset, limit, extra=None):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise APIError("Offset/Limit außerhalb der lokalen Abrufgrenzen.")
        data, headers = self._get(path, {"offset": offset, "limit": limit, **(extra or {})})
        if not isinstance(data, list) or len(data) > limit:
            raise APIError("Ungültige Bestandsantwort oder API ignoriert Abruflimit.")
        ids = []
        for item in data:
            if not isinstance(item, dict):
                raise APIError("Ungültiger Datensatz in API-Antwort.")
            ids.append(positive_id(item.get(id_key)))
        if len(ids) != len(set(ids)):
            raise APIError("Doppelte IDs in API-Antwort.")
        counts = {}
        for name in ("X-Total-Count", "X-Result-Count"):
            value = headers.get(name)
            if value is not None:
                if not value.isascii() or not value.isdigit():
                    raise APIError("Ungültige Pagination-Header.")
                counts[name] = int(value)
        if "X-Result-Count" in counts and counts["X-Result-Count"] != len(data):
            raise APIError("Ergebniszahl widerspricht Pagination-Header.")
        total = counts.get("X-Total-Count")
        if total is not None and data and total < offset + len(data):
            raise APIError("Gesamtzahl widerspricht Pagination-Header.")
        return Page(data, total)

    def dealers(self, offset=0, limit=10):
        return self._page("/dealers", "dealerId", offset, limit)

    def _dealer_path(self):
        if self.config.dealer_id is None:
            raise APIError("WEBMOBIL24_DEALER_ID fehlt; zuerst --list-dealers ausführen.")
        return f"/dealers/{positive_id(self.config.dealer_id)}/listings"

    def listings(self, offset=0, limit=10):
        page = self._page(self._dealer_path(), "listingId", offset, limit,
                          {"language": "DE", "onlyActiveAds": "true"})
        for item in page.items:
            if positive_id(item.get("dealerId")) != self.config.dealer_id:
                raise APIError("API-Antwort gehört zu einem anderen Händler.")
        return page

    def detail(self, listing_id):
        listing_id = positive_id(listing_id)
        data, _ = self._get(f"{self._dealer_path()}/{listing_id}", {"language": "DE"})
        if not isinstance(data, dict) or positive_id(data.get("listingId")) != listing_id or positive_id(data.get("dealerId")) != self.config.dealer_id:
            raise APIError("Ungültige Fahrzeugdetail-Antwort.")
        return data

    def images(self, listing_id):
        data, _ = self._get(f"{self._dealer_path()}/{positive_id(listing_id)}/images")
        if not isinstance(data, list):
            raise APIError("Ungültige Bildantwort.")
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                raise APIError("Ungültige Bildadresse.")
            positive_id(item.get("id"))
            try:
                url = urlsplit(item["url"])
                valid = url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
            except ValueError:
                valid = False
            if not valid:
                raise APIError("Ungültige Bildadresse.")
        return data
