from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker

from .geometry import parse_size, validate_generation_size, validate_normalized_box
from .io_utils import load_json


STUDIO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_BY_ARTIFACT = {
    "story_bible": "story-bible.schema.json",
    "visual_asset": "visual-asset.schema.json",
    "episode_script": "episode-script.schema.json",
    "scroll_plan": "scroll-plan.schema.json",
    "director_brief": "director-brief.schema.json",
    "render_task": "render-task.schema.json",
    "qc_report": "qc-report.schema.json",
}


@dataclass
class ValidationReport:
    path: Path
    artifact_type: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def _json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def _custom_checks(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    kind = data.get("artifact_type")
    if kind == "director_brief":
        canvas = data.get("canvas", {})
        if "width_px" in canvas and "height_px" in canvas:
            errors.extend(
                f"$.canvas: {message}"
                for message in validate_generation_size(canvas["width_px"], canvas["height_px"])
            )
        for index, subject in enumerate(data.get("subjects", [])):
            errors.extend(
                validate_normalized_box(subject.get("bbox_norm", {}), f"$.subjects[{index}].bbox_norm")
            )
        background = data.get("background", {})
        errors.extend(
            validate_normalized_box(background.get("source_crop_norm", {}), "$.background.source_crop_norm")
        )
        text = data.get("text", {})
        for index, item in enumerate(text.get("items", [])):
            errors.extend(
                validate_normalized_box(item.get("anchor_norm", {}), f"$.text.items[{index}].anchor_norm")
            )
        for index, region in enumerate(text.get("reserved_regions", [])):
            errors.extend(validate_normalized_box(region, f"$.text.reserved_regions[{index}]"))
        reference_count = sum(len(subject.get("references", [])) for subject in data.get("subjects", []))
        reference_count += len(background.get("references", []))
        if reference_count > 16:
            errors.append("$: combined references exceed the runtime limit of 16")
        if text.get("mode") == "deterministic_lettering" and not text.get("reserved_regions") and text.get("items"):
            warnings.append("$.text: deterministic lettering has text items but no reserved regions")
    elif kind == "render_task":
        size = data.get("request", {}).get("size")
        if size:
            try:
                width, height = parse_size(size)
                errors.extend(f"$.request.size: {message}" for message in validate_generation_size(width, height))
            except ValueError as exc:
                errors.append(f"$.request.size: {exc}")
        references = data.get("references", [])
        if data.get("operation") == "edit" and not references:
            errors.append("$.references: edit operation requires at least one reference")
        if data.get("operation") == "generate" and references:
            warnings.append("$.references: generate operation ignores declared references")
    elif kind == "visual_asset":
        size = data.get("output", {}).get("size")
        if size:
            try:
                width, height = parse_size(size)
                errors.extend(f"$.output.size: {message}" for message in validate_generation_size(width, height))
            except ValueError as exc:
                errors.append(f"$.output.size: {exc}")
    return errors, warnings


def validate_data(data: dict[str, Any], path: str | Path = "<memory>") -> ValidationReport:
    report = ValidationReport(path=Path(path), artifact_type=data.get("artifact_type"))
    if not report.artifact_type:
        report.skipped = True
        report.warnings.append("no artifact_type; treated as configuration, not a canonical artifact")
        return report
    schema_name = SCHEMA_BY_ARTIFACT.get(report.artifact_type)
    if not schema_name:
        report.errors.append(f"unsupported artifact_type: {report.artifact_type}")
        return report
    schema = load_json(STUDIO_ROOT / "schemas" / "v1" / schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path)):
        report.errors.append(f"{_json_path(error.absolute_path)}: {error.message}")
    custom_errors, custom_warnings = _custom_checks(data)
    report.errors.extend(custom_errors)
    report.warnings.extend(custom_warnings)
    return report


def validate_file(path: str | Path) -> ValidationReport:
    source = Path(path)
    try:
        data = load_json(source)
    except Exception as exc:
        return ValidationReport(path=source, errors=[f"could not read JSON: {exc}"])
    return validate_data(data, source)


def discover_json(paths: Iterable[str | Path]) -> list[Path]:
    discovered: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            discovered.extend(sorted(path.rglob("*.json")))
        else:
            discovered.append(path)
    return sorted(dict.fromkeys(item.resolve() for item in discovered))
