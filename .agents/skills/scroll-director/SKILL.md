---
name: scroll-director
description: Converts an episode script into a vertical-scroll rhythm plan and shot-level director briefs with shot size, camera geometry, normalized character bounding boxes, background crop, continuity, and lettering-safe regions. Use when directing panels, planning scroll pacing, or specifying spatial composition.
---

# Scroll Director

Create `scroll-plan.json` and one `briefs/shot-NNN.json` per planned shot.

## Scroll plan

1. Group beats into reveal sequences.
2. Choose rhythm per sequence: compressed, normal, expanded, or splash.
3. Use whitespace deliberately for pause, anticipation, location change, or impact.
4. Keep each shot ID stable and list it exactly once.
5. For every new or revised sequence, add one `bridge_inserts` item. Its `shot_id` is an extra generated bridge image placed after its declared `after_shot_id`; it is never two or three independently generated shots.
6. Validate against `schemas/v1/scroll-plan.schema.json`.

## Director brief

For every shot:

1. State the dramatic purpose before visual decoration.
2. Choose `camera.shot_size`, angle, lens feel, position, movement, and focus.
3. Give every visible character a normalized `bbox_norm`, depth, pose, expression, gaze, action, and identity invariants.
4. Specify the environment reference and `background.source_crop_norm`; describe foreground, midground, and background depth layers.
5. Reserve clean normalized regions for balloons/captions. Avoid placing faces, hands, or essential props there. For dialogue and thought balloons, set `tail_target_norm` to the intended speaker or thinker; captions and SFX do not need a tail.
6. Track screen direction and explicit state in/out.
7. Select a generation canvas within GPT Image 2 limits. Prefer a normal shot block such as `1536x2048`; use larger dimensions only when composition needs them.
8. Validate all briefs, including custom geometry checks.

## Bridge composites

Use a bridge composite to make a transition feel continuous without increasing image-generation count.

- Set `bridge.panel_count` to exactly `2` or `3` and `bridge.layout` to `vertical_stack`. Its one source image uses the matching tall canvas: width:height is exactly `1:panel_count` (for example, `1536x3072` for two panels or `1280x3840` for three); it is not constrained to the ordinary `3:4` shot block.
- Describe a distinct, causally connected micro-beat for each panel in `bridge.panel_beats`, ordered top-to-bottom. Suitable functions are action continuation, reaction, time/location transition, observation, or emotional breath.
- Keep the same spatial logic, character identity, and screen direction across the mini-panels. Use clean gutters; do not make a collage of alternative poses or repeat the same beat.
- The bridge insert is separate from the sequence's regular `shot_ids`, preserving the existing primary-shot continuity chain. Do not create a separate render task for each mini-panel.

```powershell
python tools/validate_artifacts.py episodes/<episode-id>/scroll-plan.json episodes/<episode-id>/briefs
```

Do not write the final model prompt here. The `brief-to-image-prompt` skill owns that transformation.

## Deterministic lettering

- Keep generated art free of text. Put final Korean copy in `text.items`; the compositor renders it after image generation.
- Use `dialogue` for a white balloon with a speaker tail, `thought` for a cloud-like balloon with a dot tail, `caption` for a dark narration box, and `sfx` for outlined text without a balloon.
- Read each scroll block top-to-bottom. When two speakers share a height, order their balloons by the actual turn and keep tails unambiguous.
