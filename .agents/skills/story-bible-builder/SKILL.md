---
name: story-bible-builder
description: Creates or revises a webtoon story bible with premise, world rules, character arcs, voices, identity locks, episode engine, and continuity rules. Use when developing a new series concept, adapting source material, or changing foundational story canon.
---

# Story Bible Builder

Produce `story-bible/story-bible.json` conforming to `schemas/v1/story-bible.schema.json`.

## Procedure

1. Read material under `source/` and any existing bible.
2. Separate user-provided canon from proposed connective material.
3. Define the series promise, central question, themes, world rules, and repeatable episode engine.
4. Give every recurring character a stable ID, starting age, dramatic want/need/conflict, dialogue voice, growth arc, and visual `identity_lock`.
5. Add a `timeline` with `calendar_continuous` aging and season/arc milestones. Record the changing ages of all protagonists who grow across the series.
6. Phrase identity locks as observable features: silhouette, face, hair, body, palette, signature items; account for age-specific changes rather than freezing child designs forever.
7. Add continuity rules that later writers and image prompts can test.
7. Save valid UTF-8 JSON and run:

```powershell
python tools/validate_artifacts.py <path-to-story-bible.json>
```

## Temporal continuity

- Never treat a child protagonist's age as static when calendar time passes.
- A time skip must update every tracked character's age, social role, body proportions, costume fit, skills, and relationships as appropriate.
- Use milestones to distinguish the roles of siblings or peers instead of making one character solve every kind of problem.

## Adaptation rules

- Preserve source facts unless the user authorizes a change.
- Track gaps and contradictions instead of silently resolving major canon conflicts.
- Keep scene prose out of the bible; store reusable constraints and series-level logic.

## Handoff

After approval, use `reference-sheet-builder` for visual canon and `episode-script-writer` for a specific episode.
