"""Persist and load interview session state for resume across sessions and machines."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 2
INTERVIEW_STATE_FILENAME = "interview_state.json"


def _state_path(project_path: Path) -> Path:
    """Path to the interview state file inside the project."""
    return project_path / ".specify" / "orchestrator" / INTERVIEW_STATE_FILENAME


def save(
    project_path: Path,
    chat_messages: List[Dict[str, str]],
    interview_complete: bool,
    generated_parameters: Optional[Dict[str, Any]],
    *,
    active_document_ids: Optional[List[str]] = None,
    session_focus: Optional[str] = None,
    knowledge_reference_mode: Optional[str] = None,
) -> Path:
    """
    Save interview state to the project directory.

    Optional knowledge fields: pass None to preserve existing values on disk.
    """
    path = _state_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: Dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = {}

    if active_document_ids is not None:
        ads: List[str] = list(active_document_ids)
    else:
        prev = existing.get("active_document_ids")
        ads = [str(x) for x in prev] if isinstance(prev, list) else []

    if session_focus is not None:
        sf = session_focus
    else:
        p = existing.get("session_focus", "")
        sf = p if isinstance(p, str) else ""

    if knowledge_reference_mode is not None:
        krm = knowledge_reference_mode
    else:
        p = existing.get("knowledge_reference_mode", "auto")
        krm = p if p in ("auto", "prefer_inline", "rag_only") else "auto"

    payload = {
        "version": SCHEMA_VERSION,
        "chat_messages": chat_messages,
        "interview_complete": interview_complete,
        "generated_parameters": generated_parameters,
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
        "knowledge_schema_version": 1,
        "active_document_ids": ads,
        "session_focus": sf,
        "knowledge_reference_mode": krm,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path


def load(project_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load interview state from the project directory, if present and valid.
    """
    path = _state_path(project_path)
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if not isinstance(data, dict):
        return None

    version = data.get("version")
    if version is None or version > SCHEMA_VERSION:
        return None

    messages = data.get("chat_messages")
    if not isinstance(messages, list):
        return None

    ads = data.get("active_document_ids")
    if not isinstance(ads, list):
        ads = []

    sf = data.get("session_focus", "")
    if not isinstance(sf, str):
        sf = ""

    krm = data.get("knowledge_reference_mode", "auto")
    if krm not in ("auto", "prefer_inline", "rag_only"):
        krm = "auto"

    return {
        "version": version,
        "chat_messages": messages,
        "interview_complete": bool(data.get("interview_complete", False)),
        "generated_parameters": data.get("generated_parameters"),
        "saved_at": data.get("saved_at"),
        "knowledge_schema_version": data.get("knowledge_schema_version", 1),
        "active_document_ids": [str(x) for x in ads],
        "session_focus": sf,
        "knowledge_reference_mode": krm,
    }


def exists(project_path: Path) -> bool:
    """Return True if a valid interview state file exists for this project."""
    return load(project_path) is not None


def has_resumable_session(project_path: Path) -> bool:
    """
    Return True if there is saved state with at least one message (worth resuming).
    """
    state = load(project_path)
    if state is None:
        return False
    messages = state.get("chat_messages") or []
    return len(messages) > 0 or state.get("interview_complete") is True
