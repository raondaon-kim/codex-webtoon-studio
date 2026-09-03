---
name: episode-script-writer
description: Writes or revises a single webtoon episode script as dramatic beats with action, emotion, dialogue, captions, thoughts, SFX, continuity input/output, and a cliffhanger. Use when the user wants an episode outline, script, dialogue pass, or adaptation of a chapter into an episode.
---

# Episode Script Writer

Produce `episodes/<episode-id>/script.json` conforming to `schemas/v1/episode-script.schema.json`.

## Procedure

1. Read the approved story bible, previous episode continuity output, and requested source span.
2. Define the episode change: starting state, escalation, irreversible turn, and final hook.
3. Break the episode into stable `beat-NNN` units. Each beat must have one dramatic purpose.
4. Write action that can be shown. Put inner explanation into sparing thought/caption items.
5. Match each speaker's voice rules and keep dialogue short enough for mobile balloons.
6. Keep speech order unambiguous. Record critical props, injuries, outfits, knowledge, and positions in continuity output.
7. Validate the result.

## Webtoon constraints

- Do not decide exact camera framing here; that belongs to the director brief.
- Use silence as a beat when scroll distance or reaction carries meaning.
- Treat SFX as script content, but let the director decide whether it is generated or lettered.

## Handoff

Pass the approved script to `scroll-director`.
