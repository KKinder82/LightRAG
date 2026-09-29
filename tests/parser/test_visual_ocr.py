"""PDF and image OCR tests without network model dependencies."""

import base64
from io import BytesIO
import random
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PIL import Image
from pypdf import PdfWriter
import pytest

from lightrag.parser import visual_ocr as ocr

pytestmark = pytest.mark.offline


@pytest.fixture
def rag(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_OCR_ENGINE", "auto")
    monkeypatch.setenv("LIGHTRAG_PDF_OCR_MODE", "auto")
    return SimpleNamespace(
        vlm_process_enable=True,
        role_llm_funcs={"vlm": AsyncMock(return_value="中文 OCR 7391")},
        max_parallel_parse_native=2,
    )


def image_bytes(format="PNG"):
    stream = BytesIO()
    Image.new("RGB", (120, 60), "white").save(stream, format=format)
    return stream.getvalue()


def pdf_bytes(password=None):
    writer = PdfWriter()
    writer.add_blank_page(width=120, height=60)
    if password:
        writer.encrypt(password)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.mark.parametrize("suffix,format", [
    (".png", "PNG"), (".jpg", "JPEG"), (".jpeg", "JPEG"),
    (".bmp", "BMP"), (".tif", "TIFF"), (".tiff", "TIFF"), (".webp", "WEBP"),
])
async def test_image_ocr_uses_vlm_image_inputs(rag, suffix, format):
    result = await ocr.extract_visual_document(rag, image_bytes(format), suffix)
    assert result == "中文 OCR 7391"
    call = rag.role_llm_funcs["vlm"].call_args
    assert call.kwargs["stream"] is False
    assert call.kwargs["image_inputs"][0]["mime_type"] == "image/png"
    assert call.kwargs["image_inputs"][0]["base64"]


async def test_large_image_is_compressed_before_vlm_request(rag, monkeypatch):
    monkeypatch.setenv("LIGHTRAG_OCR_VLM_MAX_IMAGE_BYTES", "50000")
    image = Image.frombytes("RGB", (900, 900), random.Random(42).randbytes(900 * 900 * 3))
    stream = BytesIO()
    image.save(stream, format="PNG")

    await ocr.extract_visual_document(rag, stream.getvalue(), ".png")

    payload = rag.role_llm_funcs["vlm"].call_args.kwargs["image_inputs"][0]
    assert payload["mime_type"] == "image/jpeg"
    encoded = base64.b64decode(payload["base64"])
    assert len(encoded) <= 50000
    assert Image.open(BytesIO(encoded)).format == "JPEG"


async def test_mixed_pdf_only_ocr_scanned_pages_in_order(rag, monkeypatch):
    monkeypatch.setattr(ocr, "_pdf_pages", lambda *a: (["First page", "", "Last page"], b"pdf"))
    rendered = []

    def render(source, page, root):
        rendered.append(page)
        return image_bytes()

    monkeypatch.setattr(ocr, "_render_page", render)
    text = await ocr.extract_visual_document(rag, b"pdf", ".pdf")
    assert rendered == [2]
    assert text == "[Page 1]\nFirst page\n\n[Page 2]\n中文 OCR 7391\n\n[Page 3]\nLast page"


async def test_text_pdf_does_not_require_vlm_or_poppler(rag, monkeypatch):
    rag.vlm_process_enable = False
    monkeypatch.setattr(ocr, "_pdf_pages", lambda *a: (["Digital text"], b"pdf"))
    monkeypatch.setattr(ocr.shutil, "which", lambda _: None)
    assert "Digital text" in await ocr.extract_visual_document(rag, b"pdf", ".pdf")
    rag.role_llm_funcs["vlm"].assert_not_awaited()


async def test_force_ocr_for_pdf_with_text_layer(rag, monkeypatch):
    monkeypatch.setenv("LIGHTRAG_PDF_OCR_MODE", "always")
    monkeypatch.setattr(ocr, "_pdf_pages", lambda *a: (["Bad text layer"], b"pdf"))
    monkeypatch.setattr(ocr, "_render_page", lambda *a: image_bytes())
    assert "中文 OCR" in await ocr.extract_visual_document(rag, b"pdf", ".pdf")


async def test_pdf_page_failure_is_not_silently_dropped(rag, monkeypatch):
    monkeypatch.setattr(ocr, "_render_page", lambda *a: image_bytes())
    rag.role_llm_funcs["vlm"].side_effect = RuntimeError("model unavailable")
    with pytest.raises(ValueError, match="page 1.*model unavailable"):
        await ocr.extract_visual_document(rag, pdf_bytes(), ".pdf")


def test_encrypted_pdf_decrypted_without_password_process_arguments():
    data = pdf_bytes("test-password")
    with pytest.raises(ValueError, match="password"):
        ocr._pdf_pages(data, None)
    pages, decrypted = ocr._pdf_pages(data, "test-password")
    assert pages == [""]
    assert ocr._pdf_pages(decrypted, None)[0] == [""]


async def test_tiff_all_frames_recognized(rag):
    stream = BytesIO()
    Image.new("RGB", (40, 40)).save(
        stream, format="TIFF", save_all=True,
        append_images=[Image.new("RGB", (40, 40), "white")],
    )
    rag.role_llm_funcs["vlm"].side_effect = ["第一页", "第二页"]
    assert await ocr.extract_visual_document(rag, stream.getvalue(), ".tiff") == (
        "[Page 1]\n第一页\n\n[Page 2]\n第二页"
    )


async def test_explicit_vlm_requires_enabled_role(rag, monkeypatch):
    rag.vlm_process_enable = False
    monkeypatch.setenv("LIGHTRAG_OCR_ENGINE", "vlm")
    with pytest.raises(ValueError, match="VLM_PROCESS_ENABLE"):
        await ocr.extract_visual_document(rag, image_bytes(), ".png")


async def test_no_readable_text_is_failed(rag):
    rag.role_llm_funcs["vlm"].return_value = "[NO_TEXT]"
    with pytest.raises(ValueError, match="no readable text"):
        await ocr.extract_visual_document(rag, image_bytes(), ".png")


def test_pdf_page_limit(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_OCR_MAX_PAGES", "1")
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=100, height=100)
    data = BytesIO()
    writer.write(data)
    with pytest.raises(ValueError, match="MAX_PAGES"):
        ocr._pdf_pages(data.getvalue(), None)
