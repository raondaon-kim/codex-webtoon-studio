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
5. Validate against `schemas/v1/scroll-plan.schema.json`.

## Director brief

For every shot:

1. State the dramatic purpose before visual decoration.
2. Choose `camera.shot_size`, angle, lens feel, position, movement, and focus.
3. Give every visible character a normalized `bbox_norm`, depth, pose, expression, gaze, action, and identity invariants.
4. Specify the environment reference and `background.source_crop_norm`; describe foreground, midground, and background depth layers.
5. Reserve clean normalized regions for balloons/captions. Avoid placing faces, hands, or essential props there.
6. Track screen direction and explicit state in/out.
7. Select a generation canvas within GPT Image 2 limits. Prefer a normal shot block such as `1536x2048`; use larger dimensions only when composition needs them.
8. Validate all briefs, including custom geometry checks.

```powershell
python tools/validate_artifacts.py episodes/<episode-id>/scroll-plan.json episodes/<episode-id>/briefs
```

Do not write the final model prompt here. The `brief-to-image-prompt` skill owns that transformation.
