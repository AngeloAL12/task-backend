"""
Validación de URLs para evitar SSRF (Server-Side Request Forgery).
Este módulo es la fuente de verdad para decidir si una URL es segura
para que el servidor haga un GET (p. ej. al cargar calendarios ICS).
"""
import ipaddress
import socket
from urllib.parse import urlparse

from app.core.config import settings


def _resolve_host_to_ips(hostname: str) -> list[str]:
    """Resolve hostname to IPv4 and IPv6 addresses."""
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(hostname, None):
            # info is (family, type, proto, canonname, sockaddr)
            addr = info[4][0]
            if addr and addr not in ips:
                ips.append(addr)
    except (socket.gaierror, socket.herror):
        pass
    return ips


def _is_private_or_unsafe(ip_str: str) -> bool:
    """Return True if the IP is loopback, link-local, or private."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_reserved
    )


def validate_calendar_url(url: str) -> None:
    """
    Validate that a URL is safe for the server to fetch (no SSRF).
    Raises ValueError with a clear message if the URL is not allowed.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").strip()

    if scheme not in ("http", "https"):
        raise ValueError("Solo se permiten URLs con esquema http o https.")

    if getattr(settings, "CALENDAR_REQUIRE_HTTPS", False) and scheme != "https":
        raise ValueError("Solo se permiten URLs HTTPS.")

    if not hostname:
        raise ValueError("La URL no tiene host válido.")

    allowed_hosts: list[str] = getattr(settings, "ALLOWED_CALENDAR_HOSTS", [])
    if allowed_hosts:
        if hostname not in allowed_hosts:
            raise ValueError("El host del calendario no está en la lista permitida.")
        return

    ips = _resolve_host_to_ips(hostname)
    if not ips:
        raise ValueError("No se pudo resolver el host del calendario.")

    for ip_str in ips:
        if _is_private_or_unsafe(ip_str):
            raise ValueError("No se permiten URLs a redes privadas o locales.")


def is_url_safe_for_fetch(url: str) -> bool:
    """
    Return True if the URL is safe for the server to fetch, False otherwise.
    Use this for defense-in-depth (e.g. in fetch_ics) without raising.
    """
    try:
        validate_calendar_url(url)
        return True
    except ValueError:
        return False
