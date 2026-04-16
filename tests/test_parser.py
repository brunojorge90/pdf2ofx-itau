import pytest
from parser_pdf import parse_transaction_line, extract_due_date_year, infer_year, normalize_encoding, parse_pdf


def test_parse_simple_transaction():
    line = "24/02\tDM*Spotify\t40,90"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["day"] == 24
    assert result["month"] == 2
    assert result["description"] == "DM*Spotify"
    assert result["amount"] == -40.90


def test_parse_installment_transaction():
    line = "01/09\tVIVA MOVEIS\t19/21\t333,40"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["description"] == "VIVA MOVEIS 19/21"
    assert result["amount"] == -333.40


def test_parse_negative_adjustment():
    line = "20/01\tIG*LL12minMEGAB\t- 0,03"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["amount"] == 0.03


def test_parse_large_value():
    line = "18/12\tMP *SPECIALC-CT\t04/06\t2.166,70"
    result = parse_transaction_line(line)
    assert result is not None
    assert result["amount"] == -2166.70


def test_ignore_non_transaction_line():
    line = "Total da fatura anterior"
    result = parse_transaction_line(line)
    assert result is None


def test_ignore_header_line():
    line = "DATA\tESTABELECIMENTO\tVALOR EM R$"
    result = parse_transaction_line(line)
    assert result is None


def test_extract_due_date_year():
    text = "Vencimento\n26/03/2026\nOutra coisa"
    assert extract_due_date_year(text) == (2026, 3)


def test_infer_year_same_year():
    assert infer_year(month=2, due_month=3, due_year=2026) == 2026


def test_infer_year_cross_year():
    assert infer_year(month=12, due_month=1, due_year=2026) == 2025


def test_infer_year_cross_year_feb():
    assert infer_year(month=11, due_month=1, due_year=2026) == 2025


def test_normalize_encoding():
    assert normalize_encoding("VESTU\ufffdRIO") == "VESTUÁRIO"
    assert normalize_encoding("TURISMO E ENTRETENIM") == "TURISMO E ENTRETENIM"


def test_parse_real_pdf():
    transactions = parse_pdf(r"C:\Users\Dell\Projetos\pdf2ofx-itau\Fatura_Itau_26.03.26.pdf")
    assert len(transactions) > 50
    first = transactions[0]
    assert "date" in first
    assert "description" in first
    assert "amount" in first
    assert "category" in first
