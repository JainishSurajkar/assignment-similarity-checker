from io import BytesIO
from types import SimpleNamespace

import pytest

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
