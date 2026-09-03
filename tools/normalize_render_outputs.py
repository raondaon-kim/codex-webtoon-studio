from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.image_runtime import RuntimeErrorWithEnvelope, normalize_render_output
from webtoon_studio.io_utils import dump_json, load_json, resolve_project_path
from webtoon_studio.validation import discover_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize completed render outputs to their requested canvas size.")
    parser.add_argument("paths", nargs="+", help="Render task files or directories")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    failures = 0
    normalized = 0
    for task_path in discover_json(args.paths):
        task = load_json(task_path)
        if task.get("artifact_type") != "render_task":
            continue
        try:
            output_path = resolve_project_path(root, task["output"]["path"])
            if not output_path.is_file():
                raise FileNotFoundError(output_path)
            result = normalize_render_output(output_path, task["request"]["size"])
            metadata_path = resolve_project_path(root, task["output"]["result_metadata_path"])
            if metadata_path.is_file():
                metadata = load_json(metadata_path)
                metadata["output_normalization"] = result
                dump_json(metadata_path, metadata)
            normalized += int(result["normalized"])
            print(f"PASS {task['task_id']}: {result['output_dimensions']}")
        except (FileNotFoundError, KeyError, RuntimeErrorWithEnvelope, ValueError) as exc:
            failures += 1
            print(f"FAIL {task_path}: {exc}", file=sys.stderr)
    print(f"Normalized {normalized} output(s); failures {failures}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
