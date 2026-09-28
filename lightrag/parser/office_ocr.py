"""Bounded, local extraction for legacy Office files and raster images."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

LEGACY_OFFICE = {".doc": "docx", ".ppt": "pptx", ".xls": "xlsx"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def extract_legacy_or_image(data: bytes, suffix: str, extractors: dict) -> str:
    """Use isolated conversion profiles; never execute shell command strings."""
    with tempfile.TemporaryDirectory(prefix="lightrag-extract-") as directory:
        root = Path(directory)
        source = root / f"source{suffix}"
        source.write_bytes(data)
        if suffix in LEGACY_OFFICE:
            binary = shutil.which("libreoffice") or shutil.which("soffice")
            if not binary:
                raise RuntimeError("Legacy Office extraction requires LibreOffice")
            target = LEGACY_OFFICE[suffix]
            output_dir = root / "converted"
            output_dir.mkdir()
            subprocess.run(
                [
                    binary,
                    f"-env:UserInstallation={(root / 'profile').as_uri()}",
                    "--headless",
                    "--convert-to",
                    target,
                    "--outdir",
                    str(output_dir),
                    str(source),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
            converted = output_dir / f"source.{target}"
            if not converted.is_file():
                raise ValueError(
                    "Office conversion did not produce a readable document"
                )
            return extractors[target](converted.read_bytes())
        binary = shutil.which("tesseract")
        if not binary:
            raise RuntimeError(
                "Image extraction requires Tesseract OCR and language data"
            )
        result = subprocess.run(
            [
                binary,
                str(source),
                "stdout",
                "-l",
                os.getenv("LIGHTRAG_OCR_LANG", "chi_sim+eng"),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return result.stdout.decode("utf-8").strip()
