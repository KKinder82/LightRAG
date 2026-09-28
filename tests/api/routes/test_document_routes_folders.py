"""Regression coverage for folder-aware document insertion and deletion."""

from copy import deepcopy
import importlib
from io import BytesIO
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

_original_argv = sys.argv[:]
try:
    sys.argv = sys.argv[:1]
    routes = importlib.import_module("lightrag.api.routers.document_routes")
finally:
    sys.argv = _original_argv
from lightrag.kg import shared_storage  # noqa: E402

pytestmark = pytest.mark.offline


class MemoryDocStatus:
    def __init__(self):
        self.docs = {}

    async def get_doc_by_file_basename(self, basename):
        for doc_id, doc in self.docs.items():
            if routes.normalize_file_path(doc["file_path"]) == basename:
                return doc_id, deepcopy(doc)
        return None

    async def get_by_id(self, doc_id):
        return deepcopy(self.docs.get(doc_id))

    async def upsert(self, docs):
        self.docs.update(deepcopy(docs))


@pytest.fixture
async def rig(tmp_path, monkeypatch):
    shared_storage.initialize_share_data()
    rag = SimpleNamespace(
        workspace=f"folder-routes-{uuid4().hex}",
        addon_params={},
        doc_status=MemoryDocStatus(),
    )
    await shared_storage.initialize_pipeline_status(workspace=rag.workspace)
    status = await shared_storage.get_namespace_data(
        "pipeline_status", workspace=rag.workspace
    )
    index = AsyncMock()
    monkeypatch.setattr(routes, "pipeline_index_texts_with_folder_id", index)
    router = routes.create_document_routes(rag, routes.DocumentManager(str(tmp_path)))
    endpoints = {route.name: route.endpoint for route in router.routes}
    return SimpleNamespace(rag=rag, status=status, index=index, endpoints=endpoints)


def seed(
    rig, doc_id="custom-existing-id", source="old.txt", folders=None, status="processed"
):
    rig.rag.doc_status.docs[doc_id] = {
        "file_path": source,
        "status": status,
        "track_id": "original-track",
        "metadata": {"folder_ids": folders or ["folder-a"]},
        "chunks_list": ["chunk-original"],
    }


@pytest.mark.parametrize(
    "endpoint", ["insert_text", "insert_texts"]
)
async def test_adding_existing_document_preserves_id_and_releases_slot(rig, endpoint):
    seed(rig)
    bg = BackgroundTasks()
    if endpoint == "upload_to_input_dir":
        response = await rig.endpoints[endpoint](
            bg, UploadFile(filename="old.txt", file=BytesIO(b"content")), "folder-b"
        )
    elif endpoint == "insert_text":
        response = await rig.endpoints[endpoint](
            routes.InsertTextRequest(
                text="content", file_source="old.txt", folder_id="folder-b"
            ),
            bg,
        )
    else:
        response = await rig.endpoints[endpoint](
            routes.InsertTextsRequest(
                texts=["content"], file_sources=["old.txt"], folder_id="folder-b"
            ),
            bg,
        )
    assert response.status == "success"
    assert rig.status["pending_enqueues"] == 0
    assert not bg.tasks
    assert list(rig.rag.doc_status.docs) == ["custom-existing-id"]
    doc = rig.rag.doc_status.docs["custom-existing-id"]
    assert doc["metadata"]["folder_ids"] == ["folder-a", "folder-b"]
    assert doc["chunks_list"] == ["chunk-original"]


@pytest.mark.parametrize("folder_id", [None, "folder-b"])
async def test_batch_only_enqueues_new_texts_with_matching_sources(rig, folder_id):
    seed(rig)
    bg = BackgroundTasks()
    await rig.endpoints["insert_texts"](
        routes.InsertTextsRequest(
            texts=["old content", "new content"],
            file_sources=["old.txt", "new.txt"],
            folder_id=folder_id,
        ),
        bg,
    )
    await bg()
    assert rig.index.await_args.args[1] == ["new content"]
    assert rig.index.await_args.kwargs["file_sources"] == ["new.txt"]
    assert rig.status["pending_enqueues"] == 0


async def test_batch_conflict_does_not_partially_add_folder(rig):
    seed(rig)
    seed(rig, "second-id", "conflict.txt", ["folder-b"])
    original = deepcopy(rig.rag.doc_status.docs)
    bg = BackgroundTasks()
    with pytest.raises(HTTPException) as exc:
        await rig.endpoints["insert_texts"](
            routes.InsertTextsRequest(
                texts=["one", "two"],
                file_sources=["old.txt", "conflict.txt"],
                folder_id="folder-b",
            ),
            bg,
        )
    assert exc.value.status_code == 409
    assert rig.rag.doc_status.docs == original
    assert not bg.tasks
    assert rig.status["pending_enqueues"] == 0


async def test_invalid_batch_chunking_does_not_add_folder(rig):
    seed(rig)
    original = deepcopy(rig.rag.doc_status.docs)
    rig.rag.addon_params = {
        "chunker": {"fixed_token": {"chunk_overlap_token_size": 100}}
    }
    with pytest.raises(HTTPException) as exc:
        await rig.endpoints["insert_texts"](
            routes.InsertTextsRequest(
                texts=["old", "new"],
                file_sources=["old.txt", "new.txt"],
                folder_id="folder-b",
                chunking={"params": {"chunk_token_size": 50}},
            ),
            BackgroundTasks(),
        )
    assert exc.value.status_code == 422
    assert rig.rag.doc_status.docs == original
    assert rig.status["pending_enqueues"] == 0


