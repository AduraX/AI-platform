"""Tests for text extraction logic."""
from unittest.mock import MagicMock, patch

from ocr_service.extraction import (
    ExtractionResult,
    detect_content_type,
    extract_text,
    extract_text_from_plain,
)

# --- Content type detection ---

def test_detect_pdf():
    assert detect_content_type("documents/abc/report.pdf") == "application/pdf"


def test_detect_png():
    assert detect_content_type("documents/abc/scan.png") == "image/png"


def test_detect_jpeg():
    assert detect_content_type("documents/abc/photo.jpg") == "image/jpeg"


def test_detect_tiff():
    assert detect_content_type("documents/abc/scan.tiff") == "image/tiff"


def test_detect_plain_text():
    assert detect_content_type("documents/abc/notes.txt") == "text/plain"


def test_detect_csv():
    assert detect_content_type("documents/abc/data.csv") == "text/csv"


def test_detect_json():
    assert detect_content_type("documents/abc/config.json") == "application/json"


def test_detect_markdown():
    ct = detect_content_type("documents/abc/readme.md")
    assert ct in ("text/markdown", "text/x-markdown")


def test_detect_docx():
    ct = detect_content_type("documents/abc/report.docx")
    assert "wordprocessingml" in ct


def test_detect_pptx():
    ct = detect_content_type("documents/abc/slides.pptx")
    assert "presentationml" in ct


def test_detect_xlsx():
    ct = detect_content_type("documents/abc/data.xlsx")
    assert "spreadsheetml" in ct


def test_detect_html():
    assert detect_content_type("documents/abc/page.html") == "text/html"


def test_detect_unknown():
    assert detect_content_type("documents/abc/file.xyz") != ""


# --- Plain text extraction ---

def test_extract_plain_text_utf8():
    data = b"Hello, world!"
    result = extract_text_from_plain(data, "text/plain")
    assert result.text == "Hello, world!"
    assert result.content_type == "text/plain"


def test_extract_plain_text_latin1():
    data = "café résumé".encode("latin-1")
    result = extract_text_from_plain(data, "text/plain")
    assert "caf" in result.text


def test_extract_csv_as_plain():
    data = b"name,age\nAlice,30\nBob,25"
    # CSV via PLAIN_TEXT_TYPES would not apply (CSV is in DOCLING_TYPES)
    # but extract_text_from_plain handles it if called directly
    result = extract_text_from_plain(data, "text/csv")
    assert "Alice" in result.text


def test_extract_json_as_plain():
    data = b'{"key": "value"}'
    result = extract_text_from_plain(data, "application/json")
    assert '"key"' in result.text


# --- Routing to correct handler ---

def test_extract_text_routes_plain_text():
    data = b"Some plain text content"
    result = extract_text(data, "documents/abc/file.txt")
    assert result.text == "Some plain text content"
    assert result.content_type == "text/plain"


def test_extract_text_routes_json():
    data = b'{"key": "value"}'
    result = extract_text(data, "documents/abc/config.json")
    assert '"key"' in result.text
    assert result.content_type == "application/json"


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_pdf_to_docling(mock_docling):
    mock_docling.return_value = ExtractionResult(
        text="# Report\n\nPDF content here",
        content_type="application/pdf",
        page_count=2,
        tables=["| col1 | col2 |"],
    )
    result = extract_text(b"%PDF-fake", "documents/abc/report.pdf")
    mock_docling.assert_called_once_with(b"%PDF-fake", "report.pdf")
    assert result.text == "# Report\n\nPDF content here"
    assert result.page_count == 2
    assert len(result.tables) == 1


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_image_to_docling(mock_docling):
    mock_docling.return_value = ExtractionResult(
        text="OCR text from image", content_type="image/png"
    )
    result = extract_text(b"\x89PNG", "documents/abc/scan.png")
    mock_docling.assert_called_once_with(b"\x89PNG", "scan.png")
    assert result.text == "OCR text from image"


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_docx_to_docling(mock_docling):
    docx_type = (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    )
    mock_docling.return_value = ExtractionResult(
        text="Word document content", content_type=docx_type
    )
    result = extract_text(b"PK\x03\x04", "documents/abc/report.docx")
    mock_docling.assert_called_once_with(b"PK\x03\x04", "report.docx")
    assert result.text == "Word document content"


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_pptx_to_docling(mock_docling):
    pptx_type = (
        "application/vnd.openxmlformats-officedocument"
        ".presentationml.presentation"
    )
    mock_docling.return_value = ExtractionResult(
        text="Slide content", content_type=pptx_type
    )
    result = extract_text(b"PK\x03\x04", "documents/abc/slides.pptx")
    mock_docling.assert_called_once()
    assert result.text == "Slide content"


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_html_to_docling(mock_docling):
    mock_docling.return_value = ExtractionResult(
        text="Web page content", content_type="text/html"
    )
    result = extract_text(b"<html>", "documents/abc/page.html")
    mock_docling.assert_called_once()
    assert result.text == "Web page content"


