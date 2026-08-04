"""
Excel routes — upload, preview, confirm import, and export.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.excel import (
    ExcelUploadResponse,
    ExcelConfirmRequest,
    ExcelConfirmResponse,
)
from app.services import excel_import, excel_export

router = APIRouter(prefix="/excel", tags=["Excel Import/Export"])


@router.post("/upload", response_model=ExcelUploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an Excel file for preview and column mapping.
    Does NOT save to database — returns preview + mapping suggestions.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx são aceitos")

    # Validate file size
    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o limite de {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    try:
        return await excel_import.process_upload(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar arquivo: {str(e)}")


@router.post("/confirm", response_model=ExcelConfirmResponse)
async def confirm_import(
    data: ExcelConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm column mapping and execute the import.
    Saves transactions to the database.
    """
    try:
        return await excel_import.confirm_import(db, current_user.id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export")
async def export_excel(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export transactions to a formatted Excel file."""
    file_bytes, filename = await excel_export.export_transactions(
        db, current_user.id, start_date, end_date
    )

    return StreamingResponse(
        file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
