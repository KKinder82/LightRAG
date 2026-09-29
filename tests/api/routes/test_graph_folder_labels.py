"""Folder-filtered graphs must display entity names rather than entity types."""

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

_original_argv = sys.argv[:]
try:
    sys.argv = [sys.argv[0]]
    _graph_routes = importlib.import_module("lightrag.api.routers.graph_routes")
finally:
    sys.argv = _original_argv

pytestmark = pytest.mark.offline


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "type_properties",
    [{"entity_type": "人物"}, {"entity_type": ["人物", "专家"]}, {}],
)
async def test_folder_graph_labels_use_entity_names(type_properties):
    nodes = [
        {"id": "张三", "source_id": "chunk-in", **type_properties},
        {"id": "李四", "source_id": "chunk-in", **type_properties},
        {"id": "王五", "source_id": "chunk-out", **type_properties},
    ]
    rag = SimpleNamespace(
        doc_status=SimpleNamespace(
            get_doc_ids_by_folder_ids=AsyncMock(return_value=["doc-in"])
        ),
        text_chunks=SimpleNamespace(
            get_by_ids=AsyncMock(
                return_value=[{"full_doc_id": "doc-in"}, {"full_doc_id": "doc-out"}]
            )
        ),
        chunk_entity_relation_graph=SimpleNamespace(
            get_all_nodes=AsyncMock(return_value=nodes),
            get_all_edges=AsyncMock(return_value=[]),
        ),
    )

    graph = await _graph_routes._build_folder_knowledge_graph(rag, ["folder-1"])

    assert [(node.id, node.labels) for node in graph.nodes] == [
        ("张三", ["张三"]),
        ("李四", ["李四"]),
    ]
    for node in graph.nodes:
        assert node.properties == {"source_id": "chunk-in", **type_properties}
    rag.doc_status.get_doc_ids_by_folder_ids.assert_awaited_once_with(["folder-1"])
