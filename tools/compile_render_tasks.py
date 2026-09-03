from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.compiler import compile_brief, load_configs
from webtoon_studio.io_utils import dump_json, load_json
from webtoon_studio.validation import discover_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile director briefs into deterministic image render tasks.")
    parser.add_argument("paths", nargs="+", help="Director brief files or directories")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--check", action="store_true", help="Do not write; fail if compiled tasks differ or are missing")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    project_config, provider_config = load_configs(root)
    failed = 0
    compiled = 0
    for source in discover_json(args.paths):
        brief = load_json(source)
        if brief.get("artifact_type") != "director_brief":
            continue
        try:
            task = compile_brief(brief, source, root, project_config, provider_config)
            target = source.parent.parent / "render-tasks" / f"{brief['shot_id']}.json"
            if args.check:
                if not target.is_file() or load_json(target) != task:
                    print(f"STALE {target}")
                    failed += 1
                else:
                    print(f"PASS  {target}")
            else:
                dump_json(target, task)
                print(f"WROTE {target}")
            compiled += 1
        except Exception as exc:
            failed += 1
            print(f"FAIL  {source}: {exc}", file=sys.stderr)
    if not compiled:
        print("No director briefs found.", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
