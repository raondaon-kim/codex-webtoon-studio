"""Subject-aware placement primitives for deterministic webtoon lettering.

The director brief already carries a normalized bounding box for every visible
subject. Treating those boxes as a coarse semantic segmentation mask gives the
lettering stage a stable, model-free keep-out map: speech balloons can be
placed in reserved background space instead of covering a face, hand, or
foreground silhouette. A pixel-level segmenter can supply more boxes later
without changing the placement contract.
"""

from __future__ import annotations

from typing import Any


Rect = tuple[int, int, int, int]


def normalized_rect(box: dict[str, Any], image_size: tuple[int, int]) -> Rect:
    """Convert a normalized x/y/width/height box to a clipped pixel rectangle."""
    width, height = image_size
    left = round(float(box["x"]) * width)
    top = round(float(box["y"]) * height)
    right = round((float(box["x"]) + float(box["width"])) * width)
    bottom = round((float(box["y"]) + float(box["height"])) * height)
    return max(0, left), max(0, top), min(width, right), min(height, bottom)


def expand_rect(rect: Rect, amount: int, image_size: tuple[int, int]) -> Rect:
    """Grow a keep-out rect while keeping it inside the image."""
    width, height = image_size
    left, top, right, bottom = rect
    return max(0, left - amount), max(0, top - amount), min(width, right + amount), min(height, bottom + amount)


def subject_keepouts(brief: dict[str, Any], image_size: tuple[int, int], clearance_px: int) -> list[Rect]:
    """Return expanded director-subject boxes as semantic placement obstacles."""
    keepouts: list[Rect] = []
    for subject in brief.get("subjects", []):
        box = subject.get("bbox_norm")
        if not isinstance(box, dict):
            continue
        rect = normalized_rect(box, image_size)
        if rect[2] > rect[0] and rect[3] > rect[1]:
            keepouts.append(expand_rect(rect, clearance_px, image_size))
    return keepouts


def overlap_area(first: Rect, second: Rect) -> int:
    """Return the shared area of two axis-aligned rectangles."""
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    return max(0, right - left) * max(0, bottom - top)


def rect_area(rect: Rect) -> int:
    return max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1])


def contains(outer: Rect, inner: Rect) -> bool:
    return outer[0] <= inner[0] and outer[1] <= inner[1] and outer[2] >= inner[2] and outer[3] >= inner[3]


def clamp_rect(rect: Rect, bounds: Rect) -> Rect:
    """Translate a rect just enough to keep it wholly inside its bounds."""
    left, top, right, bottom = rect
    bound_left, bound_top, bound_right, bound_bottom = bounds
    horizontal_shift = min(0, bound_right - right) + max(0, bound_left - left)
    vertical_shift = min(0, bound_bottom - bottom) + max(0, bound_top - top)
    return left + horizontal_shift, top + vertical_shift, right + horizontal_shift, bottom + vertical_shift


def subject_aware_rect(preferred: Rect, bounds: Rect, keepouts: list[Rect]) -> tuple[Rect, float]:
    """Choose the nearest in-bounds rect with the least subject-mask overlap."""
    preferred = clamp_rect(preferred, bounds)
    width = preferred[2] - preferred[0]
    height = preferred[3] - preferred[1]
    step_x = max(8, round(width * 0.18))
    step_y = max(8, round(height * 0.18))
    offsets = (
        (0, 0), (-step_x, 0), (step_x, 0), (0, -step_y), (0, step_y),
        (-step_x, -step_y), (step_x, -step_y), (-step_x, step_y), (step_x, step_y),
        (-2 * step_x, 0), (2 * step_x, 0), (0, -2 * step_y), (0, 2 * step_y),
    )
    area = max(1, rect_area(preferred))
    ranked: list[tuple[float, Rect, float]] = []
    for offset_x, offset_y in offsets:
        candidate = clamp_rect(
            (preferred[0] + offset_x, preferred[1] + offset_y, preferred[2] + offset_x, preferred[3] + offset_y),
            bounds,
        )
        overlap = sum(overlap_area(candidate, keepout) for keepout in keepouts) / area
        distance = abs(candidate[0] - preferred[0]) + abs(candidate[1] - preferred[1])
        ranked.append((overlap * 100000 + distance, candidate, overlap))
    _, rect, overlap = min(ranked, key=lambda item: item[0])
    return rect, overlap
