from __future__ import annotations

import base64
import hashlib
import socket
import ssl
from ftplib import FTP, FTP_TLS, error_perm
from urllib.parse import parse_qs

import httpx
import paramiko

from app.network import DEFAULT_PORTS, target_is_allowed, tcp_probe


AUTO_ORDER = (
    "ssh/sftp",
    "cpanel",
    "plesk",
    "directadmin",
    "ftps",
    "ftp",
    "https/api",
)
SUPPORTED_PROTOCOLS = frozenset(("auto", *AUTO_ORDER))


class HostConnectionError(ValueError):
    """A safe, user-displayable host connection error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ImplicitFTP_TLS(FTP_TLS):
    """Minimal implicit FTPS client for the conventional port 990."""

    def connect(self, host="", port=0, timeout=-999, source_address=None):  # noqa: ANN001
        if host:
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        if source_address is not None:
            self.source_address = source_address
        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, source_address=self.source_address
        )
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome


def _base_result(host: str, protocol: str, port: int) -> dict:
    return {
        "domain": host,
        "protocol": protocol,
        "port": port,
        "authenticated": False,
        "credentials_saved": False,
        "read_only_test": True,
        "capabilities": [],
        "checks": [],
    }


def _safe_close(connection) -> None:  # noqa: ANN001
    try:
        connection.close()
    except Exception:  # noqa: BLE001
        pass


def _ssh_test(host: str, port: int, username: str, password: str, timeout: float) -> dict:
    result = _base_result(host, "ssh/sftp", port)
    sock = None
    transport = None
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.settimeout(timeout)
        transport = paramiko.Transport(sock)
        transport.banner_timeout = timeout
        transport.auth_timeout = timeout
        transport.start_client(timeout=timeout)
        key = transport.get_remote_server_key()
        fingerprint = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode("ascii")
        result["host_key"] = {
            "algorithm": key.get_name(),
            "sha256": fingerprint,
            "verified": False,
            "pin_before_deploy": True,
        }
        result["checks"].append({"name": "ssh-handshake", "status": "passed"})
        try:
            transport.auth_password(username=username, password=password, fallback=False)
        except paramiko.AuthenticationException:
            result.update(
                status="authentication-failed",
                message="The server answered, but the SSH username or password was rejected.",
            )
            result["checks"].append({"name": "password-auth", "status": "failed"})
            return result

        if not transport.is_authenticated():
            result.update(
                status="authentication-failed",
                message="The SSH server did not accept the supplied credentials.",
            )
            return result

        result["authenticated"] = True
        result["checks"].append({"name": "password-auth", "status": "passed"})
        result["capabilities"].append("ssh")
        try:
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                sftp.stat(".")
                result["capabilities"].append("sftp")
                result["checks"].append({"name": "sftp-read", "status": "passed"})
            finally:
                _safe_close(sftp)
        except (OSError, paramiko.SSHException):
            result["checks"].append({"name": "sftp-read", "status": "unavailable"})

        result.update(
            status="authenticated",
            message="SSH authentication passed. No command was run and no file was changed.",
        )
        return result
    except (OSError, EOFError, paramiko.SSHException):
        result.update(
            status="connection-failed",
            message="The SSH service could not complete a secure handshake.",
        )
        return result
    finally:
        if transport is not None:
            _safe_close(transport)
        elif sock is not None:
            _safe_close(sock)


def _ftp_test(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
    tls: bool,
) -> dict:
    protocol = "ftps" if tls else "ftp"
    result = _base_result(host, protocol, port)
    connection = None
    try:
        if tls:
            context = ssl.create_default_context()
            connection = ImplicitFTP_TLS(context=context) if port == 990 else FTP_TLS(context=context)
            connection.connect(host, port, timeout=timeout)
            if port != 990:
                connection.auth()
            connection.login(username, password)
            connection.prot_p()
            result["checks"].append({"name": "tls", "status": "passed"})
        else:
            connection = FTP()
            connection.connect(host, port, timeout=timeout)
            connection.login(username, password)
        connection.pwd()
        result["authenticated"] = True
        result["capabilities"].append(protocol)
        result["checks"].append({"name": "login", "status": "passed"})
        result["checks"].append({"name": "read-current-directory", "status": "passed"})
        result.update(
            status="authenticated",
            message=f"{protocol.upper()} authentication passed. No file was uploaded or changed.",
        )
        return result
    except error_perm:
        result.update(
            status="authentication-failed",
            message=f"The {protocol.upper()} service answered, but rejected the credentials.",
        )
        result["checks"].append({"name": "login", "status": "failed"})
        return result
    except (OSError, EOFError, ssl.SSLError):
        result.update(
            status="connection-failed",
            message=f"The {protocol.upper()} service could not complete the connection test.",
        )
        return result
    finally:
        if connection is not None:
            try:
                connection.quit()
            except Exception:  # noqa: BLE001
                _safe_close(connection)


def _panel_request(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
    path: str,
    verify_tls: bool,
) -> httpx.Response:
    url = f"https://{host}:{port}{path}"
    with httpx.Client(
        timeout=httpx.Timeout(timeout),
        verify=verify_tls,
        follow_redirects=False,
        headers={"Accept": "application/json", "User-Agent": "Arkmatx-Deploy/0.2"},
    ) as client:
        return client.get(url, auth=(username, password))


def _cpanel_test(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
    verify_tls: bool,
) -> dict:
    result = _base_result(host, "cpanel", port)
    try:
        response = _panel_request(
            host,
            port,
            username,
            password,
            timeout,
            "/execute/Variables/get_user_information?name=user",
            verify_tls,
        )
    except (httpx.HTTPError, ssl.SSLError):
        result.update(status="connection-failed", message="The cPanel HTTPS API could not be reached.")
        return result
    if response.status_code in {301, 302, 307, 308}:
        result.update(
            status="server-hostname-required",
            message="cPanel redirected to another hostname. Use the hosting server hostname and test again.",
        )
        return result
    if response.status_code in {401, 403}:
        result.update(status="authentication-failed", message="cPanel rejected the credentials.")
        return result
    if response.is_success:
        try:
            payload = response.json()
            api_ok = payload.get("result", {}).get("status") == 1
        except ValueError:
            api_ok = False
        if api_ok:
            result["authenticated"] = True
            result["capabilities"].append("cpanel-uapi")
            result["checks"].append({"name": "cpanel-uapi-read", "status": "passed"})
            result.update(
                status="authenticated",
                message="cPanel authentication passed with a read-only account-information request.",
            )
        else:
            result.update(
                status="api-response-unrecognized",
                message="cPanel answered, but the account-information response was not recognized.",
            )
        return result
    result.update(status="connection-failed", message="cPanel returned an unexpected HTTP response.")
    return result


def _plesk_test(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
    verify_tls: bool,
) -> dict:
    result = _base_result(host, "plesk", port)
    try:
        response = _panel_request(
            host, port, username, password, timeout, "/api/v2/domains?limit=1", verify_tls
        )
    except (httpx.HTTPError, ssl.SSLError):
        result.update(status="connection-failed", message="The Plesk REST API could not be reached.")
        return result
    if response.status_code in {401, 403}:
        result.update(
            status="authentication-failed",
            message="Plesk rejected the credentials or this account cannot use the REST API.",
        )
        return result
    if response.is_success:
        result["authenticated"] = True
        result["capabilities"].append("plesk-rest")
        result["checks"].append({"name": "plesk-rest-read", "status": "passed"})
        result.update(
            status="authenticated",
            message="Plesk authentication passed with a read-only domains request.",
        )
        return result
    result.update(
        status="api-unavailable",
        message="Plesk answered, but its REST API is unavailable or restricted for this account.",
    )
    return result


def _directadmin_test(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: float,
    verify_tls: bool,
) -> dict:
    result = _base_result(host, "directadmin", port)
    try:
        response = _panel_request(
            host,
            port,
            username,
            password,
            timeout,
            "/CMD_API_SHOW_USER_CONFIG?json=yes",
            verify_tls,
        )
    except (httpx.HTTPError, ssl.SSLError):
        result.update(
            status="connection-failed", message="The DirectAdmin API could not be reached."
        )
        return result
    if response.status_code in {401, 403}:
        result.update(status="authentication-failed", message="DirectAdmin rejected the credentials.")
        return result
    if response.is_success:
        authenticated = False
        try:
            payload = response.json()
            authenticated = str(payload.get("error", "0")) not in {"1", "true", "True"}
        except ValueError:
            parsed = parse_qs(response.text, keep_blank_values=True)
            authenticated = parsed.get("error", ["0"])[0] != "1"
        if authenticated:
            result["authenticated"] = True
            result["capabilities"].append("directadmin-api")
            result["checks"].append({"name": "directadmin-read", "status": "passed"})
            result.update(
                status="authenticated",
                message="DirectAdmin authentication passed with a read-only user-config request.",
            )
        else:
            result.update(status="authentication-failed", message="DirectAdmin rejected the credentials.")
        return result
    result.update(status="connection-failed", message="DirectAdmin returned an unexpected response.")
    return result


def _https_test(host: str, port: int, timeout: float, verify_tls: bool) -> dict:
    result = _base_result(host, "https/api", port)
    try:
        with httpx.Client(
            timeout=httpx.Timeout(timeout), verify=verify_tls, follow_redirects=False
        ) as client:
            response = client.get(f"https://{host}:{port}/")
    except (httpx.HTTPError, ssl.SSLError):
        result.update(status="connection-failed", message="The HTTPS service could not be reached.")
        return result
    result["checks"].append({"name": "https", "status": "passed"})
    result.update(
        status="reachable-not-authenticated",
        message=f"HTTPS is reachable (HTTP {response.status_code}), but no generic login API is defined.",
    )
    return result


def test_host_connection(
    host: str,
    requested_protocol: str,
    requested_port: int | None,
    username: str,
    password: str,
    settings,
) -> dict:
    protocol = requested_protocol.strip().lower()
    if protocol not in SUPPORTED_PROTOCOLS:
        raise HostConnectionError("unsupported-protocol", "Choose a supported connection type.")
    if not settings.allow_network_probes:
        raise HostConnectionError(
            "network-tests-disabled",
            "Host connection tests are disabled on this backend. Enable ARKMATX_ALLOW_NETWORK_PROBES.",
        )
    if not username.strip() or not password:
        raise HostConnectionError(
            "credentials-required", "A hosting username and password are required for this test."
        )
    try:
        allowed = target_is_allowed(host, settings.allow_private_targets)
    except OSError as exc:
        raise HostConnectionError("dns-failed", "The hostname could not be resolved.") from exc
    if not allowed:
        raise HostConnectionError(
            "target-blocked", "Private, local, link-local, or reserved targets are blocked by policy."
        )

    timeout = float(settings.connection_timeout_seconds)
    if protocol == "auto":
        reachable = []
        seen = set()
        for candidate in AUTO_ORDER:
            port = DEFAULT_PORTS[candidate]
            identity = (candidate, port)
            if identity in seen:
                continue
            seen.add(identity)
            if tcp_probe(host, port, timeout=min(timeout, 2.0)):
                reachable.append((candidate, port))
        if not reachable:
            return {
                **_base_result(host, "auto", 0),
                "status": "no-supported-service-found",
                "message": "No supported host-management service answered on the standard ports.",
                "alternatives": [],
            }
        protocol, port = reachable[0]
        alternatives = [
            {"protocol": candidate, "port": candidate_port, "status": "reachable"}
            for candidate, candidate_port in reachable[1:]
        ]
    else:
        port = requested_port or DEFAULT_PORTS[protocol]
        alternatives = []
        if not tcp_probe(host, port, timeout=min(timeout, 2.0)):
            return {
                **_base_result(host, protocol, port),
                "status": "service-unreachable",
                "message": f"Nothing answered on {host}:{port} for the selected connection type.",
                "alternatives": alternatives,
            }

    verify_tls = not settings.allow_untrusted_tls
    if protocol == "ssh/sftp":
        result = _ssh_test(host, port, username.strip(), password, timeout)
    elif protocol == "ftp":
        result = _ftp_test(host, port, username.strip(), password, timeout, tls=False)
    elif protocol == "ftps":
        result = _ftp_test(host, port, username.strip(), password, timeout, tls=True)
    elif protocol == "cpanel":
        result = _cpanel_test(host, port, username.strip(), password, timeout, verify_tls)
    elif protocol == "plesk":
        result = _plesk_test(host, port, username.strip(), password, timeout, verify_tls)
    elif protocol == "directadmin":
        result = _directadmin_test(host, port, username.strip(), password, timeout, verify_tls)
    else:
        result = _https_test(host, port, timeout, verify_tls)
    result["alternatives"] = alternatives
    result["auto_selected"] = requested_protocol.strip().lower() == "auto"
    return result
