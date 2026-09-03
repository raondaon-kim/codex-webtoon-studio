from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.validation import discover_json, validate_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical Webtoon Studio JSON artifacts.")
    parser.add_argument("paths", nargs="+", help="JSON files or directories")
    parser.add_argument("--strict-config", action="store_true", help="Fail on JSON files without artifact_type")
    args = parser.parse_args()
    files = discover_json(args.paths)
    if not files:
        print("No JSON files found.", file=sys.stderr)
        return 2
    failed = 0
    validated = 0
    skipped = 0
    for path in files:
        report = validate_file(path)
        if report.skipped:
            skipped += 1
            label = "FAIL" if args.strict_config else "SKIP"
            print(f"{label} {path}: {report.warnings[0]}")
            if args.strict_config:
                failed += 1
            continue
        validated += 1
        print(f"{'PASS' if report.ok else 'FAIL'} {path} ({report.artifact_type})")
        for warning in report.warnings:
            print(f"  warning: {warning}")
        for error in report.errors:
            print(f"  error: {error}")
        failed += int(not report.ok)
    print(f"Validated {validated}; skipped {skipped}; failed {failed}.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
