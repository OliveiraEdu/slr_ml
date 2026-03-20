"""Integration tests for API endpoints."""
import pytest
import httpx


API_BASE = "http://localhost:8000"


class TestHealthEndpoints:
    """Test health and root endpoints."""

    def test_root(self):
        """Test root endpoint returns version."""
        response = httpx.get(f"{API_BASE}/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "0.5.0"

    def test_health(self):
        """Test health endpoint returns status."""
        response = httpx.get(f"{API_BASE}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data


class TestPaperEndpoints:
    """Test paper management endpoints."""

    def test_list_papers_empty(self):
        """Test listing papers when none loaded."""
        response = httpx.get(f"{API_BASE}/papers/list")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_list_papers_with_params(self):
        """Test listing papers with pagination."""
        response = httpx.get(f"{API_BASE}/papers/list?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "papers" in data

    def test_flagged_papers(self):
        """Test getting flagged papers."""
        response = httpx.get(f"{API_BASE}/papers/flagged")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_retrievable_papers(self):
        """Test getting retrievable papers."""
        response = httpx.get(f"{API_BASE}/papers/retrievable")
        assert response.status_code == 200
        data = response.json()
        assert "retrievable_count" in data


class TestScreeningEndpoints:
    """Test screening endpoints."""

    def test_screening_empty(self):
        """Test screening with no papers returns empty."""
        response = httpx.post(
            f"{API_BASE}/screening/run",
            json={"threshold": 0.5},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "no_papers"

    def test_screening_queue_uncertain(self):
        """Test getting uncertain papers queue."""
        response = httpx.get(f"{API_BASE}/screening/queue/uncertain")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_screening_statistics(self):
        """Test getting screening statistics."""
        response = httpx.get(f"{API_BASE}/screening/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "stage1" in data or "total" in data

    def test_screening_progression(self):
        """Test getting screening progression."""
        response = httpx.get(f"{API_BASE}/screening/progression")
        assert response.status_code == 200
        data = response.json()
        assert "total_papers" in data


class TestPrismaEndpoints:
    """Test PRISMA endpoints."""

    def test_prisma_flow_empty(self):
        """Test PRISMA flow with no papers."""
        response = httpx.get(f"{API_BASE}/prisma/flow")
        assert response.status_code == 200
        data = response.json()
        assert "total_records" in data

    def test_prisma_checklist(self):
        """Test getting PRISMA checklist."""
        response = httpx.get(f"{API_BASE}/prisma/checklist")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_prisma_extraction_template(self):
        """Test getting extraction template."""
        response = httpx.get(f"{API_BASE}/prisma/extraction/template")
        assert response.status_code == 200
        data = response.json()
        assert "fields" in data

    def test_prisma_synthesis(self):
        """Test getting synthesis stats."""
        response = httpx.get(f"{API_BASE}/prisma/synthesis")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data


class TestConfigEndpoints:
    """Test configuration endpoints."""

    def test_config_status(self):
        """Test config status."""
        response = httpx.get(f"{API_BASE}/config/status")
        assert response.status_code == 200
        data = response.json()
        assert "loaded" in data

    def test_classification_config(self):
        """Test getting classification config."""
        response = httpx.get(f"{API_BASE}/config/classification")
        assert response.status_code == 200
        data = response.json()
        assert "classification" in data
