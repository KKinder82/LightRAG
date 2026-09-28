"""Durable deletion requests, executed only after ingestion releases its lock."""

import asyncio
from uuid import uuid4

from fastapi import BackgroundTasks
from lightrag.kg.shared_storage import get_namespace_lock
from lightrag.utils import logger
from lightrag.kg.json_kv_impl import JsonKVStorage


class DeletionQueue:
    def __init__(self, rag, execute):
        self.rag = rag
        self.execute = execute
        self.storage = None
        self.task = None
        self.initialized = False
        self.start_lock = asyncio.Lock()

    async def start(self):
        async with self.start_lock:
            await self._start()

    async def _start(self):
        if not self.initialized:
            if self.storage is None:
                self.storage = JsonKVStorage(
                    namespace="deletion_jobs",
                    workspace=self.rag.workspace,
                    embedding_func=None,
                    global_config=self.rag.full_docs.global_config,
                )
            await self.storage.initialize()
            self.initialized = True
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())

    async def submit(self, request):
        await self.start()
        job_id = "delete-" + uuid4().hex
        async with get_namespace_lock(
            "deletion_jobs_consumer", workspace=self.rag.workspace
        ):
            jobs = await self.list_jobs()
            jobs[job_id] = {"request": request.model_dump(), "status": "queued"}
            await self.storage.upsert({"jobs": {"items": jobs}})
            await self.storage.index_done_callback()
        return job_id

    async def list_jobs(self):
        return (await self.storage.get_by_id("jobs") or {}).get("items", {})

    async def run(self):
        from lightrag.api.routers.document_routes import DeleteDocRequest

        while True:
            try:
                # Serialize consumers across API workers in this workspace.
                async with get_namespace_lock(
                    "deletion_jobs_consumer", workspace=self.rag.workspace
                ):
                    jobs = await self.list_jobs()
                    for job_id, job in jobs.items():
                        if job["status"] != "queued":
                            continue
                        tasks = BackgroundTasks()
                        result = await self.execute(
                            DeleteDocRequest(**job["request"]), tasks
                        )
                        if result.status == "busy":
                            break
                        await tasks()
                        # Verify actual absence; background deletion reports errors in logs.
                        remaining = []
                        for doc_id in job["request"]["doc_ids"]:
                            doc = await self.rag.doc_status.get_by_id(doc_id)
                            folder = job["request"].get("folder_id")
                            if doc and (
                                not folder
                                or folder
                                in (
                                    doc.get("metadata", {}).get("folder_ids")
                                    or [doc.get("metadata", {}).get("folder_id")]
                                )
                            ):
                                remaining.append(doc_id)
                        jobs[job_id] = {
                            **job,
                            "status": "failed" if remaining else "completed",
                            "remaining": remaining,
                        }
                        await self.storage.upsert({"jobs": {"items": jobs}})
                        await self.storage.index_done_callback()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Deletion queue processing failed; request retained for retry"
                )
            await asyncio.sleep(1)

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        if self.initialized:
            await self.storage.finalize()