@patch("ocr_service.extraction.extract_text_with_docling")
def test_extract_text_routes_csv_to_docling(mock_docling):
    mock_docling.return_value = ExtractionResult(
        text="| name | age |\n|---|---|\n| Alice | 30 |",
        content_type="text/csv",
    )
    result = extract_text(b"name,age\nAlice,30", "documents/abc/data.csv")
    mock_docling.assert_called_once()
    assert "Alice" in result.text


# --- Docling integration (mocked) ---

def test_extract_with_docling_mocked():
    import sys

    mock_docling_module = MagicMock()
    mock_base_models = MagicMock()

    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Title\n\nDocument content"
    mock_doc.pages = {"page1": MagicMock()}
    mock_doc.tables = []

    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter_cls = MagicMock()
    mock_converter_instance = MagicMock()
    mock_converter_instance.convert.return_value = mock_result
    mock_converter_cls.return_value = mock_converter_instance

    mock_docling_module.DocumentConverter = mock_converter_cls

    with patch.dict(sys.modules, {
        "docling": MagicMock(),
        "docling.document_converter": mock_docling_module,
        "docling.datamodel": MagicMock(),
        "docling.datamodel.base_models": mock_base_models,
    }):
        from importlib import reload

        import ocr_service.extraction as ext_mod
        reload(ext_mod)
        result = ext_mod.extract_text_with_docling(b"file data", "report.pdf")
        assert result.text == "# Title\n\nDocument content"
        assert result.content_type == "application/pdf"
        assert result.page_count == 1


def test_extract_with_docling_tables():
    import sys

    mock_docling_module = MagicMock()
    mock_base_models = MagicMock()

    mock_table = MagicMock()
    mock_table.export_to_markdown.return_value = "| col1 | col2 |\n|---|---|\n| a | b |"

    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "Document with table"
    mock_doc.pages = {}
    mock_doc.tables = [mock_table]

    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter_cls = MagicMock()
    mock_converter_instance = MagicMock()
    mock_converter_instance.convert.return_value = mock_result
    mock_converter_cls.return_value = mock_converter_instance

    mock_docling_module.DocumentConverter = mock_converter_cls

    with patch.dict(sys.modules, {
        "docling": MagicMock(),
        "docling.document_converter": mock_docling_module,
        "docling.datamodel": MagicMock(),
        "docling.datamodel.base_models": mock_base_models,
    }):
        from importlib import reload

        import ocr_service.extraction as ext_mod
        reload(ext_mod)
        result = ext_mod.extract_text_with_docling(b"file data", "data.pdf")
        assert len(result.tables) == 1
        assert "col1" in result.tables[0]


# --- ExtractionResult dataclass ---

def test_extraction_result_defaults():
    result = ExtractionResult(text="hello", content_type="text/plain")
    assert result.page_count is None
    assert result.tables == []


def test_extraction_result_with_all_fields():
    result = ExtractionResult(
        text="content",
        content_type="application/pdf",
        page_count=5,
        tables=["| a | b |"],
    )
    assert result.page_count == 5
    assert len(result.tables) == 1
