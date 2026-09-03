from __future__ import annotations

import html
import posixpath
import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree


_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"[ \t\r\f\v]+")
_BLANK_RE = re.compile(r"\n{3,}")


def _clean_markup(text: str) -> str:
    text = re.sub(r"<(br|/p|/div|/h[1-6]|/li)\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = _SPACE_RE.sub(" ", text)
    return _BLANK_RE.sub("\n\n", text).strip()


def _read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        paragraphs.append("".join(node.text or "" for node in paragraph.iter(f"{namespace}t")))
    return "\n\n".join(item for item in paragraphs if item.strip())


def _read_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        container = ElementTree.fromstring(archive.read("META-INF/container.xml"))
        rootfile = next(node for node in container.iter() if node.tag.endswith("rootfile"))
        opf_path = rootfile.attrib["full-path"]
        opf = ElementTree.fromstring(archive.read(opf_path))
        manifest: dict[str, str] = {}
        for node in opf.iter():
            if node.tag.endswith("item") and "id" in node.attrib and "href" in node.attrib:
                manifest[node.attrib["id"]] = node.attrib["href"]
        spine = [node.attrib["idref"] for node in opf.iter() if node.tag.endswith("itemref")]
        base = str(PurePosixPath(opf_path).parent)
        parts = []
        for item_id in spine:
            href = manifest.get(item_id)
            if not href:
                continue
            # EPUB ZIP member paths are POSIX even when this code runs on Windows.
            member = posixpath.normpath(posixpath.join(base, href)) if base != "." else posixpath.normpath(href)
            parts.append(_clean_markup(archive.read(member).decode("utf-8", errors="replace")))
    return "\n\n".join(part for part in parts if part)


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF ingestion requires the optional pypdf package") from exc
    return "\n\n".join((page.extract_text() or "").strip() for page in PdfReader(path).pages).strip()


def ingest_text(path: str | Path) -> str:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix in {".txt", ".md"}:
        return source.read_text(encoding="utf-8-sig")
    if suffix in {".html", ".htm", ".xhtml"}:
        return _clean_markup(source.read_text(encoding="utf-8", errors="replace"))
    if suffix == ".docx":
        return _read_docx(source)
    if suffix == ".epub":
        return _read_epub(source)
    if suffix == ".pdf":
        return _read_pdf(source)
    raise ValueError(f"Unsupported source format: {suffix}")
