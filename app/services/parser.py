import io

from PyPDF2 import PdfReader

from app.core.exceptions import DocumentParseError, UnsupportedFileTypeError


def extract_text(filename: str, content: bytes) -> str:
    """
    Extract plain text from PDF or TXT file bytes.
    Raises UnsupportedFileTypeError for unsupported extensions.
    Raises DocumentParseError if extraction fails.
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "txt":
        return _extract_txt(content)
    if ext == "pdf":
        return _extract_pdf(content)
    raise UnsupportedFileTypeError(ext)


def _extract_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8", errors="replace").strip()
    except Exception as exc:
        raise DocumentParseError(f"Failed to decode TXT file: {exc}") from exc


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        if not pages:
            raise DocumentParseError("PDF contains no extractable text.")
        return "\n\n".join(pages)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"Failed to parse PDF: {exc}") from exc
