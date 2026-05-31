"""Folder storage manager backed by BaseKVStorage.

FolderManager implements multi-level directory management for LightRAG.
Folders are stored as serialized ``FolderInfo`` dicts inside a KV namespace
(``doc_folders``), which makes the implementation backend-agnostic — any
storage that implements ``BaseKVStorage`` works out of the box.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from lightrag.base import BaseKVStorage, FolderInfo
from lightrag.utils import logger


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (Z suffix)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _folder_to_dict(folder: FolderInfo) -> dict[str, Any]:
    """Convert a FolderInfo to the raw dict stored in the KV backend."""
    return {
        "id": folder.id,
        "name": folder.name,
        "workspace": folder.workspace,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
        "parent_id": folder.parent_id,
        "description": folder.description,
        "metadata": folder.metadata,
    }


def _dict_to_folder(data: dict[str, Any]) -> FolderInfo:
    """Reconstruct a FolderInfo from its raw dict representation."""
    return FolderInfo(
        id=data["id"],
        name=data["name"],
        workspace=data["workspace"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        parent_id=data.get("parent_id"),
        description=data.get("description", ""),
        metadata=data.get("metadata", {}),
    )


# --------------------------------------------------------------------------- #
# FolderManager
# --------------------------------------------------------------------------- #


class FolderManager:
    """Manages document folders in a workspace.

    Each instance is tied to exactly one workspace.  The underlying KV
    storage is expected to have been initialized before any of these methods
    are called.

    Args:
        kv_storage: An initialized ``BaseKVStorage`` instance whose namespace
            is ``doc_folders``.
        workspace: The workspace identifier that owns all folders managed by
            this instance.
    """

    def __init__(self, kv_storage: BaseKVStorage, workspace: str) -> None:
        self._storage = kv_storage
        self._workspace = workspace

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #

    async def _get_raw(self, folder_id: str) -> dict[str, Any] | None:
        """Return the raw dict for *folder_id*, or None if not found."""
        data = await self._storage.get_by_id(folder_id)
        if data is None:
            return None
        # Silently drop folders that belong to a different workspace.
        if data.get("workspace") != self._workspace:
            return None
        return data

    async def _list_all_raw(self) -> list[dict[str, Any]]:
        """Return all raw folder dicts in the current workspace."""
        # We maintain a workspace-scoped index entry that holds all folder IDs.
        # This avoids needing a backend-level "scan all keys" API.
        index_key = f"__index__{self._workspace}"
        index_raw = await self._storage.get_by_id(index_key)
        if index_raw is None:
            return []

        all_ids: list[str] = index_raw.get("folder_ids", [])
        if not all_ids:
            return []

        raw_items = await self._storage.get_by_ids(all_ids)
        result = []
        for item in raw_items:
            if item is None:
                continue
            if item.get("workspace") != self._workspace:
                continue
            result.append(item)
        return result

    async def _save_index(self, folder_ids: list[str]) -> None:
        """Persist the workspace folder-ID index."""
        index_key = f"__index__{self._workspace}"
        await self._storage.upsert({index_key: {"folder_ids": folder_ids}})

    async def _get_all_ids(self) -> list[str]:
        """Return all folder IDs in the current workspace from the index."""
        index_key = f"__index__{self._workspace}"
        index_raw = await self._storage.get_by_id(index_key)
        if index_raw is None:
            return []
        return list(index_raw.get("folder_ids", []))

    async def _add_to_index(self, folder_id: str) -> None:
        existing = await self._get_all_ids()
        if folder_id not in existing:
            existing.append(folder_id)
            await self._save_index(existing)

    async def _remove_from_index(self, folder_id: str) -> None:
        existing = await self._get_all_ids()
        if folder_id in existing:
            existing.remove(folder_id)
            await self._save_index(existing)

    # ------------------------------------------------------------------ #
    # CRUD operations
    # ------------------------------------------------------------------ #

    async def create_folder(
        self,
        name: str,
        parent_id: str | None = None,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> FolderInfo:
        """Create a new folder and return the resulting FolderInfo.

        Args:
            name: Display name for the folder.  Must be non-empty.
            parent_id: ID of the parent folder; ``None`` creates a root folder.
            description: Optional free-text description.
            metadata: Optional extra key/value pairs to attach.

        Returns:
            The newly created :class:`FolderInfo`.

        Raises:
            ValueError: If *name* is empty, if *parent_id* does not exist, or
                if a sibling folder with the same name already exists.
        """
        name = name.strip()
        if not name:
            raise ValueError("Folder name must not be empty.")

        # Validate parent exists (if given)
        if parent_id is not None:
            parent_raw = await self._get_raw(parent_id)
            if parent_raw is None:
                raise ValueError(f"Parent folder '{parent_id}' not found.")

        # Check name uniqueness within the same parent
        siblings = await self.list_folders(parent_id=parent_id)
        for sibling in siblings:
            if sibling.name == name:
                raise ValueError(
                    f"A folder named '{name}' already exists under parent '{parent_id}'."
                )

        now = _now_iso()
        folder = FolderInfo(
            id=f"folder-{uuid.uuid4().hex}",
            name=name,
            workspace=self._workspace,
            created_at=now,
            updated_at=now,
            parent_id=parent_id,
            description=description,
            metadata=metadata or {},
        )

        await self._storage.upsert({folder.id: _folder_to_dict(folder)})
        await self._add_to_index(folder.id)
        logger.info(
            f"[{self._workspace}] Created folder '{folder.name}' (id={folder.id}, parent={parent_id})"
        )
        return folder

    async def get_folder(self, folder_id: str) -> FolderInfo | None:
        """Get a folder by ID.

        Returns:
            :class:`FolderInfo` if found, ``None`` otherwise.
        """
        raw = await self._get_raw(folder_id)
        if raw is None:
            return None
        try:
            return _dict_to_folder(raw)
        except KeyError as exc:
            logger.error(
                f"[{self._workspace}] Malformed folder record '{folder_id}': {exc}"
            )
            return None

    async def list_folders(
        self, parent_id: str | None = "__unset__"
    ) -> list[FolderInfo]:
        """List folders.

        Args:
            parent_id: If provided (including ``None``), filters by parent.
                Pass the sentinel ``"__unset__"`` (default) to return *all*
                folders in the workspace without filtering.

        Returns:
            List of matching :class:`FolderInfo` instances, sorted by name.
        """
        raw_list = await self._list_all_raw()
        result = []
        for raw in raw_list:
            try:
                folder = _dict_to_folder(raw)
            except KeyError as exc:
                logger.warning(
                    f"[{self._workspace}] Skipping malformed folder record: {exc}"
                )
                continue

            if parent_id != "__unset__":
                if folder.parent_id != parent_id:
                    continue

            result.append(folder)

        result.sort(key=lambda f: f.name)
        return result

    async def update_folder(
        self,
        folder_id: str,
        name: str | None = None,
        description: str | None = None,
        parent_id: str | None = "__unset__",
        metadata: dict[str, Any] | None = None,
    ) -> FolderInfo:
        """Update folder properties.

        Only the supplied (non-None / non-sentinel) fields are updated.

        Args:
            folder_id: The ID of the folder to update.
            name: New display name (stripped).
            description: New description text.
            parent_id: New parent ID; pass ``None`` to promote to root.  The
                default sentinel ``"__unset__"`` leaves the parent unchanged.
            metadata: New metadata dict (replaces existing; ``None`` leaves unchanged).

        Returns:
            Updated :class:`FolderInfo`.

        Raises:
            ValueError: If the folder is not found, the new parent doesn't
                exist, a naming conflict would be created, or a circular
                reference would result.
        """
        raw = await self._get_raw(folder_id)
        if raw is None:
            raise ValueError(f"Folder '{folder_id}' not found.")

        folder = _dict_to_folder(raw)

        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Folder name must not be empty.")
            folder.name = name

        if description is not None:
            folder.description = description

        if metadata is not None:
            folder.metadata = metadata

        if parent_id != "__unset__":
            # Validate parent exists (if not None)
            if parent_id is not None:
                parent_raw = await self._get_raw(parent_id)
                if parent_raw is None:
                    raise ValueError(f"Parent folder '{parent_id}' not found.")
                # Prevent circular reference
                await self._validate_no_circular_reference(folder_id, parent_id)

            folder.parent_id = parent_id

        # Name uniqueness check within new/current parent
        siblings = await self.list_folders(parent_id=folder.parent_id)
        for sibling in siblings:
            if sibling.name == folder.name and sibling.id != folder_id:
                raise ValueError(
                    f"A folder named '{folder.name}' already exists under parent '{folder.parent_id}'."
                )

        folder.updated_at = _now_iso()
        await self._storage.upsert({folder.id: _folder_to_dict(folder)})
        logger.info(f"[{self._workspace}] Updated folder '{folder.id}'")
        return folder

    async def delete_folder(
        self, folder_id: str, recursive: bool = False
    ) -> list[str]:
        """Delete a folder and optionally all its descendants.

        Args:
            folder_id: The ID of the folder to delete.
            recursive: If ``True``, also deletes all sub-folders recursively.
                If ``False`` and the folder has children, raises ``ValueError``.

        Returns:
            List of all deleted folder IDs (including sub-folders when recursive).

        Raises:
            ValueError: If the folder is not found, or if non-recursive delete
                is attempted on a folder that has children.
        """
        raw = await self._get_raw(folder_id)
        if raw is None:
            raise ValueError(f"Folder '{folder_id}' not found.")

        children = await self.list_folders(parent_id=folder_id)
        if children and not recursive:
            raise ValueError(
                f"Folder '{folder_id}' has {len(children)} sub-folder(s). "
                "Use recursive=True to delete with all descendants."
            )

        # Collect all IDs to delete
        to_delete = await self._collect_descendant_ids(folder_id)
        to_delete.append(folder_id)

        # Remove from KV storage
        await self._storage.delete(to_delete)

        # Remove from index
        current_ids = await self._get_all_ids()
        remaining = [fid for fid in current_ids if fid not in set(to_delete)]
        await self._save_index(remaining)

        logger.info(
            f"[{self._workspace}] Deleted folder '{folder_id}' (and {len(to_delete)-1} descendants)"
        )
        return to_delete

    # ------------------------------------------------------------------ #
    # Tree helpers
    # ------------------------------------------------------------------ #

    async def get_folder_tree(
        self, parent_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Return a nested tree representation starting from *parent_id*.

        Args:
            parent_id: Root of the tree.  ``None`` = top-level folders.

        Returns:
            List of dicts with shape:
            ``{"folder": FolderInfo, "children": [<same shape>, ...]}``.
        """
        children = await self.list_folders(parent_id=parent_id)
        result = []
        for child in children:
            sub_tree = await self.get_folder_tree(parent_id=child.id)
            result.append({"folder": child, "children": sub_tree})
        return result

    async def get_ancestors(self, folder_id: str) -> list[FolderInfo]:
        """Return the ancestor chain from root to the direct parent of *folder_id*.

        Args:
            folder_id: The folder whose ancestors to retrieve.

        Returns:
            List of :class:`FolderInfo` from root to the direct parent,
            ordered root-first.  Empty list if the folder is already at root.

        Raises:
            ValueError: If *folder_id* doesn't exist.
        """
        raw = await self._get_raw(folder_id)
        if raw is None:
            raise ValueError(f"Folder '{folder_id}' not found.")

        folder = _dict_to_folder(raw)
        ancestors: list[FolderInfo] = []
        current_parent = folder.parent_id
        visited: set[str] = {folder_id}

        while current_parent is not None:
            if current_parent in visited:
                # Circular reference guard — shouldn't happen but be safe
                logger.warning(
                    f"[{self._workspace}] Circular reference detected at '{current_parent}'"
                )
                break
            visited.add(current_parent)
            parent_raw = await self._get_raw(current_parent)
            if parent_raw is None:
                break
            parent = _dict_to_folder(parent_raw)
            ancestors.insert(0, parent)
            current_parent = parent.parent_id

        return ancestors

    async def get_descendant_ids(self, folder_id: str) -> list[str]:
        """Return all descendant folder IDs (excluding *folder_id* itself).

        Args:
            folder_id: The root folder whose descendants to find.

        Returns:
            Flat list of descendant folder IDs.
        """
        return await self._collect_descendant_ids(folder_id)

    # ------------------------------------------------------------------ #
    # Internal tree helpers
    # ------------------------------------------------------------------ #

    async def _collect_descendant_ids(self, folder_id: str) -> list[str]:
        """DFS collection of all descendant folder IDs (not including *folder_id*)."""
        result: list[str] = []
        children = await self.list_folders(parent_id=folder_id)
        for child in children:
            result.append(child.id)
            result.extend(await self._collect_descendant_ids(child.id))
        return result

    async def _validate_no_circular_reference(
        self, folder_id: str, new_parent_id: str
    ) -> None:
        """Raise ``ValueError`` if moving *folder_id* under *new_parent_id* would
        create a cycle.

        A cycle exists if *new_parent_id* is a descendant of *folder_id*.
        """
        descendants = await self._collect_descendant_ids(folder_id)
        if new_parent_id in descendants or new_parent_id == folder_id:
            raise ValueError(
                f"Moving folder '{folder_id}' under '{new_parent_id}' would create "
                "a circular reference."
            )
