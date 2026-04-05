"""Paths under `.specify/orchestrator/knowledge/` for a Spec Kit project."""

from pathlib import Path


def knowledge_root(project_path: Path) -> Path:
    return project_path / ".specify" / "orchestrator" / "knowledge"


def files_base(project_path: Path) -> Path:
    return knowledge_root(project_path) / "files"


def doc_files_dir(project_path: Path, doc_id: str) -> Path:
    return files_base(project_path) / doc_id


def manifest_path(project_path: Path) -> Path:
    return knowledge_root(project_path) / "manifest.json"


def parsed_dir(project_path: Path) -> Path:
    return knowledge_root(project_path) / "parsed"


def parsed_text_path(project_path: Path, doc_id: str) -> Path:
    return parsed_dir(project_path) / f"{doc_id}.txt"


def rag_db_path(project_path: Path) -> Path:
    return knowledge_root(project_path) / "rag.sqlite"


def ensure_knowledge_dirs(project_path: Path) -> Path:
    root = knowledge_root(project_path)
    root.mkdir(parents=True, exist_ok=True)
    files_base(project_path).mkdir(parents=True, exist_ok=True)
    parsed_dir(project_path).mkdir(parents=True, exist_ok=True)
    return root
