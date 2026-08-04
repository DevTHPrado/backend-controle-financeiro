"""Pydantic schemas for Excel import/export flow."""

import uuid
from pydantic import BaseModel, Field


class ColumnMappingSuggestion(BaseModel):
    """Suggested mapping for a single column."""
    original_column: str
    suggested_field: str | None = None  # "date" | "amount" | "description" | None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    sample_values: list[str] = []


class ExcelUploadResponse(BaseModel):
    """Response after uploading an Excel file — preview + mapping suggestions."""
    upload_id: str  # Temporary ID to reference the uploaded file
    filename: str
    total_rows: int
    columns: list[str]
    suggestions: list[ColumnMappingSuggestion]
    preview_rows: list[dict]  # First 5 rows as dicts


class ExcelConfirmRequest(BaseModel):
    """User-confirmed column mapping to finalize import."""
    upload_id: str
    column_mapping: dict[str, str]  # {"date": "Col A", "amount": "Col B", "description": "Col C"}
    default_type: str = "DESPESA"  # RECEITA | DESPESA — applies to all rows if no type column
    default_category_id: uuid.UUID | None = None


class ExcelConfirmResponse(BaseModel):
    """Result of confirmed import."""
    batch_id: uuid.UUID
    imported_rows: int
    skipped_rows: int
    errors: list[str] = []
