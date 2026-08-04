"""
Excel import service — heuristic column detection + 2-step import flow.

Heuristics strategy (3 layers, priority order):
1. Column name matching against PT-BR/EN dictionaries
2. Data type inference (date/numeric/text patterns)
3. Position-based tiebreaking
"""

import uuid
import re
import tempfile
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.import_batch import ImportBatch
from app.schemas.excel import (
    ColumnMappingSuggestion,
    ExcelUploadResponse,
    ExcelConfirmRequest,
    ExcelConfirmResponse,
)

# Temporary storage for uploaded files (keyed by upload_id)
# In production, use Redis or object storage; for v1, in-memory dict is fine.
_upload_cache: dict[str, dict] = {}

# ─── Heuristic dictionaries ───────────────────────────────────────────

DATE_KEYWORDS = {
    "data", "date", "dt", "vencimento", "competencia", "competência",
    "data_transacao", "data_pagamento", "data_lancamento", "periodo",
}
AMOUNT_KEYWORDS = {
    "valor", "value", "amount", "montante", "preço", "preco", "total",
    "quantia", "vlr", "debito", "credito", "débito", "crédito",
}
DESCRIPTION_KEYWORDS = {
    "descricao", "descrição", "description", "desc", "categoria",
    "item", "historico", "histórico", "obs", "observacao", "observação",
    "memo", "detalhe", "nome",
}


def _normalize(text: str) -> str:
    """Normalize column name for matching: lowercase, strip, remove accents."""
    return re.sub(r"[^a-z0-9]", "", text.lower().strip())


def _try_parse_date(value: str) -> bool:
    """Try to parse a string as a Brazilian date (dd/mm/yyyy) or ISO date."""
    if not isinstance(value, str):
        return False
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            datetime.strptime(value.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def _try_parse_br_number(value: str) -> bool:
    """Try to parse a Brazilian-formatted number (1.234,56)."""
    if not isinstance(value, str):
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    cleaned = value.strip().replace("R$", "").replace(" ", "").strip()
    # Brazilian format: 1.234,56 → remove dots, replace comma with dot
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        Decimal(cleaned)
        return True
    except (InvalidOperation, ValueError):
        return False


def _detect_column_type(series: pd.Series) -> tuple[str | None, float]:
    """
    Analyze a column's values to detect its type.
    Returns (suggested_field, confidence).
    """
    non_null = series.dropna().astype(str).head(50)
    if len(non_null) == 0:
        return None, 0.0

    # Check date pattern
    date_matches = sum(1 for v in non_null if _try_parse_date(str(v)))
    date_ratio = date_matches / len(non_null)
    if date_ratio >= 0.7:
        return "date", date_ratio

    # Check numeric pattern
    num_matches = sum(1 for v in non_null if _try_parse_br_number(str(v)))
    num_ratio = num_matches / len(non_null)
    if num_ratio >= 0.7:
        return "amount", num_ratio

    # Default: text → description
    return "description", 0.5


def analyze_columns(df: pd.DataFrame) -> list[ColumnMappingSuggestion]:
    """
    Run heuristics to suggest column mappings.
    Returns suggestions for each column.
    """
    suggestions: list[ColumnMappingSuggestion] = []
    assigned_fields: set[str] = set()

    # Layer 1: Name matching
    name_matches: dict[str, tuple[str, float]] = {}
    for col in df.columns:
        normalized = _normalize(str(col))
        if normalized in {_normalize(k) for k in DATE_KEYWORDS}:
            name_matches[col] = ("date", 0.9)
        elif normalized in {_normalize(k) for k in AMOUNT_KEYWORDS}:
            name_matches[col] = ("amount", 0.9)
        elif normalized in {_normalize(k) for k in DESCRIPTION_KEYWORDS}:
            name_matches[col] = ("description", 0.9)

    # Layer 2: Data type inference for unmatched columns
    type_matches: dict[str, tuple[str, float]] = {}
    for col in df.columns:
        if col not in name_matches:
            field, confidence = _detect_column_type(df[col])
            if field:
                type_matches[col] = (field, confidence)

    # Build suggestions with priority: name > type > position
    all_matches = {**type_matches, **name_matches}  # name_matches overrides

    # Assign fields, ensuring uniqueness (one column per field)
    for col in df.columns:
        sample = df[col].dropna().head(5).astype(str).tolist()

        if col in all_matches:
            field, confidence = all_matches[col]
            if field not in assigned_fields:
                suggestions.append(
                    ColumnMappingSuggestion(
                        original_column=str(col),
                        suggested_field=field,
                        confidence=confidence,
                        sample_values=sample,
                    )
                )
                assigned_fields.add(field)
            else:
                suggestions.append(
                    ColumnMappingSuggestion(
                        original_column=str(col),
                        suggested_field=None,
                        confidence=0.0,
                        sample_values=sample,
                    )
                )
        else:
            suggestions.append(
                ColumnMappingSuggestion(
                    original_column=str(col),
                    suggested_field=None,
                    confidence=0.0,
                    sample_values=sample,
                )
            )

    return suggestions


def parse_br_date(value) -> datetime | None:
    """Parse a date value from various Brazilian formats."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if not isinstance(value, str):
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_br_amount(value) -> Decimal | None:
    """Parse a monetary value from Brazilian format (1.234,56)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip().replace("R$", "").replace(" ", "").strip()
        # Remove thousand separators (dots) and replace decimal comma
        cleaned = cleaned.replace(".", "").replace(",", ".")
        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
    return None


async def process_upload(file_content: bytes, filename: str) -> ExcelUploadResponse:
    """
    Process an uploaded Excel file: read, analyze columns, return preview.
    Does NOT save to database — just stores in temp cache for confirmation.
    """
    # Save to temp file for pandas to read
    upload_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)

    with open(temp_path, "wb") as f:
        f.write(file_content)

    # Read with pandas
    df = pd.read_excel(temp_path, engine="openpyxl")

    # Analyze columns
    suggestions = analyze_columns(df)

    # Build preview (first 5 rows)
    preview_rows = df.head(5).fillna("").astype(str).to_dict(orient="records")

    # Cache the dataframe for later confirmation
    _upload_cache[upload_id] = {
        "df": df,
        "filename": filename,
        "temp_path": temp_path,
    }

    return ExcelUploadResponse(
        upload_id=upload_id,
        filename=filename,
        total_rows=len(df),
        columns=[str(c) for c in df.columns],
        suggestions=suggestions,
        preview_rows=preview_rows,
    )


