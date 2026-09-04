from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.io_utils import dump_json, load_json
from webtoon_studio.compiler import load_configs
from webtoon_studio.qc import inspect_episode
from webtoon_studio.validation import validate_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic episode QC report.")
    parser.add_argument("episode_dir")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--platform-profile", default=None)
    args = parser.parse_args()
    studio_root = Path(__file__).resolve().parents[1]
    profile_path = Path(args.platform_profile) if args.platform_profile else studio_root / "config" / "platforms" / "generic-webtoon.json"
    profile = load_json(profile_path)
    project_config, _ = load_configs(args.project_root)
    report = inspect_episode(
        args.episode_dir,
        args.project_root,
        profile,
        master_width=int(project_config["scroll_master"]["width_px"]),
    )
    schema_report = validate_data(report)
    if schema_report.errors:
        for error in schema_report.errors:
            print(f"FAIL report: {error}", file=sys.stderr)
        return 1
    target = dump_json(Path(args.episode_dir) / "qc-report.json", report)
    print(f"{report['status'].upper()} {target}")
    for issue in report["issues"]:
        print(f"  {issue['severity']}: {issue['code']} - {issue['message']}")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
