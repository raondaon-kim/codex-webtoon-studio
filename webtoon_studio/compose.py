from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from .io_utils import load_json, resolve_project_path
from .lettering import apply_lettering


def _hex_color(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        raise ValueError(f"Invalid RGB color: {value}")
    return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))


def ordered_shot_ids(scroll_plan: dict[str, Any]) -> list[str]:
    return [shot_id for sequence in scroll_plan["sequences"] for shot_id in sequence["shot_ids"]]


def compose_episode(
    episode_dir: str | Path,
    project_root: str | Path,
    project_config: dict[str, Any],
    font_path: str | Path | None = None,
) -> tuple[Path, list[Path]]:
    episode = Path(episode_dir).resolve()
    root = Path(project_root).resolve()
    scroll_plan = load_json(episode / "scroll-plan.json")
    brief_by_id = {
        brief["shot_id"]: brief
        for brief in (load_json(path) for path in sorted((episode / "briefs").glob("*.json")))
    }
    master_width = int(project_config["scroll_master"]["width_px"])
    background = _hex_color(project_config["scroll_master"].get("background", "#ffffff"))
    prepared: list[tuple[Image.Image, int, int]] = []
    for shot_id in ordered_shot_ids(scroll_plan):
        if shot_id not in brief_by_id:
            raise FileNotFoundError(f"Director brief missing for {shot_id}")
        brief = brief_by_id[shot_id]
        art_path = resolve_project_path(root, brief["output"]["path"])
        if not art_path.is_file():
            raise FileNotFoundError(f"Rendered art missing for {shot_id}: {art_path}")
        with Image.open(art_path) as source:
            art = source.convert("RGB")
        display_width = max(1, round(master_width * brief["scroll"]["display_width_ratio"]))
        display_height = max(1, round(art.height * display_width / art.width))
        art = art.resize((display_width, display_height), Image.Resampling.LANCZOS)
        art = apply_lettering(art, brief, font_path)
        prepared.append(
            (
                art,
                int(brief["scroll"]["whitespace_before_px"]),
                int(brief["scroll"]["whitespace_after_px"]),
            )
        )
    total_height = sum(before + image.height + after for image, before, after in prepared)
    if total_height <= 0:
        raise ValueError("Episode has no composable shots")
    master = Image.new("RGB", (master_width, total_height), background)
    y = 0
    for art, before, after in prepared:
        y += before
        x = (master_width - art.width) // 2
        master.paste(art, (x, y))
        y += art.height + after
    render_dir = episode / "renders"
    render_dir.mkdir(parents=True, exist_ok=True)
    master_path = render_dir / "episode-master.png"
    master.save(master_path, format="PNG", optimize=True)
    return master_path, []


def slice_master(master_path: str | Path, output_dir: str | Path, profile: dict[str, Any]) -> list[Path]:
    master_source = Path(master_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(master_source) as opened:
        master = opened.convert("RGB")
    target_width = int(profile["width_px"])
    if master.width != target_width:
        height = round(master.height * target_width / master.width)
        master = master.resize((target_width, height), Image.Resampling.LANCZOS)
    slice_height = int(profile["slice_height_px"])
    count = math.ceil(master.height / slice_height)
    extension = "jpg" if profile["format"] == "jpeg" else profile["format"]
    background = _hex_color(profile.get("background", "#ffffff"))
    for stale_slice in target_dir.glob("slice-*.*"):
        if stale_slice.is_file():
            stale_slice.unlink()
    outputs: list[Path] = []
    for index in range(count):
        top = index * slice_height
        bottom = min(master.height, top + slice_height)
        crop = master.crop((0, top, master.width, bottom))
        empty_slice = Image.new("RGB", crop.size, background)
        if ImageChops.difference(crop, empty_slice).getbbox() is None:
            continue
        target = target_dir / f"slice-{index + 1:03d}.{extension}"
        save_args: dict[str, Any] = {"format": profile["format"].upper()}
        if profile["format"] in {"jpeg", "webp"}:
            save_args["quality"] = int(profile.get("quality", 92))
        crop.save(target, **save_args)
        outputs.append(target)
    return outputs
