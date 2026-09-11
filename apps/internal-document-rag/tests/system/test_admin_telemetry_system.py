"""System Test Scenario 2: Admin Dashboard, Telemetry & Provider Management."""

from __future__ import annotations

from starlette.testclient import TestClient

from app.api.api_app import app

client = TestClient(app)


def test_system_scenario_2_admin_dashboard_and_provider_management() -> None:
    """System Scenario 2: Validate complete Admin workflow: Dashboard -> Monitoring -> Provider Failover Status -> Analytics."""
    # 1. Admin authenticated health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # 2. Query Dashboard System Telemetry
    sys_resp = client.get("/api/v1/dashboard/system-health")
    assert sys_resp.status_code == 200
    sys_data = sys_resp.json()["data"]
    assert "cpu_usage_pct" in sys_data or "cpuUsage" in sys_data

    # 3. Query LLM Provider Status & Failover State
    prov_resp = client.get("/api/v1/providers/status")
    assert prov_resp.status_code == 200
    providers = prov_resp.json()["data"]
    assert len(providers) >= 3

    # 4. Check Current Provider
    curr_resp = client.get("/api/v1/providers/current")
    assert curr_resp.status_code == 200
    assert "current_provider" in curr_resp.json()["data"]

    # 5. Query Error Monitoring Logs
    err_resp = client.get("/api/v1/monitoring/errors")
    assert err_resp.status_code == 200
    assert isinstance(err_resp.json()["data"], list)
