"""System Test Scenario 6: Telemetry & Analytics Report Export."""

from __future__ import annotations

from unittest.mock import patch

from starlette.testclient import TestClient

from app.api.api_app import app

client = TestClient(app)


def test_system_scenario_6_export_analytics_reports() -> None:
    """System Scenario 6: Verify export report endpoint options and file generation capabilities."""
    with patch(
        "app.api.services.excel_report_service.EnterpriseExcelReportService.generate",
        return_value=b"PK\x03\x04mock_excel",
    ):
        export_resp = client.get("/api/v1/export/report")
        assert export_resp.status_code == 200
        assert (
            export_resp.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
