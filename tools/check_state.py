from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.state import project_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Show canonical project and episode stage state.")
    parser.add_argument("project_root", nargs="?", default=".")
    args = parser.parse_args()
    print(json.dumps(project_state(args.project_root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
