from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.compiler import compile_visual_asset, load_configs
from webtoon_studio.io_utils import dump_json, load_json
from webtoon_studio.validation import discover_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile visual bible assets into image render tasks.")
    parser.add_argument("paths", nargs="+", help="Visual asset JSON files or directories")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    _, provider_config = load_configs(root)
    failed = 0
    compiled = 0
    for source in discover_json(args.paths):
        asset = load_json(source)
        if asset.get("artifact_type") != "visual_asset":
            continue
        try:
            task = compile_visual_asset(asset, source, root, provider_config)
            target = root / "visual-bible" / "render-tasks" / f"{asset['asset_id']}.json"
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
        print("No visual assets found.", file=sys.stderr)
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
