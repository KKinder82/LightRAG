"""Project datasets with independent RAG instances and workspace-scoped storage."""

import asyncio
from copy import deepcopy
from dataclasses import fields
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from starlette.middleware import Middleware

from lightrag import LightRAG
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.kg.folder_storage import FolderManager
from lightrag.kg.json_kv_impl import JsonKVStorage
from lightrag.kg.shared_storage import get_namespace_lock
from lightrag.llm_roles import RoleLLMConfig


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProjectDatasets:
    def __init__(self, base, input_dir, api_key, top_k):
        self.base = base
        self.input_dir = input_dir
        self.api_key = api_key
        self.top_k = top_k
        self.storage = JsonKVStorage(
            namespace="project_catalog",
            workspace=base.workspace,
            embedding_func=None,
            global_config=base.full_docs.global_config,
        )
        self.instances = {}
        self.lock = asyncio.Lock()

    async def start(self):
        await self.storage.initialize()
        # Recover queued deletions even when nobody opens a project after restart.
        for project_id in await self.list_projects():
            await self.get(project_id)

    async def list_projects(self):
        return (await self.storage.get_by_id("catalog") or {}).get("projects", {})

    async def create(self, name):
        project_id = "project_" + uuid4().hex
        async with get_namespace_lock(
            "project_catalog_consumer", workspace=self.base.workspace
        ):
            projects = await self.list_projects()
            projects[project_id] = {"id": project_id, "name": name}
            await self.storage.upsert({"catalog": {"projects": projects}})
            await self.storage.index_done_callback()
        return projects[project_id]

    async def get(self, project_id):
        async with self.lock:
            if project_id in self.instances:
                return self.instances[project_id][0]
            if project_id not in await self.list_projects():
                raise HTTPException(404, "Unknown project dataset")
            from lightrag.api.routers.document_routes import (
                DocumentManager,
                create_document_routes,
            )
            from lightrag.api.routers.folder_routes import create_folder_routes
            from lightrag.api.routers.query_routes import create_query_routes
            from lightrag.api.routers.graph_routes import create_graph_routes

            config = {
                field.name: getattr(self.base, field.name)
                for field in fields(LightRAG)
                if field.init
                and not field.name.startswith("_")
                and field.name != "folder_manager"
            }
            # Use unwrapped providers so caches and queues belong to the new dataset.
            config["embedding_func"] = self.base.full_docs.global_config[
                "embedding_func"
            ]
            config["role_llm_configs"] = {
                role: RoleLLMConfig(
                    func=state.raw_func,
                    kwargs=deepcopy(state.kwargs),
                    max_async=state.max_async,
                    timeout=state.timeout,
                    metadata=deepcopy(state.metadata),
                )
                for role, state in self.base._role_llm_states.items()
            }
            config["workspace"] = project_id
            config["addon_params"] = deepcopy(dict(self.base.addon_params))
            rag = LightRAG(**config)
            builder = getattr(self.base, "_llm_role_builder", None)
            if callable(builder):
                rag.register_role_llm_builder(builder)
            await rag.initialize_storages()
            # Backends with forced workspace overrides cannot safely serve projects.
            from lightrag.api.lightrag_server import _get_storage_workspaces

            if any(
                value != project_id for value in _get_storage_workspaces(rag).values()
            ):
                await rag.finalize_storages()
                raise HTTPException(
                    409, "Storage workspace overrides prevent project isolation"
                )
            folder_kv = JsonKVStorage(
                namespace="doc_folders",
                workspace=project_id,
                embedding_func=None,
                global_config=rag.full_docs.global_config,
            )
            await folder_kv.initialize()
            await rag.check_and_migrate_data()
            folders = FolderManager(folder_kv, project_id)
            rag.folder_manager = folders
            app = FastAPI()
            app.include_router(
                create_document_routes(
                    rag,
                    DocumentManager(self.input_dir, workspace=project_id),
                    self.api_key,
                    folder_manager=folders,
                )
            )
            app.include_router(create_folder_routes(rag, folders, self.api_key))
            app.include_router(create_query_routes(rag, self.api_key, self.top_k))
            app.include_router(
                create_graph_routes(rag, self.api_key, folder_manager=folders)
            )
            from lightrag.api.routers.ollama_api import OllamaAPI

            app.include_router(
                OllamaAPI(rag, top_k=self.top_k, api_key=self.api_key).router,
                prefix="/api",
            )
            await rag.deletion_queue.start()
            self.instances[project_id] = (app, rag, folder_kv)
            return app

    async def close(self):
        for _, rag, folders in self.instances.values():
            await rag.deletion_queue.close()
            await rag.finalize_storages()
            await folders.finalize()
        await self.storage.finalize()


def install_project_routes(app, datasets, api_key):
    auth = get_combined_auth_dependency(api_key)

    @app.get("/projects", dependencies=[Depends(auth)])
    async def list_projects():
        return list((await datasets.list_projects()).values())

    @app.post("/projects", dependencies=[Depends(auth)])
    async def create_project(request: ProjectCreate):
        name = request.name.strip()
        if not name:
            raise HTTPException(422, "Project name cannot be blank")
        return await datasets.create(name)

    # Keep CORS and other application middleware outside project dispatch.
    app.user_middleware.append(Middleware(ProjectDispatch, datasets=datasets))


class ProjectDispatch:
    """Dispatch data endpoints using an explicit project header, never a fallback."""

    def __init__(self, app, datasets):
        self.app = app
        self.datasets = datasets

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] != "OPTIONS":
            project = (
                dict(scope.get("headers", [])).get(b"x-lightrag-project", b"").decode()
            )
            path = scope["path"]
            root_path = scope.get("root_path", "").rstrip("/")
            if root_path and (path == root_path or path.startswith(root_path + "/")):
                path = path[len(root_path) :] or "/"
            if project and any(
                path == p or path.startswith(p + "/")
                for p in ("/documents", "/query", "/graphs", "/graph", "/api")
            ):
                try:
                    target = await self.datasets.get(project)
                except HTTPException as error:
                    await JSONResponse(
                        {"detail": error.detail}, status_code=error.status_code
                    )(scope, receive, send)
                    return
                await target(scope, receive, send)
                return
        await self.app(scope, receive, send)
