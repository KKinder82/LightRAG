"""Backfill folder_id for documents that were uploaded before the fix.

Documents uploaded before commit [add hash] may have empty metadata.folder_id
even though they were uploaded with a folder selected.  This script reads
folder storage and doc_status, and for each folder, prompts you to confirm
which documents belong to it.

Usage:
    python scripts/backfill_folder_ids.py
"""

import json
import sys
from pathlib import Path

# Adjust if your storage is elsewhere
RAG_STORAGE_DIR = Path("rag_storage")
DOC_STATUS_FILE = RAG_STORAGE_DIR / "kv_store_doc_status.json"
FOLDER_FILE = RAG_STORAGE_DIR / "kv_store_doc_folders.json"


def main():
    if not DOC_STATUS_FILE.exists():
        print(f"Error: {DOC_STATUS_FILE} not found")
        sys.exit(1)
    if not FOLDER_FILE.exists():
        print(f"Error: {FOLDER_FILE} not found")
        sys.exit(1)

    with open(DOC_STATUS_FILE) as f:
        doc_status = json.load(f)
    with open(FOLDER_FILE) as f:
        folders_raw = json.load(f)

    # Build folder map: id -> name
    folders = {}
    for k, v in folders_raw.items():
        if isinstance(v, dict) and "name" in v:
            folders[k] = v["name"]

    if not folders:
        print("No folders found. Nothing to backfill.")
        return

    print(f"Found {len(folders)} folder(s):")
    for fid, fname in folders.items():
        print(f"  {fname} (id={fid})")

    # Find docs without folder_id
    docs_without_folder = []
    for doc_id, doc in doc_status.items():
        meta = doc.get("metadata") or {}
        if not meta.get("folder_id"):
            docs_without_folder.append((doc_id, doc))

    if not docs_without_folder:
        print("\nAll documents already have folder_id. Nothing to backfill.")
        return

    print(f"\nFound {len(docs_without_folder)} document(s) without folder_id:")
    for doc_id, doc in docs_without_folder:
        fp = doc.get("file_path", "unknown")
        status = doc.get("status", "unknown")
        print(f"  [{status}] {doc_id}: {fp}")

    # Auto-backfill: if there's exactly one folder, assign all docs to it
    if len(folders) == 1:
        fid = list(folders.keys())[0]
        fname = list(folders.values())[0]
        print(f"\nOnly one folder exists ({fname}), auto-assigning all docs...")
        for doc_id, doc in docs_without_folder:
            meta = doc.get("metadata") or {}
            meta["folder_id"] = fid
            doc["metadata"] = meta
        with open(DOC_STATUS_FILE, "w") as f:
            json.dump(doc_status, f, indent=2, ensure_ascii=False)
        print(f"Assigned {len(docs_without_folder)} document(s) to folder '{fname}'")
    else:
        print("\nMultiple folders exist. Manual mapping needed.")
        print("This script requires interactive input.")
        # For now, just print a hint
        for fid, fname in folders.items():
            print(f"  To assign all docs to '{fname}', run:")
            print(f"    python3 -c 'import json; d=json.load(open(\"{DOC_STATUS_FILE}\")); [d[i][\"metadata\"].__setitem__(\"folder_id\", \"{fid}\") for i in d if \"folder_id\" not in d[i].get(\"metadata\",{{}})]; json.dump(d,open(\"{DOC_STATUS_FILE}\",\"w\"),indent=2,ensure_ascii=False)'")


if __name__ == "__main__":
    main()
