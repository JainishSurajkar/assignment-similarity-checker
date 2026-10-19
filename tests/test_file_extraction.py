from io import BytesIO
from types import SimpleNamespace

import pytest
from pypdf.errors import PdfReadError

from file_extraction import extract_text


def test_empty_text_file_is_rejected():
    uploaded = SimpleNamespace(name="empty.txt", getvalue=lambda: b" \n")
    with pytest.raises(ValueError, match="no readable text"):
        extract_text(uploaded)


def test_utf8_text_is_extracted():
    uploaded = SimpleNamespace(
        name="assignment.txt",
        getvalue=lambda: b"An assignment paragraph.",
    )
    assert extract_text(uploaded) == "An assignment paragraph."


def test_invalid_pdf_is_reported():
    uploaded = SimpleNamespace(name="broken.pdf", getvalue=lambda: b"not pdf")
    with pytest.raises(PdfReadError):
        extract_text(uploaded)


def test_invalid_docx_is_reported():
    uploaded = SimpleNamespace(name="broken.docx", getvalue=lambda: b"not docx")
    with pytest.raises(ValueError, match="corrupt|valid Word"):
        extract_text(uploaded)
