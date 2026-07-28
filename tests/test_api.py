from fastapi.testclient import TestClient

from app.main import create_app


def client():
    return TestClient(create_app(":memory:"))


def test_health():
    response = client().get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


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
    body = response.text
    assert "not-saved" not in body
    assert response.json()["credentials_saved"] is False
