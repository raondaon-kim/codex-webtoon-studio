from __future__ import annotations

import copy
import unittest
from pathlib import Path

from webtoon_studio.compiler import compile_brief, compile_visual_asset, load_configs
from webtoon_studio.geometry import validate_generation_size
from webtoon_studio.image_runtime import build_task_command, order_render_tasks, redact_sensitive, verify_task_inputs
from webtoon_studio.io_utils import load_json
from webtoon_studio.validation import validate_data, validate_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "project"


class ValidationCompilerTests(unittest.TestCase):
    def test_example_artifacts_validate(self) -> None:
        paths = [
            PROJECT / "story-bible" / "story-bible.json",
            PROJECT / "visual-bible" / "characters" / "haeun.json",
            PROJECT / "visual-bible" / "backgrounds" / "school-rooftop.json",
            PROJECT / "episodes" / "ep001" / "script.json",
            PROJECT / "episodes" / "ep001" / "scroll-plan.json",
            PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json",
            PROJECT / "episodes" / "ep001" / "briefs" / "shot-002.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual([], validate_file(path).errors)

    def test_generation_limits_reject_a4_and_tiny_canvas(self) -> None:
        self.assertTrue(any("8,294,400" in item for item in validate_generation_size(2480, 3508)))
        self.assertTrue(any("655,360" in item for item in validate_generation_size(512, 512)))
        self.assertEqual([], validate_generation_size(1024, 640))

    def test_normalized_box_must_fit_canvas(self) -> None:
        brief = load_json(PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json")
        broken = copy.deepcopy(brief)
        broken["subjects"][0]["bbox_norm"] = {"x": 0.8, "y": 0.2, "width": 0.4, "height": 0.4}
        report = validate_data(broken)
        self.assertTrue(any("x + width" in item for item in report.errors))

    def test_story_bible_rejects_regressing_or_unknown_age_milestone(self) -> None:
        story = load_json(PROJECT / "story-bible" / "story-bible.json")
        broken = copy.deepcopy(story)
        broken["timeline"]["milestones"][1]["year"] = 0
        broken["timeline"]["milestones"][1]["age_by_character"]["unknown-child"] = 7
        report = validate_data(broken)
        self.assertTrue(any("milestones must be chronological" in item for item in report.errors))
        self.assertTrue(any("unknown character ID" in item for item in report.errors))

    def test_brief_compiles_to_reference_edit_task(self) -> None:
        source = PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json"
        brief = load_json(source)
        project_config, provider_config = load_configs(PROJECT)
        first = compile_brief(brief, source, PROJECT, project_config, provider_config)
        second = compile_brief(brief, source, PROJECT, project_config, provider_config)
        self.assertEqual(first, second)
        self.assertEqual("edit", first["operation"])
        self.assertEqual("webtoon-shot-v1", first["template_id"])
        self.assertEqual("character_identity", first["references"][0]["role"])
        self.assertIn("left 12%", first["prompt"])
        self.assertIn("Generate no speech balloons", first["prompt"])

    def test_visual_asset_without_reference_is_generate(self) -> None:
        source = PROJECT / "visual-bible" / "characters" / "haeun.json"
        asset = load_json(source)
        _, provider_config = load_configs(PROJECT)
        task = compile_visual_asset(asset, source, PROJECT, provider_config)
        self.assertEqual("generate", task["operation"])
        self.assertEqual("character-reference-sheet-v1", task["template_id"])
        self.assertIn("front, left profile", task["prompt"])

    def test_runtime_command_matches_current_cli_surface(self) -> None:
        source = PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json"
        project_config, provider_config = load_configs(PROJECT)
        task = compile_brief(load_json(source), source, PROJECT, project_config, provider_config)
        command = build_task_command(task, PROJECT, provider_config)
        self.assertNotIn("--model", command)
        self.assertEqual(2, command.count("--ref-image"))
        self.assertNotIn("--retries", command)

    def test_sensitive_runtime_fields_are_redacted(self) -> None:
        value = {"access_token": "secret-token", "nested": {"refresh_token": "refresh", "ready": True}}
        redacted = redact_sensitive(value)
        self.assertEqual("<redacted>", redacted["access_token"])
        self.assertEqual("<redacted>", redacted["nested"]["refresh_token"])
        self.assertTrue(redacted["nested"]["ready"])

    def test_runtime_rejects_path_escape(self) -> None:
        source = PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json"
        project_config, provider_config = load_configs(PROJECT)
        task = compile_brief(load_json(source), source, PROJECT, project_config, provider_config)
        task["output"]["path"] = "../outside.png"
        errors = verify_task_inputs(task, PROJECT)
        self.assertTrue(any("escapes project root" in error for error in errors))

    def test_render_tasks_put_reference_producers_first(self) -> None:
        producer = {
            "task_id": "visual-hero",
            "output": {"path": "visual-bible/hero.png"},
            "references": [],
        }
        consumer = {
            "task_id": "ep001-shot-001",
            "output": {"path": "episodes/ep001/art/shot-001.png"},
            "references": [{"path": "visual-bible/hero.png"}],
        }
        ordered = order_render_tasks([(Path("consumer.json"), consumer), (Path("producer.json"), producer)])
        self.assertEqual("visual-hero", ordered[0][1]["task_id"])


if __name__ == "__main__":
    unittest.main()
