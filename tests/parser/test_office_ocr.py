"""Local extraction contracts; converters are mocked for portable unit tests."""

from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from lightrag.parser.office_ocr import extract_legacy_or_image

pytestmark = pytest.mark.offline


@pytest.mark.parametrize(
    "suffix,target", [(".doc", "docx"), (".ppt", "pptx"), (".xls", "xlsx")]
)
def test_office_conversion_uses_private_profile_and_bounded_process(
    monkeypatch, suffix, target
):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/libreoffice")

    def convert(args, **kwargs):
        assert kwargs["timeout"] == 120
        assert kwargs["check"] is True
        assert any(arg.startswith("-env:UserInstallation=file:") for arg in args)
        out = Path(args[args.index("--outdir") + 1])
        (out / f"source.{target}").write_bytes(b"converted content")

    monkeypatch.setattr("subprocess.run", convert)
    assert (
        extract_legacy_or_image(b"legacy", suffix, {target: bytes.decode})
        == "converted content"
    )


def test_ocr_language_and_result(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setenv("LIGHTRAG_OCR_LANG", "chi_sim+eng")

    def ocr(args, **kwargs):
        assert args[-1] == "chi_sim+eng"
        assert kwargs["timeout"] == 120
        return SimpleNamespace(stdout="图片正文\n".encode())

    monkeypatch.setattr("subprocess.run", ocr)
    assert extract_legacy_or_image(b"image", ".png", {}) == "图片正文"


@pytest.mark.parametrize("suffix", [".doc", ".png"])
def test_missing_converter_is_actionable(monkeypatch, suffix):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="requires"):
        extract_legacy_or_image(b"file", suffix, {})


def test_conversion_timeout_propagates(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/libreoffice")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 120)

    monkeypatch.setattr("subprocess.run", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        extract_legacy_or_image(b"file", ".doc", {})
