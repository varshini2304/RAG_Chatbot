"""Integration test for Workflow 5: Admin Login -> Dashboard APIs -> Analytics APIs -> Export Report Service."""

from __future__ import annotations

from unittest.mock import patch

from starlette.testclient import TestClient

from app.api.api_app import app

client = TestClient(app)


def test_admin_dashboard_and_analytics_integration_workflow() -> None:
    """Test full administrative API sequence: Health check -> Overview -> Analytics -> Telemetry -> Export."""
    # 1. Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # 2. Get Dashboard Overview
    overview_resp = client.get("/api/v1/dashboard/overview")
    assert overview_resp.status_code == 200
    overview_json = overview_resp.json()
    assert overview_json["success"] is True

    # 3. Get System Health
    sys_resp = client.get("/api/v1/dashboard/system-health")
    assert sys_resp.status_code == 200
    sys_json = sys_resp.json()
    assert sys_json["success"] is True

    # 4. Get Analytics Summary
    analytics_resp = client.get("/api/v1/analytics")
    assert analytics_resp.status_code == 200
    analytics_json = analytics_resp.json()
    assert analytics_json["success"] is True

    # 5. Export Enterprise Report
    with patch(
        "app.api.services.excel_report_service.EnterpriseExcelReportService.generate",
        return_value=b"PK\x03\x04mock_excel",
    ):
        export_resp = client.get("/api/v1/export/report")
        assert export_resp.status_code == 200
