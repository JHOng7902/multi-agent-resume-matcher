from io import BytesIO

import pytest
from docx import Document

from pdf_utils import extract_text_from_pdf, extract_text_from_uploaded_file


def test_extract_text_from_pdf_raises_clear_error_for_invalid_pdf():
    invalid_pdf = BytesIO(b"not a real pdf")

    with pytest.raises(ValueError, match="Could not extract text from the uploaded PDF."):
        extract_text_from_pdf(invalid_pdf)


def test_extract_text_from_uploaded_txt_file():
    uploaded_file = BytesIO(b"Software tester role requiring SQL, JIRA, and UAT.")
    uploaded_file.name = "job-description.txt"

    assert (
        extract_text_from_uploaded_file(uploaded_file)
        == "Software tester role requiring SQL, JIRA, and UAT."
    )


def test_extract_text_from_uploaded_file_rejects_unsupported_extension():
    uploaded_file = BytesIO(b"content")
    uploaded_file.name = "job-description.xlsx"

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_uploaded_file(uploaded_file)


def test_extract_text_from_uploaded_docx_file():
    document = Document()
    document.add_paragraph("Business analyst role requiring requirements analysis and SQL.")
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    buffer.name = "job-description.docx"

    assert (
        extract_text_from_uploaded_file(buffer)
        == "Business analyst role requiring requirements analysis and SQL."
    )
