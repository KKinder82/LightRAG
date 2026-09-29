"""Offline API regressions using real file storages and deterministic models."""

# ruff: noqa: F811
import asyncio

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest

from tests.api.routes.test_document_upload_functional import upload_app, routes  # noqa: F401
from lightrag.api.projects import ProjectDatasets, install_project_routes
from lightrag.kg.shared_storage import get_namespace_data

pytestmark = pytest.mark.offline


async def test_repeat_upload_replaces_previous_content_in_same_folder(upload_app):
    client, rag, folder, _ = upload_app
    for content in (b"repeated content", b"repeated content", b"changed content"):
        response = await client.post(
            "/documents/upload",
            files={"file": ("same.txt", content)},
            data={"folder_id": folder.id},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "success"
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 1
    doc_id, doc = next(iter(docs.items()))
    assert doc.metadata["upload_name"] == "same.txt"
    assert "changed content" in (await rag.full_docs.get_by_id(doc_id))["content"]
    chunks = await rag.text_chunks.get_by_ids(doc.chunks_list)
    assert all("changed content" in item["content"] for item in chunks)
    assert all("repeated content" not in item["content"] for item in chunks)


async def test_fast_index_skips_extraction_and_releases_slot_on_completion(
    upload_app, monkeypatch
):
    client, rag, _, _ = upload_app
    calls = []
    original = rag.apipeline_process_enqueue_documents

    async def checked_process(*args, **kwargs):
        status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
        assert status["pending_enqueues"] == 0
        return await original(*args, **kwargs)

    async def unexpected_llm(*args, **kwargs):
        calls.append(1)
        raise AssertionError("Fast indexing must not call entity extraction")

    monkeypatch.setattr(rag, "apipeline_process_enqueue_documents", checked_process)
    monkeypatch.setattr(rag, "llm_model_func", unexpected_llm)
    for state in rag._role_llm_states.values():
        state.wrapped = unexpected_llm
    response = await client.post(
        "/documents/upload",
        files={"file": ("fast.txt", b"fast indexed content")},
        data={"fast_index": "true"},
    )
    assert response.status_code == 200
    assert not calls
    status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
    assert status["pending_enqueues"] == 0
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 1


async def test_delete_while_busy_is_durable_and_eventually_runs(upload_app):
    client, rag, _, _ = upload_app
    await client.post("/documents/upload", files={"file": ("delete.txt", b"delete me")})
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    doc_id = next(iter(docs))
    status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
    status["busy"] = True
    try:
        response = await client.request(
            "DELETE", "/documents/delete_document", json={"doc_ids": [doc_id]}
        )
        assert response.json()["status"] == "deletion_queued", response.text
        await rag.deletion_queue.close()
        # Simulate worker restart with the durable job still present.
        rag.deletion_queue.initialized = False
        status["busy"] = False
        await rag.deletion_queue.start()
        for _ in range(60):
            jobs = await rag.deletion_queue.list_jobs()
            if all(job["status"] == "completed" for job in jobs.values()):
                break
            await asyncio.sleep(0.1)
        assert await rag.doc_status.get_by_id(doc_id) is None
        assert all(job["status"] == "completed" for job in jobs.values())
    finally:
        status["busy"] = False
        await rag.deletion_queue.close()


async def test_project_upload_graph_and_query_isolation(upload_app, tmp_path):
    _, base, _, _ = upload_app
    datasets = ProjectDatasets(
        base, str(tmp_path / "project-inputs"), "upload-test-key", 10
    )
    await datasets.start()
    app = FastAPI()
    install_project_routes(app, datasets, "upload-test-key")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "upload-test-key"},
        ) as client:
            a = (await client.post("/projects", json={"name": "A"})).json()
            b = (await client.post("/projects", json={"name": "B"})).json()
            assert a["id"] != b["id"]
            for project, content in (
                (a, "alpha project secret"),
                (b, "beta project secret"),
            ):
                response = await client.post(
                    "/documents/upload",
                    files={"file": ("same.txt", content)},
                    data={"fast_index": "true"},
                    headers={"X-LightRAG-Project": project["id"]},
                )
                assert response.status_code == 200, response.text
            rag_a = datasets.instances[a["id"]][1]
            rag_b = datasets.instances[b["id"]][1]
            for rag, expected, other in (
                (rag_a, "alpha", "beta"),
                (rag_b, "beta", "alpha"),
            ):
                docs = await rag.doc_status.get_docs_by_status(
                    routes.DocStatus.PROCESSED
                )
                assert len(docs) == 1
                record = await rag.full_docs.get_by_id(next(iter(docs)))
                assert expected in record["content"] and other not in record["content"]
            for project, expected, other in (
                (a, "alpha", "beta"),
                (b, "beta", "alpha"),
            ):
                response = await client.post(
                    "/query",
                    json={
                        "query": "project secret",
                        "mode": "naive",
                        "only_need_context": True,
                    },
                    headers={"X-LightRAG-Project": project["id"]},
                )
                assert response.status_code == 200, response.text
                assert expected in response.text and other not in response.text
            assert (
                await base.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
                == {}
            )
            await rag_a.chunk_entity_relation_graph.upsert_node(
                "ONLY_A", {"entity_type": "test", "description": "A"}
            )
            for project, exists in ((a, True), (b, False)):
                response = await client.get(
                    "/graph/entity/exists",
                    params={"name": "ONLY_A"},
                    headers={"X-LightRAG-Project": project["id"]},
                )
                assert response.status_code == 200, response.text
                assert response.json()["exists"] is exists
            response = await client.get(
                "/documents", headers={"X-LightRAG-Project": "unknown"}
            )
            assert response.status_code == 404
            assert len((await client.get("/projects")).json()) == 2
    finally:
        await datasets.close()


