---
name: webtoon-showrunner
description: Orchestrates an end-to-end vertical-scroll webtoon project in this repository, from story/visual bibles through episode script, scroll plan, shot briefs, rendering, assembly, and QC. Use when the user asks what to do next, wants to make a webtoon conversationally, or requests work spanning multiple production stages.
---

# Webtoon Showrunner

Coordinate the project without collapsing all stages into one opaque prompt.

## Workflow

1. Read `AGENTS.md`, `config/project.json`, and existing canonical artifacts.
2. Run `python tools/check_state.py <project-root>` to identify the earliest missing or stale stage.
3. State which artifact will be created or revised and which upstream artifacts constrain it.
4. Follow the matching focused skill:
   - premise/world/characters: `story-bible-builder`
   - character/background reference assets: `reference-sheet-builder`
   - episode drama/dialogue: `episode-script-writer`
   - scroll plan or shot briefs: `scroll-director`
   - image task compilation: `brief-to-image-prompt`
   - assembly/review: `continuity-qc`
5. Validate every artifact before presenting it for approval.
6. Never call paid image generation merely because a task compiled. Require the user to explicitly approve execution.
7. Record approval with `python tools/approve_stage.py ...` so it contains the current input fingerprint.

## Conversation behavior

- Present story choices in ordinary language, then encode the chosen result in JSON.
- When a choice materially changes genre, ending, audience, or visual identity, ask before locking it.
- For local details, make a reasonable draft and label it as a draft.
- Report the next concrete decision after each completed stage.

## Completion gates

- Bible gate: story bible and each active visual asset validate.
- Script gate: all beat references and character/location IDs resolve.
- Direction gate: every scroll-plan shot has one valid director brief.
- Render gate: source hashes match and reference files exist.
- Delivery gate: master and slices pass technical QC; visual/continuity concerns are listed for human review.
