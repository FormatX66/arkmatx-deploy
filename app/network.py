import ipaddress
import socket
from urllib.parse import urlsplit


DEFAULT_PORTS = {
    "ssh/sftp": 22,
    "ftp": 21,
    "ftps": 990,
    "cpanel": 2083,
    "plesk": 8443,
    "directadmin": 2222,
    "https/api": 443,
}


def normalize_domain(value: str) -> str:
    candidate = value.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    host = parsed.hostname or ""
    if not host or len(host) > 253:
        raise ValueError("Enter a valid domain or hostname.")
    return host.lower().rstrip(".")


def target_is_allowed(host: str, allow_private: bool) -> bool:
    addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not allow_private and (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        ):
            return False
    return True


def tcp_probe(host: str, port: int, timeout: float = 1.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def detect_host(host: str, requested_protocol: str, requested_port: int | None, settings):
    if requested_protocol != "auto":
        candidates = [(requested_protocol, requested_port or DEFAULT_PORTS.get(requested_protocol, 22))]
    else:
        candidates = list(DEFAULT_PORTS.items())

    if not settings.allow_network_probes:
        return {
            "domain": host,
            "probe_mode": "safe-dry-run",
            "credentials_saved": False,
            "candidates": [
                {"protocol": protocol, "port": port, "status": "ready-to-test"}
                for protocol, port in candidates
            ],
        }

    if not target_is_allowed(host, settings.allow_private_targets):
        raise ValueError("Private, local, or reserved targets are blocked by policy.")

    return {
        "domain": host,
        "probe_mode": "network",
        "credentials_saved": False,
        "candidates": [
            {
                "protocol": protocol,
                "port": port,
                "status": "reachable" if tcp_probe(host, port) else "closed",
            }
            for protocol, port in candidates
        ],
    }
