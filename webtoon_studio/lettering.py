from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font_candidates(bold: bool = False) -> list[Path]:
    windows_fonts = (
        [Path("C:/Windows/Fonts/malgunbd.ttf"), Path("C:/Windows/Fonts/malgun.ttf")]
        if bold
        else [Path("C:/Windows/Fonts/malgun.ttf"), Path("C:/Windows/Fonts/malgunbd.ttf")]
    )
    return windows_fonts + [
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]


def load_font(
    size: int, font_path: str | Path | None = None, bold: bool = False
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [Path(font_path)] if font_path else _font_candidates(bold)
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


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
    height: int,
    initial_size: int,
    font_path: str | Path | None,
    bold: bool = False,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    font_size = initial_size
    font = load_font(font_size, font_path, bold=bold)
    lines = _wrap_text(draw, content, font, width)
    while font_size > 10:
        line_height = _line_height(draw, font)
        if line_height * len(lines) <= height:
            return font, lines, line_height
        font_size -= 2
        font = load_font(font_size, font_path, bold=bold)
        lines = _wrap_text(draw, content, font, width)
    return font, lines, _line_height(draw, font)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    rect: tuple[int, int, int, int],
    lines: list[str],
    font: ImageFont.ImageFont,
    line_height: int,
    fill: str,
    padding: int,
    stroke_width: int = 0,
    stroke_fill: str | None = None,
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


def _tail_base(rect: tuple[int, int, int, int], target: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]] | None:
    left, top, right, bottom = rect
    target_x, target_y = target
    if left <= target_x <= right and top <= target_y <= bottom:
        return None
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    half_width = max(1, (right - left) // 2)
    half_height = max(1, (bottom - top) // 2)
    if abs(target_x - center_x) / half_width > abs(target_y - center_y) / half_height:
        x = left if target_x < center_x else right
        y = max(top + 12, min(bottom - 12, target_y))
        return (x, y - 10), (x, y + 10)
    y = top if target_y < center_y else bottom
    x = max(left + 12, min(right - 12, target_x))
    return (x - 10, y), (x + 10, y)


def _shorten_tail(start: tuple[int, int], target: tuple[int, int], maximum_length: int) -> tuple[int, int]:
    delta_x = target[0] - start[0]
    delta_y = target[1] - start[1]
    distance = (delta_x * delta_x + delta_y * delta_y) ** 0.5
    if distance <= maximum_length or distance == 0:
        return target
    ratio = maximum_length / distance
    return round(start[0] + delta_x * ratio), round(start[1] + delta_y * ratio)


def _draw_dialogue_tail(
    draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], target: tuple[int, int]
) -> None:
    base = _tail_base(rect, target)
    if base is None:
        return
    first, second = base
    start = ((first[0] + second[0]) // 2, (first[1] + second[1]) // 2)
    tip = _shorten_tail(start, target, max(24, int(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.55)))
    draw.polygon([first, second, tip], fill="#fffefc")
    draw.line([first, tip, second], fill="#181716", width=2)


def _draw_thought_tail(
    draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], target: tuple[int, int]
) -> None:
    base = _tail_base(rect, target)
    if base is None:
        return
    first, second = base
    start = ((first[0] + second[0]) // 2, (first[1] + second[1]) // 2)
    tip = _shorten_tail(start, target, max(30, int(min(rect[2] - rect[0], rect[3] - rect[1]) * 0.8)))
    for ratio, radius in ((0.3, 10), (0.55, 7), (0.78, 4)):
        x = round(start[0] + (tip[0] - start[0]) * ratio)
        y = round(start[1] + (tip[1] - start[1]) * ratio)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#fffefc", outline="#45413d", width=2)


def apply_lettering(image: Image.Image, brief: dict[str, Any], font_path: str | Path | None = None) -> Image.Image:
    text_spec = brief.get("text", {})
    if text_spec.get("mode") != "deterministic_lettering" or not text_spec.get("items"):
        return image
    result = image.convert("RGB").copy()
    draw = ImageDraw.Draw(result)
    width, height = result.size
    for item in text_spec["items"]:
        box = item["anchor_norm"]
        left = int(box["x"] * width)
        top = int(box["y"] * height)
        right = int((box["x"] + box["width"]) * width)
        bottom = int((box["y"] + box["height"]) * height)
        padding = max(8, int(min(width, height) * 0.014))
        available_width = max(20, right - left - padding * 2)
        available_height = max(20, bottom - top - padding * 2)
        rect = (left, top, right, bottom)
        kind = item["kind"]
        target_spec = item.get("tail_target_norm")
        target = (
            (round(float(target_spec["x"]) * width), round(float(target_spec["y"]) * height))
            if target_spec
            else None
        )
        if kind == "sfx":
            chosen_font, lines, line_height = _fit_text(
                draw, item["content"], available_width, available_height, max(16, int(height * 0.035)), font_path, bold=True
            )
            _draw_centered_text(
                draw, rect, lines, chosen_font, line_height, "#28201d", padding, max(1, int(height * 0.0025)), "#fffdf6"
            )
            continue
        is_caption = kind == "caption"
        chosen_font, lines, line_height = _fit_text(
            draw,
            item["content"],
            available_width,
            available_height,
            max(14, int(height * (0.025 if is_caption else 0.027))),
            font_path,
            bold=is_caption,
        )
        if is_caption:
            draw.rounded_rectangle(rect, radius=max(4, padding // 2), fill="#292725", outline="#111111", width=2)
            _draw_centered_text(draw, rect, lines, chosen_font, line_height, "#fffdf8", padding)
            continue
        if target is not None:
            if kind == "thought":
                _draw_thought_tail(draw, rect, target)
            else:
                _draw_dialogue_tail(draw, rect, target)
        radius = max(18, int(min(right - left, bottom - top) * (0.42 if kind == "thought" else 0.32)))
        outline = "#45413d" if kind == "thought" else "#181716"
        draw.rounded_rectangle(rect, radius=radius, fill="#fffefc", outline=outline, width=2)
        _draw_centered_text(draw, rect, lines, chosen_font, line_height, "#171615", padding)
    return result
