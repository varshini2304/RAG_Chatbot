"""Integration tests for FastAPI Admin Console REST API routers."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.api.api_app import app

client = TestClient(app)


class TestRootHealthRouter:
    """Test cases for root application health check."""

    def test_health_check_returns_healthy(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "healthy"
        assert "app_name" in json_data
        assert "environment" in json_data


class TestProvidersRouter:
    """Test cases for /api/v1/providers endpoints."""

    def test_get_providers_summary(self) -> None:
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert "message" in json_data
        assert "data" in json_data

        data = json_data["data"]
        assert "currentProvider" in data or "current_provider" in data
        assert "providers" in data
        assert isinstance(data["providers"], list)
        assert len(data["providers"]) >= 3

        provider_names = [p["name"] for p in data["providers"]]
        assert "Groq Cloud" in provider_names
        assert "Google Gemini" in provider_names
        assert "Ollama Server" in provider_names

    def test_get_current_provider(self) -> None:
        response = client.get("/api/v1/providers/current")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert "current_provider" in json_data["data"]

    def test_get_providers_status(self) -> None:
        response = client.get("/api/v1/providers/status")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)
        assert len(json_data["data"]) >= 3


class TestSettingsRouter:
    """Test cases for /api/v1/settings endpoints."""

    def test_get_system_settings(self) -> None:
        response = client.get("/api/v1/settings")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "app_name" in data or "appName" in data
        assert "primary_provider" in data or "primaryProvider" in data

    def test_update_system_settings_success(self) -> None:
        payload = {
            "primary_provider": "groq",
            "chunk_size": 1024,
            "retrieval_top_k": 5,
        }
        response = client.put("/api/v1/settings", json=payload)
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert data["primary_provider"] == "groq"
        assert data["chunk_size"] == 1024

    def test_update_system_settings_validation_error(self) -> None:
        # Invalid integer type for chunk_size to trigger Pydantic 422 error
        payload = {
            "chunk_size": "not-an-integer-value",
        }
        response = client.put("/api/v1/settings", json=payload)
        assert (
            response.status_code == 422
        )  # Unprocessable Entity for Pydantic validation error


class TestDashboardRouter:
    """Test cases for /api/v1/dashboard endpoints."""

    def test_get_dashboard_overview(self) -> None:
        response = client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "metrics" in data
        assert "systemHealth" in data or "system_health" in data
        assert "providerStatus" in data or "provider_status" in data
        assert "recentActivities" in data or "recent_activities" in data

    def test_get_system_health(self) -> None:
        response = client.get("/api/v1/dashboard/system-health")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "apiStatus" in data or "api_status" in data
        assert "cpuUsage" in data or "cpu_usage_pct" in data

    def test_get_provider_status(self) -> None:
        response = client.get("/api/v1/dashboard/provider-status")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "activeProvider" in data or "active_provider" in data

    def test_get_recent_activity(self) -> None:
        response = client.get("/api/v1/dashboard/recent-activity")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)


class TestAnalyticsRouter:
    """Test cases for /api/v1/analytics endpoints."""

    def test_get_all_analytics(self) -> None:
        response = client.get("/api/v1/analytics")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "trendData" in data or "trend_data" in data
        assert "providerShares" in data or "provider_shares" in data

    def test_get_conversation_analytics(self) -> None:
        response = client.get("/api/v1/analytics/conversations?time_frame=daily")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)

    def test_get_provider_usage_analytics(self) -> None:
        response = client.get("/api/v1/analytics/provider-usage")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)


class TestMonitoringRouter:
    """Test cases for /api/v1/monitoring endpoints."""

    def test_get_monitoring_data(self) -> None:
        response = client.get("/api/v1/monitoring")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "logs" in data
        assert "errors" in data
        assert "alerts" in data

    def test_get_system_logs_with_filter(self) -> None:
        response = client.get("/api/v1/monitoring/logs?level=INFO&limit=10")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)

    def test_get_system_errors(self) -> None:
        response = client.get("/api/v1/monitoring/errors")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)


class TestUsersRouter:
    """Test cases for /api/v1/users and RBAC endpoints."""

    def test_get_user_profile_me(self) -> None:
        response = client.get("/api/v1/users/me")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        data = json_data["data"]
        assert "username" in data
        assert "role" in data

    def test_get_users_list(self) -> None:
        response = client.get("/api/v1/users")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)

    def test_get_roles_list(self) -> None:
        response = client.get("/api/v1/roles")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)

    def test_get_api_keys(self) -> None:
        response = client.get("/api/v1/apikeys")
        assert response.status_code == 200
        json_data = response.json()

        assert json_data["success"] is True
        assert isinstance(json_data["data"], list)
