from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.compiler import load_configs
from webtoon_studio.image_runtime import (
    RuntimeErrorWithEnvelope,
    build_task_command,
    display_command,
    execute_task,
    order_render_tasks,
    redact_sensitive,
    run_preflight,
    verify_task_inputs,
)
from webtoon_studio.io_utils import load_json
from webtoon_studio.validation import discover_json, validate_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or execute gpt-image-2-skill render tasks.")
    parser.add_argument("paths", nargs="+", help="Render task files or directories")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--execute", action="store_true", help="Perform external image calls; may incur cost")
    parser.add_argument("--show-prompt", action="store_true", help="Include full prompts in dry-run output")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    _, provider_config = load_configs(root)
    tasks = []
    for path in discover_json(args.paths):
        task = load_json(path)
        if task.get("artifact_type") == "render_task":
            tasks.append((path, task))
    if not tasks:
        print("No render tasks found.", file=sys.stderr)
        return 2
    try:
        tasks = order_render_tasks(tasks)
    except ValueError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for path, task in tasks:
        report = validate_data(task, path)
        if report.errors:
            print(f"FAIL {path}: {'; '.join(report.errors)}", file=sys.stderr)
            return 1
    if not args.execute:
        for path, task in tasks:
            command = build_task_command(task, root, provider_config)
            print(f"DRY-RUN {path}")
            print("  " + display_command(command, redact_prompt=not args.show_prompt))
            for warning in verify_task_inputs(task, root):
                print(f"  preflight warning: {warning}")
        print("No external image call was made. Add --execute only after approving these tasks.")
        return 0
    if provider_config.get("allow_automatic_fallback"):
        print("Refusing execution: automatic provider fallback must remain disabled for an auditable run.", file=sys.stderr)
        return 1
    try:
        provider = tasks[0][1]["provider"]
        doctor = run_preflight(provider_config, ["--provider", provider, "doctor"])
        auth = run_preflight(provider_config, ["auth", "inspect"])
        print(json.dumps(redact_sensitive({"doctor": doctor, "auth": auth}), ensure_ascii=False, indent=2))
        for path, task in tasks:
            print(f"EXECUTE {path}")
            result = execute_task(task, root, provider_config)
            print(json.dumps(redact_sensitive(result), ensure_ascii=False, indent=2))
    except RuntimeErrorWithEnvelope as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        if exc.envelope:
            print(json.dumps(redact_sensitive(exc.envelope), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
