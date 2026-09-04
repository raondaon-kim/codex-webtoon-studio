from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from .balloon_assets import BalloonAssetError, selected_balloon_asset
from .compose import ordered_shot_ids
from .geometry import contains, parse_size
from .io_utils import content_hash, load_json, resolve_project_path
from .validation import validate_file


def _issue(severity: str, code: str, message: str, path: Path | None = None, shot_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if path is not None:
        result["path"] = str(path)
    if shot_id is not None:
        result["shot_id"] = shot_id
    return result


def inspect_episode(episode_dir: str | Path, project_root: str | Path, platform_profile: dict[str, Any]) -> dict[str, Any]:
    episode = Path(episode_dir).resolve()
    root = Path(project_root).resolve()
    issues: list[dict[str, Any]] = []
    checks = {
        "schema": True,
        "files": True,
        "dimensions": True,
        "continuity": True,
        "lettering": True,
        "publish_slices": True,
    }
    canonical_paths = [episode / "script.json", episode / "scroll-plan.json"]
    canonical_paths.extend(sorted((episode / "briefs").glob("*.json")))
    canonical_paths.extend(sorted((episode / "render-tasks").glob("*.json")))
    for path in canonical_paths:
        if not path.is_file():
            checks["files"] = False
            issues.append(_issue("error", "missing_artifact", f"Required artifact is missing: {path.name}", path))
            continue
        report = validate_file(path)
        if report.errors:
            checks["schema"] = False
            for message in report.errors:
                issues.append(_issue("error", "schema_invalid", message, path))
    scroll_path = episode / "scroll-plan.json"
    if not scroll_path.is_file():
        shot_ids: list[str] = []
        scroll_plan: dict[str, Any] = {"sequences": []}
    else:
        scroll_plan = load_json(scroll_path)
        shot_ids = ordered_shot_ids(scroll_plan)
    script_path = episode / "script.json"
    script = load_json(script_path) if script_path.is_file() else {"beats": []}
    beat_ids = {beat["id"] for beat in script.get("beats", [])}
    sequence_by_id = {sequence["id"]: sequence for sequence in scroll_plan.get("sequences", [])}
    planned_beats = {beat for sequence in sequence_by_id.values() for beat in sequence["beat_refs"]}
    unknown_beats = planned_beats - beat_ids
    missing_beats = beat_ids - planned_beats
    if unknown_beats:
        checks["continuity"] = False
        issues.append(_issue("error", "unknown_beat_ref", f"Scroll plan references unknown beats: {sorted(unknown_beats)}", scroll_path))
    if missing_beats:
        checks["continuity"] = False
        issues.append(_issue("error", "unplanned_beats", f"Script beats missing from scroll plan: {sorted(missing_beats)}", scroll_path))
    if len(shot_ids) != len(set(shot_ids)):
        checks["continuity"] = False
        issues.append(_issue("error", "duplicate_shot", "A shot ID appears more than once in the scroll plan", scroll_path))
    briefs = {
        value["shot_id"]: (path, value)
        for path in sorted((episode / "briefs").glob("*.json"))
        for value in [load_json(path)]
        if value.get("artifact_type") == "director_brief"
    }
    scripted_text = Counter(
        item["content"]
        for beat in script.get("beats", [])
        for item in beat.get("text", [])
    )
    planned_text = Counter(
        item["content"]
        for _, brief in briefs.values()
        for item in brief.get("text", {}).get("items", [])
    )
    for content, count in (scripted_text - planned_text).items():
        checks["lettering"] = False
        issues.append(
            _issue(
                "error",
                "script_text_missing",
                f"Script text is not placed in a director brief ({count} occurrence(s)): {content}",
                script_path,
            )
        )
    for content, count in (planned_text - scripted_text).items():
        checks["lettering"] = False
        issues.append(
            _issue(
                "error",
                "brief_text_unsourced",
                f"Director brief text is not present in the script ({count} occurrence(s)): {content}",
                episode / "briefs",
            )
        )
    tasks = {
        value["task_id"].split("-shot-")[-1]: (path, value)
        for path in sorted((episode / "render-tasks").glob("*.json"))
        for value in [load_json(path)]
        if value.get("artifact_type") == "render_task" and "-shot-" in value.get("task_id", "")
    }
    bridge_sequence_by_shot: dict[str, str] = {}
    expected_previous_by_shot: dict[str, str | None] = {}
    previous_primary_id: str | None = None
    for sequence in sequence_by_id.values():
        bridges_by_after: dict[str, list[str]] = {}
        for bridge in sequence.get("bridge_inserts", []):
            bridge_shot_id = bridge["shot_id"]
            after_shot_id = bridge["after_shot_id"]
            if bridge_shot_id in sequence["shot_ids"] or after_shot_id not in sequence["shot_ids"]:
                checks["continuity"] = False
                issues.append(
                    _issue(
                        "error",
                        "bridge_sequence_link",
                        "Bridge insert must be an extra shot placed after one of its sequence shot_ids",
                        scroll_path,
                        bridge_shot_id,
                    )
                )
                continue
            bridge_sequence_by_shot[bridge_shot_id] = sequence["id"]
            bridges_by_after.setdefault(after_shot_id, []).append(bridge_shot_id)
            bridge_entry = briefs.get(bridge_shot_id)
            if not bridge_entry or not bridge_entry[1].get("bridge"):
                checks["continuity"] = False
                issues.append(
                    _issue(
                        "error",
                        "bridge_brief_missing",
                        "A bridge insert requires a director brief with a bridge composite definition",
                        scroll_path,
                        bridge_shot_id,
                    )
                )
        for shot_id in sequence["shot_ids"]:
            expected_previous_by_shot[shot_id] = previous_primary_id
            for bridge_shot_id in bridges_by_after.get(shot_id, []):
                expected_previous_by_shot[bridge_shot_id] = shot_id
            previous_primary_id = shot_id
    for shot_id in shot_ids:
        brief_entry = briefs.get(shot_id)
        if not brief_entry:
            checks["files"] = False
            issues.append(_issue("error", "missing_brief", "No director brief for planned shot", shot_id=shot_id))
            continue
        brief_path, brief = brief_entry
        sequence = sequence_by_id.get(brief["sequence_id"])
        if not sequence or (
            shot_id not in sequence["shot_ids"] and bridge_sequence_by_shot.get(shot_id) != brief["sequence_id"]
        ):
            checks["continuity"] = False
            issues.append(_issue("error", "sequence_link", "Brief sequence_id does not own this shot", brief_path, shot_id))
        unknown_brief_beats = set(brief["source"]["beat_refs"]) - beat_ids
        if unknown_brief_beats:
            checks["continuity"] = False
            issues.append(
                _issue("error", "brief_unknown_beat", f"Brief references unknown beats: {sorted(unknown_brief_beats)}", brief_path, shot_id)
            )
        text_for_brief_beats = {
            item["content"]
            for beat in script.get("beats", [])
            if beat["id"] in brief["source"]["beat_refs"]
            for item in beat.get("text", [])
        }
        for item in brief["text"]["items"]:
            if item["content"] not in text_for_brief_beats:
                checks["lettering"] = False
                issues.append(
                    _issue(
                        "error",
                        "lettering_beat_link",
                        "Text must be sourced from one of the brief's beat_refs",
                        brief_path,
                        shot_id,
                    )
                )
            try:
                selected_asset = selected_balloon_asset(item)
            except BalloonAssetError as error:
                checks["lettering"] = False
                issues.append(_issue("error", "lettering_asset_invalid", str(error), brief_path, shot_id))
            else:
                if selected_asset and selected_asset["tail_behavior"] == "baked":
                    issues.append(
                        _issue(
                            "info",
                            "lettering_fixed_tail_review",
                            "Selected SVG balloon has a fixed tail; verify that its baked direction reads correctly.",
                            brief_path,
                            shot_id,
                        )
                    )
        declared_previous = brief["continuity"]["previous_shot_id"]
        expected_previous = expected_previous_by_shot.get(shot_id)
        if declared_previous != expected_previous:
            checks["continuity"] = False
            issues.append(
                _issue(
                    "error",
                    "continuity_chain",
                    f"previous_shot_id is {declared_previous!r}; expected {expected_previous!r}",
                    brief_path,
                    shot_id,
                )
            )
        if brief["text"]["mode"] == "deterministic_lettering":
            regions = brief["text"]["reserved_regions"]
            for item in brief["text"]["items"]:
                if not any(contains(region, item["anchor_norm"]) for region in regions):
                    checks["lettering"] = False
                    issues.append(
                        _issue("warning", "lettering_outside_reserve", "Text anchor is outside all reserved regions", brief_path, shot_id)
                    )
        task_key = shot_id.removeprefix("shot-")
        task_entry = tasks.get(task_key)
        if not task_entry:
            checks["files"] = False
            issues.append(_issue("error", "missing_render_task", "No render task for shot", shot_id=shot_id))
            continue
        task_path, task = task_entry
        if task["source_hash"] != content_hash(brief):
            checks["files"] = False
            issues.append(_issue("error", "stale_render_task", "Render task source hash does not match brief", task_path, shot_id))
        try:
            art_path = resolve_project_path(root, task["output"]["path"])
        except ValueError as exc:
            checks["files"] = False
            issues.append(_issue("error", "unsafe_art_path", str(exc), task_path, shot_id))
            continue
        if not art_path.is_file():
            checks["files"] = False
            issues.append(_issue("error", "missing_art", "Rendered image is missing", art_path, shot_id))
            continue
        try:
            with Image.open(art_path) as image:
                actual_size = image.size
            expected_size = parse_size(task["request"]["size"])
            if actual_size != expected_size:
                checks["dimensions"] = False
                issues.append(
                    _issue("error", "image_dimensions", f"Image is {actual_size}, expected {expected_size}", art_path, shot_id)
                )
        except Exception as exc:
            checks["files"] = False
            issues.append(_issue("error", "image_unreadable", str(exc), art_path, shot_id))
    extra_briefs = set(briefs) - set(shot_ids)
    if extra_briefs:
        checks["continuity"] = False
        issues.append(_issue("warning", "unplanned_briefs", f"Briefs are not present in the scroll plan: {sorted(extra_briefs)}", episode / "briefs"))
    master_path = episode / "renders" / "episode-master.png"
    slices = sorted((episode / "publish").glob("slice-*.*"))
    if not master_path.is_file():
        checks["publish_slices"] = False
        issues.append(_issue("warning", "master_missing", "Episode master has not been composed", master_path))
    if not slices:
        checks["publish_slices"] = False
        issues.append(_issue("warning", "slices_missing", "Publish slices have not been exported", episode / "publish"))
    else:
        for path in slices:
            try:
                with Image.open(path) as image:
                    if image.width != int(platform_profile["width_px"]) or image.height > int(platform_profile["slice_height_px"]):
                        checks["publish_slices"] = False
                        issues.append(_issue("error", "slice_dimensions", f"Invalid publish slice dimensions: {image.size}", path))
            except Exception as exc:
                checks["publish_slices"] = False
                issues.append(_issue("error", "slice_unreadable", str(exc), path))
    issues.append(
        _issue(
            "info",
            "human_visual_review_required",
            "Review identity, hands, background geography, screen direction, emotional clarity, and reading order in the assembled scroll.",
        )
    )
    if any(item["severity"] == "error" for item in issues):
        status = "fail"
    elif any(item["severity"] == "warning" for item in issues):
        status = "warn"
    else:
        status = "pass"
    episode_id = episode.name
    if scroll_path.is_file():
        episode_id = load_json(scroll_path).get("episode_id", episode_id)
    return {
        "schema_version": "1.0",
        "artifact_type": "qc_report",
        "episode_id": episode_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "issues": issues,
    }
