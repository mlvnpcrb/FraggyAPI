"""Pinned-address HTTP with no redirects, ambient proxy, cookies or remote defaults."""

import asyncio
import http.client
import ipaddress
import os
import socket
import ssl
import threading
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

from ..importing.formats import MAX_BYTES
from .policy import CollectionError, Grant, public_address


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    content_type: str
    etag: str | None = None
    retry_after: str | None = None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, address: str, timeout: float) -> None:
        self.tls_context = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        raw = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class HTTPTransport:
    def __init__(self, *, allow_external: bool = False) -> None:
        self.allow_external = allow_external

    async def fetch(
        self, grant: Grant, cursor: str | None, since: str | None, etag: str | None
    ) -> Response:
        # Deny before DNS/socket work; enabling a registry flag never grants access.
        if not grant.manifest.synthetic and not self.allow_external:
            raise CollectionError("external_network_disabled")
        return await asyncio.to_thread(self._fetch, grant, cursor, since, etag)

    def _fetch(
        self, grant: Grant, cursor: str | None, since: str | None, etag: str | None
    ) -> Response:
        endpoint = grant.endpoint
        parsed = urlsplit(endpoint.url)
        host = parsed.hostname
        assert host is not None
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        headers = {
            "Accept": "application/json, text/csv, text/html",
            "Accept-Encoding": "identity",
            "User-Agent": endpoint.user_agent or "FraggyAPI-authorized-collector/0.1",
        }
        if endpoint.credential_env:
            credential = os.getenv(endpoint.credential_env)
            if not credential or any(ord(c) < 33 or ord(c) > 126 for c in credential):
                raise CollectionError("credential_unavailable")
            headers["Authorization"] = "Bearer " + credential
        if etag:
            if len(etag) > 256 or any(ord(c) < 32 or ord(c) > 126 for c in etag):
                raise CollectionError("invalid_etag")
            headers["If-None-Match"] = etag
        if grant.manifest.synthetic:
            if host != "127.0.0.1" or not ipaddress.ip_address(host).is_loopback:
                raise CollectionError("synthetic_target_denied")
            connection: http.client.HTTPConnection = http.client.HTTPConnection(
                host, port, timeout=endpoint.timeout_seconds
            )
        else:
            addresses = list(
                {
                    str(v[4][0])
                    for v in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
                }
            )
            if not addresses or any(not public_address(a) for a in addresses):
                raise CollectionError("network_address_denied")
            # Reuse the reviewed DNS answer for the actual socket; TLS still
            # verifies the original hostname. No DNS rebinding or redirect hop.
            connection = PinnedHTTPS(host, port, addresses[0], endpoint.timeout_seconds)
        query = {
            k: v for k, v in (("cursor", cursor), ("since", since)) if v is not None
        }
        if endpoint.adapter == "wikidata_sparql":
            from .wikidata import query as wikidata_query

            query = {"query": wikidata_query(endpoint, cursor), "format": "json"}
        path = (parsed.path or "/") + ("?" + urlencode(query) if query else "")

        def interrupt() -> None:
            sock = connection.sock
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            connection.close()

        timer = threading.Timer(endpoint.timeout_seconds, interrupt)
        timer.daemon = True
        timer.start()
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise CollectionError("encoded_response_denied")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise CollectionError("response_too_large")
            return Response(
                response.status,
                body,
                response.getheader("Content-Type", ""),
                response.getheader("ETag"),
                response.getheader("Retry-After"),
            )
        except (OSError, http.client.HTTPException) as exc:
            raise CollectionError("network_failure") from exc
        finally:
            timer.cancel()
            connection.close()
