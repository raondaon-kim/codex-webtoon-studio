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
4. Give every recurring character a stable ID, dramatic want/need/conflict, dialogue voice, and visual `identity_lock`.
5. Phrase identity locks as observable features: silhouette, face, hair, body, palette, signature items.
6. Add continuity rules that later writers and image prompts can test.
7. Save valid UTF-8 JSON and run:

```powershell
python tools/validate_artifacts.py <path-to-story-bible.json>
```

## Adaptation rules

- Preserve source facts unless the user authorizes a change.
- Track gaps and contradictions instead of silently resolving major canon conflicts.
- Keep scene prose out of the bible; store reusable constraints and series-level logic.

## Handoff

After approval, use `reference-sheet-builder` for visual canon and `episode-script-writer` for a specific episode.
