---
name: webtoon-lettering
description: Applies and reviews the repository's Korean webtoon typography and vector balloon system after art generation. Use when placing or revising dialogue, thoughts, narration, SFX, lettering style, or lettering-ready QC.
---

# Webtoon Lettering

Use deterministic lettering after art generation. Generated art must remain free
of Korean text and speech balloons so dialogue can be edited, localized, and
QC'd independently.

## House style

Read `assets/lettering/style-profile.json` before changing lettering behavior.
It maps the four semantic text kinds to the bundled OFL fonts in `assets/fonts/`:

- `dialogue`: Gowun Dodum in a soft, slightly irregular oval with a short curved tail.
- `thought`: Nanum Pen Script in a cloud balloon with a three-dot tail.
- `caption`: Gowun Batang Bold in a quiet charcoal narration plaque.
- `sfx`: Black Han Sans with a light outline and no balloon.

Use the bundled file for each role. An explicit `font_path` is only for a
deliberate one-off preview; do not rely on a creator's installed system font.
Keep `assets/fonts/SOURCES.md` and `OFL-1.1.txt` with any redistributed font.

## Placement and review

1. Copy final text exactly from the episode script into `brief.text.items`.
2. Use the semantic `kind`, reserve its `anchor_norm` region in direction, and
   set `tail_target_norm` for every dialogue or thought item. Captions and SFX
   have no tail target.
3. Compose the episode without regenerating art unless art itself needs a fix.
4. Run QC. It must account for every script text item and reject text assigned
   to a brief outside that brief's source beats.
5. Inspect the assembled scroll: tails identify the intended speaker without
   crossing faces, text is readable at publish width, and bubbles do not cover
   story-critical details.

Changing the house profile or balloon geometry requires updating the renderer
and its tests, then recompiling render tasks and composing the affected episode.
