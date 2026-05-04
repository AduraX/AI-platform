"""Document text extraction powered by Docling.

Docling handles PDFs, DOCX, PPTX, HTML, images (PNG/JPEG/TIFF/BMP),
AsciiDoc, Markdown, CSV, and XLSX through a single unified API with
ML-based layout analysis and table extraction.
"""
from __future__ import annotations

import io
import logging
import mimetypes
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Types that Docling handles natively
DOCLING_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "text/html",
    "text/csv",
    "text/asciidoc",
    "text/markdown",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/gif",
    "image/webp",
}

# Plain text types we handle directly without Docling overhead
PLAIN_TEXT_TYPES = {
    "text/plain",
    "application/json",
    "application/xml",
    "text/xml",
}


@dataclass
class ExtractionResult:
    text: str
    content_type: str
    page_count: int | None = None
    tables: list[str] = field(default_factory=list)


def detect_content_type(object_key: str) -> str:
    """Guess MIME type from the object key (filename)."""
    mime, _ = mimetypes.guess_type(object_key)
    return mime or "application/octet-stream"


def extract_text_with_docling(data: bytes, filename: str) -> ExtractionResult:
    """Extract text using Docling's DocumentConverter.

    Writes data to a temp file because Docling's DocumentStream
    requires a seekable source with a filename for format detection.
    """
    from docling.datamodel.base_models import DocumentStream
    from docling.document_converter import DocumentConverter

    source = DocumentStream(name=filename, stream=io.BytesIO(data))
    converter = DocumentConverter()
    result = converter.convert(source)

    markdown_text = result.document.export_to_markdown()

    page_count = None
    if hasattr(result.document, "pages") and result.document.pages:
        page_count = len(result.document.pages)

    tables: list[str] = []
    for table in result.document.tables:
        table_md = table.export_to_markdown()
        if table_md.strip():
            tables.append(table_md)

    content_type = detect_content_type(filename)
    return ExtractionResult(
        text=markdown_text,
        content_type=content_type,
        page_count=page_count,
        tables=tables,
    )


def extract_text_from_plain(data: bytes, content_type: str) -> ExtractionResult:
    """Read plain text / JSON / XML files directly."""
    for encoding in ("utf-8", "latin-1"):
        try:
            text = data.decode(encoding)
            return ExtractionResult(text=text, content_type=content_type)
        except UnicodeDecodeError:
            continue
    return ExtractionResult(
        text=data.decode("utf-8", errors="replace"),
        content_type=content_type,
    )


def extract_text(data: bytes, object_key: str) -> ExtractionResult:
    """Route extraction to the appropriate handler based on file type."""
    content_type = detect_content_type(object_key)
    filename = object_key.rsplit("/", 1)[-1] if "/" in object_key else object_key
    logger.info("Extracting text from %s (detected: %s)", object_key, content_type)

    if content_type in PLAIN_TEXT_TYPES:
        return extract_text_from_plain(data, content_type)

    if content_type in DOCLING_TYPES:
        return extract_text_with_docling(data, filename)

    # Unknown type — try plain text first, fall back to Docling
    try:
        result = extract_text_from_plain(data, content_type)
        if result.text.strip():
            return result
    except Exception:
        pass

    logger.info("Unknown type %s — attempting Docling extraction", content_type)
    return extract_text_with_docling(data, filename)
