from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageFont

from webtoon_studio.balloon_assets import BalloonAssetError, balloon_asset_spec, selected_balloon_asset
from webtoon_studio.compiler import compile_brief, load_configs
from webtoon_studio.compose import compose_episode, ordered_shot_ids, slice_master
from webtoon_studio.io_utils import dump_json, load_json
from webtoon_studio.lettering import apply_lettering, bundled_font_paths, lettering_profile, load_font
from webtoon_studio.qc import inspect_episode


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PROJECT = ROOT / "examples" / "project"


class ComposeQcTests(unittest.TestCase):
    def test_compose_slice_and_qc(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            shutil.copytree(SOURCE_PROJECT, project)
            episode = project / "episodes" / "ep001"
            project_config, provider_config = load_configs(project)
            for index, brief_path in enumerate(sorted((episode / "briefs").glob("*.json"))):
                brief = load_json(brief_path)
                brief["canvas"]["width_px"] = 1024
                brief["canvas"]["height_px"] = 640
                dump_json(brief_path, brief)
                task = compile_brief(brief, brief_path, project, project_config, provider_config)
                dump_json(episode / "render-tasks" / f"{brief['shot_id']}.json", task)
                art_path = project / brief["output"]["path"]
                art_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (1024, 640), (80 + index * 50, 110, 150)).save(art_path)
            project_config["scroll_master"]["width_px"] = 320
            master, _ = compose_episode(episode, project, project_config)
            self.assertTrue(master.is_file())
            profile = {"width_px": 320, "slice_height_px": 400, "format": "jpeg", "quality": 85}
            slices = slice_master(master, episode / "publish", profile)
            self.assertGreater(len(slices), 1)
            report = inspect_episode(episode, project, profile)
            self.assertEqual("pass", report["status"])
            self.assertTrue(all(report["checks"].values()))

    def test_slice_master_skips_uniform_trailing_slice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            master = root / "master.png"
            image = Image.new("RGB", (320, 850), "white")
            image.paste((50, 75, 100), (0, 0, 320, 700))
            image.save(master)

            slices = slice_master(
                master,
                root / "publish",
                {"width_px": 320, "slice_height_px": 400, "format": "jpeg", "quality": 85},
            )

            self.assertEqual(["slice-001.jpg", "slice-002.jpg"], [path.name for path in slices])

    def test_qc_rejects_bridge_outside_its_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            shutil.copytree(SOURCE_PROJECT, project)
            episode = project / "episodes" / "ep001"
            scroll_plan = load_json(episode / "scroll-plan.json")
            scroll_plan["sequences"][0]["bridge_inserts"] = [{"shot_id": "shot-003", "after_shot_id": "shot-002"}]
            dump_json(episode / "scroll-plan.json", scroll_plan)

            report = inspect_episode(
                episode,
                project,
                {"width_px": 320, "slice_height_px": 400, "format": "jpeg", "quality": 85},
            )

            self.assertTrue(any(issue["code"] == "bridge_sequence_link" for issue in report["issues"]))

    def test_bridge_is_composed_after_its_declared_regular_shot(self) -> None:
        scroll_plan = {
            "sequences": [
                {
                    "shot_ids": ["shot-001", "shot-002", "shot-003"],
                    "bridge_inserts": [{"shot_id": "shot-024", "after_shot_id": "shot-002"}],
                }
            ]
        }

        self.assertEqual(
            ["shot-001", "shot-002", "shot-024", "shot-003"],
            ordered_shot_ids(scroll_plan),
        )

    def test_qc_rejects_script_text_that_is_not_placed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            shutil.copytree(SOURCE_PROJECT, project)
            episode = project / "episodes" / "ep001"
            script = load_json(episode / "script.json")
            script["beats"][0]["text"].append({"kind": "dialogue", "content": "누락된 대사"})
            dump_json(episode / "script.json", script)

            report = inspect_episode(
                episode,
                project,
                {"width_px": 320, "slice_height_px": 400, "format": "jpeg", "quality": 85},
            )

            self.assertTrue(any(issue["code"] == "script_text_missing" for issue in report["issues"]))

    def test_lettering_renders_distinct_balloon_types_with_tails(self) -> None:
        source = Image.new("RGB", (640, 960), "#7a8aa0")
        brief = {
            "text": {
                "mode": "deterministic_lettering",
                "items": [
                    {"kind": "caption", "content": "장면 전환", "anchor_norm": {"x": 0.05, "y": 0.05, "width": 0.30, "height": 0.12}},
                    {"kind": "dialogue", "content": "대사", "anchor_norm": {"x": 0.55, "y": 0.10, "width": 0.30, "height": 0.15}, "tail_target_norm": {"x": 0.76, "y": 0.48}},
                    {"kind": "thought", "content": "독백", "anchor_norm": {"x": 0.08, "y": 0.50, "width": 0.30, "height": 0.15}, "tail_target_norm": {"x": 0.23, "y": 0.82}},
                    {"kind": "sfx", "content": "쾅!", "anchor_norm": {"x": 0.52, "y": 0.62, "width": 0.30, "height": 0.16}},
                ],
                "reserved_regions": [],
            }
        }

        rendered = apply_lettering(source, brief)

        self.assertNotEqual(source.tobytes(), rendered.tobytes())

    def test_lettering_renders_only_an_svg_balloon_that_passed_similarity_validation(self) -> None:
        source = Image.new("RGB", (640, 960), "#7a8aa0")
        brief = {
            "text": {
                "mode": "deterministic_lettering",
                "items": [
                    {
                        "kind": "sfx",
                        "content": "쾅!",
                        "anchor_norm": {"x": 0.18, "y": 0.32, "width": 0.64, "height": 0.30},
                        "balloon_asset_id": "37",
                    }
                ],
                "reserved_regions": [],
            }
        }

        rendered = apply_lettering(source, brief)

        self.assertEqual("37", balloon_asset_spec("37")["asset_id"])
        self.assertNotEqual(source.tobytes(), rendered.tobytes())
        with self.assertRaises(BalloonAssetError):
            selected_balloon_asset({"kind": "sfx", "balloon_asset_id": "11"})

    def test_lettering_uses_the_bundled_house_fonts(self) -> None:
        profile = lettering_profile()
        fonts = bundled_font_paths()

        self.assertEqual("fantasy-korean-webtoon-nanum-v2", profile["profile_id"])
        self.assertEqual({"dialogue", "thought", "caption", "sfx"}, set(fonts))
        self.assertEqual("NanumGothic-Regular.ttf", fonts["dialogue"].name)
        self.assertEqual("NanumPenScript-Regular.ttf", fonts["thought"].name)
        self.assertEqual("NanumMyeongjo-Bold.ttf", fonts["caption"].name)
        self.assertEqual("NanumGothic-Bold.ttf", fonts["sfx"].name)
        for kind, path in fonts.items():
            with self.subTest(kind=kind):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 100_000)
                self.assertIsInstance(load_font(24, kind=kind), ImageFont.FreeTypeFont)


if __name__ == "__main__":
    unittest.main()
