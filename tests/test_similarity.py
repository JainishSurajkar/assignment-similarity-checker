import pytest

from similarity import compare_paragraphs, split_paragraph


def test_split_paragraph_normalizes_line_endings_and_whitespace():
    text = "First  paragraph.\r\n\r\nSecond\tparagraph.\n\n\nThird."
    assert split_paragraph(text) == [
        "First paragraph.",
        "Second paragraph.",
        "Third.",
    ]


def test_compare_paragraphs_returns_ranked_scores():
    results = compare_paragraphs(
        "shared words here\n\nunrelated content",
        "shared words here\n\nanother sentence",
    )
    assert results[0]["similarity"] == pytest.approx(1.0)
    assert results[0]["paragraph_a"] == 1
    assert results[0]["paragraph_b"] == 1


def test_compare_paragraphs_reports_empty_vocabulary():
    with pytest.raises(ValueError, match="readable words"):
        compare_paragraphs("!!!", "???")
