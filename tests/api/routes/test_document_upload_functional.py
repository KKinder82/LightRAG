"""Multipart upload checks with real parsing, pipeline and local storages."""

import importlib
from io import BytesIO
import sys
from uuid import uuid4

import numpy as np
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

_original_argv = sys.argv[:]
try:
    sys.argv = sys.argv[:1]
    routes = importlib.import_module("lightrag.api.routers.document_routes")
finally:
    sys.argv = _original_argv

from lightrag import LightRAG  # noqa: E402
from lightrag.kg.folder_storage import FolderManager  # noqa: E402
from lightrag.kg.shared_storage import get_namespace_data  # noqa: E402
from lightrag.utils import EmbeddingFunc, Tokenizer  # noqa: E402

pytestmark = pytest.mark.offline


class CharacterTokenizer:
    def encode(self, text):
        return list(map(ord, text))

    def decode(self, tokens):
        return "".join(map(chr, tokens))


async def fake_embedding(texts, **kwargs):
    return np.ones((len(texts), 8))


async def fake_llm(*args, **kwargs):
    return "<|COMPLETE|>"


@pytest.fixture
async def upload_app(tmp_path, monkeypatch):
    input_dir = tmp_path / "inputs"
    monkeypatch.setenv("INPUT_DIR", str(input_dir))
    monkeypatch.setenv("LIGHTRAG_PARSER", "*:legacy")
    rag = LightRAG(
        working_dir=str(tmp_path / "storage"),
        workspace=f"upload-{uuid4().hex}",
        tokenizer=Tokenizer("test", CharacterTokenizer()),
        llm_model_func=fake_llm,
        embedding_func=EmbeddingFunc(embedding_dim=8, func=fake_embedding),
        vlm_process_enable=False,
    )
    await rag.initialize_storages()
    folders_kv = rag.key_string_value_json_storage_cls(
        namespace="doc_folders",
        workspace=rag.workspace,
        embedding_func=None,
    )
    await folders_kv.initialize()
    folders = FolderManager(folders_kv, rag.workspace)
    # Match create_app: folder filtering attaches a live manager to the RAG.
    rag.folder_manager = folders
    folder = await folders.create_folder("Upload checks")
    app = FastAPI()
    app.include_router(
        routes.create_document_routes(
            rag,
            routes.DocumentManager(str(input_dir)),
            api_key="upload-test-key",
            folder_manager=folders,
        )
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "upload-test-key"},
        ) as client:
            yield client, rag, folder, input_dir
    finally:
        await rag.finalize_storages()
        await folders_kv.finalize()


@pytest.mark.parametrize(
    "filename",
    [
        "upload.txt",
        "上传测试.md",
        "data.csv",
        "data.json",
        "文档.docx",
        "原生.[native-F].docx",
        "report.pdf",
    ],
)
@pytest.mark.parametrize("use_folder", [False, True])
async def test_new_file_upload_is_processed_and_visible(
    upload_app, filename, use_folder
):
    client, rag, folder, input_dir = upload_app
    if filename.endswith(".docx"):
        from docx import Document

        document = Document()
        document.add_paragraph("Alice works at Example Labs. 这是一份文件上传测试。")
        stream = BytesIO()
        document.save(stream)
        content = stream.getvalue()
    elif filename.endswith(".pdf"):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {
                        NameObject("/F1"): DictionaryObject(
                            {
                                NameObject("/Type"): NameObject("/Font"),
                                NameObject("/Subtype"): NameObject("/Type1"),
                                NameObject("/BaseFont"): NameObject("/Helvetica"),
                            }
                        )
                    }
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (Alice works at Example Labs.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
        output = BytesIO()
        writer.write(output)
        content = output.getvalue()
    else:
        content = b"Alice works at Example Labs. This is an upload test."
    response = await client.post(
        "/documents/upload",
        files={"file": (filename, content)},
        data={"folder_id": folder.id} if use_folder else {},
    )
    assert response.status_code == 200, response.text
    track_id = response.json()["track_id"]
    docs = await rag.doc_status.get_docs_by_track_id(track_id)
    assert len(docs) == 1
    doc_id, doc = next(iter(docs.items()))
    assert doc.status.value == "processed", doc.error_msg
    assert doc.chunks_list
    assert await rag.full_docs.get_by_id(doc_id)
    assert all(await rag.text_chunks.get_by_ids(doc.chunks_list))
    if use_folder:
        assert folder.id in doc.metadata["folder_ids"]
    listed = await client.post(
        "/documents/paginated",
        json={
            "folder_id": folder.id if use_folder else None,
            "status_filters": ["processed"],
        },
    )
    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()["documents"]] == [doc_id]
    assert list((input_dir / "__parsed__").rglob("*"))
    status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
    assert status["pending_enqueues"] == 0
    assert not status["busy"]


async def test_missing_file_field_returns_validation_error(upload_app):
    client, _, _, _ = upload_app
    response = await client.post(
        "/documents/upload", files={"wrong_field": ("test.txt", b"test")}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


@pytest.mark.parametrize(
    "filename, content",
    [
        ("empty.txt", b""),
        ("broken.pdf", b"invalid pdf"),
        ("broken.docx", b"invalid docx"),
    ],
)
async def test_failed_upload_stays_visible_in_selected_folder(
    upload_app, filename, content
):
    client, rag, folder, _ = upload_app
    response = await client.post(
        "/documents/upload",
        files={"file": (filename, content)},
        data={"folder_id": folder.id},
    )
    assert response.status_code == 200
    docs = await rag.doc_status.get_docs_by_track_id(response.json()["track_id"])
    assert len(docs) == 1
    doc_id, doc = next(iter(docs.items()))
    assert doc.status.value == "failed"
    assert doc.error_msg
    listed = await client.post(
        "/documents/paginated",
        json={"folder_id": folder.id, "status_filters": ["failed"]},
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["documents"]] == [doc_id]


async def test_invalid_native_heading_does_not_break_later_uploads(upload_app):
    """A parser validation failure must leave shared storage and workers usable."""
    from docx import Document

    client, rag, folder, _ = upload_app
    document = Document()
    document.add_heading("H" * 201, level=1)
    document.add_paragraph("This document has an invalid heading.")
    stream = BytesIO()
    document.save(stream)
    response = await client.post(
        "/documents/upload",
        files={"file": ("invalid-heading.[native-F].docx", stream.getvalue())},
        data={"folder_id": folder.id},
    )
    assert response.status_code == 200, response.text
    docs = await rag.doc_status.get_docs_by_track_id(response.json()["track_id"])
    assert len(docs) == 1
    failed_doc = next(iter(docs.values()))
    assert failed_doc.status.value == "failed"
    assert "Heading too long" in failed_doc.error_msg
    assert folder.id in failed_doc.metadata["folder_ids"]

    status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
    assert not status["busy"]
    assert status["pending_enqueues"] == 0

    response = await client.post(
        "/documents/upload",
        files={"file": ("after-invalid.txt", b"Normal upload after DOCX validation failure.")},
    )
    assert response.status_code == 200, response.text
    docs = await rag.doc_status.get_docs_by_track_id(response.json()["track_id"])
    assert len(docs) == 1
    assert next(iter(docs.values())).status.value == "processed"
