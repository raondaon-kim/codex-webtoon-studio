from __future__ import annotations

import io
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACK_DIRECTORY = REPOSITORY_ROOT / "assets" / "lettering" / "reference-balloons-56"
CATALOG_PATH = PACK_DIRECTORY / "asset-catalog.json"
VALIDATION_REPORT_PATH = PACK_DIRECTORY / "vectorization-report.json"
_ASSET_ID = re.compile(r"^(?:[1-9]|[1-4][0-9]|5[0-6])$")


class BalloonAssetError(ValueError):
    """Raised when a brief selects an unavailable or unsuitable balloon asset."""


@lru_cache(maxsize=1)
def balloon_asset_catalog() -> dict[str, Any]:
    with CATALOG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def balloon_vector_validation() -> dict[str, dict[str, Any]]:
    """Index the current vector-equivalence report by asset identifier."""
    if not VALIDATION_REPORT_PATH.is_file():
        raise BalloonAssetError(
            "Balloon vector validation is missing. Run python tools/vectorize_balloon_assets.py first."
        )
    with VALIDATION_REPORT_PATH.open(encoding="utf-8") as handle:
        report = json.load(handle)
    return {entry["asset_id"]: entry for entry in report.get("assets", [])}


def _matches_asset_range(asset_id: int, declared_ids: list[str]) -> bool:
    for declared in declared_ids:
        if "-" in declared:
            start, end = (int(part) for part in declared.split("-", maxsplit=1))
            if start <= asset_id <= end:
                return True
        elif asset_id == int(declared):
            return True
    return False


def balloon_asset_spec(asset_id: str) -> dict[str, Any]:
    """Return the approved SVG asset and its semantic constraints."""
    if not isinstance(asset_id, str) or not _ASSET_ID.fullmatch(asset_id):
        raise BalloonAssetError("balloon_asset_id must be a string from '1' through '56'")
    numeric_id = int(asset_id)
    catalog = balloon_asset_catalog()
    group = next(
        (entry for entry in catalog["groups"] if _matches_asset_range(numeric_id, entry["asset_ids"])),
        None,
    )
    if group is None:
        raise BalloonAssetError(f"Balloon asset {asset_id} is not catalogued")
    source_png = PACK_DIRECTORY / f"말풍선 ({numeric_id}).png"
    svg = PACK_DIRECTORY / "vectors" / f"balloon-{numeric_id:03d}.svg"
    if not source_png.is_file():
        raise BalloonAssetError(f"Balloon asset {asset_id} source PNG is missing: {source_png}")
    if not svg.is_file():
        raise BalloonAssetError(
            f"Balloon asset {asset_id} SVG is missing. Run python tools/vectorize_balloon_assets.py first."
        )
    validation = balloon_vector_validation().get(asset_id)
    if not validation or not validation.get("passed"):
        raise BalloonAssetError(
            f"Balloon asset {asset_id} did not pass SVG similarity validation and cannot be selected yet."
        )
    return {
        "asset_id": asset_id,
        "group": group["kind"],
        "allowed_text_kinds": group["allowed_text_kinds"],
        "tail_behavior": group["tail_behavior"],
        "source_png": source_png,
        "svg": svg,
    }


def selected_balloon_asset(item: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve an optional brief selection and enforce its permitted text role."""
    asset_id = item.get("balloon_asset_id")
    if asset_id is None:
        return None
    asset = balloon_asset_spec(asset_id)
    kind = item.get("kind")
    if kind not in asset["allowed_text_kinds"]:
        allowed = ", ".join(asset["allowed_text_kinds"])
        raise BalloonAssetError(
            f"Balloon asset {asset_id} ({asset['group']}) cannot be used for {kind!r}; allowed: {allowed}"
        )
    return asset


def render_balloon_svg(asset: dict[str, Any], maximum_size: tuple[int, int]) -> Image.Image:
    """Rasterize an approved SVG at the requested display size without distortion."""
    max_width, max_height = maximum_size
    if max_width < 1 or max_height < 1:
        raise BalloonAssetError("Balloon display size must be positive")
    with Image.open(asset["source_png"]) as source:
        source_width, source_height = source.size
        source_bounds = source.convert("RGBA").getchannel("A").getbbox()
    if source_bounds is None:
        raise BalloonAssetError(f"Balloon asset {asset['asset_id']} has no visible pixels")
    content_width = source_bounds[2] - source_bounds[0]
    content_height = source_bounds[3] - source_bounds[1]
    scale = min(max_width / content_width, max_height / content_height)
    render_width = max(1, round(source_width * scale))
    render_height = max(1, round(source_height * scale))
    try:
        from resvg_py import svg_to_bytes
    except ModuleNotFoundError as error:  # pragma: no cover - dependency is declared in pyproject
        raise RuntimeError("SVG balloon rendering requires the resvg-py project dependency") from error
    rendered = svg_to_bytes(svg_path=str(asset["svg"]), width=render_width, height=render_height)
    with Image.open(io.BytesIO(rendered)) as image:
        rendered_image = image.convert("RGBA")
    rendered_bounds = rendered_image.getchannel("A").getbbox()
    if rendered_bounds is None:
        raise BalloonAssetError(f"SVG balloon asset {asset['asset_id']} rendered without visible pixels")
    cropped = rendered_image.crop(rendered_bounds)
    if cropped.width <= max_width and cropped.height <= max_height:
        return cropped
    correction = min(max_width / cropped.width, max_height / cropped.height)
    return cropped.resize(
        (max(1, round(cropped.width * correction)), max(1, round(cropped.height * correction))),
        Image.Resampling.LANCZOS,
    )
