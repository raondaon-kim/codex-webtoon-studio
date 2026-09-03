from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .io_utils import content_hash, dump_json, load_json, relative_posix


def artifact_fingerprint(paths: Iterable[str | Path], project_root: str | Path) -> tuple[str, list[dict[str, str]]]:
    root = Path(project_root).resolve()
    entries = []
    for raw in sorted((Path(path).resolve() for path in paths), key=lambda item: item.as_posix()):
        entries.append({"path": relative_posix(raw, root), "hash": content_hash(load_json(raw))})
    return content_hash(entries), entries


def approve(stage: str, paths: Iterable[str | Path], project_root: str | Path, note: str = "") -> Path:
    fingerprint, entries = artifact_fingerprint(paths, project_root)
    approval = {
        "schema_version": "1.0",
        "stage": stage,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": fingerprint,
        "artifacts": entries,
        "note": note,
    }
    return dump_json(Path(project_root) / "approvals" / f"{stage}.json", approval)


def approval_is_current(approval_path: str | Path, project_root: str | Path) -> tuple[bool, str]:
    approval = load_json(approval_path)
    paths = [Path(project_root) / item["path"] for item in approval.get("artifacts", [])]
    if any(not path.is_file() for path in paths):
        return False, "one or more approved artifacts are missing"
    fingerprint, _ = artifact_fingerprint(paths, project_root)
    if fingerprint != approval.get("fingerprint"):
        return False, "approved artifacts have changed"
    return True, "approval matches current artifact contents"
