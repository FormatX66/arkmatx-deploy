from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def client(settings: Settings | None = None):
    return TestClient(create_app(":memory:", settings_override=settings))


def test_health():
    response = client().get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["host_authentication_tests"] is False


def test_project_and_command_flow():
    test_client = client()
    projects = test_client.get("/api/projects").json()["items"]
    assert projects[0]["name"] == "Demo Website"
    response = test_client.post("/api/commands", json={"text": "ship Demo Website"})
    assert response.status_code == 201
    task = response.json()["task"]
    assert task["status"] == "waiting-confirmation"
    approved = test_client.post(
        f"/api/tasks/{task['id']}/approve", json={"confirmation": "SHIP"}
    )
    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "queued"


def test_host_password_is_not_returned():
    response = client().post(
        "/api/hosts/detect",
        json={"domain": "example.com", "username": "demo", "password": "not-saved"},
    )
    assert response.status_code == 200
    assert "not-saved" not in response.text
    assert response.json()["credentials_saved"] is False
    assert response.headers["cache-control"].startswith("no-store")


def test_host_authentication_test_is_disabled_by_default():
    response = client().post(
        "/api/hosts/test",
        json={
            "domain": "example.com",
            "username": "demo",
            "password": "never-return-this",
            "protocol": "ssh/sftp",
        },
    )
    assert response.status_code == 503
    assert "never-return-this" not in response.text
    assert response.json()["detail"]["code"] == "network-tests-disabled"
    assert response.headers["cache-control"].startswith("no-store")


def test_host_authentication_result_never_returns_password(monkeypatch):
    captured = {}

    def fake_test(host, protocol, port, username, password, settings):
        captured.update(
            host=host,
            protocol=protocol,
            port=port,
            username=username,
            password=password,
        )
        return {
            "domain": host,
            "protocol": "ssh/sftp",
            "port": 22,
            "status": "authenticated",
            "authenticated": True,
            "credentials_saved": False,
            "read_only_test": True,
            "message": "Read-only test passed.",
            "checks": [],
            "capabilities": ["ssh", "sftp"],
        }

    monkeypatch.setattr("app.main.test_host_connection", fake_test)
    settings = Settings(allow_network_probes=True, connection_test_rate_limit=10)
    response = client(settings).post(
        "/api/hosts/test",
        json={
            "domain": "https://example.com/path",
            "username": "demo",
            "password": "ephemeral-secret",
            "protocol": "auto",
        },
    )
    assert response.status_code == 200
    assert captured == {
        "host": "example.com",
        "protocol": "auto",
        "port": None,
        "username": "demo",
        "password": "ephemeral-secret",
    }
    assert "ephemeral-secret" not in response.text
    assert response.json()["authenticated"] is True
    assert response.json()["credentials_saved"] is False


def test_host_authentication_rate_limit(monkeypatch):
    monkeypatch.setattr(
        "app.main.test_host_connection",
        lambda host, protocol, port, username, password, settings: {
            "domain": host,
            "protocol": protocol,
            "port": port or 22,
            "status": "authenticated",
            "authenticated": True,
            "credentials_saved": False,
            "read_only_test": True,
            "message": "ok",
        },
    )
    settings = Settings(
        allow_network_probes=True,
        connection_test_rate_limit=1,
        connection_test_rate_window_seconds=60,
    )
    test_client = client(settings)
    payload = {
        "domain": "example.com",
        "username": "demo",
        "password": "secret",
        "protocol": "ssh/sftp",
    }
    assert test_client.post("/api/hosts/test", json=payload).status_code == 200
    limited = test_client.post("/api/hosts/test", json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"
