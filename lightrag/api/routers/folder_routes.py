"""
Folder management routes for the LightRAG API.

Provides CRUD endpoints for multi-level document folder management under
the /documents/folders prefix.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from lightrag import LightRAG
from lightrag.base import FolderInfo
from lightrag.api.utils_api import get_combined_auth_dependency
from lightrag.kg.folder_storage import FolderManager


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FolderCreateRequest(BaseModel):
    """Request body for creating a new folder."""

    name: str = Field(..., min_length=1, max_length=255, description="Folder display name")
    parent_id: Optional[str] = Field(
        default=None, description="Parent folder ID; None creates a root folder"
    )
    description: str = Field(default="", description="Optional folder description")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Optional key-value metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Research Papers",
                "parent_id": None,
                "description": "All research paper documents",
                "metadata": {"department": "R&D"},
            }
        }
    )


class FolderUpdateRequest(BaseModel):
    """Request body for updating an existing folder.

    All fields are optional; only supplied fields are updated.
    """

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=255, description="New display name"
    )
    description: Optional[str] = Field(default=None, description="New description")
    parent_id: Optional[str] = Field(
        default="__unset__",
        description="New parent folder ID; pass null to move to root. "
        "Omit this field entirely to leave the parent unchanged.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="Replacement metadata dict"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Folder Name",
                "description": "Updated description",
            }
        }
    )


class FolderResponse(BaseModel):
    """Response model for a single folder."""

    id: str = Field(description="Folder unique identifier")
    name: str = Field(description="Folder display name")
    workspace: str = Field(description="Workspace that owns this folder")
    parent_id: Optional[str] = Field(
        default=None, description="Parent folder ID; None means root folder"
    )
    description: str = Field(default="", description="Folder description")
    created_at: str = Field(description="ISO-8601 creation timestamp")
    updated_at: str = Field(description="ISO-8601 last-update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "folder-abc123",
                "name": "Research Papers",
                "workspace": "my-workspace",
                "parent_id": None,
                "description": "All research paper documents",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "metadata": {},
            }
        }
    )

    @classmethod
    def from_folder_info(cls, folder: FolderInfo) -> "FolderResponse":
        return cls(
            id=folder.id,
            name=folder.name,
            workspace=folder.workspace,
            parent_id=folder.parent_id,
            description=folder.description,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            metadata=folder.metadata,
        )


class FolderTreeNode(BaseModel):
    """A node in the folder tree response."""

    folder: FolderResponse = Field(description="The folder at this node")
    children: List["FolderTreeNode"] = Field(
        default_factory=list, description="Child nodes"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "folder": {"id": "folder-abc123", "name": "Root Folder"},
                "children": [],
            }
        }
    )


class FolderDeleteResponse(BaseModel):
    """Response returned after a folder deletion."""

    deleted_ids: List[str] = Field(description="IDs of all deleted folders")
    message: str = Field(description="Human-readable confirmation message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "deleted_ids": ["folder-abc123"],
                "message": "Folder and 0 descendants deleted successfully.",
            }
        }
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_tree_response(tree: list[dict[str, Any]]) -> list[FolderTreeNode]:
    """Convert a raw tree dict (from FolderManager.get_folder_tree) to response models."""
    result = []
    for node in tree:
        folder_resp = FolderResponse.from_folder_info(node["folder"])
        children = _build_tree_response(node["children"])
        result.append(FolderTreeNode(folder=folder_resp, children=children))
    return result


# ---------------------------------------------------------------------------
# Route factory
# ---------------------------------------------------------------------------


def create_folder_routes(
    rag: LightRAG,
    folder_manager: FolderManager,
    api_key: Optional[str] = None,
) -> APIRouter:
    """Create and return the folder management router.

    Args:
        rag: The LightRAG instance (used for workspace context).
        folder_manager: Initialized FolderManager instance.
        api_key: Optional API key for auth.

    Returns:
        Configured APIRouter with all folder endpoints.
    """
    router = APIRouter(
        prefix="/documents/folders",
        tags=["folders"],
    )

    combined_auth = get_combined_auth_dependency(api_key)

    # ------------------------------------------------------------------ #
    # POST /documents/folders  — Create a folder
    # ------------------------------------------------------------------ #

    @router.post(
        "",
        response_model=FolderResponse,
        status_code=201,
        dependencies=[Depends(combined_auth)],
        summary="Create a new folder",
    )
    async def create_folder(request: FolderCreateRequest) -> FolderResponse:
        """Create a new document folder.

        - **name**: Display name (required, must be unique within the same parent).
        - **parent_id**: ID of the parent folder; omit or pass ``null`` for a root folder.
        - **description**: Optional description text.
        - **metadata**: Optional key/value pairs to attach to the folder.
        """
        try:
            folder = await folder_manager.create_folder(
                name=request.name,
                parent_id=request.parent_id,
                description=request.description,
                metadata=request.metadata,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return FolderResponse.from_folder_info(folder)

    # ------------------------------------------------------------------ #
    # GET /documents/folders  — List folders
    # ------------------------------------------------------------------ #

    @router.get(
        "",
        response_model=List[FolderResponse],
        dependencies=[Depends(combined_auth)],
        summary="List folders",
    )
    async def list_folders(
        parent_id: Optional[str] = None,
        all: bool = False,
    ) -> List[FolderResponse]:
        """List document folders.

        - When **all=true**, all folders in the workspace are returned regardless of hierarchy.
        - When **all=false** (default), only folders whose ``parent_id`` matches the
          ``parent_id`` query parameter are returned (default: root folders where parent is null).
        """
        if all:
            folders = await folder_manager.list_folders()
        else:
            folders = await folder_manager.list_folders(parent_id=parent_id)
        return [FolderResponse.from_folder_info(f) for f in folders]

    # ------------------------------------------------------------------ #
    # GET /documents/folders/tree  — Folder tree
    # ------------------------------------------------------------------ #

    @router.get(
        "/tree",
        response_model=List[FolderTreeNode],
        dependencies=[Depends(combined_auth)],
        summary="Get folder tree",
    )
    async def get_folder_tree(
        parent_id: Optional[str] = None,
    ) -> List[FolderTreeNode]:
        """Return the complete folder tree starting from *parent_id*.

        If **parent_id** is omitted (null), returns the full tree from root level.
        """
        try:
            tree = await folder_manager.get_folder_tree(parent_id=parent_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return _build_tree_response(tree)

    # ------------------------------------------------------------------ #
    # GET /documents/folders/{folder_id}  — Get a folder
    # ------------------------------------------------------------------ #

    @router.get(
        "/{folder_id}",
        response_model=FolderResponse,
        dependencies=[Depends(combined_auth)],
        summary="Get a folder by ID",
    )
    async def get_folder(folder_id: str) -> FolderResponse:
        """Retrieve a single folder by its ID."""
        folder = await folder_manager.get_folder(folder_id)
        if folder is None:
            raise HTTPException(
                status_code=404, detail=f"Folder '{folder_id}' not found."
            )
        return FolderResponse.from_folder_info(folder)

    # ------------------------------------------------------------------ #
    # PUT /documents/folders/{folder_id}  — Update a folder
    # ------------------------------------------------------------------ #

    @router.put(
        "/{folder_id}",
        response_model=FolderResponse,
        dependencies=[Depends(combined_auth)],
        summary="Update a folder",
    )
    async def update_folder(
        folder_id: str, request: FolderUpdateRequest
    ) -> FolderResponse:
        """Update folder properties.

        Only the provided fields are updated.  To move a folder to the root, pass
        ``"parent_id": null``.  To leave the parent unchanged, omit ``parent_id``
        from the request body.
        """
        try:
            folder = await folder_manager.update_folder(
                folder_id=folder_id,
                name=request.name,
                description=request.description,
                parent_id=request.parent_id,
                metadata=request.metadata,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return FolderResponse.from_folder_info(folder)

    # ------------------------------------------------------------------ #
    # DELETE /documents/folders/{folder_id}  — Delete a folder
    # ------------------------------------------------------------------ #

    @router.delete(
        "/{folder_id}",
        response_model=FolderDeleteResponse,
        dependencies=[Depends(combined_auth)],
        summary="Delete a folder",
    )
    async def delete_folder(
        folder_id: str, recursive: bool = False
    ) -> FolderDeleteResponse:
        """Delete a folder.

        - **recursive**: If ``true``, also deletes all sub-folders.
          If ``false`` (default) and the folder has children, the request fails.

        Note: This only deletes the folder metadata.  Documents assigned to the
        deleted folder(s) are *not* deleted; they are simply left without a
        folder association.
        """
        try:
            deleted_ids = await folder_manager.delete_folder(
                folder_id=folder_id, recursive=recursive
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        descendant_count = len(deleted_ids) - 1
        return FolderDeleteResponse(
            deleted_ids=deleted_ids,
            message=f"Folder and {descendant_count} descendant(s) deleted successfully.",
        )

    # ------------------------------------------------------------------ #
    # GET /documents/folders/{folder_id}/ancestors  — Ancestor chain
    # ------------------------------------------------------------------ #

    @router.get(
        "/{folder_id}/ancestors",
        response_model=List[FolderResponse],
        dependencies=[Depends(combined_auth)],
        summary="Get ancestor chain for a folder",
    )
    async def get_folder_ancestors(folder_id: str) -> List[FolderResponse]:
        """Return the ancestor chain from root to the direct parent of *folder_id*.

        The list is ordered root-first.  An empty list means the folder is at root.
        """
        try:
            ancestors = await folder_manager.get_ancestors(folder_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return [FolderResponse.from_folder_info(f) for f in ancestors]

    return router
