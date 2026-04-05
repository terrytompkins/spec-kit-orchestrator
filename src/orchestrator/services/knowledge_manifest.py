"""Load/save knowledge manifest.json and CRUD for document records."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from orchestrator.services import knowledge_config as kcfg
from orchestrator.services.knowledge_paths import ensure_knowledge_dirs, manifest_path

IngestionStatus = Literal["pending", "parsed", "indexed", "failed"]
IngestionMode = Literal["inline_eligible", "rag_only"]
OverrideMode = Literal["force_inline", "force_rag"]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def safe_original_filename(name: str) -> str:
    """Single path segment safe for storage; never trust user paths."""
    base = Path(name).name
    base = base.replace("..", "_")
    base = re.sub(r"[^\w.\- ()\[\]]+", "_", base).strip()
    return (base[:200] or "upload").strip()


@dataclass
class DocumentRecord:
    id: str
    original_filename: str
    stored_relpath: str
    mime_type: str
    byte_size: int
    sha256: str
    ingestion_status: IngestionStatus
    ingestion_mode: IngestionMode
    user_override_mode: Optional[OverrideMode] = None
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    error_message: Optional[str] = None
    chunking: Dict[str, Any] = field(
        default_factory=lambda: {
            "strategy": "recursive_char",
            "chunk_size": kcfg.CHUNK_SIZE,
            "overlap": kcfg.CHUNK_OVERLAP,
        }
    )

    def to_json_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> DocumentRecord:
        chunking = data.get("chunking") or {
            "strategy": "recursive_char",
            "chunk_size": kcfg.CHUNK_SIZE,
            "overlap": kcfg.CHUNK_OVERLAP,
        }
        return cls(
            id=data["id"],
            original_filename=data["original_filename"],
            stored_relpath=data["stored_relpath"],
            mime_type=data.get("mime_type", "application/octet-stream"),
            byte_size=int(data.get("byte_size", 0)),
            sha256=data.get("sha256", ""),
            ingestion_status=data.get("ingestion_status", "pending"),
            ingestion_mode=data.get("ingestion_mode", "rag_only"),
            user_override_mode=data.get("user_override_mode"),
            tags=list(data.get("tags") or []),
            created_at=data.get("created_at") or _utc_now(),
            updated_at=data.get("updated_at") or _utc_now(),
            error_message=data.get("error_message"),
            chunking=chunking,
        )


def load_manifest(project_path: Path) -> Dict[str, Any]:
    path = manifest_path(project_path)
    if not path.exists():
        return {
            "version": kcfg.MANIFEST_VERSION,
            "documents": [],
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"version": kcfg.MANIFEST_VERSION, "documents": []}
    if not isinstance(data, dict):
        return {"version": kcfg.MANIFEST_VERSION, "documents": []}
    docs = data.get("documents")
    if not isinstance(docs, list):
        docs = []
    return {
        "version": int(data.get("version", kcfg.MANIFEST_VERSION)),
        "documents": docs,
    }


def save_manifest(project_path: Path, data: Dict[str, Any]) -> Path:
    ensure_knowledge_dirs(project_path)
    path = manifest_path(project_path)
    out = {
        "version": kcfg.MANIFEST_VERSION,
        "documents": data.get("documents") or [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return path


def list_documents(project_path: Path) -> List[DocumentRecord]:
    raw = load_manifest(project_path)
    result: List[DocumentRecord] = []
    for item in raw.get("documents") or []:
        if not isinstance(item, dict) or "id" not in item:
            continue
        try:
            result.append(DocumentRecord.from_json_dict(item))
        except (KeyError, TypeError, ValueError):
            continue
    return result


def get_document(project_path: Path, doc_id: str) -> Optional[DocumentRecord]:
    for d in list_documents(project_path):
        if d.id == doc_id:
            return d
    return None


def total_stored_bytes(project_path: Path) -> int:
    return sum(d.byte_size for d in list_documents(project_path))


def upsert_document(project_path: Path, record: DocumentRecord) -> None:
    raw = load_manifest(project_path)
    docs: List[Dict[str, Any]] = []
    replaced = False
    record.updated_at = _utc_now()
    if not record.created_at:
        record.created_at = record.updated_at
    rd = record.to_json_dict()
    for item in raw.get("documents") or []:
        if isinstance(item, dict) and item.get("id") == record.id:
            docs.append(rd)
            replaced = True
        elif isinstance(item, dict):
            docs.append(item)
    if not replaced:
        docs.append(rd)
    save_manifest(project_path, {"documents": docs})


def remove_document(project_path: Path, doc_id: str) -> bool:
    raw = load_manifest(project_path)
    docs = [d for d in (raw.get("documents") or []) if isinstance(d, dict) and d.get("id") != doc_id]
    if len(docs) == len(raw.get("documents") or []):
        return False
    save_manifest(project_path, {"documents": docs})
    return True


def new_doc_id() -> str:
    return str(uuid.uuid4())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_ingestion_mode(text_len: int) -> IngestionMode:
    if text_len <= kcfg.INLINE_CHAR_THRESHOLD:
        return "inline_eligible"
    return "rag_only"
