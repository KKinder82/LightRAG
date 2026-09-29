"""Folder scopes across all public query endpoints."""

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lightrag.base import QueryParam
from lightrag.lightrag import LightRAG
from lightrag.operate import (
    _filter_chunks_by_doc_ids,
    _filter_entities_relations_by_doc_ids,
)

_argv = sys.argv[:]
try:
    sys.argv = [sys.argv[0]]
    _routes = importlib.import_module("lightrag.api.routers.query_routes")
finally:
    sys.argv = _argv
QueryRequest = _routes.QueryRequest
create_query_routes = _routes.create_query_routes

pytestmark = pytest.mark.offline


@pytest.mark.parametrize("endpoint", ["/query", "/query/stream", "/query/data"])
@pytest.mark.parametrize("source", ["body", "url"])
@pytest.mark.parametrize("folder", [None, "", "   ", "parent"])
@pytest.mark.parametrize("recursive", [True, False])
def test_folder_parameters_over_http(endpoint, source, folder, recursive):
    result = {
        "status": "success",
        "message": "ok",
        "data": {},
        "metadata": {},
        "llm_response": {"content": "answer", "is_streaming": False},
    }
    rag = SimpleNamespace(
        aquery_llm=AsyncMock(return_value=result),
        aquery_data=AsyncMock(return_value=result),
    )
    app = FastAPI()
    app.include_router(create_query_routes(rag, api_key="test-key"))
    body = {"query": "test query"}
    scope = {"include_subfolders": recursive}
    if folder is not None:
        scope["folder_id"] = folder
    params = {}
    if source == "body":
        body.update(scope)
    else:
        params = scope
        # Explicit URL fields take priority over existing JSON fields.
        body.update({"include_subfolders": not recursive})
        if folder is not None:
            body["folder_id"] = "body-folder"
    with TestClient(app) as client:
        response = client.post(
            endpoint, json=body, params=params, headers={"X-API-Key": "test-key"}
        )
    assert response.status_code == 200, response.text
    call = rag.aquery_data if endpoint == "/query/data" else rag.aquery_llm
    param = call.call_args.kwargs["param"]
    assert param.folder_ids == (["parent"] if folder == "parent" else None)
    assert param.include_subfolders is recursive


def test_folder_defaults_and_openapi():
    param = QueryRequest(query="test").to_query_params(False)
    assert param.folder_ids is None
    assert param.include_subfolders is True
    app = FastAPI()
    app.include_router(create_query_routes(SimpleNamespace()))
    for path in ["/query", "/query/stream", "/query/data"]:
        names = {p["name"] for p in app.openapi()["paths"][path]["post"]["parameters"]}
        assert {"folder_id", "include_subfolders"} <= names


@pytest.mark.asyncio
@pytest.mark.parametrize("recursive", [True, False])
async def test_resolve_folder_descendants(recursive):
    rag = SimpleNamespace(
        folder_manager=SimpleNamespace(
            get_descendant_ids=AsyncMock(return_value=["child"])
        ),
        doc_status=SimpleNamespace(
            get_doc_ids_by_folder_ids=AsyncMock(return_value=["doc"])
        ),
    )
    param = QueryParam(folder_ids=["parent"], include_subfolders=recursive)
    await LightRAG._resolve_folder_filter(rag, param)
    selected = rag.doc_status.get_doc_ids_by_folder_ids.call_args.args[0]
    assert set(selected) == ({"parent", "child"} if recursive else {"parent"})
    assert param.filter_doc_ids == {"doc"}


@pytest.mark.asyncio
async def test_empty_folder_and_unresolvable_sources_never_return_all_results():
    db = SimpleNamespace(
        get_by_ids=AsyncMock(return_value=[{"full_doc_id": "outside"}])
    )
    chunks = [{"chunk_id": "c1"}]
    entities = [{"source_id": "c1"}]
    for scope in [set(), {"inside"}]:
        assert await _filter_chunks_by_doc_ids(chunks, scope, db) == []
        assert await _filter_entities_relations_by_doc_ids(
            entities, entities, scope, db, "<SEP>"
        ) == ([], [])
    db.get_by_ids.side_effect = RuntimeError("unavailable")
    with pytest.raises(RuntimeError):
        await _filter_chunks_by_doc_ids(chunks, {"inside"}, db)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["naive", "local", "global", "hybrid", "mix"])
async def test_data_query_preserves_resolved_scope(monkeypatch, mode):
    import importlib

    module = importlib.import_module("lightrag.lightrag")
    query = AsyncMock(return_value=None)
    monkeypatch.setattr(module, "kg_query", query)
    monkeypatch.setattr(module, "naive_query", query)
    rag = SimpleNamespace(
        _resolve_folder_filter=AsyncMock(),
        _build_global_config=lambda: {},
        _query_done=AsyncMock(),
        chunk_entity_relation_graph=None,
        entities_vdb=None,
        relationships_vdb=None,
        text_chunks=None,
        llm_response_cache=None,
        chunks_vdb=None,
    )
    param = QueryParam(
        mode=mode,
        folder_ids=["parent"],
        include_subfolders=False,
        filter_doc_ids={"doc"},
    )
    await LightRAG.aquery_data(rag, "test query", param)
    actual = query.call_args.args[2 if mode == "naive" else 5]
    assert actual.filter_doc_ids == {"doc"}
    assert actual.folder_ids == ["parent"]
    assert actual.include_subfolders is False
