import ipaddress
import socket
from urllib.parse import urlparse


def is_public_http_url(url: str) -> bool:
    """
    Returns True only for http(s) URLs whose host resolves exclusively to public IP addresses.

    Used to stop user-submitted report URLs from making the worker's browser open
    local files (file://), localhost services, private networks, or cloud metadata endpoints.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addr_infos = socket.getaddrinfo(parsed.hostname, port)
    except (ValueError, socket.gaierror, UnicodeError):
        return False

    for addr_info in addr_infos:
        ip = ipaddress.ip_address(addr_info[4][0].split("%")[0])
        if not ip.is_global:
            return False

    return bool(addr_infos)
