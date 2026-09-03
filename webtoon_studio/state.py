from __future__ import annotations

from pathlib import Path
from typing import Any

from .approval import approval_is_current
from .io_utils import load_json


def _approval_status(root: Path, stage: str) -> str:
    path = root / "approvals" / f"{stage}.json"
    if not path.is_file():
        return "unapproved"
    current, _ = approval_is_current(path, root)
    return "approved" if current else "stale-approval"


def project_state(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    territory_profiles = []
    for path in sorted((root / "territory").glob("**/*.json")):
        try:
            if load_json(path).get("artifact_type") == "territory_profile":
                territory_profiles.append(path)
        except Exception:
            continue
    visual_assets = []
    for path in sorted((root / "visual-bible").glob("**/*.json")):
        try:
            if load_json(path).get("artifact_type") == "visual_asset":
                visual_assets.append(path)
        except Exception:
            continue
    bible_files = [root / "story-bible" / "story-bible.json", *territory_profiles, *visual_assets]
    bible_present = (root / "story-bible" / "story-bible.json").is_file()
    episodes = []
    episodes_root = root / "episodes"
    if episodes_root.is_dir():
        for episode in sorted(path for path in episodes_root.iterdir() if path.is_dir()):
            briefs = sorted((episode / "briefs").glob("*.json"))
            tasks = sorted((episode / "render-tasks").glob("*.json"))
            renders = sorted((episode / "art").glob("*.*"))
            episodes.append(
                {
                    "episode_id": episode.name,
                    "script": "present" if (episode / "script.json").is_file() else "missing",
                    "scroll_plan": "present" if (episode / "scroll-plan.json").is_file() else "missing",
                    "brief_count": len(briefs),
                    "render_task_count": len(tasks),
                    "art_count": len(renders),
                    "master": "present" if (episode / "renders" / "episode-master.png").is_file() else "missing",
                    "qc": "present" if (episode / "qc-report.json").is_file() else "missing",
                }
            )
    return {
        "project_root": str(root),
        "bible": "missing" if not bible_present else _approval_status(root, "bible"),
        "bible_artifact_count": sum(path.is_file() for path in bible_files),
        "territory_profile_count": len(territory_profiles),
        "episodes": episodes,
    }
