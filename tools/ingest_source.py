from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webtoon_studio.ingest import ingest_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from TXT, Markdown, HTML, DOCX, EPUB, or PDF.")
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        text = ingest_text(args.source)
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text.rstrip() + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1
    print(f"WROTE {target} ({len(text)} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
