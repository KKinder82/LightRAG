"""Offline coverage of small-block retrieval and parent chunk lifecycle."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from lightrag.chunk_blocks import ChunkBlockVectorStorage, split_chunk_blocks


class MemoryVectors:
    cosine_better_than_threshold = 0.1

    def __init__(self):
        self.data = {}
        self.hits = []
        self.limits = []
        self.embedding_func = AsyncMock(return_value=np.array([[1.0, 0.0]]))

    async def upsert(self, data):
        self.data.update(data)

    async def get_by_id(self, vector_id):
        return self.data.get(vector_id)

    async def delete(self, ids):
        for vector_id in ids:
            self.data.pop(vector_id, None)

    async def query(self, query, top_k, query_embedding=None):
        self.limits.append(top_k)
        return self.hits[:top_k]


def make_storage(count=4):
    vectors = MemoryVectors()
    chunks = {}
    kv = AsyncMock()
    kv.get_by_ids.side_effect = lambda ids: [chunks.get(chunk_id) for chunk_id in ids]
    return ChunkBlockVectorStorage(vectors, kv, count), vectors, chunks


@pytest.mark.parametrize(
    "text",
    ["abcdefghi", "退款规则。申请流程。办理条件。", "a    b\n c", "短", "  ", ""],
)
@pytest.mark.parametrize("count", [1, 2, 4, 20])
def test_split_preserves_original_and_has_no_empty_blocks(text, count):
    blocks = split_chunk_blocks(text, count)
    assert "".join(blocks) == text
    assert len(blocks) <= count
    if text.strip():
        assert all(block.strip() for block in blocks)
    if count == 1:
        assert blocks == [text]


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_invalid_count_rejected(count):
    with pytest.raises(ValueError, match="positive integer"):
        make_storage(count)


@pytest.mark.asyncio
async def test_index_stores_blocks_and_does_not_mutate_parent():
    adapter, vectors, _ = make_storage()
    chunk = {"content": "abcdefghijklmno", "file_path": "a.txt", "full_doc_id": "doc"}
    await adapter.upsert({"chunk-a": chunk})
    assert len(vectors.data) == 4
    assert (
        "".join(item["content"] for item in vectors.data.values()) == chunk["content"]
    )
    assert chunk["content"] == "abcdefghijklmno"
    assert all(item["full_doc_id"] == "doc" for item in vectors.data.values())


@pytest.mark.asyncio
async def test_default_one_uses_original_id_and_content():
    adapter, vectors, _ = make_storage(1)
    chunk = {"content": "Full original chunk"}
    await adapter.upsert({"chunk-a": chunk})
    assert vectors.data == {"chunk-a": chunk}


@pytest.mark.asyncio
async def test_query_deduplicates_and_refills_top_k_full_parents():
    adapter, vectors, chunks = make_storage()
    chunks.update(
        {
            "chunk-a": {"content": "Full A", "file_path": "a.txt"},
            "chunk-b": {"content": "Full B", "file_path": "b.txt"},
        }
    )
    vectors.hits = [
        {"id": "chunk-a::block:1", "content": "part", "distance": 0.99},
        {"id": "chunk-a::block:2", "content": "part", "distance": 0.98},
        {"id": "chunk-a", "content": "part", "distance": 0.97},
        {"id": "chunk-b::block:1", "content": "part", "distance": 0.96},
    ]
    results = await adapter.query("query", 2)
    assert [item["id"] for item in results] == ["chunk-a", "chunk-b"]
    assert [item["content"] for item in results] == ["Full A", "Full B"]
    assert results[0]["distance"] == 0.99
    assert results[0]["file_path"] == "a.txt"
    assert vectors.limits == [2, 4]
    vectors.embedding_func.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_exhaustion_and_missing_parent():
    adapter, vectors, chunks = make_storage()
    chunks["chunk-a"] = {"content": "Full A"}
    vectors.hits = [
        {"id": "missing::block:1", "content": "fragment"},
        {"id": "chunk-a", "content": "part"},
    ]
    assert [item["content"] for item in await adapter.query("q", 3)] == ["Full A"]


@pytest.mark.asyncio
async def test_old_blocks_query_and_delete_after_count_change():
    adapter, vectors, chunks = make_storage(4)
    chunks["chunk-a"] = {"content": "abcdefghijklmno"}
    await adapter.upsert(chunks)
    adapter.block_count = 1
    vectors.hits = [{"id": "chunk-a::block:3", "content": "part"}]
    assert (await adapter.query("q", 1))[0]["content"] == chunks["chunk-a"]["content"]
    await adapter.delete({"chunk-a"})
    assert not vectors.data


@pytest.mark.asyncio
async def test_reindex_cleans_stale_blocks_and_shorter_chunks():
    adapter, vectors, _ = make_storage(4)
    await adapter.upsert({"chunk-a": {"content": "abcdefghijklmno"}})
    adapter.block_count = 2
    await adapter.upsert({"chunk-a": {"content": "abcdefghijklmno"}})
    assert set(vectors.data) == {"chunk-a", "chunk-a::block:1"}
    await adapter.upsert({"chunk-a": {"content": "短"}})
    assert vectors.data == {"chunk-a": {"content": "短"}}


@pytest.mark.asyncio
async def test_provided_query_embedding_and_legacy_vectors():
    adapter, vectors, _ = make_storage(1)
    vectors.hits = [{"id": "legacy", "content": "Full legacy chunk"}]
    assert (await adapter.query("q", 2, query_embedding=[1, 0]))[0][
        "content"
    ] == "Full legacy chunk"
    vectors.embedding_func.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_nano_embeds_blocks_and_restores_full_context(tmp_path):
    from lightrag.kg.nano_vector_db_impl import NanoVectorDBStorage
    from lightrag.kg.shared_storage import finalize_share_data, initialize_share_data
    from lightrag.utils import EmbeddingFunc

    initialize_share_data()
    embedded = []

    async def embed(texts, **kwargs):
        embedded.extend(texts)
        return np.array([[1.0, 0.0] for _ in texts], dtype=np.float32)

    storage = NanoVectorDBStorage(
        namespace="chunks",
        workspace="blocks-test",
        global_config={
            "working_dir": str(tmp_path),
            "embedding_batch_num": 16,
            "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.1},
        },
        embedding_func=EmbeddingFunc(embedding_dim=2, max_token_size=512, func=embed),
        meta_fields={"content", "file_path", "full_doc_id"},
    )
    kv = AsyncMock()
    full = {
        "content": "申请条件。办理流程。退款规则。费用说明。",
        "file_path": "rules.txt",
    }
    kv.get_by_ids.side_effect = lambda ids: [
        full if chunk_id == "chunk-a" else None for chunk_id in ids
    ]
    adapter = ChunkBlockVectorStorage(storage, kv, 4)
    try:
        await adapter.initialize()
        await adapter.upsert({"chunk-a": full})
        await adapter.index_done_callback()
        assert len(embedded) == 4
        assert "".join(embedded) == full["content"]
        results = await adapter.query("退款", 2)
        assert len(results) == 1
        assert results[0]["id"] == "chunk-a"
        assert results[0]["content"] == full["content"]
        # Restart/reconfigure using persisted vectors, then delete all blocks.
        await adapter.finalize()
        replacement = NanoVectorDBStorage(
            namespace="chunks",
            workspace="blocks-test",
            global_config=storage.global_config,
            embedding_func=storage.embedding_func,
            meta_fields=storage.meta_fields,
        )
        adapter = ChunkBlockVectorStorage(replacement, kv, 1)
        await adapter.initialize()
        assert (await adapter.query("退款", 1))[0]["content"] == full["content"]
        await adapter.delete(["chunk-a"])
        await adapter.index_done_callback()
        assert await adapter.query("退款", 2) == []
    finally:
        await adapter.finalize()
        finalize_share_data()


@pytest.mark.asyncio
async def test_lightrag_env_block_count_and_naive_context(tmp_path, monkeypatch):
    from lightrag import LightRAG, QueryParam
    from lightrag.kg.shared_storage import finalize_share_data
    from lightrag.utils import EmbeddingFunc, Tokenizer

    class CharacterTokenizer:
        def encode(self, text):
            return [ord(char) for char in text]

        def decode(self, tokens):
            return "".join(chr(token) for token in tokens)

    indexed = []

    async def embed(texts, **kwargs):
        if kwargs.get("context") == "document":
            indexed.extend(texts)
        return np.array(
            [[1.0, 0.0] if "退款" in text else [0.0, 1.0] for text in texts]
        )

    async def llm(prompt, **kwargs):
        return "unused"

    monkeypatch.setenv("CHUNK_BLOCKS_COUNT", "4")
    monkeypatch.setenv("block_count", "2")
    monkeypatch.setenv("BLOCK_COUNT", "2")
    full_text = "申请条件：必须实名。办理流程：提交申请。退款规则：七天内可退款。费用说明：免费。"
    rag = LightRAG(
        working_dir=str(tmp_path),
        workspace="naive-block-test",
        llm_model_func=llm,
        embedding_func=EmbeddingFunc(
            embedding_dim=2, max_token_size=512, func=embed, supports_asymmetric=True
        ),
        tokenizer=Tokenizer("characters", CharacterTokenizer()),
    )
    try:
        assert rag.block_count == 4
        await rag.initialize_storages()
        await rag.ainsert_custom_kg(
            {
                "chunks": [
                    {
                        "content": full_text,
                        "source_id": "source-1",
                        "file_path": "rules.txt",
                    }
                ],
                "entities": [],
                "relationships": [],
            }
        )
        assert len(indexed) == 4
        assert "".join(indexed) == full_text
        result = await rag.aquery(
            "退款",
            QueryParam(
                mode="naive", only_need_context=True, enable_rerank=False, chunk_top_k=1
            ),
        )
        assert full_text in result
        assert "rules.txt" in result
    finally:
        await rag.finalize_storages()
        finalize_share_data()
