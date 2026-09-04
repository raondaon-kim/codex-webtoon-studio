from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STANDARD = ROOT / "assets" / "lettering" / "lettering-standard-v2.json"
GENERATOR = ROOT / "tools" / "generate_lettering_reference_sheet.py"


class LetteringStandardTests(unittest.TestCase):
    def test_standard_defines_mobile_proof_and_text_first_geometry(self) -> None:
        standard = json.loads(STANDARD.read_text(encoding="utf-8"))

        self.assertEqual("approved", standard["status"])
        self.assertEqual(360, standard["review_target"]["mobile_review_width_px"])
        self.assertEqual(2, standard["text_first_layout"]["inner_clearance"]["target_each_side"])
        self.assertEqual(3, standard["balloon_semantics"]["thought"]["minimum_dot_count"])
        self.assertEqual(0.22, standard["balloon_semantics"]["dialogue"]["tail_gap_fraction"]["preferred"])
        self.assertIn("seamless", standard["balloon_semantics"]["dialogue"]["contour"])
        self.assertEqual(0.14, standard["balloon_semantics"]["dialogue"]["tail_geometry"]["length_cap_by_balloon_min_dimension"])
        self.assertEqual(0.22, standard["balloon_semantics"]["dialogue"]["tail_geometry"]["renderer_target_gap_fraction"])
        self.assertEqual("https://github.com/wenn-id/comicsol", standard["implementation_boundary"]["reference_engine"])
        self.assertIn("seamless_curved_tail_rendering", standard["implementation_boundary"]["adopt_patterns"])
        self.assertEqual("NanumGothic-Regular.ttf", standard["type_selection"]["selected_house_type_system"]["dialogue"])
        self.assertEqual("NanumGothic-Regular.ttf", standard["type_selection"]["selected_house_type_system"]["thought"])
        self.assertEqual("NanumGothic-Regular.ttf", standard["type_selection"]["selected_house_type_system"]["caption"])

    def test_reference_sheet_generator_outputs_a_mobile_review_asset(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "lettering-standard.png"
            subprocess.run([sys.executable, str(GENERATOR), "--out", str(output)], check=True, cwd=ROOT)

            self.assertTrue(output.is_file())
            with Image.open(output) as image:
                self.assertEqual("RGB", image.mode)
                self.assertEqual((1080, 2160), image.size)


if __name__ == "__main__":
    unittest.main()
