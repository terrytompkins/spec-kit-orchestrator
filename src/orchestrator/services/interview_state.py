"""Persist and load interview session state for resume across sessions and machines."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

SCHEMA_VERSION = 1
INTERVIEW_STATE_FILENAME = "interview_state.json"


def _state_path(project_path: Path) -> Path:
    """Path to the interview state file inside the project."""
    return project_path / ".specify" / "orchestrator" / INTERVIEW_STATE_FILENAME


def save(
    project_path: Path,
    chat_messages: List[Dict[str, str]],
    interview_complete: bool,
    generated_parameters: Optional[Dict[str, Any]],
) -> Path:
    """
    Save interview state to the project directory.

    State is written to `.specify/orchestrator/interview_state.json` so it can
    be committed to the project repo and used to resume on another computer.

    Args:
        project_path: Root path of the Spec Kit project.
        chat_messages: List of {"role": "user"|"assistant", "content": "..."}.
        interview_complete: True if the interview has finished and parameters were generated.
        generated_parameters: Phase parameters dict, or None if not complete.

    Returns:
        Path to the written state file.
    """
    path = _state_path(project_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": SCHEMA_VERSION,
        "chat_messages": chat_messages,
        "interview_complete": interview_complete,
        "generated_parameters": generated_parameters,
        "saved_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return path


def load(project_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load interview state from the project directory, if present and valid.

    Args:
        project_path: Root path of the Spec Kit project.

    Returns:
        State dict with keys: version, chat_messages, interview_complete,
        generated_parameters, saved_at. None if file is missing or invalid.
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

    # Normalize for older or future schema
    return {
        "version": version,
        "chat_messages": messages,
        "interview_complete": bool(data.get("interview_complete", False)),
        "generated_parameters": data.get("generated_parameters"),
        "saved_at": data.get("saved_at"),
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
