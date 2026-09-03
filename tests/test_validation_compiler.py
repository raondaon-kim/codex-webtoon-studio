from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from webtoon_studio.compiler import compile_brief, compile_visual_asset, load_configs
from webtoon_studio.geometry import validate_generation_size
from webtoon_studio.image_runtime import (
    RuntimeErrorWithEnvelope,
    build_task_command,
    normalize_render_output,
    order_render_tasks,
    redact_sensitive,
    verify_task_inputs,
)
from webtoon_studio.io_utils import load_json
from webtoon_studio.validation import validate_data, validate_file


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "project"
CURRENT_PROJECT = ROOT / "projects" / "fallen-minister-territory"
TERRITORY_PROFILE = CURRENT_PROJECT / "territory" / "rowend-march-profile.json"


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

    def test_territory_profile_defines_exposure_without_scheduling_a_disaster(self) -> None:
        territory = load_json(TERRITORY_PROFILE)
        self.assertEqual([], validate_file(TERRITORY_PROFILE).errors)
        self.assertTrue(territory["chronic_problems"])
        self.assertTrue(all(item["scenario_not_scheduled"] for item in territory["disaster_exposure"]))

    def test_current_project_keeps_its_own_project_config(self) -> None:
        project_config, _ = load_configs(CURRENT_PROJECT)
        self.assertEqual("fallen-minister-territory", project_config["project_id"])

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

    def test_bridge_brief_compiles_to_one_multi_panel_image_prompt(self) -> None:
        source = PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json"
        brief = copy.deepcopy(load_json(source))
        brief["bridge"] = {
            "panel_count": 2,
            "layout": "vertical_stack",
            "function": "reaction",
            "panel_beats": ["Haeun notices the wet notebook.", "She quietly pulls it closer."],
        }
        project_config, provider_config = load_configs(PROJECT)

        task = compile_brief(brief, source, PROJECT, project_config, provider_config)

        self.assertIn("single generated image contains exactly 2", task["prompt"])
        self.assertIn("stacked vertically", task["prompt"])
        self.assertIn("panel 1: Haeun notices the wet notebook.", task["prompt"])

    def test_bridge_panel_count_must_match_declared_micro_beats(self) -> None:
        brief = copy.deepcopy(load_json(PROJECT / "episodes" / "ep001" / "briefs" / "shot-001.json"))
        brief["bridge"] = {
            "panel_count": 2,
            "layout": "vertical_stack",
            "function": "reaction",
            "panel_beats": ["Haeun notices the wet notebook.", "She pauses.", "She pulls it closer."],
        }

        report = validate_data(brief)

        self.assertTrue(any("length must match" in error for error in report.errors))

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
        value = {
            "access_token": "secret-token",
            "email": "artist@example.com",
            "nested": {"refresh_token": "refresh", "account_id": "account-123", "ready": True},
        }
        redacted = redact_sensitive(value)
        self.assertEqual("<redacted>", redacted["access_token"])
        self.assertEqual("<redacted>", redacted["email"])
        self.assertEqual("<redacted>", redacted["nested"]["refresh_token"])
        self.assertEqual("<redacted>", redacted["nested"]["account_id"])
        self.assertTrue(redacted["nested"]["ready"])

    def test_runtime_normalizes_same_aspect_provider_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "shot.png"
            Image.new("RGB", (1086, 1448), (33, 66, 99)).save(output)

            result = normalize_render_output(output, "1536x2048")

            with Image.open(output) as image:
                self.assertEqual((1536, 2048), image.size)
        self.assertTrue(result["normalized"])
        self.assertEqual([1086, 1448], result["source_dimensions"])

    def test_runtime_rejects_provider_output_with_wrong_aspect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "shot.png"
            Image.new("RGB", (887, 1774), (33, 66, 99)).save(output)

            with self.assertRaises(RuntimeErrorWithEnvelope):
                normalize_render_output(output, "1536x2048")

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
