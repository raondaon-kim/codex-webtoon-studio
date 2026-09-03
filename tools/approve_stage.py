from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.approval import approve
from webtoon_studio.validation import discover_json, validate_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Record content-hash approval for canonical JSON artifacts.")
    parser.add_argument("stage")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    paths = discover_json(args.paths)
    if not paths:
        print("No JSON artifacts found.", file=sys.stderr)
        return 2
    for path in paths:
        report = validate_file(path)
        if report.skipped or report.errors:
            print(f"Cannot approve invalid or non-canonical artifact: {path}", file=sys.stderr)
            for error in report.errors:
                print(f"  {error}", file=sys.stderr)
            return 1
    target = approve(args.stage, paths, args.project_root, args.note)
    print(f"APPROVED {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
