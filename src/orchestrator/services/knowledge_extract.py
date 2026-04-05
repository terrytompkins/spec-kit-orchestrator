"""Extract plain text from uploaded file bytes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Set, Tuple

# (extension lower, mime hints) — we trust extension + magic less; Streamlit gives type
_TEXT_EXTENSIONS: Set[str] = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".json",
    ".yml",
    ".yaml",
}
_PDF_EXTENSIONS: Set[str] = {".pdf"}
_DOCX_EXTENSIONS: Set[str] = {".docx"}


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def extract_text(file_bytes: bytes, filename: str) -> Tuple[str, Optional[str]]:
    """
    Returns (text, error_message). error_message set on failure.
    """
    ext = _ext(filename)
    try:
        if ext in _TEXT_EXTENSIONS:
            return file_bytes.decode("utf-8", errors="replace"), None
        if ext in _PDF_EXTENSIONS:
            return _extract_pdf(file_bytes)
        if ext in _DOCX_EXTENSIONS:
            return _extract_docx(file_bytes)
    except Exception as e:
        return "", str(e)
    return "", f"Unsupported file type ({ext or 'no extension'}). Use .txt, .md, .csv, .pdf, or .docx."


def _extract_pdf(data: bytes) -> Tuple[str, Optional[str]]:
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    text = "\n\n".join(parts).strip()
    if not text:
        return "", "No text extracted from PDF (may be scanned images only)."
    return text, None


def _extract_docx(data: bytes) -> Tuple[str, Optional[str]]:
    from io import BytesIO
    from docx import Document

    doc = Document(BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(parts).strip()
    if not text:
        return "", "No text found in DOCX."
    return text, None


def is_supported_filename(filename: str) -> bool:
    return _ext(filename) in _TEXT_EXTENSIONS | _PDF_EXTENSIONS | _DOCX_EXTENSIONS
