import pytest

from app.config import Settings
from app.host_connection import HostConnectionError, test_host_connection


def test_network_tests_are_opt_in():
    settings = Settings(allow_network_probes=False)
    with pytest.raises(HostConnectionError) as caught:
        test_host_connection(
            "example.com", "ssh/sftp", None, "demo", "secret", settings
        )
    assert caught.value.code == "network-tests-disabled"


def test_unsupported_protocol_is_rejected():
    settings = Settings(allow_network_probes=True)
    with pytest.raises(HostConnectionError) as caught:
        test_host_connection("example.com", "telnet", None, "demo", "secret", settings)
    assert caught.value.code == "unsupported-protocol"


def test_auto_detect_runs_one_read_only_authentication(monkeypatch):
    monkeypatch.setattr("app.host_connection.target_is_allowed", lambda host, allow_private: True)
    monkeypatch.setattr(
        "app.host_connection.tcp_probe",
        lambda host, port, timeout=1.2: port == 22,
    )

    calls = []

    def fake_ssh(host, port, username, password, timeout):
        calls.append((host, port, username, password, timeout))
        return {
            "domain": host,
            "protocol": "ssh/sftp",
            "port": port,
            "status": "authenticated",
            "authenticated": True,
            "credentials_saved": False,
            "read_only_test": True,
            "capabilities": ["ssh", "sftp"],
            "checks": [{"name": "password-auth", "status": "passed"}],
            "message": "Read-only authentication passed.",
        }

    monkeypatch.setattr("app.host_connection._ssh_test", fake_ssh)
    settings = Settings(allow_network_probes=True, connection_timeout_seconds=4)
    result = test_host_connection(
        "example.com", "auto", None, "demo", "one-time-secret", settings
    )

    assert result["authenticated"] is True
    assert result["protocol"] == "ssh/sftp"
    assert result["credentials_saved"] is False
    assert "one-time-secret" not in str(result)
    assert calls == [("example.com", 22, "demo", "one-time-secret", 4.0)]


def test_private_target_policy_is_enforced(monkeypatch):
    monkeypatch.setattr("app.host_connection.target_is_allowed", lambda host, allow_private: False)
    settings = Settings(allow_network_probes=True, allow_private_targets=False)
    with pytest.raises(HostConnectionError) as caught:
        test_host_connection(
            "internal.example", "ssh/sftp", None, "demo", "secret", settings
        )
    assert caught.value.code == "target-blocked"
