from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STYLE_PROFILE_PATH = REPOSITORY_ROOT / "assets" / "lettering" / "style-profile.json"


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
    del bold  # Weight is encoded in each selected bundled font file.
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


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _line_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
    bounds = draw.textbbox((0, 0), "가Ag", font=font)
    return bounds[3] - bounds[1]


def _fit_text(
    draw: ImageDraw.ImageDraw,
    content: str,
    width: int,
    box_height: int,
    canvas_height: int,
    kind: str,
    font_path: str | Path | None,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    style = _style(kind)
    font_size = max(int(style["minimum_size_px"]), int(canvas_height * float(style["font_scale"])))
    font = load_font(font_size, font_path, kind=kind)
    lines = _wrap_text(draw, content, font, width)
    while font_size > 10:
        line_height = _line_height(draw, font)
        if line_height * len(lines) <= box_height:
            return font, lines, line_height
        font_size -= 2
        font = load_font(font_size, font_path, kind=kind)
        lines = _wrap_text(draw, content, font, width)
    return font, lines, _line_height(draw, font)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    lines: list[str],
    font: ImageFont.ImageFont,
    line_height: int,
    fill: tuple[int, int, int, int],
    padding: int,
    stroke_width: int = 0,
    stroke_fill: tuple[int, int, int, int] | None = None,
) -> None:
    left, top, right, bottom = rect
    total_height = line_height * len(lines)
    y = top + max(padding, (bottom - top - total_height) // 2)
    for line in lines:
        bounds = draw.textbbox((0, 0), line, font=font)
        line_width = bounds[2] - bounds[0]
        draw.text(
            (left + (right - left - line_width) // 2, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
        )
        y += line_height


def _shorten_tail(start: tuple[float, float], target: tuple[int, int], maximum_length: int) -> tuple[float, float]:
    delta_x = target[0] - start[0]
    delta_y = target[1] - start[1]
    distance = math.hypot(delta_x, delta_y)
    if distance <= maximum_length or distance == 0:
        return float(target[0]), float(target[1])
    ratio = maximum_length / distance
    return start[0] + delta_x * ratio, start[1] + delta_y * ratio


def _tail_base(
    rect: tuple[int, int, int, int], target: tuple[int, int]
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    left, top, right, bottom = rect
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    delta_x = target[0] - center_x
    delta_y = target[1] - center_y
    distance = math.hypot(delta_x, delta_y)
    if distance == 0:
        return None
    radius_x = max(1.0, (right - left) * 0.48)
    radius_y = max(1.0, (bottom - top) * 0.48)
    boundary_scale = 1 / math.sqrt((delta_x / radius_x) ** 2 + (delta_y / radius_y) ** 2)
    edge = (center_x + delta_x * boundary_scale, center_y + delta_y * boundary_scale)
    normal = (delta_x / distance, delta_y / distance)
    tangent = (-normal[1], normal[0])
    half_base = max(7.0, min(radius_x, radius_y) * 0.22)
    first = (edge[0] + tangent[0] * half_base, edge[1] + tangent[1] * half_base)
    second = (edge[0] - tangent[0] * half_base, edge[1] - tangent[1] * half_base)
    return first, second, edge, tangent


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


def _draw_dialogue_tail(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    target: tuple[int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    base = _tail_base(rect, target)
    if base is None:
        return
    first, second, edge, tangent = base
    tip = _shorten_tail(edge, target, max(24, int(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.52)))
    length = math.dist(edge, tip)
    if length < 4:
        return
    normal = ((tip[0] - edge[0]) / length, (tip[1] - edge[1]) / length)
    forward = min(length * 0.42, max(7.0, min(rect[2] - rect[0], rect[3] - rect[1]) * 0.18))
    bend = min(10.0, math.dist(first, second) * 0.22)
    first_curve = _sample_cubic(
        first,
        (first[0] + normal[0] * forward, first[1] + normal[1] * forward),
        (tip[0] + tangent[0] * bend, tip[1] + tangent[1] * bend),
        tip,
    )
    second_curve = _sample_cubic(
        tip,
        (tip[0] - tangent[0] * bend, tip[1] - tangent[1] * bend),
        (second[0] + normal[0] * forward, second[1] + normal[1] * forward),
        second,
    )
    points = first_curve + second_curve[1:]
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=stroke_width, joint="curve")


def _draw_thought_tail(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    target: tuple[int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    base = _tail_base(rect, target)
    if base is None:
        return
    _, _, edge, _ = base
    tip = _shorten_tail(edge, target, max(30, int(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.78)))
    for ratio, radius in ((0.30, 10), (0.56, 7), (0.80, 4)):
        x = round(edge[0] + (tip[0] - edge[0]) * ratio)
        y = round(edge[1] + (tip[1] - edge[1]) * ratio)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=stroke_width)


def _organic_oval_points(rect: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    left, top, right, bottom = rect
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    radius_x = max(1.0, (right - left) * 0.477)
    radius_y = max(1.0, (bottom - top) * 0.477)
    points: list[tuple[int, int]] = []
    for index in range(64):
        angle = 2 * math.pi * index / 64
        wobble = 1 + 0.016 * math.sin(3 * angle + 0.45) + 0.009 * math.sin(5 * angle - 0.9)
        points.append((round(center_x + radius_x * math.cos(angle) * wobble), round(center_y + radius_y * math.sin(angle) * wobble)))
    return points


def _draw_organic_oval(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    outline: tuple[int, int, int, int],
    stroke_width: int,
) -> None:
    points = _organic_oval_points(rect)
    draw.polygon(points, fill=fill)
    draw.line(points + [points[0]], fill=outline, width=stroke_width, joint="curve")


def _cloud_mask(size: tuple[int, int], rect: tuple[int, int, int, int]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    left, top, right, bottom = rect
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2
    radius_x = (right - left) / 2
    radius_y = (bottom - top) / 2
    draw.ellipse((left + radius_x * 0.06, top + radius_y * 0.10, right - radius_x * 0.06, bottom - radius_y * 0.10), fill=255)
    for x_factor, y_factor, size_factor in (
        (-0.62, -0.24, 0.23),
        (-0.30, -0.56, 0.21),
        (0.10, -0.60, 0.22),
        (0.48, -0.38, 0.24),
        (0.66, -0.04, 0.21),
        (0.49, 0.38, 0.23),
        (0.10, 0.55, 0.21),
        (-0.30, 0.49, 0.22),
        (-0.64, 0.18, 0.22),
    ):
        radius = min(radius_x, radius_y) * size_factor
        x = center_x + radius_x * x_factor
        y = center_y + radius_y * y_factor
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    return mask


def _draw_cloud(
    overlay: Image.Image,
    rect: tuple[int, int, int, int],
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


def _draw_caption(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = rect
    radius = max(7, int(min(right - left, bottom - top) * 0.15))
    draw.rounded_rectangle(rect, radius=radius, fill=fill)


def apply_lettering(image: Image.Image, brief: dict[str, Any], font_path: str | Path | None = None) -> Image.Image:
    text_spec = brief.get("text", {})
    if text_spec.get("mode") != "deterministic_lettering" or not text_spec.get("items"):
        return image
    source = image.convert("RGBA")
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    width, height = source.size
    for item in text_spec["items"]:
        box = item["anchor_norm"]
        left = int(box["x"] * width)
        top = int(box["y"] * height)
        right = int((box["x"] + box["width"]) * width)
        bottom = int((box["y"] + box["height"]) * height)
        rect = (left, top, right, bottom)
        kind = item["kind"]
        style = _style(kind)
        padding = max(8, int(min(width, height) * 0.018))
        available_width = max(20, right - left - padding * 2)
        available_height = max(20, bottom - top - padding * 2)
        target_spec = item.get("tail_target_norm")
        target = (
            (round(float(target_spec["x"]) * width), round(float(target_spec["y"]) * height))
            if target_spec
            else None
        )
        fill = _color(style["fill_color"])
        outline = _color(style["outline_color"])
        text_color = _color(style["text_color"])
        stroke_width = max(1, round(min(right - left, bottom - top) * 0.014))
        draw = ImageDraw.Draw(overlay)
        font, lines, line_height = _fit_text(
            draw,
            item["content"],
            available_width,
            available_height,
            height,
            kind,
            font_path,
        )

        if kind == "caption":
            _draw_caption(draw, rect, _color(style["fill_color"], alpha=232))
            _draw_centered_text(draw, rect, lines, font, line_height, text_color, padding)
            continue
        if kind == "sfx":
            _draw_centered_text(
                draw,
                rect,
                lines,
                font,
                line_height,
                text_color,
                padding,
                max(1, int(height * 0.0025)),
                outline,
            )
            continue
        if target is not None:
            if kind == "thought":
                _draw_thought_tail(draw, rect, target, fill, outline, stroke_width)
            else:
                _draw_dialogue_tail(draw, rect, target, fill, outline, stroke_width)
        if kind == "thought":
            _draw_cloud(overlay, rect, fill, outline, stroke_width)
            draw = ImageDraw.Draw(overlay)
        else:
            _draw_organic_oval(draw, rect, fill, outline, stroke_width)
        _draw_centered_text(draw, rect, lines, font, line_height, text_color, padding)
    return Image.alpha_composite(source, overlay).convert("RGB")
