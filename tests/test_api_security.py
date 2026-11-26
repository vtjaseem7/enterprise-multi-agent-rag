from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_token(role: str, tenant_id: str = "tenant_acme") -> str:
    resp = client.post(
        "/api/v1/auth/dev-token",
        json={"user_id": f"test_{role}", "tenant_id": tenant_id, "role": role},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_health_check():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_requires_authentication():
    resp = client.post("/api/v1/chat", json={"query": "What is AUTH-401?"})
    assert resp.status_code in (401, 403)


def test_customer_cannot_upload_documents():
    token = get_token("customer")
    resp = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.txt", b"hello world", "text/plain")},
        data={"category": "general", "allowed_roles": "admin"},
    )
    assert resp.status_code == 403


def test_customer_blocked_from_admin_document():
    token = get_token("customer")
    resp = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Why did API 500 errors spike after release v2.4?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "internal_postmortem.txt" not in data["citations"]


def test_admin_can_access_admin_document():
    token = get_token("admin")
    resp = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Why did API 500 errors spike after release v2.4?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "internal_postmortem.txt" in data["citations"]