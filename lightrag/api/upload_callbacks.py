"""Completion notifications for asynchronous multipart uploads."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import httpx

from lightrag.base import DocStatus
from lightrag.pipeline_messages import append_pipeline_message
from lightrag.utils import logger

if TYPE_CHECKING:
    from lightrag import LightRAG


async def wait_for_upload_result(
    rag: "LightRAG", track_id: str
) -> list[dict[str, Any]]:
    """Wait for this upload, including KG work, even if another loop owns it."""
    while True:
        docs = await rag.aget_docs_by_track_id(track_id)
        if not docs:
            raise RuntimeError("Upload has no tracked document or was deleted")
        results = []
        for doc_id, doc in docs.items():
            status = getattr(doc.status, "value", doc.status)
            metadata = doc.metadata or {}
            kg_status = metadata.get("kg_status")
            if status not in (DocStatus.PROCESSED.value, DocStatus.FAILED.value):
                break
            if status == DocStatus.PROCESSED.value and kg_status in (
                "pending",
                "running",
            ):
                break
            results.append(
                {
                    "doc_id": doc_id,
                    "file_path": doc.file_path,
                    "status": status,
                    "kg_status": kg_status,
                    "chunks_count": doc.chunks_count,
                    "error": doc.error_msg or metadata.get("kg_error"),
                }
            )
        else:
            return results
        await asyncio.sleep(1)


async def record_callback_message(
    rag: "LightRAG | None", message: str, *, warning: bool = False
) -> None:
    """Expose callback events through the existing workspace pipeline history."""
    message = f"[callback_url] {message}"
    (logger.warning if warning else logger.info)(message)
    if rag is None:
        return
    from lightrag.kg.shared_storage import get_namespace_data, get_namespace_lock

    try:
        status = await get_namespace_data("pipeline_status", workspace=rag.workspace)
        async with get_namespace_lock("pipeline_status", workspace=rag.workspace):
            append_pipeline_message(status, message)
    except Exception as exc:  # noqa: BLE001 - logging must not interrupt delivery
        logger.warning("Callback WebUI logging failed: %s", type(exc).__name__)


async def send_upload_callback(
    callback_url: str, payload: dict[str, Any], *, rag: "LightRAG | None" = None
) -> None:
    """POST JSON with bounded retries; delivery failure never changes indexing."""
    context = f"track_id={payload['track_id']} filename={payload.get('filename', '-')} status={payload.get('status', '-')}"
    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=False, trust_env=False
        ) as client:
            for attempt in range(3):
                await record_callback_message(
                    rag, f"Sending {context} attempt={attempt + 1}/3"
                )
                started = time.monotonic()
                try:
                    response = await client.post(
                        callback_url,
                        json=payload,
                        headers={"Idempotency-Key": payload["event_id"]},
                    )
                    if 200 <= response.status_code < 300:
                        await record_callback_message(
                            rag,
                            f"Success {context} attempt={attempt + 1}/3 HTTP={response.status_code} duration={time.monotonic() - started:.2f}s",
                        )
                        return
                    failure = f"HTTP={response.status_code}"
                except httpx.HTTPError as exc:
                    # Do not log URLs or exception strings: URLs may contain tokens.
                    failure = f"error={type(exc).__name__}"
                await record_callback_message(
                    rag,
                    f"Attempt failed {context} attempt={attempt + 1}/3 {failure} duration={time.monotonic() - started:.2f}s",
                    warning=True,
                )
                if attempt < 2:
                    await record_callback_message(
                        rag, f"Retry scheduled {context} delay={2**attempt}s"
                    )
                    await asyncio.sleep(2**attempt)
    except Exception as exc:  # noqa: BLE001 - notification must not fail document processing
        await record_callback_message(
            rag,
            f"Client failed {context} error={type(exc).__name__}",
            warning=True,
        )
        return
    await record_callback_message(
        rag,
        f"Delivery exhausted {context} attempts=3",
        warning=True,
    )


async def run_upload_with_callback(
    indexing_task: Callable[[], Awaitable[None]],
    rag: "LightRAG",
    callback_url: str | None,
    track_id: str,
    filename: str,
) -> None:
    """Keep notification monitoring outside the upload target lock."""
    if callback_url is None:
        await indexing_task()
        return
    documents = []
    error = None
    try:
        await indexing_task()
        documents = await wait_for_upload_result(rag, track_id)
    except Exception as exc:  # noqa: BLE001 - report all background processing failures
        error = str(exc)
        logger.warning("Upload processing failed for track_id=%s", track_id)
    failed = error is not None or any(
        doc["status"] == DocStatus.FAILED.value or doc["kg_status"] == "failed"
        for doc in documents
    )
    await send_upload_callback(
        callback_url,
        {
            "event": "document.processing_completed",
            "event_id": track_id,
            "track_id": track_id,
            "filename": filename,
            "status": "failed" if failed else "processed",
            "documents": documents,
            "error": error,
        },
        rag=rag,
    )
