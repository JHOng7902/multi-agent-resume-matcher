from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from utils import clean_text


def extract_text_from_pdf(uploaded_file) -> str:
    try:
        reader = PdfReader(uploaded_file)
        page_text = []
        for page in reader.pages:
            page_text.append(page.extract_text() or "")
        text = clean_text("\n".join(page_text))
    except Exception as exc:
        raise ValueError("Could not extract text from the uploaded PDF.") from exc

    if not text:
        raise ValueError("Could not extract text from the uploaded PDF.")
    return text


def extract_text_from_uploaded_file(uploaded_file) -> str:
    file_name = getattr(uploaded_file, "name", "")
    suffix = Path(file_name).suffix.lower()
    data = _read_uploaded_bytes(uploaded_file)

    if suffix == ".pdf":
        return extract_text_from_pdf(BytesIO(data))
    if suffix == ".txt":
        return _extract_text_from_txt(data)
    if suffix == ".docx":
        return _extract_text_from_docx(data)

    raise ValueError("Unsupported file type. Upload a PDF, DOCX, or TXT file.")


def _read_uploaded_bytes(uploaded_file) -> bytes:
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()

    current_position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    data = uploaded_file.read()
    if current_position is not None and hasattr(uploaded_file, "seek"):
        uploaded_file.seek(current_position)
    return data


def _extract_text_from_txt(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            text = data.decode(encoding)
            cleaned = clean_text(text)
            if cleaned:
                return cleaned
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not extract text from the uploaded text file.")


def _extract_text_from_docx(data: bytes) -> str:
    try:
        document = Document(BytesIO(data))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        cleaned = clean_text(text)
    except Exception as exc:
        raise ValueError("Could not extract text from the uploaded DOCX file.") from exc

    if not cleaned:
        raise ValueError("Could not extract text from the uploaded DOCX file.")
    return cleaned
