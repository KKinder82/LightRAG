"""Offline checks for completion timing and callback delivery."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from lightrag.api import upload_callbacks as callbacks
from lightrag.base import DocStatus

pytestmark = pytest.mark.offline


def document(status=DocStatus.PROCESSED, kg_status="completed"):
    return SimpleNamespace(
        status=status,
        metadata={"kg_status": kg_status},
        file_path="test.txt",
        chunks_count=1,
        error_msg=None,
    )


async def test_waits_for_other_processing_loop_and_kg(monkeypatch):
    rag = SimpleNamespace(
        aget_docs_by_track_id=AsyncMock(
            side_effect=[
                {"doc": document(DocStatus.PENDING, None)},
                {"doc": document(kg_status="running")},
                {"doc": document()},
            ]
        )
    )
    sleep = AsyncMock()
    monkeypatch.setattr(callbacks.asyncio, "sleep", sleep)
    result = await callbacks.wait_for_upload_result(rag, "track")
    assert result[0]["kg_status"] == "completed"
    assert sleep.await_count == 2


@pytest.mark.parametrize("failure", ["500", "timeout", "redirect"])
async def test_callback_retries_and_accepts_empty_204(monkeypatch, failure, caplog):
    monkeypatch.setattr(callbacks.logger, "propagate", True)
    requests = []

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            return httpx.Response(
                500 if failure == "500" else 302,
                headers={"Location": "http://other.example"},
            )
        return httpx.Response(204)

    original = httpx.AsyncClient
    options = []

    def client(**kwargs):
        options.append(kwargs)
        return original(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(callbacks.httpx, "AsyncClient", client)
    monkeypatch.setattr(callbacks.asyncio, "sleep", AsyncMock())
    await callbacks.send_upload_callback(
        "http://caller.example/done", {"event_id": "track", "track_id": "track"}
    )
    assert len(requests) == 2
    assert requests[0].headers["Idempotency-Key"] == "track"
    assert requests[0].headers["Content-Type"] == "application/json"
    assert options[0]["follow_redirects"] is False
    assert options[0]["trust_env"] is False
    assert (
        "error=ReadTimeout" in caplog.text
        if failure == "timeout"
        else "HTTP=" in caplog.text
    )


async def test_exhausted_delivery_does_not_raise(monkeypatch, caplog):
    monkeypatch.setattr(callbacks.logger, "propagate", True)
    post = AsyncMock(return_value=httpx.Response(503))
    client = AsyncMock()
    client.__aenter__.return_value.post = post
    monkeypatch.setattr(callbacks.httpx, "AsyncClient", lambda **kwargs: client)
    monkeypatch.setattr(callbacks.asyncio, "sleep", AsyncMock())
    await callbacks.send_upload_callback(
        "http://caller.example/done", {"event_id": "track", "track_id": "track"}
    )
    assert post.await_count == 3
    assert "Delivery exhausted" in caplog.text
    assert "HTTP=503" in caplog.text


async def test_pre_enqueue_failure_notifies_caller(monkeypatch):
    send = AsyncMock()
    monkeypatch.setattr(callbacks, "send_upload_callback", send)
    task = AsyncMock(side_effect=RuntimeError("Replacement failed"))
    await callbacks.run_upload_with_callback(
        task, None, "http://caller.example/done", "track", "test.txt"
    )
    payload = send.await_args.args[1]
    assert payload["status"] == "failed"
    assert payload["error"] == "Replacement failed"


async def test_no_callback_preserves_existing_behavior():
    task = AsyncMock(side_effect=RuntimeError("Original failure"))
    with pytest.raises(RuntimeError, match="Original failure"):
        await callbacks.run_upload_with_callback(task, None, None, "track", "test.txt")
