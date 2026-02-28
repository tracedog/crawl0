"""API endpoint tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from crawl0.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAPIHealth:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert "jobs_active" in data

    def test_docs_endpoint(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Crawl0 API"
        assert "/scrape" in schema["paths"]
        assert "/crawl" in schema["paths"]
        assert "/extract" in schema["paths"]
        assert "/batch" in schema["paths"]
        assert "/health" in schema["paths"]
