"""Invalid DOCX content must fail its document without terminating the server."""

import pytest

from lightrag.parser.docx import parse_document as parser

pytestmark = pytest.mark.offline


def test_heading_limit_raises_catchable_error():
    parser.validate_heading_length("H" * parser.MAX_HEADING_LENGTH, "heading-1")
    with pytest.raises(ValueError, match="Heading too long") as exc:
        parser.validate_heading_length(
            "H" * (parser.MAX_HEADING_LENGTH + 1), "heading-1"
        )
    assert "heading-1" in str(exc.value)
    assert "Re-upload" in str(exc.value)


def test_table_limit_raises_catchable_error(monkeypatch):
    monkeypatch.setattr(
        parser, "estimate_tokens", lambda _: parser.MAX_BLOCK_CONTENT_TOKENS + 1
    )
    with pytest.raises(ValueError, match="Table too large") as exc:
        parser.validate_table_tokens("{}", "Large table section")
    assert "Large table section" in str(exc.value)


def test_unsplittable_block_raises_catchable_error(monkeypatch):
    monkeypatch.setattr(
        parser, "estimate_tokens", lambda _: parser.MAX_BLOCK_CONTENT_TOKENS + 1
    )
    paragraphs = [
        {"text": "X" * (parser.MAX_ANCHOR_CANDIDATE_LENGTH + 1), "para_id": "p1"}
    ]
    with pytest.raises(ValueError, match="Cannot split long block"):
        parser.split_long_block("Long section", paragraphs, [], 1)
