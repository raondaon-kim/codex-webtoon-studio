from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.compiler import load_configs
from webtoon_studio.compose import compose_episode, slice_master
from webtoon_studio.io_utils import load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Letter, compose, and slice a vertical-scroll episode.")
    parser.add_argument("episode_dir")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--platform-profile", default=None)
    parser.add_argument("--font", default=None)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    project_config, _ = load_configs(root)
    studio_root = Path(__file__).resolve().parents[1]
    profile_path = Path(args.platform_profile) if args.platform_profile else studio_root / "config" / "platforms" / "generic-webtoon.json"
    profile = load_json(profile_path)
    try:
        master_path, _ = compose_episode(args.episode_dir, root, project_config, args.font)
        slices = slice_master(master_path, Path(args.episode_dir) / "publish", profile)
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"MASTER {master_path}")
    for path in slices:
        print(f"SLICE  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
