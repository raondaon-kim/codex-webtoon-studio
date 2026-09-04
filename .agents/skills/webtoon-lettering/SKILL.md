---
name: webtoon-lettering
description: Applies and reviews the repository's Korean webtoon typography and vector balloon system after art generation. Use when placing or revising dialogue, thoughts, narration, SFX, lettering style, or lettering-ready QC.
---

# Webtoon Lettering

Use deterministic lettering after art generation. Generated art must remain free
of Korean text and speech balloons so dialogue can be edited, localized, and
QC'd independently.

## Reference-driven standard

Read `assets/lettering/lettering-standard-v2.json` before designing a new
lettering profile or renderer. It is a reviewable contract, not an instruction
to overwrite an approved episode automatically.

For the source-backed rationale behind its rules, read
[references/research-principles.md](references/research-principles.md). Use it
when reviewing an existing episode, choosing a dialogue typeface, or revising
balloon geometry.

The standard is text-first:

1. Typeset the exact dialogue at a mobile-readable size.
2. Choose line breaks that form a roughly diamond-shaped text block and avoid
   orphaned first or last lines.
3. Size the balloon from the text block using a consistent glyph-relative
   clearance.
4. Add the tail last, aiming dialogue at the mouth and thought dots at the
   head.

The approved 56-shape pack is vectorized at
`assets/lettering/reference-balloons-56/vectors/`. It is an explicit special
effect library, not a replacement for ordinary speech balloons. Before using
one, check `asset-catalog.json` and `vectorization-report.json`; only a
passing asset may be selected through `text.items[].balloon_asset_id`. Its
catalog text kind must match the item. A `tail_behavior` of `baked` preserves
the original SVG tail and cannot be re-aimed with `tail_target_norm`.

Use the bundled files in `assets/fonts/` for any selected house font. An
explicit `font_path` is only for a deliberate one-off preview; do not rely on
a creator's installed system font. Keep `assets/fonts/SOURCES.md` and
`OFL-1.1.txt` with any redistributed font.

The active house type system is Nanum Gothic Regular for dialogue, Nanum Pen
Script for thoughts, Nanum Myeongjo Bold for narration, and Nanum Gothic Bold
for SFX. Do not substitute another face for normal dialogue unless its 360px
comparison is approved and the profile, source record, reference sheet, and
renderer tests change together.

## Placement and review

1. Copy final text exactly from the episode script into `brief.text.items`.
2. Reserve a simple background region in direction. Set `tail_target_norm` for
   every dialogue or thought item; captions and SFX have no tail target.
3. Generate or update the visual review sheet with:

   ```powershell
   python tools/generate_lettering_reference_sheet.py
   ```

4. Compose without regenerating art unless art itself needs a fix.
5. Run QC. It must account for every script text item and reject text assigned
   to a brief outside that brief's source beats.
6. Inspect the assembled scroll at its mobile review width. Confirm reading
   order, glyph-relative clearance, non-crossing tails, and that faces, hands,
   and depth cues remain visible.

Regenerate and validate the SVG pack only when changing its source artwork or
tracing settings:

```powershell
python tools/vectorize_balloon_assets.py
```

Use `--check` to prove that already committed SVG files still match their
approved source PNGs. Do not relax the recorded thresholds merely to make an
asset selectable; leave it out or correct its vector source instead.

Changing the selected house profile or balloon geometry requires an approved
comparison sheet, renderer tests, recompilation of affected render tasks, and
composition of the affected episode.
