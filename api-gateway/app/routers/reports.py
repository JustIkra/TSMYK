"""
Report upload and download endpoints.
"""

from __future__ import annotations

import base64
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.repositories.report_image import ReportImageRepository
from app.schemas.report import (
    ReportImageResponse,
    ReportListResponse,
    ReportResponse,
    ReportUploadResponse,
)
from app.services.report import ReportService
from app.services.storage import LocalReportStorage
from app.tasks.extraction import extract_images_from_report

router = APIRouter(tags=["reports"])


@router.get(
    "/participants/{participant_id}/reports",
    response_model=ReportListResponse,
)
async def get_participant_reports(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportListResponse:
    """
    Get all reports for a participant.

    Returns list of reports with their current status (UPLOADED, EXTRACTED, FAILED).

    Requires active authentication.
    """
    service = ReportService(db)
    reports = await service.get_participant_reports(participant_id)
    items = [ReportResponse.model_validate(r) for r in reports]
    return ReportListResponse(items=items, total=len(items))


@router.post(
    "/participants/{participant_id}/reports",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_report(
    participant_id: UUID,
    file: UploadFile = File(..., description="DOCX report file"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportUploadResponse:
    """
    Upload a DOCX report for a participant.

    Requires active authentication.
    """
    service = ReportService(db)
    return await service.upload_report(participant_id, file)


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download original DOCX report.

    Returns 304 when If-None-Match matches stored ETag.
    """
    service = ReportService(db)
    context = await service.get_download_context(report_id)

    if ReportService.matches_etag(request.headers.get("if-none-match"), context.etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    headers = {"ETag": ReportService.format_etag(context.etag)}

    return FileResponse(
        path=context.path,
        media_type=context.mime,
        filename=context.filename,
        headers=headers,
    )

@router.delete(
    "/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """
    Delete report with all related data and files.
    Returns 204 No Content on success, 404 if not found.
    """
    service = ReportService(db)
    await service.delete_report(report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/reports/{report_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
)
async def extract_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """
    Start extraction of images from a DOCX report.

    Returns immediately with task ID. Extraction happens asynchronously.
    Report status will be updated to EXTRACTED or FAILED when complete.

    Requires active authentication.
    """
    service = ReportService(db)

    # Verify report exists and belongs to accessible participant
    report = await service.get_report_by_id(report_id)

    # Update report status to PROCESSING
    report.status = "PROCESSING"
    await db.commit()

    # Queue extraction task
    request_id = getattr(request.state, "request_id", None)
    task = extract_images_from_report.delay(str(report_id), request_id=request_id)

    return {
        "report_id": str(report_id),
        "task_id": task.id,
        "status": "accepted",
        "message": "Extraction task started",
    }


@router.get("/reports/{report_id}/images", response_model=list[ReportImageResponse])
async def get_report_images(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ReportImageResponse]:
    """
    Get all images for a report as base64 data URLs.

    Returns list of images with:
    - id: Image UUID
    - filename: Original filename
    - data_url: Base64-encoded data URL (data:image/png;base64,...)
    - page_number: Page number in document (if available)

    Requires active authentication.
    """
    # Verify report exists
    report_service = ReportService(db)
    await report_service.get_report_by_id(report_id)

    # Get all images for the report
    image_repo = ReportImageRepository(db)
    images = await image_repo.get_by_report(report_id)

    if not images:
        return []

    # Initialize storage
    storage = LocalReportStorage(settings.file_storage_base)

    # Convert images to response format
    result = []
    for image in images:
        if not image.file_ref or image.file_ref.storage != "LOCAL":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Only LOCAL storage is supported in this version.",
            )

        # Resolve file path
        file_path = storage.resolve_path(image.file_ref.key)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Image file not found: {image.file_ref.filename}",
            )

        # Read file and encode to base64
        try:
            with file_path.open("rb") as f:
                file_data = f.read()
            base64_data = base64.b64encode(file_data).decode("utf-8")

            # Determine MIME type from file extension or file_ref
            mime_type = image.file_ref.mime
            if not mime_type or mime_type == "application/octet-stream":
                # Infer from filename
                if image.file_ref.filename:
                    ext = image.file_ref.filename.lower().split(".")[-1]
                    mime_map = {
                        "png": "image/png",
                        "jpg": "image/jpeg",
                        "jpeg": "image/jpeg",
                        "gif": "image/gif",
                        "webp": "image/webp",
                    }
                    mime_type = mime_map.get(ext, "image/png")
                else:
                    mime_type = "image/png"

            data_url = f"data:{mime_type};base64,{base64_data}"

            result.append(
                ReportImageResponse(
                    id=image.id,
                    filename=image.file_ref.filename or f"image_{image.order_index}.png",
                    data_url=data_url,
                    page_number=image.page if image.page >= 0 else None,
                )
            )
        except OSError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read image file: {exc}",
            ) from exc

    return result
