# Research principles for Korean webtoon lettering

These are observed production and lettering rules, distilled into decisions the
repository can verify. They are not a source of artwork: do not copy published
webtoon panels or store screenshots in the repository.

## Text before balloon

- Set text before drawing its tail and center the final text block. The Korean
  webtoon typesetting guide asks for even clearance on every side, about the
  space occupied by two Korean characters.
- Prefer a diamond-like text block: its middle line is longest, and its top and
  bottom lines are shorter. Avoid a one-word first or last line unless it is
  deliberately emphatic.
- Use one normal dialogue typeface, weight, and baseline treatment throughout
  an episode. Change size, weight, or clearance only to signal a deliberate
  voice change such as a shout or whisper.

## Geometry and reading

- Create clean path-like balloon contours. Normal dialogue balloons are
  consistent in outline width, tail width, and proportion; random wobble is not
  a substitute for a hand-drawn style.
- Aim a dialogue tail at the mouth or emitting object. End it roughly halfway
  to three-fifths of the gap to the speaker unless distance is a deliberate
  story signal. Thought balloons use at least three diminishing dots aimed at
  the head.
- Put the first balloon higher, preserve top-to-bottom scroll order, and do not
  cross tails or construct a wall between speakers. Space close turns closer
  only when the timing is intentionally immediate.
- Keep balloons in simple background space and away from faces, essential hand
  actions, and depth-defining edges.

## Mobile proof

- The usable unit is the target phone display, not a nominal point size. Review
  at 360 CSS pixels wide before adopting a dialogue font.
- Test the same representative Korean lines in each candidate typeface. Reject
  a candidate if its normal dialogue cannot be comfortably read at that width,
  if bold text collides with neighboring lines, or if its glyph widths make
  regular balloons excessively wide or tall.

## Engine reference boundary

[Comic Sol](https://github.com/wenn-id/comicsol) is a useful implementation
reference, not a dependency or a project template for this repository. Its
deterministic lettering engine demonstrates three mechanics worth carrying
forward: explicit speaker anchors, seamless curved tails rendered at higher
resolution, and a preflight that refuses unavailable glyphs.

Do not import its whole project model or page-composition flow: it targets
page comics and a provider-neutral, multi-host workflow. For this project,
keep the vertical-scroll episode model, Korean lettering contract, and existing
approval gates. Before borrowing implementation detail, read Comic Sol's MIT
license and preserve the required attribution if any source code is copied.

As of 2026-09-04, its two public forks (`weanzme-a11y/comicsol` and
`gentosai404/comicsol`) contain no fork-only commits and trail the canonical
repository, so neither is an alternate implementation to adopt.

## Sources

- Totus, [웹툰 식자 가이드](https://guide.totus.pro/0c91fe75-a5be-42d6-8bac-dcc89279389d): text-first construction, approximately two-glyph clearance, centered text, mouth-directed tails, and clear-background placement.
- Clip Studio TIPS, [Letter Your Webtoon Like a Pro](https://tips.clip-studio.com/en-us/articles/3751): phone-width review, diamond text blocks, reading order, and avoiding tail crossings or dialogue walls.
- Evan Waterman, [General Tips](https://evanjwaterman.com/guide/lettering/general-tips/): consistent negative space, tail width and length, and typography consistency.
- Blambot, [Comic Book Grammar & Tradition](https://blambot.com/pages/comic-book-grammar-tradition): tail distance, thought-dot direction, and semantic balloon variants.