async def confirm_import(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: ExcelConfirmRequest,
) -> ExcelConfirmResponse:
    """
    Confirm and execute import with user-validated column mapping.
    Creates an ImportBatch and Transaction records.
    """
    cached = _upload_cache.pop(data.upload_id, None)
    if not cached:
        raise ValueError("Upload expirado ou não encontrado. Faça o upload novamente.")

    df: pd.DataFrame = cached["df"]
    filename: str = cached["filename"]

    # Clean up temp file
    try:
        os.unlink(cached["temp_path"])
    except OSError:
        pass

    mapping = data.column_mapping
    date_col = mapping.get("date")
    amount_col = mapping.get("amount")
    desc_col = mapping.get("description")

    if not date_col or not amount_col:
        raise ValueError("Mapeamento deve incluir pelo menos colunas de 'date' e 'amount'")

    # Create import batch
    batch = ImportBatch(
        user_id=user_id,
        original_filename=filename,
        total_rows=len(df),
        column_mapping=mapping,
        status="PENDING",
    )
    db.add(batch)
    await db.flush()

    imported = 0
    skipped = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 for 1-based + header row

        # Parse date
        parsed_date = parse_br_date(row.get(date_col))
        if not parsed_date:
            errors.append(f"Linha {row_num}: data inválida '{row.get(date_col)}'")
            skipped += 1
            continue

        # Parse amount
        parsed_amount = parse_br_amount(row.get(amount_col))
        if not parsed_amount:
            errors.append(f"Linha {row_num}: valor inválido '{row.get(amount_col)}'")
            skipped += 1
            continue

        # Determine type from amount sign or default
        tx_type = data.default_type
        if parsed_amount < 0:
            tx_type = "DESPESA"
            parsed_amount = abs(parsed_amount)

        # Description
        description = str(row.get(desc_col, "")).strip() if desc_col else None
        if description == "nan":
            description = None

        transaction = Transaction(
            user_id=user_id,
            category_id=data.default_category_id,
            type=tx_type,
            amount=parsed_amount,
            transaction_date=parsed_date.date(),
            description=description,
            origin="IMPORT",
            import_batch_id=batch.id,
        )
        db.add(transaction)
        imported += 1

    batch.imported_rows = imported
    batch.status = "COMPLETED" if imported > 0 else "FAILED"

    await db.commit()

    return ExcelConfirmResponse(
        batch_id=batch.id,
        imported_rows=imported,
        skipped_rows=skipped,
        errors=errors[:20],  # Limit error messages
    )
