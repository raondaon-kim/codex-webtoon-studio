from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.compose import slice_master
from webtoon_studio.io_utils import load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Slice an assembled webtoon master for a platform profile.")
    parser.add_argument("master")
    parser.add_argument("--out", required=True)
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()
    studio_root = Path(__file__).resolve().parents[1]
    profile_path = Path(args.profile) if args.profile else studio_root / "config" / "platforms" / "generic-webtoon.json"
    try:
        outputs = slice_master(args.master, args.out, load_json(profile_path))
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
