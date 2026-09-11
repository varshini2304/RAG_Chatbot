"""
Export Router
==============
Provides the enterprise Excel report download endpoint.
Does NOT modify any existing routes or business logic.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from app.api.services.excel_report_service import EnterpriseExcelReportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


@router.get(
    "/report",
    summary="Download Enterprise Excel Report",
    description=(
        "Generates and streams a polished multi-sheet Excel workbook "
        "containing system health, provider analytics, user activity, "
        "error summaries, and configuration snapshot. "
        "Suitable for administrators, auditors, and management."
    ),
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Excel workbook (.xlsx) download",
        }
    },
)
def download_enterprise_report() -> Response:
    """
    Stream the enterprise Excel report as a file download.
    Filename is automatically timestamped.
    """
    try:
        svc = EnterpriseExcelReportService()
        xlsx_bytes = svc.generate()
        filename = svc.suggested_filename()
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Excel report generation failed: %s\n%s", exc, tb)
        return JSONResponse(  # type: ignore[return-value]
            status_code=500,
            content={
                "success": False,
                "message": f"Report generation failed: {exc}",
                "detail": tb,
            },
        )

    if not xlsx_bytes:
        return JSONResponse(  # type: ignore[return-value]
            status_code=503,
            content={
                "success": False,
                "message": (
                    "Excel generation unavailable. "
                    "Please install openpyxl: "
                    ".\\venv\\Scripts\\python.exe -m pip install 'openpyxl>=3.1,<4.0'"
                ),
            },
        )

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(xlsx_bytes)),
        },
    )
