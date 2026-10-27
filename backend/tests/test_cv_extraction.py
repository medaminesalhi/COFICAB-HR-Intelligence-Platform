import fitz
import pytest

from services.cv_extraction import extract_cv_from_pdf


def _make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 50), text)
    content = document.tobytes()
    document.close()
    return content


def test_extract_cv_from_text_pdf():
    pdf = _make_pdf(
        "AMINA BEN SALEM\nData Engineer\nEmail: amina@example.com\n"
        "COMPETENCES\nPython, SQL, Spark\nFORMATION\nMaster Informatique"
    )
    result = extract_cv_from_pdf(pdf)
    assert result["email"] == "amina@example.com"
    assert "python" in result["competences"]
    assert "sql" in result["competences"]
    assert result["formation"]


def test_rejects_non_pdf():
    with pytest.raises(ValueError, match="pas un PDF"):
        extract_cv_from_pdf(b"not a pdf")


def test_reports_scanned_or_empty_pdf_without_text():
    document = fitz.open()
    document.new_page()
    pdf = document.tobytes()
    document.close()
    with pytest.raises(ValueError, match="Aucun texte"):
        extract_cv_from_pdf(pdf)
