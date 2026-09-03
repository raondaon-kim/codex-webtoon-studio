---
name: continuity-qc
description: Reviews and verifies a webtoon episode after briefs or image generation, including artifact validity, shot continuity, image dimensions, missing files, character/reference consistency, lettering regions, vertical assembly, and publish slices. Use for QC, continuity review, episode assembly, or release readiness.
---

# Continuity QC

Perform deterministic checks first, then a visual review.

## Technical pass

1. Validate all JSON artifacts.
2. Confirm each planned shot has a brief, render task, and generated file where required.
3. Verify render task `source_hash` still matches its brief.
4. Check image dimensions, aspect, format, sequence order, master width, and publish slice limits.
5. Confirm text items fit reserved regions and no required dialogue is missing.
6. Run assembly and QC:

```powershell
python tools/compose_episode.py episodes/<episode-id> --project-root <project-root>
python tools/qc_episode.py episodes/<episode-id> --project-root <project-root>
```

## Visual pass

Review in scroll order, not as isolated images:

- character face, hair, body proportions, outfit, and signature items
- left/right screen direction and gaze/action match
- background geography and crop plausibility
- scale and distance implied by bbox and shot size
- emotional beat clarity and scroll reveal timing
- balloon reading order, contrast, margins, and face/hand occlusion
- accidental text, watermarks, duplicate limbs/characters, or continuity drift

Record every issue with severity, code, shot ID, and an actionable fix. A technical pass does not replace human visual approval.
