from fastapi.testclient import TestClient

from app.api.routes import service as dependency
from app.main import app


def test_read_and_role_guard(service):
    app.dependency_overrides[dependency] = lambda: service
    try:
        with TestClient(app) as client:
            assert len(client.get("/api/claims").json()) == 3
            response = client.get("/api/claims/CLM-001")
            assert response.status_code == 200 and response.headers["X-Correlation-ID"]
            assert client.get("/api/claims/absent").status_code == 404
            assert (
                client.get("/api/claims", headers={"X-Role": "employee"}).status_code
                == 403
            )
            assert (
                client.post(
                    "/api/reviews/absent/decisions",
                    json={
                        "expected_version": 1,
                        "decision": "accept",
                        "rationale": "Valid review",
                    },
                ).status_code
                == 403
            )
            assert (
                client.post(
                    "/api/reviews/absent/decisions",
                    headers={"X-Role": "manager"},
                    json={
                        "expected_version": 1,
                        "decision": "accept",
                        "rationale": "   ",
                    },
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()