async def test_batch_failed_existing_text_returns_conflict(rig):
    seed(rig, status="failed")
    with pytest.raises(HTTPException) as exc:
        await rig.endpoints["insert_texts"](
            routes.InsertTextsRequest(texts=["old"], file_sources=["old.txt"]),
            BackgroundTasks(),
        )
    assert exc.value.status_code == 409
    assert rig.status["pending_enqueues"] == 0


async def test_folder_batch_delete_preserves_other_folder_references(rig):
    seed(rig, "shared", "shared.txt", ["folder-a", "folder-b"])
    seed(rig, "last", "last.txt", ["folder-a"])
    seed(rig, "unrelated", "unrelated.txt", ["folder-b"])
    bg = BackgroundTasks()
    response = await rig.endpoints["delete_document"](
        routes.DeleteDocRequest(
            doc_ids=["shared", "last", "unrelated", "missing"], folder_id="folder-a"
        ),
        bg,
    )
    assert response.status == "deletion_started"
    assert rig.rag.doc_status.docs["shared"]["metadata"]["folder_ids"] == ["folder-b"]
    assert rig.rag.doc_status.docs["unrelated"]["metadata"]["folder_ids"] == [
        "folder-b"
    ]
    assert len(bg.tasks) == 1
    assert bg.tasks[0].args[2] == ["last"]


async def test_folder_only_batch_removal_releases_busy_without_full_delete(rig):
    seed(rig, "one", "one.txt", ["folder-a", "folder-b"])
    seed(rig, "two", "two.txt", ["folder-a", "folder-b"])
    bg = BackgroundTasks()
    response = await rig.endpoints["delete_document"](
        routes.DeleteDocRequest(doc_ids=["one", "two"], folder_id="folder-a"), bg
    )
    assert response.status == "success"
    assert not bg.tasks
    assert not rig.status["busy"]
    assert not rig.status.get("destructive_busy", False)
    assert all(
        doc["metadata"]["folder_ids"] == ["folder-b"]
        for doc in rig.rag.doc_status.docs.values()
    )


@pytest.mark.parametrize("busy_field", ["busy", "scanning", "pending_enqueues"])
async def test_folder_removal_obeys_pipeline_exclusion(rig, busy_field):
    seed(rig, folders=["folder-a", "folder-b"])
    original = deepcopy(rig.rag.doc_status.docs)
    rig.status[busy_field] = 1
    rig.rag.deletion_queue.submit = AsyncMock(return_value="delete-test")
    response = await rig.endpoints["delete_document"](
        routes.DeleteDocRequest(doc_ids=["custom-existing-id"], folder_id="folder-a"),
        BackgroundTasks(),
    )
    assert response.status == "deletion_queued"
    rig.rag.deletion_queue.submit.assert_awaited_once()
    assert rig.rag.doc_status.docs == original


async def test_folder_removal_releases_reservation_on_storage_error(rig, monkeypatch):
    seed(rig, folders=["folder-a", "folder-b"])
    monkeypatch.setattr(
        rig.rag.doc_status,
        "upsert",
        AsyncMock(side_effect=RuntimeError("storage unavailable")),
    )
    with pytest.raises(HTTPException) as exc:
        await rig.endpoints["delete_document"](
            routes.DeleteDocRequest(
                doc_ids=["custom-existing-id"], folder_id="folder-a"
            ),
            BackgroundTasks(),
        )
    assert exc.value.status_code == 500
    assert not rig.status["busy"]
    assert not rig.status["destructive_busy"]


async def test_folder_workflow_over_http_persists_original_document_ids(rig, tmp_path):
    """Exercise HTTP validation, JSON storage and folder filtering together."""
    import json

    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from lightrag.kg.json_doc_status_impl import JsonDocStatusStorage

    storage = JsonDocStatusStorage(
        namespace="doc_status",
        workspace=rig.rag.workspace,
        global_config={"working_dir": str(tmp_path)},
        embedding_func=None,
    )
    await storage.initialize()
    rig.rag.doc_status = storage
    docs = {
        doc_id: {
            "file_path": source,
            "status": "processed",
            "track_id": "original-track",
            "content_summary": "existing content",
            "content_length": 16,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "chunks_list": [f"chunk-{doc_id}"],
            "metadata": {"folder_id": "folder-a"},
        }
        for doc_id, source in [("custom-one", "one.txt"), ("custom-two", "two.txt")]
    }
    await storage.upsert(docs)
    app = FastAPI()
    app.include_router(
        routes.create_document_routes(
            rig.rag,
            routes.DocumentManager(str(tmp_path)),
            api_key="test-key",
            folder_manager=SimpleNamespace(),
        )
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-API-Key": "test-key"},
    ) as client:
        inserted = await client.post(
            "/documents/texts",
            json={
                "texts": ["one", "two"],
                "file_sources": ["one.txt", "two.txt"],
                "folder_id": "folder-b",
            },
        )
        assert inserted.status_code == 200
        rig.index.assert_not_awaited()
        listed = await client.post(
            "/documents/paginated",
            json={
                "folder_id": "folder-b",
                "include_subfolders": False,
                "status_filters": ["processed"],
            },
        )
        assert listed.status_code == 200
        assert {doc["id"] for doc in listed.json()["documents"]} == set(docs)
        deleted = await client.request(
            "DELETE",
            "/documents/delete_document",
            json={
                "doc_ids": list(docs),
                "folder_id": "folder-a",
            },
        )
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "success"

    persisted = json.loads(
        (tmp_path / rig.rag.workspace / "kv_store_doc_status.json").read_text()
    )
    assert set(persisted) == set(docs)
    for doc_id, doc in persisted.items():
        assert doc["metadata"]["folder_ids"] == ["folder-b"]
        assert doc["chunks_list"] == [f"chunk-{doc_id}"]
    assert rig.status["pending_enqueues"] == 0
    assert not rig.status["busy"]
