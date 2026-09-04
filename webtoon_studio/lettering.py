from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .balloon_assets import render_balloon_svg, selected_balloon_asset
from .placement import Rect, contains, normalized_rect, subject_aware_rect, subject_keepouts


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STYLE_PROFILE_PATH = REPOSITORY_ROOT / "assets" / "lettering" / "style-profile.json"
ELLIPSE_TEXT_RATIO = math.sqrt(2.0)
MOBILE_REVIEW_WIDTH = 360
MOBILE_MINIMUM_FONT_SIZE = {"dialogue": 12, "thought": 12, "caption": 11, "sfx": 15}
TAIL_RENDER_SCALE = 4


@lru_cache(maxsize=1)
def lettering_profile() -> dict[str, Any]:
    """Load the repository's deterministic lettering house style."""
    with STYLE_PROFILE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def bundled_font_paths() -> dict[str, Path]:
    profile = lettering_profile()
    font_dir = REPOSITORY_ROOT / profile["font_dir"]
    return {kind: font_dir / style["font"] for kind, style in profile["styles"].items()}


def _font_candidates(kind: str, font_path: str | Path | None) -> list[Path]:
    if font_path is not None:
        return [Path(font_path)]
    bundled = bundled_font_paths().get(kind)
    fallback = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    return ([bundled] if bundled is not None else []) + fallback


