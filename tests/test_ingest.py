from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from webtoon_studio.ingest import ingest_text


class IngestTests(unittest.TestCase):
    def test_epub_member_paths_use_posix_separators(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            epub = Path(raw) / "sample.epub"
            with zipfile.ZipFile(epub, "w") as archive:
                archive.writestr(
                    "META-INF/container.xml",
                    """<?xml version="1.0"?>
                    <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                      <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
                    </container>""",
                )
                archive.writestr(
                    "OEBPS/content.opf",
                    """<?xml version="1.0"?>
                    <package xmlns="http://www.idpf.org/2007/opf">
                      <manifest><item id="c1" href="Text/chapter.xhtml" media-type="application/xhtml+xml"/></manifest>
                      <spine><itemref idref="c1"/></spine>
                    </package>""",
                )
                archive.writestr("OEBPS/Text/chapter.xhtml", "<html><body><p>첫 장면</p><p>둘째 장면</p></body></html>")
            extracted = ingest_text(epub)
            self.assertIn("첫 장면", extracted)
            self.assertIn("둘째 장면", extracted)


if __name__ == "__main__":
    unittest.main()