async def test_concurrent_same_filename_uploads_leave_one_version(upload_app):
    client, rag, _, _ = upload_app
    responses = await asyncio.gather(
        *[
            client.post(
                "/documents/upload",
                files={"file": ("race.txt", f"version {i}")},
                data={"fast_index": "true"},
            )
            for i in range(3)
        ]
    )
    assert all(response.status_code == 200 for response in responses)
    # A second enqueue may nudge the first processing loop; all background tasks
    # have completed when ASGITransport returns the responses.
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 1
    assert next(iter(docs.values())).metadata["upload_name"] == "race.txt"


async def test_deleting_one_folder_copy_keeps_other_folder(upload_app):
    client, rag, folder, _ = upload_app
    other_folder = await rag.folder_manager.create_folder("Other upload folder")
    for target in (folder.id, other_folder.id):
        await client.post(
            "/documents/upload",
            files={"file": ("version.txt", b"shared text content")},
            data={"fast_index": "true", "folder_id": target},
        )
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    first, second = list(docs)
    assert set(docs[first].chunks_list).isdisjoint(docs[second].chunks_list)
    response = await client.request(
        "DELETE", "/documents/delete_document", json={"doc_ids": [first]}
    )
    assert response.json()["status"] == "deletion_started"
    assert await rag.doc_status.get_by_id(first) is None
    assert await rag.doc_status.get_by_id(second) is not None
    assert all(await rag.text_chunks.get_by_ids(docs[second].chunks_list))


async def test_replace_in_one_folder_preserves_same_name_in_other(upload_app):
    client, rag, folder, _ = upload_app
    other = await rag.folder_manager.create_folder("Other folder")
    for target, body in (
        (folder.id, b"first folder old"),
        (other.id, b"second folder stays"),
        (folder.id, b"first folder new"),
    ):
        response = await client.post(
            "/documents/upload",
            files={"file": ("shared.txt", body)},
            data={"folder_id": target, "fast_index": "true"},
        )
        assert response.status_code == 200, response.text

    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 2
    by_folder = {
        doc.metadata["folder_id"]: await rag.full_docs.get_by_id(doc_id)
        for doc_id, doc in docs.items()
    }
    assert "first folder new" in by_folder[folder.id]["content"]
    assert "second folder stays" in by_folder[other.id]["content"]
    assert all(doc.metadata["upload_name"] == "shared.txt" for doc in docs.values())


async def test_replacing_legacy_shared_document_detaches_only_target(upload_app):
    client, rag, folder, _ = upload_app
    other = await rag.folder_manager.create_folder("Legacy shared folder")
    response = await client.post(
        "/documents/upload",
        files={"file": ("legacy-shared.txt", b"shared old body")},
        data={"folder_id": folder.id, "fast_index": "true"},
    )
    assert response.status_code == 200
    old_docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    old_id = next(iter(old_docs))
    old_record = await rag.doc_status.get_by_id(old_id)
    old_record["metadata"]["folder_ids"] = [folder.id, other.id]
    await rag.doc_status.upsert({old_id: old_record})
    await rag.doc_status.index_done_callback()

    response = await client.post(
        "/documents/upload",
        files={"file": ("legacy-shared.txt", b"replacement body")},
        data={"folder_id": folder.id, "fast_index": "true"},
    )
    assert response.status_code == 200
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 2
    assert docs[old_id].metadata["folder_ids"] == [other.id]
    assert "shared old body" in (await rag.full_docs.get_by_id(old_id))["content"]
    replacement = next(doc_id for doc_id in docs if doc_id != old_id)
    assert docs[replacement].metadata["folder_ids"] == [folder.id]
    assert "replacement body" in (await rag.full_docs.get_by_id(replacement))["content"]


async def test_rejected_replacement_keeps_previous_document(upload_app, monkeypatch):
    from types import SimpleNamespace

    client, rag, folder, _ = upload_app
    first = await client.post(
        "/documents/upload",
        files={"file": ("keep.txt", b"keep original content")},
        data={"folder_id": folder.id, "fast_index": "true"},
    )
    assert first.status_code == 200
    monkeypatch.setattr(routes, "global_args", SimpleNamespace(max_upload_size=5))
    rejected = await client.post(
        "/documents/upload",
        files={"file": ("keep.txt", b"oversized replacement")},
        data={"folder_id": folder.id},
    )
    assert rejected.status_code == 413
    docs = await rag.doc_status.get_docs_by_status(routes.DocStatus.PROCESSED)
    assert len(docs) == 1
    assert "keep original content" in (
        await rag.full_docs.get_by_id(next(iter(docs)))
    )["content"]


async def test_project_dispatch_respects_proxy_root_path():
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from lightrag.api.projects import ProjectDispatch

    target = FastAPI()

    @target.get("/documents")
    async def selected_documents():
        return {"dataset": "selected"}

    base = FastAPI()

    @base.get("/documents")
    async def default_documents():
        return {"dataset": "default"}

    datasets = SimpleNamespace(get=AsyncMock(return_value=target))
    app = ProjectDispatch(base, datasets)
    async with AsyncClient(
        transport=ASGITransport(app=app, root_path="/knowledge"), base_url="http://test"
    ) as client:
        response = await client.get(
            "/knowledge/documents", headers={"X-LightRAG-Project": "project-test"}
        )
        assert response.json() == {"dataset": "selected"}
        datasets.get.assert_awaited_once_with("project-test")
