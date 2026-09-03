from __future__ import annotations

from typing import Any


MAX_EDGE = 3840
MIN_PIXELS = 655_360
MAX_PIXELS = 8_294_400
MAX_ASPECT = 3.0


def validate_generation_size(width: int, height: int) -> list[str]:
    errors: list[str] = []
    if width <= 0 or height <= 0:
        return ["canvas dimensions must be positive"]
    if width % 16 or height % 16:
        errors.append("canvas dimensions must be multiples of 16")
    if max(width, height) > MAX_EDGE:
        errors.append(f"canvas edge exceeds {MAX_EDGE}px")
    if width * height < MIN_PIXELS:
        errors.append(f"canvas is below {MIN_PIXELS:,} total pixels")
    if width * height > MAX_PIXELS:
        errors.append(f"canvas exceeds {MAX_PIXELS:,} total pixels")
    if max(width / height, height / width) > MAX_ASPECT:
        errors.append(f"canvas aspect ratio exceeds {MAX_ASPECT}:1")
    return errors


def parse_size(size: str) -> tuple[int, int]:
    try:
        width_text, height_text = size.lower().split("x", 1)
        return int(width_text), int(height_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid image size {size!r}; expected WIDTHxHEIGHT") from exc


def validate_normalized_box(box: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    try:
        x = float(box["x"])
        y = float(box["y"])
        width = float(box["width"])
        height = float(box["height"])
    except (KeyError, TypeError, ValueError):
        return [f"{label} is not a valid normalized box"]
    if x + width > 1.000001:
        errors.append(f"{label}: x + width must be <= 1")
    if y + height > 1.000001:
        errors.append(f"{label}: y + height must be <= 1")
    return errors


def box_as_percent(box: dict[str, Any]) -> str:
    return (
        f"left {round(float(box['x']) * 100)}%, "
        f"top {round(float(box['y']) * 100)}%, "
        f"width {round(float(box['width']) * 100)}%, "
        f"height {round(float(box['height']) * 100)}%"
    )


def contains(outer: dict[str, Any], inner: dict[str, Any]) -> bool:
    return (
        float(inner["x"]) >= float(outer["x"])
        and float(inner["y"]) >= float(outer["y"])
        and float(inner["x"]) + float(inner["width"])
        <= float(outer["x"]) + float(outer["width"]) + 1e-9
        and float(inner["y"]) + float(inner["height"])
        <= float(outer["y"]) + float(outer["height"]) + 1e-9
    )
