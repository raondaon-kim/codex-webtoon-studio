from __future__ import annotations

from pathlib import Path
from typing import Any

from .geometry import box_as_percent
from .io_utils import content_hash, load_json, relative_posix, resolve_project_path
from .validation import validate_data


STUDIO_ROOT = Path(__file__).resolve().parents[1]


def _load_prompt_template(name: str) -> dict[str, Any]:
    return load_json(STUDIO_ROOT / "prompt-templates" / name)


def _unique_references(brief: dict[str, Any]) -> list[dict[str, Any]]:
    raw: list[dict[str, Any]] = []
    for subject in brief.get("subjects", []):
        raw.extend(subject.get("references", []))
    raw.extend(brief.get("background", {}).get("references", []))
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for ref in raw:
        key = (ref["path"], ref["role"])
        if key in seen:
            continue
        seen.add(key)
        result.append({"path": ref["path"], "role": ref["role"], "index": len(result) + 1})
    if len(result) > 16:
        raise ValueError("Combined reference images exceed 16")
    return result


def _reference_lines(references: list[dict[str, Any]]) -> list[str]:
    if not references:
        return ["References: none; establish an original design from the declared visual canon."]
    lines = ["References, in authoritative input order:"]
    for ref in references:
        lines.append(f"- Image {ref['index']}: {ref['role']}; use only for that declared role.")
    return lines


def _bridge_lines(bridge: dict[str, Any] | None) -> list[str]:
    if bridge is None:
        return []
    panel_count = bridge["panel_count"]
    panel_beats = "; ".join(
        f"panel {index + 1}: {description}" for index, description in enumerate(bridge["panel_beats"])
    )
    return [
        (
            f"Bridge composition: this single generated image contains exactly {panel_count} connected full-width mini-panels "
            "stacked vertically, separated by clean gutters. Read them top-to-bottom as one continuous transition, not as "
            "duplicate variants of the same pose."
        ),
        f"Bridge function: {bridge['function']}. Ordered micro-beats: {panel_beats}.",
    ]


def _brief_prompt(brief: dict[str, Any], references: list[dict[str, Any]], project: dict[str, Any]) -> str:
    template = _load_prompt_template("webtoon-shot.json")
    camera = brief["camera"]
    canvas = brief["canvas"]
    background = brief["background"]
    art = brief["art_direction"]
    continuity = brief["continuity"]
    lines = [
        f"Create one finished original vertical-scroll webtoon art shot. Template: {template['template_id']}.",
        f"Purpose: {brief['source']['dramatic_purpose']}",
        f"Canvas: {canvas['width_px']}x{canvas['height_px']} pixels; keep a {canvas['safe_margin_norm']:.0%} safe margin.",
        (
            "Composition and camera: "
            f"{camera['shot_size']} shot, {camera['angle']} angle, {camera['lens_feel']} lens feel, "
            f"camera position {camera['position']}, movement {camera['movement']}, focus on {camera['focus']}. "
            f"{art['composition']}"
        ),
        *_bridge_lines(brief.get("bridge")),
        "Subjects:",
    ]
    for subject in brief["subjects"]:
        lines.append(
            f"- {subject['character_id']} at {box_as_percent(subject['bbox_norm'])}, {subject['depth']}; "
            f"pose {subject['pose']}; expression {subject['expression']}; gaze {subject['gaze']}; "
            f"action {subject['action']}. Preserve: {', '.join(subject['identity_invariants'])}."
        )
    lines.extend(
        [
            (
                f"Background: location {background['location_id']}; {background['description']}. "
                f"Use source crop {box_as_percent(background['source_crop_norm'])}; perspective {background['perspective']}; "
                f"depth layers: {', '.join(background['depth_layers'])}; lighting {background['lighting']}."
            ),
            f"Visual treatment: line {art['line']}; color {art['color']}; rendering {art['rendering']}; mood {art['mood']}.",
            *_reference_lines(references),
            (
                f"Continuity: screen direction {continuity['screen_direction']}; "
                f"state entering: {', '.join(continuity['state_in']) or 'none'}; "
                f"state leaving: {', '.join(continuity['state_out']) or 'none'}."
            ),
        ]
    )
    text = brief["text"]
    if text["mode"] == "deterministic_lettering":
        reserved = "; ".join(box_as_percent(box) for box in text["reserved_regions"]) or "none"
        lines.append(
            "Lettering: leave visually quiet negative space in these regions: "
            f"{reserved}. Generate no speech balloons, captions, or readable text."
        )
    elif text["mode"] == "none":
        lines.append("Lettering: generate no speech balloons, captions, or readable text.")
    else:
        embedded = "; ".join(item["content"] for item in text["items"])
        lines.append(f"Embedded text requested: {embedded}")
    avoid = list(project.get("art_generation", {}).get("negative_defaults", [])) + list(art["must_avoid"])
    lines.append(f"Avoid: {', '.join(dict.fromkeys(avoid))}.")
    return "\n".join(lines)


