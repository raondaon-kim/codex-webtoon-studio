from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font_candidates() -> list[Path]:
    return [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]


def load_font(size: int, font_path: str | Path | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [Path(font_path)] if font_path else _font_candidates()
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
        padding = max(8, int(min(width, height) * 0.012))
        available_width = max(20, right - left - padding * 2)
        available_height = max(20, bottom - top - padding * 2)
        font_size = max(14, int(height * 0.026))
        chosen_font = load_font(font_size, font_path)
        lines = _wrap_text(draw, item["content"], chosen_font, available_width)
        while font_size > 10:
            line_height = draw.textbbox((0, 0), "가Ag", font=chosen_font)[3]
            if line_height * len(lines) <= available_height:
                break
            font_size -= 2
            chosen_font = load_font(font_size, font_path)
            lines = _wrap_text(draw, item["content"], chosen_font, available_width)
        line_height = draw.textbbox((0, 0), "가Ag", font=chosen_font)[3]
        total_height = line_height * len(lines)
        if item["kind"] == "sfx":
            draw.multiline_text(
                (left + padding, top + max(0, (bottom - top - total_height) // 2)),
                "\n".join(lines),
                font=chosen_font,
                fill="#111111",
                stroke_width=max(1, font_size // 14),
                stroke_fill="#ffffff",
                align="center",
            )
            continue
        radius = max(12, int(min(right - left, bottom - top) * 0.18))
        draw.rounded_rectangle((left, top, right, bottom), radius=radius, fill="#ffffff", outline="#111111", width=2)
        y = top + max(padding, (bottom - top - total_height) // 2)
        for line in lines:
            bounds = draw.textbbox((0, 0), line, font=chosen_font)
            line_width = bounds[2] - bounds[0]
            draw.text((left + (right - left - line_width) // 2, y), line, font=chosen_font, fill="#111111")
            y += line_height
    return result
