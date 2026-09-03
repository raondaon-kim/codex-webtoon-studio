from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from .geometry import parse_size
from .io_utils import content_hash, dump_json, load_json, resolve_project_path


class RuntimeErrorWithEnvelope(RuntimeError):
    def __init__(self, message: str, envelope: dict[str, Any] | None = None):
        super().__init__(message)
        self.envelope = envelope


_SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "authorization",
    "cookie",
    "password",
    "secret",
    "account_id",
    "auth_file",
    "chatgpt_user_id",
    "email",
    "expires_at",
    "last_refresh",
}


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if key.lower() in _SENSITIVE_KEYS else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def runtime_command(provider_config: dict[str, Any]) -> list[str]:
    configured = provider_config.get("runtime", {}).get("command", ["gpt-image-2-skill"])
    command = [str(part) for part in configured]
    override = os.environ.get("GPT_IMAGE_2_SKILL_BIN")
    if override:
        command = [override]
    return command


def runtime_available(provider_config: dict[str, Any]) -> bool:
    command = runtime_command(provider_config)
    executable = command[0]
    return Path(executable).exists() or shutil.which(executable) is not None


def runtime_subprocess_command(command: list[str]) -> list[str]:
    """Use the Node entrypoint behind a Windows npm .cmd shim without invoking a shell."""
    if os.name != "nt" or not command:
        return command
    resolved = Path(command[0])
    if not resolved.is_file():
        located = shutil.which(command[0])
        if not located:
            return command
        resolved = Path(located)
    if resolved.suffix.lower() not in {".cmd", ".bat"}:
        return command
    package_entry = resolved.parent / "node_modules" / resolved.stem / "bin" / f"{resolved.stem}.js"
    node = shutil.which("node")
    if package_entry.is_file() and node:
        return [node, str(package_entry), *command[1:]]
    return command


def normalize_render_output(output_path: str | Path, requested_size: str) -> dict[str, Any]:
    """Normalize a provider image only when its aspect ratio matches the requested canvas."""
    path = Path(output_path)
    expected_size = parse_size(requested_size)
    with Image.open(path) as opened:
        actual_size = opened.size
        if actual_size == expected_size:
            return {
                "source_dimensions": list(actual_size),
                "output_dimensions": list(actual_size),
                "normalized": False,
            }
        if actual_size[0] * expected_size[1] != actual_size[1] * expected_size[0]:
            raise RuntimeErrorWithEnvelope(
                f"image runtime returned {actual_size}, which cannot be normalized to requested {expected_size} without distortion"
            )
        normalized = opened.copy().resize(expected_size, Image.Resampling.LANCZOS)

    temporary_path = path.with_name(f"{path.stem}.normalized{path.suffix}")
    try:
        normalized.save(temporary_path, format="PNG")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return {
        "source_dimensions": list(actual_size),
        "output_dimensions": list(expected_size),
        "normalized": True,
    }


def build_task_command(task: dict[str, Any], project_root: str | Path, provider_config: dict[str, Any]) -> list[str]:
    root = Path(project_root).resolve()
    command = runtime_command(provider_config)
    runtime = provider_config.get("runtime", {})
    if runtime.get("json_output", True):
        command.append("--json")
    if runtime.get("json_events", True):
        command.append("--json-events")
    command.extend(["--provider", task["provider"], "images", task["operation"]])
    command.extend(["--prompt", task["prompt"]])
    command.extend(["--out", str(resolve_project_path(root, task["output"]["path"]))])
    model = provider_config.get("model_by_provider", {}).get(task["provider"])
    if model:
        command.extend(["--model", str(model)])
    command.extend(["--size", task["request"]["size"]])
    command.extend(["--quality", task["request"]["quality"]])
    command.extend(["--format", task["request"]["format"]])
    if task["operation"] == "edit":
        for reference in task["references"]:
            command.extend(["--ref-image", str(resolve_project_path(root, reference["path"]))])
    return command


def display_command(command: list[str], redact_prompt: bool = False) -> str:
    shown = list(command)
    if redact_prompt and "--prompt" in shown:
        shown[shown.index("--prompt") + 1] = "<prompt omitted>"
    return subprocess.list2cmdline(shown)


