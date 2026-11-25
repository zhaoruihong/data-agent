from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.api.dependencies import get_report_service
from app.api.schemas.query_schema import QuerySchema
from app.services.report_service import ReportService

report_router = APIRouter()

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@report_router.post("/api/report")
async def generate_report(
    query: QuerySchema, report_service: ReportService = Depends(get_report_service)
):
    content, disposition = await report_service.generate_report(query.query)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )


@report_router.post("/api/report/data")
async def generate_report_data(
    query: QuerySchema, report_service: ReportService = Depends(get_report_service)
):
    payload = await report_service.generate_report_data(query.query)
    return JSONResponse(content=payload)