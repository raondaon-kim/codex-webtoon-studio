from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from webtoon_studio.compiler import compile_brief, load_configs
from webtoon_studio.compose import compose_episode, slice_master
from webtoon_studio.io_utils import dump_json, load_json
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
            scroll_plan["sequences"][0]["bridge_shot_id"] = "shot-002"
            dump_json(episode / "scroll-plan.json", scroll_plan)

            report = inspect_episode(
                episode,
                project,
                {"width_px": 320, "slice_height_px": 400, "format": "jpeg", "quality": 85},
            )

            self.assertTrue(any(issue["code"] == "bridge_sequence_link" for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