def compile_brief(
    brief: dict[str, Any],
    source_path: str | Path,
    project_root: str | Path,
    project_config: dict[str, Any],
    provider_config: dict[str, Any],
) -> dict[str, Any]:
    try:
        Path(source_path).resolve().relative_to(Path(project_root).resolve())
    except ValueError as exc:
        raise ValueError("Director brief must be inside the project root") from exc
    report = validate_data(brief, source_path)
    if report.errors:
        raise ValueError("Invalid director brief:\n" + "\n".join(report.errors))
    references = _unique_references(brief)
    output = brief["output"]
    resolve_project_path(project_root, output["path"])
    for reference in references:
        resolve_project_path(project_root, reference["path"])
    task = {
        "schema_version": "1.0",
        "artifact_type": "render_task",
        "task_id": f"{brief['episode_id']}-{brief['shot_id']}",
        "source_brief": relative_posix(source_path, project_root),
        "source_hash": content_hash(brief),
        "template_id": _load_prompt_template("webtoon-shot.json")["template_id"],
        "provider": provider_config.get("provider", "codex"),
        "operation": "edit" if references else "generate",
        "prompt": _brief_prompt(brief, references, project_config),
        "references": references,
        "request": {
            "size": f"{brief['canvas']['width_px']}x{brief['canvas']['height_px']}",
            "quality": output["quality"],
            "format": output["format"],
        },
        "output": {
            "path": output["path"],
            "result_metadata_path": str(Path(output["path"]).with_suffix(".result.json")).replace("\\", "/"),
        },
    }
    task_report = validate_data(task)
    if task_report.errors:
        raise ValueError("Compiled invalid render task:\n" + "\n".join(task_report.errors))
    return task


def _visual_template(asset: dict[str, Any]) -> dict[str, Any]:
    if asset["asset_kind"] == "background":
        return _load_prompt_template("background-reference-sheet.json")
    if asset["asset_kind"] == "prop":
        return _load_prompt_template("prop-reference-sheet.json")
    if asset["references"]:
        return _load_prompt_template("character-reference-edit.json")
    return _load_prompt_template("character-reference-sheet.json")


def _visual_prompt(asset: dict[str, Any]) -> str:
    plan = asset["sheet_plan"]
    lock = asset["identity_or_space_lock"]
    template = _visual_template(asset)
    references = [
        {"path": ref["path"], "role": ref["role"], "index": index + 1}
        for index, ref in enumerate(asset["references"])
    ]
    kind = asset["asset_kind"]
    opening = {
        "character": "Create a clean canonical reference sheet for one original webtoon character.",
        "background": "Create a reusable spatial reference sheet for one original webtoon location.",
        "prop": "Create a clean canonical design sheet for one original webtoon prop.",
    }[kind]
    lines = [
        opening,
        f"Template: {template['template_id']}. {template['purpose']}",
        f"Asset ID: {asset['asset_id']}.",
        f"Layout: {plan['layout']}.",
        f"Required views: {', '.join(plan['views'])}.",
        f"Sheet background: {plan['background']}. Labels: {plan['labels']}.",
        f"Preserve exactly: {', '.join(lock['must_preserve'])}.",
        *_reference_lines(references),
    ]
    if references:
        lines.append("Requested change: produce only the declared new views while retaining the authoritative identity or spatial layout from the references.")
    if template.get("invariants"):
        lines.append(f"Standard sheet invariants: {', '.join(template['invariants'])}.")
    if template.get("instructions"):
        lines.append(f"Edit discipline: {' '.join(template['instructions'])}")
    if plan.get("palette_swatches"):
        lines.append(f"Palette swatches: {', '.join(plan['palette_swatches'])}.")
    avoid = list(lock["must_avoid"]) + list(template.get("avoid", [])) + ["readable text", "watermark", "signature"]
    lines.append(f"Avoid: {', '.join(dict.fromkeys(avoid))}.")
    return "\n".join(lines)


def compile_visual_asset(
    asset: dict[str, Any],
    source_path: str | Path,
    project_root: str | Path,
    provider_config: dict[str, Any],
) -> dict[str, Any]:
    try:
        Path(source_path).resolve().relative_to(Path(project_root).resolve())
    except ValueError as exc:
        raise ValueError("Visual asset must be inside the project root") from exc
    report = validate_data(asset, source_path)
    if report.errors:
        raise ValueError("Invalid visual asset:\n" + "\n".join(report.errors))
    references = [
        {"path": ref["path"], "role": ref["role"], "index": index + 1}
        for index, ref in enumerate(asset["references"])
    ]
    template = _visual_template(asset)
    resolve_project_path(project_root, asset["output"]["path"])
    for reference in references:
        resolve_project_path(project_root, reference["path"])
    task = {
        "schema_version": "1.0",
        "artifact_type": "render_task",
        "task_id": f"visual-{asset['asset_id']}",
        "source_brief": relative_posix(source_path, project_root),
        "source_hash": content_hash(asset),
        "template_id": template["template_id"],
        "provider": provider_config.get("provider", "codex"),
        "operation": "edit" if references else "generate",
        "prompt": _visual_prompt(asset),
        "references": references,
        "request": {
            "size": asset["output"]["size"],
            "quality": provider_config.get("defaults", {}).get("quality", "high"),
            "format": Path(asset["output"]["path"]).suffix.lower().lstrip(".") or "png",
        },
        "output": {
            "path": asset["output"]["path"],
            "result_metadata_path": str(Path(asset["output"]["path"]).with_suffix(".result.json")).replace("\\", "/"),
        },
    }
    task_report = validate_data(task)
    if task_report.errors:
        raise ValueError("Compiled invalid render task:\n" + "\n".join(task_report.errors))
    return task


def load_configs(project_root: str | Path, studio_root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(project_root)
    studio = Path(studio_root) if studio_root else Path(__file__).resolve().parents[1]
    project_path = root / "config" / "project.json"
    if not project_path.exists():
        project_path = studio / "config" / "project.json"
    return load_json(project_path), load_json(studio / "config" / "image-provider.json")