def load_font(
    size: int,
    font_path: str | Path | None = None,
    bold: bool = False,
    kind: str = "dialogue",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Use a bundled house font unless an explicit preview override is supplied."""
    del bold
    for candidate in _font_candidates(kind, font_path):
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _style(kind: str) -> dict[str, Any]:
    try:
        return lettering_profile()["styles"][kind]
    except KeyError as error:
        raise ValueError(f"Unsupported lettering kind: {kind}") from error


def _color(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}")
    return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4)) + (alpha,)


def _line_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> float:
    return float(draw.textlength(text, font=font))


def _char_wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and _line_width(draw, candidate, font) > width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _wrap_paragraph(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    """Wrap at Korean word boundaries first, then safely fall back to syllables."""
    if not text:
        return [""]
    words = re.findall(r"\S+", text)
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if not current or _line_width(draw, candidate, font) <= width:
            current = candidate
            continue
        lines.append(current)
        if _line_width(draw, word, font) <= width:
            current = word
        else:
            fragments = _char_wrap(draw, word, font, width)
            lines.extend(fragments[:-1])
            current = fragments[-1]
    if current:
        lines.append(current)
    if len(lines) > 1 and len(lines[-1].replace(" ", "")) == 1:
        previous = lines[-2]
        movable = previous[-1:]
        if movable and not movable.isspace():
            lines[-2] = previous[:-1].rstrip()
            lines[-1] = movable + lines[-1]
    return lines


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(_wrap_paragraph(draw, paragraph, font, width))
    return lines or [""]


def _text_metrics(
    draw: ImageDraw.ImageDraw, lines: list[str], font: ImageFont.ImageFont
) -> tuple[int, int, int]:
    widths = [math.ceil(_line_width(draw, line, font)) for line in lines]
    glyph_bounds = [draw.textbbox((0, 0), line or "가", font=font, anchor="lt") for line in lines]
    glyph_height = max(1, max(bounds[3] - bounds[1] for bounds in glyph_bounds))
    line_advance = max(glyph_height, math.ceil(font.size * 1.22))
    total_height = glyph_height + line_advance * max(0, len(lines) - 1)
    return max(widths, default=0), total_height, line_advance


def _shape_ratio(kind: str) -> float:
    if kind == "dialogue":
        return ELLIPSE_TEXT_RATIO
    if kind == "thought":
        return 1.22
    return 1.0


def _balloon_padding(font_size: int, image_width: int, kind: str) -> int:
    if kind == "sfx":
        return max(10, round(font_size * 0.35))
    # One full-height Korean glyph stays perceptible as white space at 360px;
    # the ellipse adds further clearance at its ends.
    return max(round(image_width * 0.022), round(font_size * 1.08))


def _font_sizes(kind: str, image_size: tuple[int, int]) -> range:
    width, height = image_size
    style = _style(kind)
    minimum = max(
        int(style["minimum_size_px"]),
        math.ceil(width / MOBILE_REVIEW_WIDTH * MOBILE_MINIMUM_FONT_SIZE[kind]),
    )
    preferred = max(minimum, round(height * float(style["font_scale"])))
    return range(preferred, minimum - 1, -2)


def _layout_cost(kind: str, lines: list[str], text_width: int, text_height: int) -> float:
    aspect = text_width / max(1, text_height)
    target_aspect = 1.42 if kind == "dialogue" else 1.15
    lengths = [len(line.replace(" ", "")) for line in lines if line]
    raggedness = (max(lengths) - min(lengths)) / max(lengths) if len(lengths) > 1 else 0.0
    orphan_penalty = 2.0 if len(lines) > 1 and min(lengths, default=2) <= 1 else 0.0
    single_line_penalty = 1.4 if len(lines) == 1 and max(lengths, default=0) > 8 else 0.0
    return abs(math.log(max(0.1, aspect) / target_aspect)) + raggedness * 0.22 + orphan_penalty + single_line_penalty


def _fit_text_first(
    draw: ImageDraw.ImageDraw,
    content: str,
    bounds: Rect,
    image_size: tuple[int, int],
    kind: str,
    font_path: str | Path | None,
) -> tuple[ImageFont.ImageFont, list[str], int, int, int, int]:
    """Measure text first, then derive a balloon that fits its reserved area."""
    maximum_width = bounds[2] - bounds[0]
    maximum_height = bounds[3] - bounds[1]
    shape_ratio = _shape_ratio(kind)
    for font_size in _font_sizes(kind, image_size):
        font = load_font(font_size, font_path, kind=kind)
        padding = _balloon_padding(font_size, image_size[0], kind)
        usable_width = max(20, math.floor((maximum_width - 2 * padding) / shape_ratio))
        candidates: list[tuple[float, ImageFont.ImageFont, list[str], int, int, int, int]] = []
        for fraction in (1.0, 0.88, 0.76, 0.66, 0.57, 0.49):
            lines = _wrap_text(draw, content, font, max(20, math.floor(usable_width * fraction)))
            text_width, text_height, line_advance = _text_metrics(draw, lines, font)
            balloon_width = math.ceil(text_width * shape_ratio) + 2 * padding
            balloon_height = math.ceil(text_height * shape_ratio) + 2 * padding
            if balloon_width <= maximum_width and balloon_height <= maximum_height:
                candidates.append(
                    (_layout_cost(kind, lines, text_width, text_height), font, lines, line_advance, padding, balloon_width, balloon_height)
                )
        if candidates:
            _, font, lines, line_advance, padding, balloon_width, balloon_height = min(candidates, key=lambda candidate: candidate[0])
            return font, lines, line_advance, padding, balloon_width, balloon_height
    raise ValueError(f"{kind} text cannot fit the declared lettering reserve at a mobile-readable size")


def _reserve_for(anchor: Rect, regions: list[Rect], image_size: tuple[int, int]) -> Rect:
    containing = [region for region in regions if contains(region, anchor)]
    if containing:
        return min(containing, key=lambda region: (region[2] - region[0]) * (region[3] - region[1]))
    width, height = image_size
    # Older fixtures may have no reserved regions. Keep their lettering
    # readable, while the QC stage separately identifies the missing reserve.
    return round(width * 0.04), round(height * 0.04), round(width * 0.96), round(height * 0.96)


def _centered_rect(width: int, height: int, center: tuple[float, float]) -> Rect:
    center_x, center_y = center
    left = round(center_x - width / 2)
    top = round(center_y - height / 2)
    return left, top, left + width, top + height


def plan_lettering(brief: dict[str, Any], image_size: tuple[int, int], font_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Resolve text-first balloons into final, subject-aware pixel geometry."""
    text_spec = brief.get("text", {})
    if text_spec.get("mode") != "deterministic_lettering":
        return []
    measurement = Image.new("RGBA", image_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(measurement)
    regions = [normalized_rect(region, image_size) for region in text_spec.get("reserved_regions", [])]
    plans: list[dict[str, Any]] = []
    for item in text_spec.get("items", []):
        kind = item["kind"]
        anchor = normalized_rect(item["anchor_norm"], image_size)
        bounds = _reserve_for(anchor, regions, image_size)
        selected_asset = selected_balloon_asset(item)
        # Fixed-tail SVGs cannot preserve a speaker link after text-first
        # resizing. They remain an explicit tail-free SFX option only.
        use_svg_asset = selected_asset is not None and kind == "sfx"
        if kind == "sfx":
            rect = anchor
            font, lines, line_advance, padding, _, _ = _fit_text_first(
                draw, item["content"], rect, image_size, kind, font_path
            )
            subject_overlap = 0.0
        else:
            font, lines, line_advance, padding, balloon_width, balloon_height = _fit_text_first(
                draw, item["content"], bounds, image_size, kind, font_path
            )
            preferred = _centered_rect(
                balloon_width,
                balloon_height,
                ((anchor[0] + anchor[2]) / 2, (anchor[1] + anchor[3]) / 2),
            )
            keepouts = subject_keepouts(brief, image_size, max(8, round(font.size * 0.28)))
            rect, subject_overlap = subject_aware_rect(preferred, bounds, keepouts)
        target_spec = item.get("tail_target_norm")
        target = (
            (round(float(target_spec["x"]) * image_size[0]), round(float(target_spec["y"]) * image_size[1]))
            if target_spec
            else None
        )
        plans.append(
            {
                "item": item,
                "kind": kind,
                "rect": rect,
                "bounds": bounds,
                "font": font,
                "font_size": font.size,
                "lines": lines,
                "line_advance": line_advance,
                "padding": padding,
                "tail_target": target,
                "subject_overlap_ratio": subject_overlap,
                "svg_asset": selected_asset if use_svg_asset else None,
            }
        )
    return plans


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    rect: Rect,
    lines: list[str],
    font: ImageFont.ImageFont,
    line_advance: int,
    fill: tuple[int, int, int, int],
    padding: int,
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] | None = None,
) -> None:
    del padding
    left, top, right, bottom = rect
    glyph_bounds = [draw.textbbox((0, 0), line or "가", font=font, anchor="lt") for line in lines]
    glyph_height = max(1, max(bounds[3] - bounds[1] for bounds in glyph_bounds))
    total_height = glyph_height + line_advance * max(0, len(lines) - 1)
    y = top + (bottom - top - total_height) / 2
    center_x = (left + right) / 2
    for line in lines:
        draw.text(
            (center_x, y),
            line,
            font=font,
            fill=fill,
            anchor="mt",
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += line_advance


def _tail_base(rect: Rect, target: tuple[int, int]) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    left, top, right, bottom = rect
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    delta_x = target[0] - center_x
    delta_y = target[1] - center_y
    distance = math.hypot(delta_x, delta_y)
    if distance < 1:
        return None
    radius_x = max(1.0, (right - left) * 0.49)
    radius_y = max(1.0, (bottom - top) * 0.49)
    boundary_scale = 1 / math.sqrt((delta_x / radius_x) ** 2 + (delta_y / radius_y) ** 2)
    edge = (center_x + delta_x * boundary_scale, center_y + delta_y * boundary_scale)
    normal = (delta_x / distance, delta_y / distance)
    tangent = (-normal[1], normal[0])
    # A normal dialogue tail should read as a short, broad continuation of
    # the balloon, not as a needle pointing at the speaker.
    half_base = max(9.0, min(radius_x, radius_y) * 0.14)
    first = (edge[0] + tangent[0] * half_base, edge[1] + tangent[1] * half_base)
    second = (edge[0] - tangent[0] * half_base, edge[1] - tangent[1] * half_base)
    return first, second, edge, tangent


def _tail_tip(edge: tuple[float, float], target: tuple[int, int], maximum_length: int, fraction: float) -> tuple[float, float] | None:
    delta_x = target[0] - edge[0]
    delta_y = target[1] - edge[1]
    distance = math.hypot(delta_x, delta_y)
    if distance < 12:
        return None
    length = min(distance * fraction, maximum_length)
    return edge[0] + delta_x * length / distance, edge[1] + delta_y * length / distance


def _sample_cubic(
    start: tuple[float, float],
    control_one: tuple[float, float],
    control_two: tuple[float, float],
    end: tuple[float, float],
    count: int = 10,
) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for index in range(count + 1):
        t = index / count
        inverse = 1 - t
        x = inverse**3 * start[0] + 3 * inverse**2 * t * control_one[0] + 3 * inverse * t**2 * control_two[0] + t**3 * end[0]
        y = inverse**3 * start[1] + 3 * inverse**2 * t * control_one[1] + 3 * inverse * t**2 * control_two[1] + t**3 * end[1]
        points.append((round(x), round(y)))
    return points


def _dialogue_tail_polygon(
    rect: Rect,
    target: tuple[int, int],
) -> tuple[list[tuple[float, float]], tuple[float, float], tuple[float, float]] | None:
    """Return a short, broad tail that overlaps the balloon's interior.

    The overlap is intentional.  The dialogue balloon is rendered as one
    union mask, so the original oval edge cannot remain as a line across the
    point where this tail joins it.
    """
    base = _tail_base(rect, target)
    if base is None:
        return None
    first, second, edge, tangent = base
    minimum_dimension = min(rect[2] - rect[0], rect[3] - rect[1])
    tip = _tail_tip(edge, target, max(18, round(minimum_dimension * 0.22)), 0.34)
    if tip is None:
        return None
    length = math.dist(edge, tip)
    normal = ((tip[0] - edge[0]) / length, (tip[1] - edge[1]) / length)
    # Pull the base into the oval.  A unioned silhouette is what removes the
    # unwanted internal outline at the tail/balloon join.
    overlap = max(4.0, minimum_dimension * 0.055)
    first = (first[0] - normal[0] * overlap, first[1] - normal[1] * overlap)
    second = (second[0] - normal[0] * overlap, second[1] - normal[1] * overlap)
    forward = min(length * 0.42, max(6.0, minimum_dimension * 0.075))
    bend = min(5.0, math.dist(first, second) * 0.10)
    first_curve = _sample_cubic(first, (first[0] + normal[0] * forward, first[1] + normal[1] * forward), (tip[0] + tangent[0] * bend, tip[1] + tangent[1] * bend), tip)
    second_curve = _sample_cubic(tip, (tip[0] - tangent[0] * bend, tip[1] - tangent[1] * bend), (second[0] + normal[0] * forward, second[1] + normal[1] * forward), second)
    return [(float(x), float(y)) for x, y in first_curve + second_curve[1:]], edge, tip


def _scaled_rect(rect: Rect, scale: int) -> Rect:
    return tuple(round(value * scale) for value in rect)  # type: ignore[return-value]


def _dialogue_masks(
    size: tuple[int, int],
    rect: Rect,
    target: tuple[int, int] | None,
    stroke_width: int,
) -> tuple[Image.Image, Image.Image, tuple[int, int]]:
    """Create anti-aliased union masks for one seamless dialogue silhouette."""
    tail = _dialogue_tail_polygon(rect, target) if target is not None else None
    points = [
        (float(rect[0]), float(rect[1])),
        (float(rect[2]), float(rect[3])),
    ]
    if tail is not None:
        points.extend(tail[0])
    margin = stroke_width + 3
    left = max(0, math.floor(min(point[0] for point in points)) - margin)
    top = max(0, math.floor(min(point[1] for point in points)) - margin)
    right = min(size[0], math.ceil(max(point[0] for point in points)) + margin)
    bottom = min(size[1], math.ceil(max(point[1] for point in points)) + margin)
    local_size = right - left, bottom - top
    scale = TAIL_RENDER_SCALE
    large_size = local_size[0] * scale, local_size[1] * scale
    fill_mask = Image.new("L", large_size, 0)
    draw = ImageDraw.Draw(fill_mask)
    local_rect = rect[0] - left, rect[1] - top, rect[2] - left, rect[3] - top
    draw.ellipse(_scaled_rect(local_rect, scale), fill=255)
    if tail is not None:
        tail_points, _, _ = tail
        draw.polygon([(round((x - left) * scale), round((y - top) * scale)) for x, y in tail_points], fill=255)
    kernel = max(3, stroke_width * scale * 2 + 1)
    outline_mask = fill_mask.filter(ImageFilter.MaxFilter(kernel))
    return (
        outline_mask.resize(local_size, Image.Resampling.LANCZOS),
        fill_mask.resize(local_size, Image.Resampling.LANCZOS),
        (left, top),
    )


def _draw_seamless_dialogue_balloon(
    overlay: Image.Image,
    rect: Rect,
    target: tuple[int, int] | None,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    """Paint the outer contour once, without a tail/oval junction line."""
    outline_mask, fill_mask, origin = _dialogue_masks(overlay.size, rect, target, stroke_width)
    overlay.paste(outline, origin, outline_mask)
    overlay.paste(fill, origin, fill_mask)


def _draw_thought_tail(
    draw: ImageDraw.ImageDraw,
    rect: Rect,
    target: tuple[int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    base = _tail_base(rect, target)
    if base is None:
        return
    _, _, edge, _ = base
    tip = _tail_tip(edge, target, max(22, round(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.46)), 0.68)
    if tip is None:
        return
    base_radius = max(3, round(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.046))
    for ratio, radius in ((0.28, base_radius), (0.56, max(3, round(base_radius * 0.72))), (0.82, max(2, round(base_radius * 0.46)))):
        x = round(edge[0] + (tip[0] - edge[0]) * ratio)
        y = round(edge[1] + (tip[1] - edge[1]) * ratio)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=stroke_width)


def _cloud_mask(size: tuple[int, int], rect: Rect) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    left, top, right, bottom = rect
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    radius_x = (right - left) / 2
    radius_y = (bottom - top) / 2
    draw.ellipse((left + radius_x * 0.08, top + radius_y * 0.12, right - radius_x * 0.08, bottom - radius_y * 0.12), fill=255)
    for x_factor, y_factor, size_factor in ((-0.56, -0.30, 0.19), (-0.18, -0.54, 0.20), (0.25, -0.50, 0.20), (0.58, -0.18, 0.19), (0.57, 0.25, 0.18), (0.18, 0.50, 0.19), (-0.26, 0.47, 0.18), (-0.60, 0.14, 0.19)):
        radius = min(radius_x, radius_y) * size_factor
        x = center_x + radius_x * x_factor
        y = center_y + radius_y * y_factor
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    return mask


def _draw_cloud(
    overlay: Image.Image,
    rect: Rect,
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    mask = _cloud_mask(overlay.size, rect)
    expansion = max(3, stroke_width * 2 + 1)
    if expansion % 2 == 0:
        expansion += 1
    outline_mask = mask.filter(ImageFilter.MaxFilter(expansion))
    overlay.paste(outline, mask=outline_mask)
    overlay.paste(fill, mask=mask)


def _draw_caption(draw: ImageDraw.ImageDraw, rect: Rect, fill: tuple[int, int, int, int]) -> None:
    left, top, right, bottom = rect
    radius = max(7, int(min(right - left, bottom - top) * 0.12))
    draw.rounded_rectangle(rect, radius=radius, fill=fill)


def _draw_selected_svg_balloon(overlay: Image.Image, asset: dict[str, Any], rect: Rect) -> Rect:
    left, top, right, bottom = rect
    balloon = render_balloon_svg(asset, (right - left, bottom - top))
    x = left + (right - left - balloon.width) // 2
    y = top + (bottom - top - balloon.height) // 2
    overlay.alpha_composite(balloon, (x, y))
    return x, y, x + balloon.width, y + balloon.height


def apply_lettering(image: Image.Image, brief: dict[str, Any], font_path: str | Path | None = None) -> Image.Image:
    text_spec = brief.get("text", {})
    if text_spec.get("mode") != "deterministic_lettering" or not text_spec.get("items"):
        return image
    source = image.convert("RGBA")
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for plan in plan_lettering(brief, source.size, font_path):
        kind = plan["kind"]
        rect = plan["rect"]
        style = _style(kind)
        fill = _color(style["fill_color"])
        outline = _color(style["outline_color"])
        text_color = _color(style["text_color"])
        draw = ImageDraw.Draw(overlay)
        stroke_width = max(2, round(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.012))
        svg_asset = plan["svg_asset"]
        text_rect = _draw_selected_svg_balloon(overlay, svg_asset, rect) if svg_asset is not None else rect
        if kind == "caption":
            _draw_caption(draw, text_rect, _color(style["fill_color"], alpha=236))
        elif kind == "thought":
            if plan["tail_target"] is not None:
                _draw_thought_tail(draw, text_rect, plan["tail_target"], fill, outline, stroke_width)
            _draw_cloud(overlay, text_rect, fill, outline, stroke_width)
            draw = ImageDraw.Draw(overlay)
        elif kind == "dialogue":
            _draw_seamless_dialogue_balloon(
                overlay,
                text_rect,
                plan["tail_target"],
                fill,
                outline,
                stroke_width,
            )
            draw = ImageDraw.Draw(overlay)
        _draw_centered_text(
            draw,
            text_rect,
            plan["lines"],
            plan["font"],
            plan["line_advance"],
            text_color,
            plan["padding"],
            max(1, round(plan["font_size"] * 0.06)) if kind == "sfx" else 0,
            outline if kind == "sfx" else None,
        )
    return Image.alpha_composite(source, overlay).convert("RGB")
