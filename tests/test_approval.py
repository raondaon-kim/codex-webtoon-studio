from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from webtoon_studio.approval import approval_is_current, approve
from webtoon_studio.io_utils import dump_json


class ApprovalTests(unittest.TestCase):
    def test_approval_becomes_stale_when_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            artifact = dump_json(root / "artifact.json", {"artifact_type": "test", "value": 1})
            approval = approve("demo", [artifact], root)
            self.assertTrue(approval_is_current(approval, root)[0])
            dump_json(artifact, {"artifact_type": "test", "value": 2})
            self.assertFalse(approval_is_current(approval, root)[0])


if __name__ == "__main__":
    unittest.main()