def verify_task_inputs(task: dict[str, Any], project_root: str | Path) -> list[str]:
    root = Path(project_root).resolve()
    errors: list[str] = []
    for field in ("path", "result_metadata_path"):
        value = task.get("output", {}).get(field)
        if value:
            try:
                resolve_project_path(root, value)
            except ValueError as exc:
                errors.append(str(exc))
    try:
        source_path = resolve_project_path(root, task["source_brief"])
    except ValueError as exc:
        return [str(exc)]
    if not source_path.is_file():
        errors.append(f"source artifact missing: {source_path}")
    else:
        actual = content_hash(load_json(source_path))
        if actual != task["source_hash"]:
            errors.append(f"source hash mismatch: {source_path}")
    if task["operation"] == "edit":
        for reference in task["references"]:
            try:
                ref_path = resolve_project_path(root, reference["path"])
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if not ref_path.is_file():
                errors.append(f"reference image missing: {ref_path}")
    return errors


def order_render_tasks(items: list[tuple[Path, dict[str, Any]]]) -> list[tuple[Path, dict[str, Any]]]:
    producer_by_output = {
        task["output"]["path"]: index
        for index, (_, task) in enumerate(items)
    }
    dependencies: dict[int, set[int]] = {}
    for index, (_, task) in enumerate(items):
        dependencies[index] = {
            producer_by_output[reference["path"]]
            for reference in task.get("references", [])
            if reference["path"] in producer_by_output and producer_by_output[reference["path"]] != index
        }
    ordered: list[tuple[Path, dict[str, Any]]] = []
    completed: set[int] = set()
    while len(ordered) < len(items):
        ready = [
            index
            for index in range(len(items))
            if index not in completed and dependencies[index].issubset(completed)
        ]
        if not ready:
            cycle = [items[index][1]["task_id"] for index in range(len(items)) if index not in completed]
            raise ValueError(f"Render task reference cycle: {cycle}")
        ready.sort(key=lambda index: items[index][1]["task_id"])
        for index in ready:
            ordered.append(items[index])
            completed.add(index)
    return ordered


def _parse_envelope(stdout: str) -> dict[str, Any]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeErrorWithEnvelope(f"runtime returned invalid JSON: {exc}") from exc
    if not isinstance(envelope, dict):
        raise RuntimeErrorWithEnvelope("runtime returned a non-object JSON value")
    return envelope


def run_preflight(provider_config: dict[str, Any], command_parts: list[str]) -> dict[str, Any]:
    if not runtime_available(provider_config):
        raise RuntimeErrorWithEnvelope("gpt-image-2-skill runtime is not installed or not on PATH")
    command = runtime_subprocess_command(runtime_command(provider_config) + ["--json", *command_parts])
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    envelope = _parse_envelope(completed.stdout)
    if completed.returncode != 0 or not envelope.get("ok"):
        raise RuntimeErrorWithEnvelope("image runtime preflight failed", envelope)
    return envelope


def execute_task(task: dict[str, Any], project_root: str | Path, provider_config: dict[str, Any]) -> dict[str, Any]:
    input_errors = verify_task_inputs(task, project_root)
    if input_errors:
        raise RuntimeErrorWithEnvelope("render task inputs are stale or missing: " + "; ".join(input_errors))
    if not runtime_available(provider_config):
        raise RuntimeErrorWithEnvelope("gpt-image-2-skill runtime is not installed or not on PATH")
    output_path = resolve_project_path(project_root, task["output"]["path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = runtime_subprocess_command(build_task_command(task, project_root, provider_config))
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    envelope = _parse_envelope(completed.stdout)
    if completed.returncode != 0 or not envelope.get("ok"):
        raise RuntimeErrorWithEnvelope("image generation failed", envelope)
    output_normalization = normalize_render_output(output_path, task["request"]["size"])
    metadata = {
        "schema_version": "1.0",
        "task_id": task["task_id"],
        "source_hash": task["source_hash"],
        "provider": envelope.get("provider_selection", {}).get("resolved", task["provider"]),
        "output_normalization": output_normalization,
        "runtime_result": redact_sensitive(envelope),
    }
    dump_json(resolve_project_path(project_root, task["output"]["result_metadata_path"]), metadata)
    return metadata
