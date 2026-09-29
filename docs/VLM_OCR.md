# PDF and image OCR

The upload dialog accepts PDF, PNG, JPG/JPEG, BMP, TIF/TIFF and WebP. The legacy
parser extracts PDF text page by page; pages without a text layer are rendered
with Poppler and passed to the VLM role for OCR. PDF pages with extractable text
are read directly without rendering or model calls. Multipage TIFF images are read in order. OCR text
enters the normal document chunking/indexing pipeline and retains folder metadata.

Enable a vision-capable model through the existing VLM role:

```dotenv
VLM_PROCESS_ENABLE=true
LIGHTRAG_OCR_ENGINE=vlm
# Set VLM_LLM_BINDING, VLM_LLM_BINDING_HOST, VLM_LLM_MODEL and
# VLM_LLM_BINDING_API_KEY if the vision model differs from the base LLM.
```

`LIGHTRAG_OCR_ENGINE` applies only to standalone images: `auto` uses VLM when
enabled, otherwise local Tesseract. Scanned PDF pages always require VLM.
Explicit `vlm` fails clearly if the VLM role is unavailable. Model errors do not
silently switch OCR engines or omit failed pages. A document with no readable text
is marked failed. The document status/track endpoint reports background failures;
a successful upload response alone does not establish successful indexing.

PDF extraction always reads available text and uses VLM OCR only for textless
pages, including mixed PDFs, in original page order. The former
`LIGHTRAG_PDF_OCR_MODE` setting is no longer used (`always` and `never` do not
override this behavior). Extracted PDF text contains `[Page N]` markers.
OCR recognizes text, not arbitrary picture descriptions.

Use the legacy parser for these formats, for example `*:native-teP,*:legacy-R`
(the existing default fallback), or `*.pdf:legacy-R,*.png:legacy-R,*:legacy-R`.
An explicit `[native]` hint still selects the DOCX-only native parser. Existing
MinerU/Docling routes remain available and use their own recognition services.

Install `poppler-utils` on the API host for scanned PDF rendering. Pillow is part
of the `api` extra. Local Tesseract additionally requires `tesseract-ocr`,
`tesseract-ocr-chi-sim` and `tesseract-ocr-eng`; VLM mode does not need Tesseract.
Docker images include Poppler and the local OCR dependencies.

Limits: `LIGHTRAG_OCR_MAX_PAGES=200` rejects larger PDFs/multipage images rather
than truncating them; `LIGHTRAG_OCR_IMAGE_MAX_EDGE=2560` bounds image resolution.
Image decoding rejects images larger than 40 megapixels. Rendering has a
120-second timeout per page; model calls use the VLM role timeout and concurrency
queue. PDF passwords use `PDF_DECRYPT_PASSWORD` and are never renderer arguments.
OCR errors remain possible; check important extracted text against the original.
