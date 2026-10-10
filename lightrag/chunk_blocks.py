"""Small-block vector indexing with full parent-chunk retrieval.

The first block keeps the chunk ID; additional blocks use reversible IDs.
This works with existing vector schemas without adding backend-specific fields.
"""

import asyncio
import re
from itertools import pairwise
from typing import Any

from lightrag.base import BaseKVStorage, BaseVectorStorage

_BLOCK_SUFFIX = "::block:"


def split_chunk_blocks(content: str, block_count: int) -> list[str]:
    """Split contiguous original text, preferring nearby sentence boundaries."""
    if block_count == 1 or not content.strip():
        return [content]
    # Never create whitespace-only vectors, even for very short chunks.
    positions = [match.start() for match in re.finditer(r"\S", content)]
    count = min(block_count, len(positions))
    boundaries = [0]
    sentence_ends = [
        match.end() for match in re.finditer(r"[。！？!?；;\n]|\.(?=\s)", content)
    ]
    for i in range(1, count):
        target = len(content) * i / count
        minimum = positions[i - 1] + 1
        maximum = positions[len(positions) - (count - i)]
        minimum = max(minimum, boundaries[-1] + 1)
        candidates = [
            end
            for end in sentence_ends
            if minimum <= end <= maximum
            and abs(end - target) <= len(content) / count / 4
            and content[boundaries[-1] : end].strip()
        ]
        boundary = (
            min(candidates, key=lambda end: abs(end - target))
            if candidates
            else max(minimum, min(maximum, round(target)))
        )
        # Leave non-whitespace text in every remaining block.
        if not content[boundaries[-1] : boundary].strip():
            boundary = next(pos + 1 for pos in positions if pos >= boundaries[-1])
        boundaries.append(boundary)
    boundaries.append(len(content))
    return [content[start:end] for start, end in pairwise(boundaries)]


def _block_id(chunk_id: str, index: int) -> str:
    return chunk_id if index == 0 else f"{chunk_id}{_BLOCK_SUFFIX}{index}"


def _parent_id(vector_id: str) -> str:
    parent, separator, index = vector_id.rpartition(_BLOCK_SUFFIX)
    return parent if separator and index.isdigit() else vector_id


class ChunkBlockVectorStorage:
    """Delegate storage lifecycle while translating blocks to parent chunks.

    Always wrap, including when count=1, so previously indexed blocks remain
    readable/deletable after a configuration change. Existing chunk vectors
    continue to work; changing the count does not automatically reindex them.
    """

    def __init__(
        self, storage: BaseVectorStorage, text_chunks: BaseKVStorage, block_count: int
    ):
        if (
            isinstance(block_count, bool)
            or not isinstance(block_count, int)
            or block_count < 1
        ):
            raise ValueError("block_count must be a positive integer")
        self.storage = storage
        self.text_chunks = text_chunks
        self.block_count = block_count

    def __getattr__(self, name: str) -> Any:
        return getattr(self.storage, name)

    async def _existing_extra_ids(self, chunk_id: str) -> list[str]:
        # Contiguous deterministic IDs allow cleanup independently of today's
        # block_count, with no manifest/schema changes in any storage backend.
        ids = []
        index = 1
        while await self.storage.get_by_id(_block_id(chunk_id, index)) is not None:
            ids.append(_block_id(chunk_id, index))
            index += 1
        return ids

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        if not data:
            return
        old_ids = await asyncio.gather(
            *(self._existing_extra_ids(chunk_id) for chunk_id in data)
        )
        vectors = {}
        stale_ids = []
        for (chunk_id, chunk), previous in zip(data.items(), old_ids):
            blocks = split_chunk_blocks(chunk["content"], self.block_count)
            current_ids = {_block_id(chunk_id, index) for index in range(len(blocks))}
            stale_ids.extend(
                vector_id for vector_id in previous if vector_id not in current_ids
            )
            for index, block in enumerate(blocks):
                vectors[_block_id(chunk_id, index)] = {**chunk, "content": block}
        if stale_ids:
            await self.storage.delete(stale_ids)
        await self.storage.upsert(vectors)

    async def delete(self, ids: list[str]) -> None:
        extra_ids = await asyncio.gather(
            *(self._existing_extra_ids(chunk_id) for chunk_id in ids)
        )
        await self.storage.delete(
            list(
                dict.fromkeys(
                    list(ids) + [item for group in extra_ids for item in group]
                )
            )
        )

    async def query(
        self, query: str, top_k: int, query_embedding: list[float] | None = None
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        # Reuse one query embedding across adaptive over-fetches.
        if query_embedding is None:
            query_embedding = (
                await self.storage.embedding_func([query], context="query", _priority=5)
            )[0]
        limit = top_k
        while True:
            results = await self.storage.query(
                query, limit, query_embedding=query_embedding
            )
            parents = list(
                dict.fromkeys(_parent_id(result["id"]) for result in results)
            )
            records = await self.text_chunks.get_by_ids(parents)
            full_chunks = dict(zip(parents, records))
            chunks = []
            seen = set()
            # Backends return best-first hits. The first hit per parent is its
            # maximum-similarity block (distance conventions vary by backend).
            for result in results:
                parent = _parent_id(result["id"])
                if parent in seen:
                    continue
                full_chunk = full_chunks.get(parent)
                if not full_chunk:
                    # Legacy vectors can be read without KV; block fragments
                    # must never masquerade as complete parent chunks.
                    if parent != result["id"] or self.block_count > 1:
                        continue
                    full_chunk = result
                seen.add(parent)
                chunks.append(
                    {
                        **result,
                        "id": parent,
                        "content": full_chunk["content"],
                        "file_path": full_chunk.get(
                            "file_path", result.get("file_path", "unknown_source")
                        ),
                    }
                )
                if len(chunks) == top_k:
                    return chunks
            if len(results) < limit:
                return chunks
            limit *= 2
