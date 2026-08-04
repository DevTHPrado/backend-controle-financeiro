"""
Tests for Excel import service — heuristics and parsing.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.services.excel_import import (
    _normalize,
    _try_parse_date,
    _try_parse_br_number,
    parse_br_date,
    parse_br_amount,
    analyze_columns,
)

import pandas as pd


class TestNormalize:
    def test_lowercase_strip(self):
        assert _normalize("  Data  ") == "data"

    def test_remove_special_chars(self):
        assert _normalize("Descrição") == "descrio"

    def test_remove_spaces(self):
        assert _normalize("Data Transação") == "datatransao"


class TestDateParsing:
    def test_br_date_ddmmyyyy(self):
        assert _try_parse_date("15/03/2024") is True

    def test_br_date_ddmmyy(self):
        assert _try_parse_date("15/03/24") is True

    def test_iso_date(self):
        assert _try_parse_date("2024-03-15") is True

    def test_invalid_date(self):
        assert _try_parse_date("not a date") is False

    def test_empty_string(self):
        assert _try_parse_date("") is False

    def test_parse_br_date_returns_datetime(self):
        result = parse_br_date("25/12/2024")
        assert isinstance(result, datetime)
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2024

    def test_parse_br_date_iso(self):
        result = parse_br_date("2024-12-25")
        assert result.day == 25

    def test_parse_br_date_invalid(self):
        assert parse_br_date("invalid") is None


class TestAmountParsing:
    def test_br_format_with_comma(self):
        assert _try_parse_br_number("1.234,56") is True

    def test_simple_number(self):
        assert _try_parse_br_number("100") is True

    def test_with_currency_symbol(self):
        assert _try_parse_br_number("R$ 1.234,56") is True

    def test_negative_br(self):
        assert _try_parse_br_number("-500,00") is True

    def test_invalid_value(self):
        assert _try_parse_br_number("abc") is False

    def test_parse_br_amount_comma_decimal(self):
        result = parse_br_amount("1.234,56")
        assert result == Decimal("1234.56")

    def test_parse_br_amount_simple(self):
        result = parse_br_amount("100")
        assert result == Decimal("100")

    def test_parse_br_amount_currency(self):
        result = parse_br_amount("R$ 500,00")
        assert result == Decimal("500.00")

    def test_parse_br_amount_float(self):
        result = parse_br_amount(1234.56)
        assert result == Decimal("1234.56")

    def test_parse_br_amount_none(self):
        assert parse_br_amount(None) is None

    def test_parse_br_amount_invalid(self):
        assert parse_br_amount("abc") is None


class TestColumnHeuristics:
    def test_detects_date_by_name(self):
        df = pd.DataFrame({
            "Data": ["01/01/2024", "02/01/2024"],
            "Valor": [100.0, 200.0],
            "Descrição": ["Compra", "Venda"],
        })
        suggestions = analyze_columns(df)
        date_sug = next(s for s in suggestions if s.original_column == "Data")
        assert date_sug.suggested_field == "date"
        assert date_sug.confidence >= 0.9

    def test_detects_amount_by_name(self):
        df = pd.DataFrame({
            "Data": ["01/01/2024"],
            "Valor": [100.0],
            "Desc": ["Compra"],
        })
        suggestions = analyze_columns(df)
        amount_sug = next(s for s in suggestions if s.original_column == "Valor")
        assert amount_sug.suggested_field == "amount"

    def test_detects_description_by_name(self):
        df = pd.DataFrame({
            "Data": ["01/01/2024"],
            "Valor": [100.0],
            "Descrição": ["Compra"],
        })
        suggestions = analyze_columns(df)
        desc_sug = next(s for s in suggestions if s.original_column == "Descrição")
        assert desc_sug.suggested_field == "description"

    def test_detects_by_data_type_when_name_unknown(self):
        df = pd.DataFrame({
            "Col_A": ["01/01/2024", "02/01/2024", "03/01/2024", "04/01/2024", "05/01/2024"],
            "Col_B": [100.0, 200.0, 300.0, 400.0, 500.0],
            "Col_C": ["Compra A", "Compra B", "Compra C", "Compra D", "Compra E"],
        })
        suggestions = analyze_columns(df)

        col_a = next(s for s in suggestions if s.original_column == "Col_A")
        col_b = next(s for s in suggestions if s.original_column == "Col_B")
        assert col_a.suggested_field == "date"
        assert col_b.suggested_field == "amount"

    def test_includes_sample_values(self):
        df = pd.DataFrame({"Data": ["01/01/2024", "02/01/2024"]})
        suggestions = analyze_columns(df)
        assert len(suggestions[0].sample_values) > 0
