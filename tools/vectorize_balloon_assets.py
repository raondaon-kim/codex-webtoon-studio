from __future__ import annotations

"""Trace the approved balloon PNGs to SVG and prove their visual equivalence."""

import argparse
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat


ROOT = Path(__file__).resolve().parents[1]
PACK_DIRECTORY = ROOT / "assets" / "lettering" / "reference-balloons-56"
VECTOR_DIRECTORY = PACK_DIRECTORY / "vectors"
REPORT_PATH = PACK_DIRECTORY / "vectorization-report.json"
TOTAL_ASSETS = 56
VISUAL_SIMILARITY_MINIMUM = 0.985
ALPHA_IOU_MINIMUM = 0.970


def _source_path(asset_id: int) -> Path:
    return PACK_DIRECTORY / f"말풍선 ({asset_id}).png"


def _svg_path(asset_id: int) -> Path:
    return VECTOR_DIRECTORY / f"balloon-{asset_id:03d}.svg"


def _flatten(image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    background = Image.new("RGBA", image.size, color + (255,))
    background.alpha_composite(image.convert("RGBA"))
    return background.convert("RGB")


def _alpha_iou(source: Image.Image, rendered: Image.Image) -> float:
    source_alpha = source.convert("RGBA").getchannel("A").getdata()
    rendered_alpha = rendered.convert("RGBA").getchannel("A").getdata()
    intersection = 0
    union = 0
    for source_value, rendered_value in zip(source_alpha, rendered_alpha, strict=True):
        source_visible = source_value >= 16
        rendered_visible = rendered_value >= 16
        intersection += source_visible and rendered_visible
        union += source_visible or rendered_visible
    return 1.0 if union == 0 else intersection / union


def _measure(source: Image.Image, rendered: Image.Image) -> dict[str, Any]:
    if source.size != rendered.size:
        return {
            "dimensions_match": False,
            "visual_similarity": 0.0,
            "alpha_iou": 0.0,
            "mean_absolute_error": 255.0,
            "passed": False,
        }
    differences = [
        ImageStat.Stat(ImageChops.difference(_flatten(source, color), _flatten(rendered, color))).mean
        for color in ((255, 255, 255), (128, 176, 208))
    ]
    mean_absolute_error = sum(sum(channels) / len(channels) for channels in differences) / len(differences)
    visual_similarity = 1 - mean_absolute_error / 255
    alpha_iou = _alpha_iou(source, rendered)
    return {
        "dimensions_match": True,
        "visual_similarity": round(visual_similarity, 6),
        "alpha_iou": round(alpha_iou, 6),
        "mean_absolute_error": round(mean_absolute_error, 6),
        "passed": visual_similarity >= VISUAL_SIMILARITY_MINIMUM and alpha_iou >= ALPHA_IOU_MINIMUM,
    }


def _trace(source: Path, target: Path) -> None:
    try:
        import vtracer
    except ModuleNotFoundError as error:  # pragma: no cover - optional build dependency
        raise RuntimeError("Tracing requires vtracer. Install with: pip install .[vectorize]") from error
    target.parent.mkdir(parents=True, exist_ok=True)
    vtracer.convert_image_to_svg_py(
        str(source),
        str(target),
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=8,
        layer_difference=4,
        corner_threshold=60,
        length_threshold=3.5,
        max_iterations=10,
        splice_threshold=45,
        path_precision=8,
    )


def _render(svg: Path) -> Image.Image:
    try:
        from resvg_py import svg_to_bytes
    except ModuleNotFoundError as error:  # pragma: no cover - runtime dependency
        raise RuntimeError("SVG validation requires the resvg-py project dependency") from error
    png_bytes = svg_to_bytes(svg_path=str(svg))
    with Image.open(io.BytesIO(png_bytes)) as image:
        return image.convert("RGBA")


def build_report(trace: bool) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    for asset_id in range(1, TOTAL_ASSETS + 1):
        source = _source_path(asset_id)
        svg = _svg_path(asset_id)
        if trace:
            _trace(source, svg)
        if not svg.is_file():
            raise FileNotFoundError(f"Missing SVG for asset {asset_id}: {svg}")
        with Image.open(source) as source_image:
            metrics = _measure(source_image.convert("RGBA"), _render(svg))
        assets.append(
            {
                "asset_id": str(asset_id),
                "source_png": source.name,
                "svg": svg.relative_to(PACK_DIRECTORY).as_posix(),
                **metrics,
            }
        )
    return {
        "schema_version": "1.0",
        "asset_pack_id": "private-contributor-balloon-pack-56",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": {
            "tracer": "vtracer color/spline",
            "renderer": "resvg-py",
            "visual_similarity_minimum": VISUAL_SIMILARITY_MINIMUM,
            "alpha_iou_minimum": ALPHA_IOU_MINIMUM,
        },
        "summary": {
            "total": len(assets),
            "passed": sum(1 for asset in assets if asset["passed"]),
            "failed": sum(1 for asset in assets if not asset["passed"]),
        },
        "assets": assets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate existing SVGs without retracing them")
    args = parser.parse_args()
    report = build_report(trace=not args.check)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['summary']['passed']}/{report['summary']['total']} SVG balloon assets passed validation")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
