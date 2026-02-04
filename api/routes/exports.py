from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, JSONResponse

from api.dependencies import get_export_service
from services.export_service import ExportService

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.get("/json")
def export_json(service: ExportService = Depends(get_export_service)):
    data = service.export_json(save_to_file=False)
    return JSONResponse(content=__import__("json").loads(data))


@router.get("/csv")
def export_csv(service: ExportService = Depends(get_export_service)):
    data = service.export_csv(save_to_file=False)
    return PlainTextResponse(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=price_monitor_export.csv"},
    )
