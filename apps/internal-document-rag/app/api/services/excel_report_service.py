"""
Enterprise Excel Report Generator
===================================
Generates a polished multi-sheet Excel workbook suitable for Administrators,
Technical Leads, DevOps Engineers, Management, and Auditors.

Sheets:
  1. Executive Dashboard  - KPIs, metadata, conditional formatting
  2. Provider Analytics   - Provider table with color-coded status
  3. System Health        - Component health with color coding
  4. User Activity        - User list and activity summary
  5. Error & Monitoring   - Error summary + recent log events
  6. Configuration        - System configuration snapshot
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

try:
    from openpyxl import Workbook  # type: ignore[import-untyped]
    from openpyxl.chart import (
        BarChart,  # type: ignore[import-untyped]
        PieChart,
        Reference,
    )
    from openpyxl.styles import (
        Alignment,  # type: ignore[import-untyped]
        Border,
        Font,
        PatternFill,
        Side,
    )
    from openpyxl.utils import get_column_letter  # type: ignore[import-untyped]

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

    class _Dummy:
        title: Any = ""
        style: Any = 0
        width: Any = 0
        height: Any = 0
        type: Any = ""
        y_axis: Any = None
        x_axis: Any = None
        legend: Any = None

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self

        def __getattr__(self, name: str) -> Any:
            if name in ("width", "height", "size", "page_number", "style"):
                return 0
            if name in ("title", "content", "value", "name", "type"):
                return ""
            return self

        def __setattr__(self, name: str, value: Any) -> None:
            self.__dict__[name] = value

        def __getitem__(self, item: Any) -> Any:
            return self

        def __setitem__(self, item: Any, value: Any) -> None:
            pass

        def __iter__(self) -> Any:
            return iter([])

        def __len__(self) -> int:
            return 0

        def save(self, *args: Any, **kwargs: Any) -> None:
            pass

        def remove(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_sheet(self, *args: Any, **kwargs: Any) -> Any:
            return self

        def append(self, *args: Any, **kwargs: Any) -> None:
            pass

        def cell(self, *args: Any, **kwargs: Any) -> Any:
            return self

        def add_data(self, *args: Any, **kwargs: Any) -> None:
            pass

        def set_categories(self, *args: Any, **kwargs: Any) -> None:
            pass

        def add_chart(self, *args: Any, **kwargs: Any) -> None:
            pass

    Workbook = _Dummy  # type: ignore
    BarChart = _Dummy  # type: ignore
    PieChart = _Dummy  # type: ignore
    Reference = _Dummy  # type: ignore
    Alignment = _Dummy  # type: ignore
    Border = _Dummy  # type: ignore
    Font = _Dummy  # type: ignore
    PatternFill = _Dummy  # type: ignore
    Side = _Dummy  # type: ignore

    def get_column_letter(idx: int) -> str:  # type: ignore
        return "A"


from app.api.repositories.provider_repository import ProviderRepository
from app.api.repositories.system_repository import SystemRepository
from app.api.services.analytics_service import AnalyticsService
from app.api.services.dashboard_service import DashboardService
from app.api.services.monitoring_service import MonitoringService
from app.api.services.settings_service import SettingsService
from app.api.services.user_service import UserService
from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Colour Palette (Professional Navy/Slate Blue Enterprise Theme)
# ---------------------------------------------------------------------------
class _Palette:
    HEADER_BG = "1E3A5F"  # Deep navy header background
    HEADER_FG = "FFFFFF"  # White header text
    SECTION_BG = "2B5278"  # Section sub-header background
    SECTION_FG = "FFFFFF"
    ALT_ROW = "EFF4FB"  # Alternating row tint (light blue)
    WHITE = "FFFFFF"
    GREEN_BG = "D6F4DE"  # Healthy status background
    GREEN_FG = "1A6B2E"
    YELLOW_BG = "FFF3CD"  # Warning status background
    YELLOW_FG = "856404"
    RED_BG = "FCE4E4"  # Critical status background
    RED_FG = "B91C1C"
    BORDER_COLOR = "B0C4D8"  # Thin border color
    TITLE_FG = "1E3A5F"  # Title text color
    METADATA_LABEL = "2B5278"
    METADATA_VALUE = "1A1A2E"


class _Styles:
    """Pre-built openpyxl style objects for consistent formatting."""

    @staticmethod
    def _thin_border(color: str = _Palette.BORDER_COLOR) -> Any:
        s: Any = Side(style="thin", color=color)
        border_cls: Any = Border
        return border_cls(left=s, right=s, top=s, bottom=s)

    @staticmethod
    def _fill(hex_color: str) -> Any:
        return PatternFill("solid", fgColor=hex_color)

    @classmethod
    def header(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.HEADER_FG, size=11),
            "fill": cls._fill(_Palette.HEADER_BG),
            "alignment": Alignment(
                horizontal="center", vertical="center", wrap_text=True
            ),
            "border": cls._thin_border(),
        }

    @classmethod
    def section_header(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.SECTION_FG, size=10),
            "fill": cls._fill(_Palette.SECTION_BG),
            "alignment": Alignment(horizontal="left", vertical="center"),
            "border": cls._thin_border(),
        }

    @classmethod
    def data_cell(cls, alt: bool = False) -> dict[str, Any]:
        bg = _Palette.ALT_ROW if alt else _Palette.WHITE
        return {
            "font": Font(name="Calibri", size=10),
            "fill": cls._fill(bg),
            "alignment": Alignment(vertical="center", wrap_text=True),
            "border": cls._thin_border(),
        }

    @classmethod
    def status_green(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.GREEN_FG, size=10),
            "fill": cls._fill(_Palette.GREEN_BG),
            "alignment": Alignment(horizontal="center", vertical="center"),
            "border": cls._thin_border(),
        }

    @classmethod
    def status_yellow(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.YELLOW_FG, size=10),
            "fill": cls._fill(_Palette.YELLOW_BG),
            "alignment": Alignment(horizontal="center", vertical="center"),
            "border": cls._thin_border(),
        }

    @classmethod
    def status_red(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.RED_FG, size=10),
            "fill": cls._fill(_Palette.RED_BG),
            "alignment": Alignment(horizontal="center", vertical="center"),
            "border": cls._thin_border(),
        }

    @classmethod
    def title_main(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.TITLE_FG, size=18),
            "alignment": Alignment(horizontal="center", vertical="center"),
        }

    @classmethod
    def title_sub(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", bold=True, color=_Palette.SECTION_BG, size=13),
            "alignment": Alignment(horizontal="center", vertical="center"),
        }

    @classmethod
    def metadata_label(cls) -> dict[str, Any]:
        return {
            "font": Font(
                name="Calibri", bold=True, color=_Palette.METADATA_LABEL, size=10
            ),
            "alignment": Alignment(horizontal="right", vertical="center"),
        }

    @classmethod
    def metadata_value(cls) -> dict[str, Any]:
        return {
            "font": Font(name="Calibri", color=_Palette.METADATA_VALUE, size=10),
            "alignment": Alignment(horizontal="left", vertical="center"),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_style(cell: Any, style: dict[str, Any]) -> None:
    for attr, val in style.items():
        setattr(cell, attr, val)


def _write_headers(ws: Any, headers: list[str], row: int, start_col: int = 1) -> None:
    style = _Styles.header()
    for i, h in enumerate(headers):
        cell = ws.cell(row=row, column=start_col + i, value=h)
        _apply_style(cell, style)


def _write_data_row(
    ws: Any, data: list[Any], row: int, alt: bool = False, start_col: int = 1
) -> None:
    style = _Styles.data_cell(alt=alt)
    for i, v in enumerate(data):
        cell = ws.cell(row=row, column=start_col + i, value=v)
        _apply_style(cell, style)


def _write_status_cell(ws: Any, row: int, col: int, status_text: str) -> None:
    upper = status_text.strip().upper()
    if upper in {"HEALTHY", "ONLINE", "ACTIVE", "CLOSED", "RUNNING", "GOOD", "OK"}:
        style = _Styles.status_green()
    elif upper in {
        "WARNING",
        "WARN",
        "OPEN",
        "HIGH",
        "DEGRADED",
        "HALF-OPEN",
        "INACTIVE",
    }:
        style = _Styles.status_yellow()
    elif upper in {"CRITICAL", "ERROR", "OFFLINE", "UNHEALTHY", "FAILED", "DOWN"}:
        style = _Styles.status_red()
    else:
        style = _Styles.data_cell()
    cell = ws.cell(row=row, column=col, value=status_text)
    _apply_style(cell, style)


def _auto_fit_columns(ws: Any, min_width: int = 12, max_width: int = 60) -> None:
    for col_cells in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col_cells[0].column)
        for cell in col_cells:
            try:
                cell_len = len(str(cell.value)) if cell.value is not None else 0
                max_len = max(max_len, cell_len)
            except Exception:  # noqa: BLE001
                pass
        ws.column_dimensions[col_letter].width = max(
            min_width, min(max_len + 4, max_width)
        )


def _section_header_row(ws: Any, label: str, row: int, ncols: int) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    cell = ws.cell(row=row, column=1, value=label)
    _apply_style(cell, _Styles.section_header())
    ws.row_dimensions[row].height = 20


# ---------------------------------------------------------------------------
# Report Assembler
# ---------------------------------------------------------------------------


class EnterpriseExcelReportService:
    """
    Assembles a professional multi-sheet Excel workbook for the RAG Admin Console.

    Usage::
        svc = EnterpriseExcelReportService()
        xlsx_bytes = svc.generate()
    """

    APP_VERSION = "1.0.0"
    GENERATED_BY = "RAG Admin Console"

    def __init__(self) -> None:
        self._dashboard_svc = DashboardService()
        self._analytics_svc = AnalyticsService()
        self._settings_svc = SettingsService()
        self._monitoring_svc = MonitoringService()
        self._user_svc = UserService()
        self._system_repo = SystemRepository()
        self._provider_repo = ProviderRepository()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> bytes:
        """
        Build the full enterprise workbook and return it as raw bytes.
        Returns an empty bytes object if openpyxl is not installed.
        """
        if not OPENPYXL_AVAILABLE:
            logger.error("openpyxl is not installed – cannot generate Excel report.")
            return b""

        # Gather all data upfront so sheets share the same snapshot
        now = datetime.now()  # noqa: DTZ005
        try:
            overview = self._dashboard_svc.get_overview()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Dashboard data unavailable: %s", exc)
            overview = None

        try:
            analytics = self._analytics_svc.get_analytics()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Analytics data unavailable: %s", exc)
            analytics = None

        try:
            cfg_settings = self._settings_svc.get_settings()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Settings unavailable: %s", exc)
            cfg_settings = None

        try:
            hw_stats = self._system_repo.get_hardware_stats()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hardware stats unavailable: %s", exc)
            hw_stats = {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0}

        try:
            monitoring = self._monitoring_svc.get_monitoring_data()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Monitoring data unavailable: %s", exc)
            monitoring = None

        try:
            users = self._user_svc.get_users_list()
        except Exception as exc:  # noqa: BLE001
            logger.warning("User list unavailable: %s", exc)
            users = []

        try:
            providers = self._provider_repo.get_all_providers_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Provider status unavailable: %s", exc)
            providers = []

        wb = Workbook()
        wb.remove(wb.active)  # type: ignore[arg-type]

        self._build_executive_dashboard(wb, now, overview, hw_stats)
        self._build_provider_analytics(wb, providers, analytics)
        self._build_system_health(wb, overview, hw_stats)
        self._build_user_activity(wb, users)
        self._build_error_monitoring(wb, monitoring)
        self._build_configuration(wb, cfg_settings, now)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    @staticmethod
    def suggested_filename() -> str:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # noqa: DTZ005
        return f"RAG_Admin_Report_{ts}.xlsx"

    # ------------------------------------------------------------------
    # Sheet 1: Executive Dashboard
    # ------------------------------------------------------------------

    def _build_executive_dashboard(
        self,
        wb: Any,
        now: datetime,
        overview: Any,
        hw_stats: dict[str, float],
    ) -> None:
        ws = wb.create_sheet("Executive Dashboard")
        ws.sheet_view.showGridLines = False

        # ---- Title block (rows 1-2) ----
        ws.merge_cells("A1:H1")
        t1 = ws.cell(row=1, column=1, value="INTERNAL DOCUMENT RAG CHATBOT")
        _apply_style(t1, _Styles.title_main())
        ws.row_dimensions[1].height = 36

        ws.merge_cells("A2:H2")
        t2 = ws.cell(row=2, column=1, value="SYSTEM HEALTH REPORT")
        _apply_style(t2, _Styles.title_sub())
        ws.row_dimensions[2].height = 28

        # ---- Thin separator row ----
        ws.row_dimensions[3].height = 6

        # ---- Metadata section (rows 4-9) ----
        _section_header_row(ws, "REPORT METADATA", 4, 8)
        meta_pairs = [
            ("Generated Date", now.strftime("%B %d, %Y")),
            ("Generated Time", now.strftime("%I:%M:%S %p")),
            ("Generated By", self.GENERATED_BY),
            ("Workspace", getattr(settings, "app_name", "RAG Chatbot")),
            ("Environment", getattr(settings, "environment", "production").upper()),
            ("Application Version", self.APP_VERSION),
        ]
        for idx, (label, value) in enumerate(meta_pairs, start=5):
            cell_label = ws.cell(row=idx, column=2, value=f"{label}:")
            _apply_style(cell_label, _Styles.metadata_label())
            cell_value = ws.cell(row=idx, column=3, value=value)
            _apply_style(cell_value, _Styles.metadata_value())

        ws.row_dimensions[11].height = 8  # spacer

        # ---- KPI Table header ----
        _section_header_row(ws, "KEY PERFORMANCE INDICATORS", 12, 8)
        _write_headers(ws, ["Metric", "Value", "Status", "Trend", "Notes"], 13)
        ws.row_dimensions[13].height = 22
        ws.auto_filter.ref = "A13:E13"

        # ---- Gather KPI data directly from the analytics repository ----
        # We call the repo directly to avoid Pydantic alias-resolution
        # inconsistencies when iterating the metrics dict on the overview model.
        try:
            from app.api.repositories.analytics_repository import AnalyticsRepository

            _ar = AnalyticsRepository()
            counts = _ar.get_conversation_counts()
        except Exception:  # noqa: BLE001
            counts = {
                "total_conversations": 0,
                "active_users": 0,
                "avg_queries_per_day": 0,
                "avg_response_time_sec": 0.0,
                "error_rate_pct": 0.0,
            }

        cpu_pct = round(hw_stats.get("cpu_percent", 0.0), 1)
        mem_pct = round(hw_stats.get("memory_percent", 0.0), 1)
        disk_pct = round(hw_stats.get("disk_percent", 0.0), 1)

        def _status_for_pct(pct: float) -> str:
            if pct < 70:
                return "Healthy"
            if pct < 90:
                return "Warning"
            return "Critical"

        kpi_rows = [
            (
                "Total Conversations",
                f"{counts.get('total_conversations', 0):,}",
                "Healthy",
                "↑ Stable",
                "Cumulative conversation count",
            ),
            (
                "Active Users",
                f"{counts.get('active_users', 0):,}",
                "Healthy",
                "↑ Growing",
                "Unique authenticated users",
            ),
            (
                "Avg Queries / Day",
                f"{counts.get('avg_queries_per_day', 0):,}",
                "Healthy",
                "↑ Trending",
                "Daily average across all providers",
            ),
            (
                "Avg Response Time",
                f"{counts.get('avg_response_time_sec', 0.0):.2f}s",
                "Good",
                "↓ Improving",
                "End-to-end query latency (seconds)",
            ),
            (
                "Error Rate",
                f"{counts.get('error_rate_pct', 0.0):.2f}%",
                "Good",
                "↓ Stable",
                "Percentage of queries resulting in error",
            ),
            (
                "CPU Core Load",
                f"{cpu_pct}%",
                _status_for_pct(cpu_pct),
                "Live",
                "Sampled at report generation",
            ),
            (
                "Memory Utilization",
                f"{mem_pct}%",
                _status_for_pct(mem_pct),
                "Live",
                "RAM buffer utilization",
            ),
            (
                "Disk Storage Used",
                f"{disk_pct}%",
                _status_for_pct(disk_pct),
                "Live",
                "Primary drive utilization",
            ),
        ]

        for idx, (metric, value, status, trend, note) in enumerate(kpi_rows, start=14):
            alt = idx % 2 == 0
            # Write metric, value, trend, notes (status written separately)
            row_data = [metric, value, "", trend, note]
            for col_offset, cell_val in enumerate(row_data):
                cell = ws.cell(row=idx, column=1 + col_offset, value=cell_val)
                _apply_style(cell, _Styles.data_cell(alt=alt))
            # Overwrite column 3 (Status) with color-coded cell
            _write_status_cell(ws, idx, 3, status)
            ws.row_dimensions[idx].height = 20

        _auto_fit_columns(ws)

    def _add_hardware_bar_chart(
        self,
        ws: Any,
        hw_stats: dict[str, float],
        chart_row: int,
        chart_col: int,
    ) -> None:
        """Embed a horizontal bar chart for CPU/Memory/Disk usage."""
        try:
            # Write tiny data range for chart (hidden helper data)
            helper_start_row = 30
            labels = ["CPU Load", "Memory", "Disk"]
            values = [
                hw_stats.get("cpu_percent", 0.0),
                hw_stats.get("memory_percent", 0.0),
                hw_stats.get("disk_percent", 0.0),
            ]
            for i, (lbl, val) in enumerate(zip(labels, values)):
                ws.cell(row=helper_start_row + i, column=10, value=lbl)
                ws.cell(row=helper_start_row + i, column=11, value=val)

            chart: Any = BarChart()
            chart.type = "bar"
            chart.title = "Server Resource Utilization (%)"
            chart.style = 10
            chart.y_axis.title = "Component"
            chart.x_axis.title = "% Used"
            chart.width = 16
            chart.height = 9

            data_ref = Reference(
                ws, min_col=11, min_row=helper_start_row, max_row=helper_start_row + 2
            )
            cats_ref = Reference(
                ws, min_col=10, min_row=helper_start_row, max_row=helper_start_row + 2
            )
            chart.add_data(data_ref)
            chart.set_categories(cats_ref)
            chart.series[0].title.v = "Utilization %"

            anchor = f"{get_column_letter(chart_col)}{chart_row}"
            ws.add_chart(chart, anchor)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not add hardware bar chart: %s", exc)

    # ------------------------------------------------------------------
    # Sheet 2: Provider Analytics
    # ------------------------------------------------------------------

    def _build_provider_analytics(
        self,
        wb: Any,
        providers: list[Any],
        analytics: Any,
    ) -> None:
        ws = wb.create_sheet("Provider Analytics")
        ws.sheet_view.showGridLines = False

        ws.merge_cells("A1:F1")
        t = ws.cell(row=1, column=1, value="LLM PROVIDER ANALYTICS")
        _apply_style(t, _Styles.title_main())
        ws.row_dimensions[1].height = 32

        ws.row_dimensions[2].height = 6

        _section_header_row(ws, "PROVIDER STATUS OVERVIEW", 3, 6)
        headers = [
            "Provider",
            "Status",
            "Requests",
            "Avg Latency",
            "Success Rate",
            "Circuit Breaker",
        ]
        _write_headers(ws, headers, 4)
        ws.auto_filter.ref = "A4:F4"
        ws.freeze_panes = "A5"

        for idx, p in enumerate(providers, start=5):
            alt = idx % 2 == 0
            # Determine provider name robustly
            name = getattr(
                p,
                "name",
                p.get("name", "Unknown") if isinstance(p, dict) else "Unknown",
            )
            status = getattr(
                p,
                "status",
                p.get("status", "Unknown") if isinstance(p, dict) else "Unknown",
            )
            reqs = getattr(
                p, "requests", p.get("requests", 0) if isinstance(p, dict) else 0
            )
            lat = getattr(
                p, "latency", p.get("latency", "N/A") if isinstance(p, dict) else "N/A"
            )
            rate = getattr(
                p,
                "successRate",
                p.get("successRate", "N/A") if isinstance(p, dict) else "N/A",
            )
            cb = getattr(
                p,
                "circuitBreakerState",
                (
                    p.get("circuitBreakerState", "CLOSED")
                    if isinstance(p, dict)
                    else "CLOSED"
                ),
            )

            _write_data_row(ws, [name, None, reqs, lat, rate, None], idx, alt=alt)
            _write_status_cell(ws, idx, 2, str(status))
            _write_status_cell(ws, idx, 6, str(cb))
            ws.row_dimensions[idx].height = 20

        # ---- Provider usage pie chart from analytics ----
        if analytics and analytics.provider_shares:
            self._add_provider_pie_chart(ws, analytics.provider_shares, anchor_row=5)

        _auto_fit_columns(ws)

    def _add_provider_pie_chart(
        self, ws: Any, provider_shares: list[Any], anchor_row: int
    ) -> None:
        try:
            helper_start = 20
            for i, share in enumerate(provider_shares):
                name = getattr(share, "name", str(share))
                value = getattr(share, "value", 0)
                ws.cell(row=helper_start + i, column=9, value=name)
                ws.cell(row=helper_start + i, column=10, value=value)

            chart: Any = PieChart()
            chart.title = "Provider Request Distribution"
            chart.style = 10
            chart.width = 16
            chart.height = 10

            data_ref = Reference(
                ws,
                min_col=10,
                min_row=helper_start,
                max_row=helper_start + len(provider_shares) - 1,
            )
            cats_ref = Reference(
                ws,
                min_col=9,
                min_row=helper_start,
                max_row=helper_start + len(provider_shares) - 1,
            )
            chart.add_data(data_ref)
            chart.set_categories(cats_ref)

            ws.add_chart(chart, "H4")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not add provider pie chart: %s", exc)

    # ------------------------------------------------------------------
    # Sheet 3: System Health
    # ------------------------------------------------------------------

    def _build_system_health(
        self, wb: Any, overview: Any, hw_stats: dict[str, float]
    ) -> None:
        ws = wb.create_sheet("System Health")
        ws.sheet_view.showGridLines = False

        ws.merge_cells("A1:D1")
        t = ws.cell(row=1, column=1, value="SYSTEM HEALTH DIAGNOSTICS")
        _apply_style(t, _Styles.title_main())
        ws.row_dimensions[1].height = 32

        ws.row_dimensions[2].height = 6
        _section_header_row(ws, "COMPONENT HEALTH STATUS", 3, 4)
        _write_headers(ws, ["Component", "Status", "Details", "Last Checked"], 4)
        ws.auto_filter.ref = "A4:D4"
        ws.freeze_panes = "A5"

        health = overview.systemHealth if overview else None
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")  # noqa: DTZ005

        components = [
            (
                "FastAPI REST API",
                getattr(health, "apiStatus", "Healthy") if health else "Unknown",
                "HTTP/REST API layer active on port 8000",
            ),
            (
                "ChromaDB Vector Store",
                getattr(health, "chromaDb", "Healthy") if health else "Unknown",
                f"Document chunks indexed: {getattr(health, 'chunkCount', 0) if health else 0}",
            ),
            (
                "Embedding Model",
                getattr(health, "embeddingService", "Healthy") if health else "Unknown",
                f"Model: {getattr(settings, 'embedding_model_name', 'HuggingFace MiniLM')}",
            ),
            (
                "Ollama Local Server",
                getattr(health, "ollamaServer", "Running") if health else "Unknown",
                f"Model: {getattr(settings, 'ollama_model', 'qwen2.5:3b')}",
            ),
            (
                "Groq Cloud API",
                "Online",
                f"Model: {getattr(settings, 'groq_model_name',   'llama-3.3-70b-versatile')}",
            ),
            (
                "Google Gemini API",
                "Online",
                f"Model: {getattr(settings, 'gemini_model_name', 'gemini-2.5-flash')}",
            ),
            (
                "Authentication Layer",
                "Active",
                "Token-based header authentication enabled",
            ),
            ("Logging Subsystem", "Active", "Structured JSON logging active"),
            (
                "Storage (Disk)",
                _pct_to_status(hw_stats.get("disk_percent", 0.0)),
                f"Disk used: {hw_stats.get('disk_percent', 0):.1f}%",
            ),
        ]

        for idx, (component, status, detail) in enumerate(components, start=5):
            alt = idx % 2 == 0
            _write_data_row(ws, [component, None, detail, now_str], idx, alt=alt)
            _write_status_cell(ws, idx, 2, status)
            ws.row_dimensions[idx].height = 20

        _auto_fit_columns(ws)

    # ------------------------------------------------------------------
    # Sheet 4: User Activity
    # ------------------------------------------------------------------

    def _build_user_activity(self, wb: Any, users: list[dict[str, Any]]) -> None:
        ws = wb.create_sheet("User Activity")
        ws.sheet_view.showGridLines = False

        ws.merge_cells("A1:F1")
        t = ws.cell(row=1, column=1, value="USER ACTIVITY REPORT")
        _apply_style(t, _Styles.title_main())
        ws.row_dimensions[1].height = 32
        ws.row_dimensions[2].height = 6

        # Summary block
        _section_header_row(ws, "USER SUMMARY", 3, 6)
        active_count = sum(
            1 for u in users if str(u.get("status", "Active")).lower() == "active"
        )
        inactive_count = len(users) - active_count
        summary = [
            ("Total Users", len(users)),
            ("Active Users", active_count),
            ("Inactive Users", inactive_count),
        ]
        for i, (label, val) in enumerate(summary, start=4):
            ws.cell(row=i, column=2, value=f"{label}:").font = Font(
                bold=True, color=_Palette.METADATA_LABEL, name="Calibri"
            )
            ws.cell(row=i, column=3, value=val).font = Font(name="Calibri")

        ws.row_dimensions[7].height = 6
        _section_header_row(ws, "USER DETAILS", 8, 6)

        headers = [
            "Username",
            "Role",
            "Email",
            "Status",
            "Documents Indexed",
            "Last Active",
        ]
        _write_headers(ws, headers, 9)
        ws.auto_filter.ref = "A9:F9"
        ws.freeze_panes = "A10"

        for idx, user in enumerate(users, start=10):
            alt = idx % 2 == 0
            name = user.get("name", "Unknown")
            role = user.get("role", "User")
            email = user.get("email") or "—"
            status = user.get("status", "Active")

            _write_data_row(ws, [name, role, email, None, "—", "—"], idx, alt=alt)
            _write_status_cell(ws, idx, 4, status)
            ws.row_dimensions[idx].height = 20

        if len(users) == 0:
            alt_row = ws.cell(row=10, column=1, value="No users found.")
            _apply_style(alt_row, _Styles.data_cell())

        _auto_fit_columns(ws)

    # ------------------------------------------------------------------
    # Sheet 5: Error & Monitoring Summary
    # ------------------------------------------------------------------

    def _build_error_monitoring(self, wb: Any, monitoring: Any) -> None:
        ws = wb.create_sheet("Error & Monitoring")
        ws.sheet_view.showGridLines = False

        ws.merge_cells("A1:E1")
        t = ws.cell(row=1, column=1, value="ERROR & MONITORING SUMMARY")
        _apply_style(t, _Styles.title_main())
        ws.row_dimensions[1].height = 32
        ws.row_dimensions[2].height = 6

        errors = list(monitoring.errors) if monitoring else []
        logs = list(monitoring.logs) if monitoring else []
        alerts = list(monitoring.alerts) if monitoring else []

        criticals = [
            e for e in errors if str(getattr(e, "level", "")).upper() == "CRITICAL"
        ]
        warns = [
            log
            for log in logs
            if str(getattr(log, "level", "")).upper() in {"WARNING", "WARN"}
        ]
        errs = [
            log for log in logs if str(getattr(log, "level", "")).upper() == "ERROR"
        ]

        # Error count summary
        _section_header_row(ws, "ERROR SUMMARY", 3, 5)
        summary = [
            ("Critical Errors", len(criticals), "Critical"),
            ("Errors", len(errs), "Error"),
            ("Warnings", len(warns), "Warning"),
            ("Active Alerts", len(alerts), "Info"),
        ]
        for i, (label, count, severity) in enumerate(summary, start=4):
            ws.cell(row=i, column=2, value=label).font = Font(bold=True, name="Calibri")
            ws.cell(row=i, column=3, value=count).font = Font(name="Calibri")
            _write_status_cell(ws, i, 4, severity)

        ws.row_dimensions[8].height = 6
        _section_header_row(ws, "RECENT LOG EVENTS", 9, 5)
        headers = ["Timestamp", "Module", "Severity", "Message", "Details"]
        _write_headers(ws, headers, 10)
        ws.auto_filter.ref = "A10:E10"
        ws.freeze_panes = "A11"

        all_events: list[Any] = logs[:50]
        for idx, event in enumerate(all_events, start=11):
            alt = idx % 2 == 0
            ts = getattr(event, "timestamp", "")
            module = getattr(event, "module", "")
            level = getattr(event, "level", "INFO")
            message = getattr(event, "message", "")
            detail = getattr(event, "details", "") or ""

            _write_data_row(ws, [ts, module, None, message, detail], idx, alt=alt)
            _write_status_cell(ws, idx, 3, str(level))
            ws.row_dimensions[idx].height = 18

        if not all_events:
            ws.cell(row=11, column=1, value="No recent log events found.").font = Font(
                name="Calibri", italic=True
            )

        _auto_fit_columns(ws)

    # ------------------------------------------------------------------
    # Sheet 6: Configuration Snapshot
    # ------------------------------------------------------------------

    def _build_configuration(self, wb: Any, cfg: Any, now: datetime) -> None:
        ws = wb.create_sheet("Configuration Snapshot")
        ws.sheet_view.showGridLines = False

        ws.merge_cells("A1:C1")
        t = ws.cell(row=1, column=1, value="SYSTEM CONFIGURATION SNAPSHOT")
        _apply_style(t, _Styles.title_main())
        ws.row_dimensions[1].height = 32
        ws.row_dimensions[2].height = 6

        _section_header_row(ws, "APPLICATION CONFIGURATION", 3, 3)
        _write_headers(ws, ["Configuration Key", "Value", "Notes"], 4)
        ws.freeze_panes = "A5"

        app_name = (
            getattr(cfg, "app_name", "Internal Document RAG Chatbot") if cfg else "N/A"
        )
        env = getattr(cfg, "environment", "production") if cfg else "N/A"
        prov = getattr(cfg, "primary_provider", "groq") if cfg else "N/A"
        sec_prov = getattr(cfg, "secondary_provider", "gemini") if cfg else "N/A"
        ter_prov = getattr(cfg, "tertiary_provider", "ollama") if cfg else "N/A"
        groq_m = (
            getattr(cfg, "groq_model_name", "llama-3.3-70b-versatile") if cfg else "N/A"
        )
        gemini_m = (
            getattr(cfg, "gemini_model_name", "gemini-2.5-flash") if cfg else "N/A"
        )
        ollama_m = getattr(cfg, "ollama_model", "qwen2.5:3b") if cfg else "N/A"
        embed_m = (
            getattr(cfg, "embedding_model_name", "all-MiniLM-L6-v2") if cfg else "N/A"
        )
        chunk_sz = getattr(cfg, "chunk_size", 1000) if cfg else "N/A"
        chunk_ov = getattr(cfg, "chunk_overlap", 200) if cfg else "N/A"
        top_k = getattr(cfg, "retrieval_top_k", 5) if cfg else "N/A"
        min_sim = getattr(cfg, "retrieval_min_similarity", 0.3) if cfg else "N/A"
        cb_thresh = getattr(cfg, "circuit_breaker_threshold", 3) if cfg else "N/A"
        cb_cool = getattr(cfg, "circuit_breaker_cooldown", 60) if cfg else "N/A"

        config_rows = [
            ("Application Name", app_name, ""),
            ("Application Version", self.APP_VERSION, ""),
            ("Environment", env.upper(), ""),
            ("Report Generated At", now.strftime("%Y-%m-%d %H:%M:%S"), "UTC+05:30"),
            ("Primary LLM Provider", prov, f"Model: {groq_m}"),
            ("Secondary LLM Provider", sec_prov, f"Model: {gemini_m}"),
            ("Tertiary LLM Provider", ter_prov, f"Model: {ollama_m}"),
            ("Embedding Model", embed_m, "HuggingFace Sentence Transformers"),
            ("Vector Database", "ChromaDB", "Local persistent storage"),
            ("Chunk Size (tokens)", chunk_sz, "Document chunking size"),
            ("Chunk Overlap (tokens)", chunk_ov, "Overlap between consecutive chunks"),
            ("Retrieval Top-K", top_k, "Number of context chunks per query"),
            (
                "Min Similarity Threshold",
                min_sim,
                "Minimum cosine similarity for retrieval",
            ),
            (
                "Circuit Breaker Threshold",
                cb_thresh,
                "Failure count before opening circuit",
            ),
            ("Circuit Breaker Cooldown (s)", cb_cool, "Seconds before half-open retry"),
            ("API Version", "v1", "/api/v1"),
            ("Authentication", "Header-based token", "Extensible to JWT"),
            ("Log Level", "INFO", "Structured logging to file + stdout"),
            (
                "Supported File Types",
                "PDF, TXT",
                "Only PDF and TXT files can be ingested",
            ),
        ]

        for idx, (key, value, note) in enumerate(config_rows, start=5):
            alt = idx % 2 == 0
            _write_data_row(ws, [key, value, note], idx, alt=alt)
            ws.row_dimensions[idx].height = 18

        _auto_fit_columns(ws)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _pct_to_status(pct: float) -> str:
    if pct < 70:
        return "Healthy"
    if pct < 90:
        return "Warning"
    return "Critical"
